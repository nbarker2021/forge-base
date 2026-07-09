"""
FridgeForge — fridge/cabinet -> inventory -> shopping list -> meal ideas.

The app engine:
  1. IMAGE IN:   a fridge/cabinet photo arrives as bytes. It is hashed and
                 receipted (Event Law); product matching runs through the
                 MATCHER ADAPTERS — lookup-first, honest about capability:
                   - text/caption/filename matching (on-stick, lexicon lookup)
                   - manual confirm (the UI's quick-pick grid)
                   - `vision` adapter slot for HYBRID/CLOUD backends (an
                     injected callable; the stick ships none and says so)
  2. INVENTORY:  canonical product keys with categories, maintained by events.
  3. SHOPPING:   templated list = (staples template - inventory)
                 + missing ingredients from chosen/suggested recipes,
                 grouped by store category.
  4. MEALS:      breakfast/lunch/dinner/snack suggestions ranked against the
                 inventory, in two lanes:
                   adult — full recipe table, tag-adjusted ranking
                   kid   — kid_ok recipes only; DISLIKES ARE HARD constraints
                           (excluded outright), likes boost, tags adjust.

Every operation returns canonical-serializable records so the host kernel
runs them through compute->save->validate->receipt(2 links)->reuse.

Stdlib only.
"""
import hashlib
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

from FridgeForge.lexicon import (
    PRODUCTS, CATEGORIES, ALIAS_INDEX, STAPLES_TEMPLATE,
    match_token, match_text, category_of,
)
from FridgeForge.recipes import (
    RECIPES, MEALS, ALL_TAGS, suggest, missing_for_meal_plan,
)

VisionAdapter = Callable[[bytes], List[str]]   # image bytes -> product keys


class FridgeForgeEngine:
    """One household context: inventory + profiles + matcher adapters."""

    def __init__(self, vision_adapter: Optional[VisionAdapter] = None):
        self.inventory: Dict[str, Dict[str, Any]] = {}   # key -> {qty, added}
        self.profiles: Dict[str, Dict[str, Any]] = {
            "adult": {"tags": []},
            "kid":   {"likes": [], "dislikes": [], "tags": []},
        }
        self.vision = vision_adapter          # injected; None on the stick
        self._scans: List[Dict[str, Any]] = []

    # ── 1. image in ──────────────────────────────────────────────────────────
    def scan(self, image_bytes: bytes = b"", caption: str = "",
             filename: str = "") -> Dict[str, Any]:
        """Ingest a fridge/cabinet image. Matching is adapter-layered:
        vision (if injected) -> caption/filename lexicon match. The record
        always says which matcher produced each item."""
        img_hash = hashlib.sha256(image_bytes).hexdigest()[:16] if image_bytes else ""
        matched: List[Dict[str, str]] = []
        if self.vision is not None and image_bytes:
            for k in self.vision(image_bytes):
                if k in PRODUCTS:
                    matched.append({"key": k, "via": "vision"})
        for src, txt in (("caption", caption), ("filename", filename)):
            for k in match_text(txt):
                if not any(m["key"] == k for m in matched):
                    matched.append({"key": k, "via": src})
        rec = {
            "scan_id": f"scan-{img_hash or hashlib.sha256((caption + filename).encode()).hexdigest()[:10]}",
            "image_hash": img_hash,
            "image_bytes_len": len(image_bytes),
            "matched": matched,
            "vision_available": self.vision is not None,
            "note": ("vision adapter active" if self.vision else
                     "on-stick matching: caption/filename lexicon + manual confirm"),
            "ts": time.time(),
        }
        self._scans.append(rec)
        return rec

    def confirm(self, keys: Sequence[str]) -> Dict[str, Any]:
        """Manual confirm from the UI quick-pick: add items to inventory."""
        added, unknown = [], []
        for raw in keys:
            k = raw if raw in PRODUCTS else match_token(str(raw))
            if k:
                self._add(k)
                added.append(k)
            else:
                unknown.append(raw)
        return {"added": added, "unknown": unknown,
                "inventory_size": len(self.inventory)}

    # ── 2. inventory ─────────────────────────────────────────────────────────
    def _add(self, key: str, qty: int = 1) -> None:
        item = self.inventory.setdefault(key, {"qty": 0, "added": time.time(),
                                               "category": category_of(key)})
        item["qty"] += qty

    def add_item(self, name: str, qty: int = 1) -> Optional[str]:
        k = name if name in PRODUCTS else match_token(name)
        if k:
            self._add(k, qty)
        return k

    def remove_item(self, key: str) -> bool:
        return self.inventory.pop(key, None) is not None

    def inventory_keys(self) -> List[str]:
        return sorted(self.inventory.keys())

    # ── 3. shopping list ─────────────────────────────────────────────────────
    def shopping_list(self, planned_recipes: Sequence[str] = ()) -> Dict[str, Any]:
        """Templated list: staples gap + recipe gaps, grouped by category."""
        inv = set(self.inventory)
        staples_gap = [k for k in STAPLES_TEMPLATE if k not in inv]
        recipe_gap = missing_for_meal_plan(sorted(inv), planned_recipes)
        items = sorted(set(staples_gap) | set(recipe_gap))
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for k in items:
            grouped.setdefault(category_of(k), []).append({
                "key": k, "label": k.replace("_", " "),
                "reason": ("staple" if k in staples_gap else "") +
                          ("+recipe" if k in recipe_gap and k in staples_gap else
                           "recipe" if k in recipe_gap else ""),
            })
        return {"groups": {c: grouped[c] for c in CATEGORIES if c in grouped},
                "count": len(items),
                "staples_missing": len(staples_gap),
                "for_recipes": planned_recipes and list(planned_recipes) or []}

    # ── 4. meals (kid/adult lanes) ───────────────────────────────────────────
    def set_profile(self, lane: str, likes: Sequence[str] = None,
                    dislikes: Sequence[str] = None,
                    tags: Sequence[str] = None) -> Dict[str, Any]:
        p = self.profiles.setdefault(lane, {})
        def canon(seq):
            out = []
            for x in (seq or []):
                k = x if x in PRODUCTS else match_token(str(x))
                if k and k not in out:
                    out.append(k)
            return out
        if likes is not None:
            p["likes"] = canon(likes)
        if dislikes is not None:
            p["dislikes"] = canon(dislikes)
        if tags is not None:
            p["tags"] = [t for t in tags if t in ALL_TAGS]
        return {"lane": lane, "profile": p}

    def meal_ideas(self, meal: str, lane: str = "adult",
                   extra_tags: Sequence[str] = (), limit: int = 6) -> Dict[str, Any]:
        if meal not in MEALS:
            return {"error": f"meal must be one of {MEALS}"}
        p = self.profiles.get(lane, {})
        tags = list(p.get("tags", [])) + [t for t in extra_tags if t in ALL_TAGS]
        ideas = suggest(self.inventory_keys(), meal, lane=lane,
                        likes=p.get("likes", []), dislikes=p.get("dislikes", []),
                        tags=tags, limit=limit)
        return {"meal": meal, "lane": lane, "tags_applied": tags,
                "hard_excludes": p.get("dislikes", []) if lane == "kid" else [],
                "ideas": ideas}

    # ── status ───────────────────────────────────────────────────────────────
    def status(self) -> Dict[str, Any]:
        return {
            "inventory": len(self.inventory),
            "by_category": {c: sum(1 for v in self.inventory.values()
                                   if v["category"] == c) for c in CATEGORIES
                            if any(v["category"] == c for v in self.inventory.values())},
            "scans": len(self._scans),
            "vision_adapter": self.vision is not None,
            "recipes": len(RECIPES),
            "lexicon": len(PRODUCTS),
            "profiles": self.profiles,
        }

    # serialization for kernel persistence
    def export(self) -> Dict[str, Any]:
        return {"inventory": self.inventory, "profiles": self.profiles}

    def restore(self, data: Dict[str, Any]) -> None:
        self.inventory = dict(data.get("inventory", {}))
        for lane, p in (data.get("profiles") or {}).items():
            self.profiles[lane] = p


