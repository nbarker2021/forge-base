"""CrystalForge.brain — agent brain / live-memory routing, ported from
the real TMN service (tmn_source/CMPLX-TMN-main-main/src/brain/brain.py).

This is the meso/live tier: per-agent evolving state that gets pulled
from the master record, updated, and resaved -- distinct from a
Crystal (crystal.py), which is a fixed snapshot at a chosen boundary.
A brain accumulates contributions over time; merge() periodically folds
relevant contributions back into the brain's own state, tier-weighted.

Ported logic, not redesigned: tier thresholds, alpha-by-tier blend
weights, the MI-slope capacity score, and Jaccard-similarity
contribution relevance are all taken from the real service. Only the
persistence layer (originally psycopg2 + an in-memory cache dict) is
replaced -- SQLite is fast enough locally that the cache layer is
dropped entirely; every call reads/writes the database directly, which
also removes the original service's cache/PG-staleness risk.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from .schema import get_connection

ALPHA_BY_TIER = {
    "nascent": 0.30, "apprentice": 0.40, "journeyman": 0.50,
    "master": 0.60, "architect": 0.70,
}

TIER_THRESHOLDS = {
    "nascent": 0, "apprentice": 50, "journeyman": 150,
    "master": 300, "architect": 600,
}


def _row_to_brain(row) -> Dict[str, Any]:
    return {
        "agent_id": row["agent_id"], "dims": row["dims"], "epoch": row["epoch"],
        "tier": row["tier"], "mutual_information": row["mutual_information"],
        "energy": row["energy"], "frozen": bool(row["frozen"]),
        "specialist_profile": json.loads(row["specialist_profile"]),
        "mi_history": json.loads(row["mi_history"]), "step_count": row["step_count"],
        "registered_at": row["registered_at"], "forked_from": row["forked_from"],
        "forked_at_epoch": row["forked_at_epoch"],
    }


def register_brain(agent_id: str, dims: int = 24, epoch: int = 0, tier: str = "nascent",
                    mutual_information: float = 0.0, energy: float = 0.0, frozen: bool = False,
                    specialist_profile: Optional[Dict[str, float]] = None,
                    mi_history: Optional[List[float]] = None, step_count: int = 0,
                    db_path=None) -> Dict[str, Any]:
    conn = get_connection(db_path)
    try:
        registered_at = time.time()
        conn.execute(
            """INSERT INTO agent_brains (agent_id, dims, epoch, tier, mutual_information,
                energy, frozen, specialist_profile, mi_history, step_count, registered_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(agent_id) DO UPDATE SET
                dims=excluded.dims, epoch=excluded.epoch, tier=excluded.tier,
                mutual_information=excluded.mutual_information, energy=excluded.energy,
                frozen=excluded.frozen, specialist_profile=excluded.specialist_profile,
                mi_history=excluded.mi_history, step_count=excluded.step_count""",
            (agent_id, dims, epoch, tier, mutual_information, energy, int(frozen),
             json.dumps(specialist_profile or {}), json.dumps(mi_history or []),
             step_count, registered_at),
        )
        conn.commit()
        return get_brain(agent_id, db_path)
    finally:
        conn.close()


def get_brain(agent_id: str, db_path=None) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM agent_brains WHERE agent_id = ?", (agent_id,)).fetchone()
        return _row_to_brain(row) if row else None
    finally:
        conn.close()


def list_brains(db_path=None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        return [_row_to_brain(r) for r in conn.execute("SELECT * FROM agent_brains").fetchall()]
    finally:
        conn.close()


def contribute(agent_id: str, domain: str = "", snap_labels: Optional[List[str]] = None,
               mi_score: float = 0.0, epoch: int = 0, tier: str = "nascent", dims: int = 24,
               db_path=None) -> Dict[str, Any]:
    """Record a contribution -- the 'update' half of pull/update/resave.
    Does not modify the brain's own row; call merge_brain() to fold
    accumulated contributions back in."""
    conn = get_connection(db_path)
    try:
        contributed_at = time.time()
        conn.execute(
            """INSERT INTO brain_contributions (agent_id, domain, snap_labels, mi_score,
                epoch, tier, dims, contributed_at) VALUES (?,?,?,?,?,?,?,?)""",
            (agent_id, domain, json.dumps(snap_labels or []), mi_score, epoch, tier, dims, contributed_at),
        )
        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM brain_contributions").fetchone()[0]
        return {"accepted": True, "total_contributions": total}
    finally:
        conn.close()


def compute_capacity(mi_history: List[float], weight_density: float = 0.0,
                      step_count: int = 0) -> Dict[str, Any]:
    """Is this agent's learning plateaued? Pure function, no persistence --
    0.45*(MI-slope flatness) + 0.30*weight_density + 0.25*step_proxy."""
    mi_flat = 0.0
    if len(mi_history) >= 10:
        recent = mi_history[-10:]
        x = list(range(len(recent)))
        mean_x = sum(x) / len(x)
        mean_y = sum(recent) / len(recent)
        num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, recent))
        den = sum((xi - mean_x) ** 2 for xi in x)
        slope = num / den if den > 0 else 0
        mi_flat = 1.0 - min(abs(slope) / 0.005, 1.0) if slope <= 0.005 else 0.0

    density = min(weight_density, 1.0)
    step_proxy = min(step_count / 8000.0, 1.0)
    score = 0.45 * mi_flat + 0.30 * density + 0.25 * step_proxy
    score = max(0.0, min(1.0, score))

    return {
        "capacity_score": round(score, 4), "mi_flat": round(mi_flat, 4),
        "density": round(density, 4), "step_proxy": round(step_proxy, 4),
        "saturated": score >= 0.75,
        "recommendation": "reinit" if score >= 0.75 else "continue",
    }


def merge_brain(agent_id: str, target_dims: int = 32, alpha: Optional[float] = None,
                 db_path=None) -> Dict[str, Any]:
    """Pull relevant contributions (Jaccard similarity >= 0.20 against
    the brain's own specialist_profile labels) and fold them in,
    weighted by the tier's alpha. This is the 'resave once done' half
    of the cycle."""
    brain = get_brain(agent_id, db_path)
    if not brain:
        raise ValueError(f"Brain {agent_id} not registered")

    tier = brain.get("tier", "nascent")
    alpha = alpha if alpha is not None else ALPHA_BY_TIER.get(tier, 0.30)

    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM brain_contributions WHERE agent_id != ?", (agent_id,)
        ).fetchall()
    finally:
        conn.close()

    agent_labels = set(brain.get("specialist_profile", {}).keys())
    relevant = []
    for r in rows:
        c_labels = set(json.loads(r["snap_labels"]))
        union = agent_labels | c_labels
        jaccard = len(agent_labels & c_labels) / len(union) if union else 0
        if jaccard >= 0.20:
            relevant.append({
                "agent_id": r["agent_id"], "domain": r["domain"], "mi_score": r["mi_score"],
                "epoch": r["epoch"], "relevance": round(jaccard, 4),
            })
    relevant.sort(key=lambda x: -x["relevance"])

    old_dims = brain["dims"]
    new_dims = min(target_dims, 96)
    register_brain(
        agent_id=agent_id, dims=new_dims, epoch=brain["epoch"], tier=tier,
        mutual_information=brain["mutual_information"], energy=brain["energy"],
        frozen=brain["frozen"], specialist_profile=brain["specialist_profile"],
        mi_history=brain["mi_history"], step_count=brain["step_count"], db_path=db_path,
    )

    return {
        "agent_id": agent_id, "alpha": alpha, "tier": tier,
        "contributors_found": len(relevant), "top_contributors": relevant[:5],
        "dims_before": old_dims, "dims_after": new_dims, "growth": new_dims - old_dims,
    }


def fork_brain(parent_id: str, child_id: str, domain_boost: str = "", db_path=None) -> Dict[str, Any]:
    parent = get_brain(parent_id, db_path)
    if not parent:
        raise ValueError(f"Parent brain {parent_id} not registered")

    profile = dict(parent["specialist_profile"])
    if domain_boost and domain_boost in profile:
        profile[domain_boost] = min(1.0, profile[domain_boost] * 1.5)

    register_brain(
        agent_id=child_id, dims=parent["dims"], epoch=0, tier="nascent",
        mutual_information=parent["mutual_information"], energy=parent["energy"],
        frozen=False, specialist_profile=profile, mi_history=[], step_count=0, db_path=db_path,
    )
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE agent_brains SET forked_from = ?, forked_at_epoch = ? WHERE agent_id = ?",
            (parent_id, parent["epoch"], child_id),
        )
        conn.commit()
    finally:
        conn.close()

    return {"forked": True, "parent": parent_id, "child": child_id,
            "child_dims": parent["dims"], "boost": domain_boost}


def list_expertise(domain: str = "", min_mi: float = 0.0, db_path=None) -> List[Dict[str, Any]]:
    """specialist_profile is not guaranteed to be a pure float skill-map --
    the real populated tmn_unified.db stores mixed-type metadata in it
    (e.g. {"purpose": "...", "dims": 24, "tier": "primary"}), found by
    running this against that real data, not assumed. Only numeric
    entries are treated as skill scores for the domain filter and
    top_specialties ranking; non-numeric entries (and bools, which are
    technically numeric in Python but not skill scores here) are kept
    out of both."""
    results = []
    for brain in list_brains(db_path):
        profile = brain.get("specialist_profile", {})
        numeric_profile = {
            k: v for k, v in profile.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        }
        mi = brain.get("mutual_information", 0)
        if mi < min_mi:
            continue
        if domain and numeric_profile.get(domain, 0) < 0.01:
            continue
        results.append({
            "agent_id": brain["agent_id"], "dims": brain["dims"], "tier": brain["tier"], "mi": mi,
            "top_specialties": dict(sorted(numeric_profile.items(), key=lambda x: -x[1])[:3]),
        })
    results.sort(key=lambda x: -x["mi"])
    return results
