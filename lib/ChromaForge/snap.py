"""
ChromaForge SNAP — Gate369 + Lenses + Taxonomy + Stratifier.

SNAP stratifies, not labels. Every concept exploded into all presentations,
meanings, connections, fictions, non-standard interpretations — recursively
until convergence (no new labels at this depth).

Gate369:
  Triad  (Gate 3) — pick 3 best bodies by lens-scored predicate
  Hexad  (Gate 6) — find polarity invariants across record pairs
  Ennead (Gate 9) — resolve into containment-stable 9-body package

Lenses: BaseLens, LegalityLens, NoveltyLens, SymmetryLens
Stratifier: recursive 8-angle questionnaire until convergence

Design: SNAPEngine is a class. Module-level singleton `engine` + helpers available.
"""
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# ─── Lookup tables (import-time, read-only) ────────────────────────────────────

# The 8 stratification angles — fixed vocabulary, computed once
ANGLES: Tuple[Tuple[str, str], ...] = (
    ("what",     "Define {seed}: components, properties, boundaries, forms"),
    ("how",      "How {seed} works: mechanism, process, steps"),
    ("why",      "Why {seed} matters: dependencies, what breaks without it"),
    ("connects", "What {seed} connects to: related concepts, adjacent ideas"),
    ("formal",   "Formal structure: equations, rules, invariants, types"),
    ("breaks",   "Limitations: edge cases, paradoxes, alternatives"),
    ("analogy",  "Analogies: other domains, other scales, fiction, nature"),
    ("builds",   "What to build from {seed}: applications, extensions, derivatives"),
)

# Angle name → template (lookup, not search)
_ANGLE_MAP: Dict[str, str] = dict(ANGLES)

# Core taxonomy families — the default label classification frame
_DEFAULT_FAMILIES: Tuple[str, ...] = (
    "domain", "op", "formal", "meta", "type", "keyword", "touch",
    "role", "composite", "family", "literal", "sci", "effect",
    "xform", "intent", "action", "dr", "notation", "proof",
)


# ─── Core data types ──────────────────────────────────────────────────────────

@dataclass
class Predicate:
    name: str
    cost: float = 1.0
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Body:
    id: str
    features: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SNAPRecord:
    record_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    kind: str = "generic"
    ts: float = field(default_factory=time.time)
    members: List[Body] = field(default_factory=list)
    predicates: List[Predicate] = field(default_factory=list)
    delta_u: float = 0.0
    polarity_conflict: float = 0.0
    payload: Dict[str, Any] = field(default_factory=dict)

    def hash(self) -> str:
        return hashlib.sha256(
            json.dumps({"id": self.record_id, "kind": self.kind, "ts": self.ts},
                       sort_keys=True).encode()
        ).hexdigest()[:16]


@dataclass
class HexadInvariant:
    pos: Body
    neg: Body
    invariant: str
    margin: float


@dataclass
class EnneadPackage:
    facets: List[Body]
    lens_name: str
    mirror_pass: bool
    containment_c: float
    delta_u: float
    reversibility: bool


# ─── Lenses ───────────────────────────────────────────────────────────────────

class BaseLens:
    name = "base"

    def evaluate(self, state: Dict) -> str:
        if not state.get("mirror_pass", False):
            return "refine"
        if state.get("polarity_conflict", 1.0) > state.get("polarity_thresh", 0.2):
            return "refine"
        if state.get("containment_c", 0.0) < state.get("c_thresh", 0.7):
            return "refine"
        return "pass"

    def score_reward(self, before: Dict, after: Dict) -> float:
        return (after.get("delta_u", 0.0) - before.get("delta_u", 0.0)
                - 0.1 * after.get("edbsu_growth", 0.0))

    def pick_predicate(self, candidates: List[Predicate], state: Dict) -> Predicate:
        return sorted(candidates,
                      key=lambda p: -(p.meta.get("expected_du", 0.0) / max(p.cost, 1e-6)))[0]


class LegalityLens(BaseLens):
    name = "legality"

    def evaluate(self, state: Dict) -> str:
        if state.get("violates_policy", False):
            return "fail"
        return super().evaluate(state)


class NoveltyLens(BaseLens):
    name = "novelty"

    def score_reward(self, before: Dict, after: Dict) -> float:
        return super().score_reward(before, after) + 0.2 * after.get("novelty", 0.0)


class SymmetryLens(BaseLens):
    name = "symmetry"

    def score_reward(self, before: Dict, after: Dict) -> float:
        return super().score_reward(before, after) + 0.15 * after.get("symmetry_score", 0.0)