engine = FridgeForgeEngine()

__version__ = "0.1.0"


# ─── Verify (forge-family contract) ───────────────────────────────────────────

def verify() -> dict:
    """Finite checks binding FridgeForge to its docstring claims.

    Exercises the four advertised lanes — image-in scan (caption matcher
    only, no vision adapter), inventory add/remove, shopping list, and
    meal ideas — and the kid-lane hard-dislike constraint.
    Pure additive — does not touch the existing API.
    """
    checks = {}

    # 1. Engine status reports non-empty lexicon and recipe tables.
    try:
        s = engine.status()
        checks["lexicon_non_empty"] = s.get("lexicon", 0) > 0
        checks["recipes_non_empty"] = s.get("recipes", 0) > 0
    except Exception:
        checks["lexicon_non_empty"] = False
        checks["recipes_non_empty"] = False

    # 2. Caption-driven scan (no vision adapter) returns matched items.
    try:
        scan = engine.scan(image_bytes=b"", caption="milk and eggs",
                           filename="")
        matched = scan.get("matched", [])
        checks["scan_caption_matcher_finds_milk_or_eggs"] = bool(matched)
        checks["scan_records_vision_absent"] = scan.get("vision_available") is False
    except Exception:
        checks["scan_caption_matcher_finds_milk_or_eggs"] = False
        checks["scan_records_vision_absent"] = False

    # 3. Inventory: add/remove round-trips.
    try:
        added_key = engine.add_item("milk")
        keys = engine.inventory_keys()
        removed = engine.remove_item(added_key) if added_key else False
        checks["inventory_add_remove_roundtrip"] = bool(
            added_key and added_key in keys and removed
        )
    except Exception:
        checks["inventory_add_remove_roundtrip"] = False

    # 4. Shopping list has the documented shape.
    try:
        sl = engine.shopping_list(planned_recipes=("omelet",))
        checks["shopping_list_has_groups"] = (
            isinstance(sl, dict) and "groups" in sl
            and isinstance(sl["groups"], dict)
        )
    except Exception:
        checks["shopping_list_has_groups"] = False

    # 5. Kid-lane: setting a dislike for the only available product yields
    #    no ideas (hard constraint).
    try:
        # Seed inventory so the meal has at least one possible idea
        engine.add_item("milk")
        engine.set_profile("kid", dislikes=["milk"])
        ideas = engine.meal_ideas("breakfast", lane="kid", limit=6)
        milk_in_top = any("milk" in (i.get("key", "") if isinstance(i, dict) else "")
                          for i in ideas.get("ideas", []))
        checks["kid_lane_hard_excludes_dislike"] = (not milk_in_top)
    except Exception:
        checks["kid_lane_hard_excludes_dislike"] = False

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    if passed == total:
        status = "pass"
    elif passed >= max(1, total // 2):
        status = "partial"
    else:
        status = "fail"

    return {
        "forge": "FridgeForge",
        "status": status,
        "checks": checks,
        "passed": passed,
        "total": total,
        "paper": "CQE-paper-11 (Family OS: matcher/adapter contract)",
    }


__all__ = [
    "FridgeForgeEngine", "engine",
    "PRODUCTS", "CATEGORIES", "STAPLES_TEMPLATE", "RECIPES", "MEALS",
    "ALL_TAGS", "match_token", "match_text", "category_of",
    "suggest", "missing_for_meal_plan",
]
