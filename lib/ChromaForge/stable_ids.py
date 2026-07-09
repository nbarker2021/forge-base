"""Content-addressed stable IDs for ChromaForge — no uuid4 identity churn."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional


def _canon(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def grain_id_for(glyph: str, e8_coords: List[float], position: int = 0) -> str:
    e8 = [round(float(c), 8) for c in (e8_coords or [])[:8]]
    return "gr-" + hashlib.sha256(_canon({"glyph": glyph, "e8": e8, "pos": position}).encode()).hexdigest()[:8]


def grain_id_for_content(content: str, position: int = 0) -> str:
    """Alias aligned with create_grain e6 signature prefix."""
    sig = hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()[:32]
    return f"gr-{sig[:8]}"


def wall_id_for(wall_type: str, content: str, grains: List[str]) -> str:
    body = _canon({"type": wall_type, "content": content, "grains": sorted(grains)})
    return "wall-" + hashlib.sha256(body.encode()).hexdigest()[:8]


def tarpit_session_id(content: str, derivation_key: str) -> str:
    body = _canon({"content": content[:500], "derivation": derivation_key})
    return "sess-" + hashlib.sha256(body.encode()).hexdigest()[:8]


def snap_record_id(
    kind: str,
    member_ids: List[str],
    predicate_names: List[str],
    delta_u: float = 0.0,
    payload: Optional[Dict[str, Any]] = None,
) -> str:
    body = _canon({
        "kind": kind,
        "members": sorted(member_ids),
        "predicates": sorted(predicate_names),
        "delta_u": round(float(delta_u), 8),
        "payload": payload or {},
    })
    return hashlib.sha256(body.encode()).hexdigest()[:12]


def mdhg_session_id(name: Optional[str] = None, seed_content: str = "") -> str:
    key = (name or "").strip() or (seed_content or "").strip() or "mdhg-root"
    return "mdhg-" + hashlib.sha256(key.encode()).hexdigest()[:12]


def ecology_receipt_id(
    survivor_ids: List[str],
    absorbed_ids: List[str],
    mass_before: float,
    mass_after: float,
) -> str:
    body = _canon({
        "survivors": sorted(survivor_ids),
        "absorbed": sorted(absorbed_ids),
        "mass_before": round(float(mass_before), 6),
        "mass_after": round(float(mass_after), 6),
    })
    return "eco-" + hashlib.sha256(body.encode()).hexdigest()[:12]


def mmdb_crystal_id(content: str, snap_labels: Optional[List[str]] = None, mdhg_address: str = "") -> str:
    body = _canon({
        "content": content,
        "labels": sorted(set(snap_labels or [])),
        "mdhg": mdhg_address or "",
    })
    return hashlib.sha256(body.encode()).hexdigest()