class LensBank:
    """Registry of available lenses. Injectable into Gate369Engine."""

    def __init__(self):
        self._lenses: Dict[str, BaseLens] = {}
        for lens in [BaseLens(), LegalityLens(), NoveltyLens(), SymmetryLens()]:
            self._lenses[lens.name] = lens

    def get(self, name: str) -> Optional[BaseLens]:
        return self._lenses.get(name)

    def add(self, lens: BaseLens) -> None:
        self._lenses[lens.name] = lens

    def best_lens(self, state: Dict) -> BaseLens:
        for lens in self._lenses.values():
            if lens.evaluate(state) == "pass":
                return lens
        return self._lenses["base"]

    def evaluate_all(self, state: Dict) -> Dict[str, str]:
        return {n: l.evaluate(state) for n, l in self._lenses.items()}

    @property
    def names(self) -> List[str]:
        return list(self._lenses.keys())


# ─── Gate369 — pure selection logic ──────────────────────────────────────────

class Gate369:
    """3-6-9 selection. Stateless except for history log."""

    def __init__(self, lens_bank: Optional[LensBank] = None):
        self.lens_bank: LensBank = lens_bank or LensBank()
        self._history: List[Dict] = []

    def triad(self, bodies: List[Body], predicates: List[Predicate],
              state: Dict) -> SNAPRecord:
        lens = self.lens_bank.best_lens(state)
        du_sum = sum(p.meta.get("expected_du", 0.0) for p in predicates)
        scored = [(b, lens.score_reward({}, {"delta_u": du_sum})) for b in bodies]
        top3 = [b for b, _ in sorted(scored, key=lambda x: -x[1])[:3]]
        return SNAPRecord(kind="triad", members=top3, predicates=predicates,
                          delta_u=sum(s for _, s in scored[:3]))

    def hexad(self, records: List[SNAPRecord]) -> List[HexadInvariant]:
        invariants = []
        for i in range(0, len(records) - 1, 2):
            a, b = records[i], records[i + 1]
            if a.members and b.members:
                invariants.append(HexadInvariant(
                    pos=a.members[0], neg=b.members[0],
                    invariant=f"{a.kind}↔{b.kind}",
                    margin=abs(a.delta_u - b.delta_u),
                ))
        return invariants

    def ennead(self, records: List[SNAPRecord],
               lens_name: str = "base") -> EnneadPackage:
        all_bodies = [b for r in records for b in r.members][:9]
        lens = self.lens_bank.get(lens_name) or self.lens_bank.get("base")
        delta_us = [r.delta_u for r in records] if records else [0.0]
        mean_du = sum(delta_us) / len(delta_us)
        variance = sum((d - mean_du) ** 2 for d in delta_us) / max(len(delta_us), 1)
        polarity_conflict = min(variance / max(abs(mean_du) + 1e-9, 1.0), 1.0)
        conflict_free = sum(1 for r in records if r.polarity_conflict == 0)
        containment_c = conflict_free / max(len(records), 1)
        state = {
            "mirror_pass": polarity_conflict > 0.3,
            "polarity_conflict": polarity_conflict,
            "containment_c": containment_c,
        }
        result = lens.evaluate(state)
        return EnneadPackage(
            facets=all_bodies, lens_name=lens_name,
            mirror_pass=state["mirror_pass"], containment_c=containment_c,
            delta_u=sum(delta_us), reversibility=(result == "pass"),
        )

    def process(self, bodies: List[Body], predicates: List[Predicate],
                state: Dict = None) -> Dict:
        """Full 3-6-9 sequence. Minimum 3 bodies required."""
        state = state or {}
        if len(bodies) < 3:
            raise ValueError("Gate369 needs at least 3 bodies")

        triad = self.triad(bodies, predicates, state)
        self._history.append({"gate": 3, "members": len(triad.members)})

        remaining = [b for b in bodies if b not in triad.members]
        triads = [triad] + ([self.triad(remaining, predicates, state)] if remaining else [])

        invariants = self.hexad(triads)
        self._history.append({"gate": 6, "invariants": len(invariants)})

        ennead = self.ennead(triads)
        crystallized = ennead.containment_c > 0.7
        self._history.append({"gate": 9, "facets": len(ennead.facets),
                              "crystallized": crystallized})

        return {
            "triad":  {"members": [b.id for b in triad.members], "delta_u": triad.delta_u},
            "hexad":  [{"pos": i.pos.id, "neg": i.neg.id, "margin": i.margin}
                       for i in invariants],
            "ennead": {"facets": len(ennead.facets), "containment_c": ennead.containment_c,
                       "reversible": ennead.reversibility, "crystallized": crystallized},
        }


