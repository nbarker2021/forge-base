"""
ChromaForge MMDB — VOA-like crystal storage with E8-proximity search.

Crystals are crystallized semantic forms:
  content      — raw input text
  snap_labels  — SNAP stratification labels (the crystal's identity in label space)
  e8_coords    — 8D E8 lattice position (the crystal's identity in geometric space)
  mdhg_address — MDHG hash-graph address (the crystal's identity in resolution space)
  domain       — semantic domain classifier
  metadata     — arbitrary structured metadata

Two search modes:
  label search  — exact match on snap_labels (set intersection)
  E8 proximity  — Euclidean distance in 8D space, within radius

Design: MMDBEngine is a class. Module-level singleton `engine` available.
"""
import hashlib
import math
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

# ─── Lookup tables (import-time, read-only) ────────────────────────────────────

# E8 basis vectors (8D, norm √2) — the 8 axes of the E8 root system's first shell
# Used as default search center and reference frame
_E8_BASIS: Tuple[Tuple[float, ...], ...] = tuple(
    tuple(math.sqrt(2) if j == i else 0.0 for j in range(8))
    for i in range(8)
)

_EMPTY_E8: Tuple[float, ...] = (0.0,) * 8


# ─── Distance (pure function, no state) ──────────────────────────────────────

def e8_distance(a: List[float], b: List[float]) -> float:
    if len(a) != len(b) or not a:
        return float("inf")
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


# ─── Engine class ──────────────────────────────────────────────────────────────

class MMDBEngine:
    """VOA-like crystal storage. One instance = one crystal namespace."""

    def __init__(self):
        self._crystals: Dict[str, Dict] = {}
        self._label_index: Dict[str, Set[str]] = {}
        self._domain_index: Dict[str, Set[str]] = {}

    # ── Core ───────────────────────────────────────────────────────────────────

    def store(
        self,
        content: str,
        snap_labels: List[str] = None,
        e8_coords: List[float] = None,
        mdhg_address: str = "",
        domain: str = "general",
        metadata: Dict = None,
    ) -> Dict:
        """Store a crystal. Returns {crystal_id, content_hash, snap_labels}."""
        cid = uuid.uuid4().hex
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        labels = list(set(snap_labels or []))
        coords = list(e8_coords or _EMPTY_E8)

        record: Dict = {
            "crystal_id":    cid,
            "content":       content,
            "content_hash":  content_hash,
            "snap_labels":   labels,
            "e8_coords":     coords,
            "mdhg_address":  mdhg_address,
            "domain":        domain,
            "metadata":      metadata or {},
            "created_at":    datetime.now(timezone.utc).isoformat(),
        }
        self._crystals[cid] = record

        for lab in labels:
            self._label_index.setdefault(lab, set()).add(cid)
        self._domain_index.setdefault(domain, set()).add(cid)

        return {"crystal_id": cid, "content_hash": content_hash, "snap_labels": labels}

    def get(self, crystal_id: str) -> Dict:
        """Retrieve a crystal by ID."""
        crystal = self._crystals.get(crystal_id)
        if not crystal:
            raise KeyError(f"Crystal {crystal_id} not found")
        return crystal

    def search(
        self,
        snap_labels: List[str] = None,
        e8_center: List[float] = None,
        radius: float = 1.0,
        limit: int = 50,
    ) -> Dict:
        """Search by label match and/or E8 proximity."""
        center = list(e8_center or _EMPTY_E8)

        if snap_labels:
            candidates: Set[str] = set()
            for lab in snap_labels:
                candidates |= self._label_index.get(lab, set())
        else:
            candidates = set(self._crystals.keys())

        hits = []
        for cid in candidates:
            c = self._crystals[cid]
            dist = e8_distance(c["e8_coords"], center)
            if dist <= radius:
                hits.append({**c, "e8_distance": round(dist, 6)})

        hits.sort(key=lambda x: x["e8_distance"])
        return {"results": hits[:limit], "total": len(hits)}

    def by_domain(self, domain: str, limit: int = 50) -> List[Dict]:
        """All crystals in a domain."""
        cids = list(self._domain_index.get(domain, set()))[:limit]
        return [self._crystals[cid] for cid in cids if cid in self._crystals]

    def label_lookup(self, label: str) -> List[str]:
        """Crystal IDs carrying a specific label."""
        return list(self._label_index.get(label, set()))

    def compact(self, remove_orphans: bool = False,
                rebuild_index: bool = True) -> Dict:
        """Compact the store. Optionally remove label-less crystals."""
        removed = 0
        if remove_orphans:
            orphans = [cid for cid, c in self._crystals.items()
                       if not c.get("snap_labels")]
            for cid in orphans:
                del self._crystals[cid]
                removed += 1

        if rebuild_index:
            self._label_index.clear()
            self._domain_index.clear()
            for cid, c in self._crystals.items():
                for lab in c.get("snap_labels", []):
                    self._label_index.setdefault(lab, set()).add(cid)
                dom = c.get("domain", "general")
                self._domain_index.setdefault(dom, set()).add(cid)

        return {
            "orphans_removed":   removed,
            "crystals_remaining": len(self._crystals),
            "labels_indexed":    len(self._label_index),
            "domains_indexed":   len(self._domain_index),
        }

    def stats(self) -> Dict:
        domain_counts = {d: len(cids) for d, cids in self._domain_index.items()}
        label_counts = {lab: len(cids) for lab, cids in self._label_index.items()}
        top_labels = sorted(label_counts.items(), key=lambda x: -x[1])[:20]
        return {
            "crystal_count":      len(self._crystals),
            "domain_distribution": domain_counts,
            "label_count":        len(self._label_index),
            "top_labels":         dict(top_labels),
        }

    @property
    def count(self) -> int:
        return len(self._crystals)


# ─── Module-level singleton + forwarding ──────────────────────────────────────

engine = MMDBEngine()

def store(content: str, **kwargs) -> Dict:
    return engine.store(content, **kwargs)

def get_crystal(crystal_id: str) -> Dict:
    return engine.get(crystal_id)

def search(snap_labels: List[str] = None, e8_center: List[float] = None,
           radius: float = 1.0, limit: int = 50) -> Dict:
    return engine.search(snap_labels, e8_center, radius, limit)

def stats() -> Dict:
    return engine.stats()