# ─── Engine class ──────────────────────────────────────────────────────────────

class SNAPEngine:
    """Gate369 + Taxonomy + Stratifier. One instance = one label namespace."""

    def __init__(self, lens_bank: Optional[LensBank] = None):
        self._gate = Gate369(lens_bank=lens_bank or LensBank())
        self._families: Dict[str, Dict] = {}
        self._types: Dict[str, Dict] = {}
        # Pre-register default families from lookup table
        for fam in _DEFAULT_FAMILIES:
            self._families[fam] = {"meta": {}, "types": []}

    # ── Gate369 ────────────────────────────────────────────────────────────────

    def gate369(self, bodies_raw: List[Dict], predicates_raw: List[Dict] = None,
                state: Dict = None) -> Dict:
        """Convenience wrapper: accept plain dicts, run Gate369."""
        bodies = [Body(id=b.get("id", str(i)), features=b.get("features", {}))
                  for i, b in enumerate(bodies_raw)]
        predicates = [Predicate(name=p.get("name", str(i)), cost=p.get("cost", 1.0),
                                meta=p.get("meta", {}))
                      for i, p in enumerate(predicates_raw or [])]
        return self._gate.process(bodies, predicates, state or {})

    def evaluate_lenses(self, state: Dict) -> Dict[str, str]:
        return self._gate.lens_bank.evaluate_all(state)

    # ── Stratifier ─────────────────────────────────────────────────────────────

    def stratify(
        self,
        seed: str,
        max_depth: int = 3,
        existing_labels: Set[str] = None,
        label_fn: Optional[Callable[[str], List[str]]] = None,
    ) -> Dict:
        """Recursively expand a concept via 8 angles until convergence."""
        existing = set(existing_labels or [])
        levels = []
        current_seeds = [seed]

        for depth in range(max_depth):
            new_labels: Set[str] = set()
            level_results = []

            for s in current_seeds[:5]:
                for angle_name, template in ANGLES:
                    text = template.replace("{seed}", s)
                    if label_fn is not None:
                        try:
                            labels = set(label_fn(text))
                        except Exception:
                            labels = set()
                    else:
                        labels = {f"{angle_name}:{s}"}

                    discoveries = labels - existing
                    new_labels.update(discoveries)
                    existing.update(labels)
                    level_results.append({
                        "seed": s, "angle": angle_name,
                        "labels": len(labels), "discoveries": len(discoveries),
                    })

            levels.append({
                "depth": depth, "seeds": len(current_seeds),
                "new_labels": len(new_labels), "total_labels": len(existing),
                "results": level_results[:10],
            })

            if not new_labels:
                break
            current_seeds = list(new_labels)[:10]

        return {
            "seed": seed,
            "depths_explored": len(levels),
            "converged": len(levels) < max_depth or (levels and levels[-1]["new_labels"] == 0),
            "total_labels": len(existing),
            "levels": levels,
        }

    # ── Taxonomy ───────────────────────────────────────────────────────────────

    def register_family(self, name: str, meta: Dict = None) -> None:
        self._families[name] = {"meta": meta or {}, "types": []}

    def register_type(self, name: str, families: List[str],
                      meta: Dict = None) -> None:
        for f in families:
            if f not in self._families:
                self.register_family(f)
            self._families[f]["types"].append(name)
        self._types[name] = {"families": families, "meta": meta or {}}

    def taxonomy(self) -> Dict:
        return {"families": dict(self._families), "types": dict(self._types)}

    def angles(self) -> List[Dict]:
        return [{"name": a[0], "template": a[1]} for a in ANGLES]

    @property
    def family_count(self) -> int:
        return len(self._families)


# ─── Module-level singleton + forwarding ──────────────────────────────────────

engine = SNAPEngine()

def gate369(bodies_raw: List[Dict], predicates_raw: List[Dict] = None,
            state: Dict = None) -> Dict:
    return engine.gate369(bodies_raw, predicates_raw, state)

def stratify(seed: str, max_depth: int = 3, existing_labels: Set[str] = None,
             label_fn: Optional[Callable] = None) -> Dict:
    return engine.stratify(seed, max_depth, existing_labels, label_fn)

def taxonomy() -> Dict:
    return engine.taxonomy()
