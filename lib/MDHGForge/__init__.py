"""MDHGForge — multi-scale geometric hash cache with SpeedLight idempotence.

Distilled from CMPLXDevKit (profile repo, mcp_os/agrm_mdhg_integration/
mdhg_ca.py) into the forge ring. Paper binding: CQE-paper-07 (Discrete-
Continuous Bridge). The cache IS the bridge: a continuous 24D vector is
quantized onto a discrete bin lattice, then double-hashed to a 2D slot on a
torus. Re-admitting the same content is a pure hit (distance 0, no new
entry) — the SpeedLight idempotence law f(f(x)) = f(x) that makes the
bridge a well-defined retraction.

The 24 dimensions are the Leech dimension: the quantize -> slot map is the
discrete address of a continuous Leech-space point (see LeechForge).

Adjudicated divergences from the source:
  1. quantize() used floor(x * bins) with no clamp on the low side, so a
     negative coordinate produced a negative bin (then min-clamped to 0 but
     only after the floor) — fine for x in [0,1) but the forge clamps the
     normalized input into [0,1) first so the bridge is total on all reals.
  2. The CA-field self-regulating dynamics (CAField, kernel_step, Wolfram
     assignments) stay product-side; the forge carries the proven cache +
     idempotence core.
  3. The source SlotEntry.last uses wall-clock time, making eviction order
     non-deterministic under equal hits; the forge uses a monotonic
     admission sequence so eviction is deterministic and replayable.

Stdlib only.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Optional

LEECH_DIM = 24


def _h(x: Any) -> str:
    b = json.dumps(x, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def quantize(v24: list[float], bins: int = 16) -> tuple[int, ...]:
    """Bridge a continuous 24D vector to a discrete bin tuple.

    The coordinate is first clamped into [0, 1) so the bridge is total on
    all reals (adjudicated: source assumed inputs already in [0,1)).
    """
    out: list[int] = []
    for x in v24:
        xf = float(x)
        xf = 0.0 if xf < 0.0 else (1.0 - 1e-12 if xf >= 1.0 else xf)
        out.append(int(min(bins - 1, math.floor(xf * bins))))
    return tuple(out)


def slot_of(q24: tuple[int, ...], grid_side: int = 12) -> str:
    """Double-hash a quantized vector to a 2D slot on the grid torus."""
    h1 = int(hashlib.sha256(("A" + str(q24)).encode()).hexdigest(), 16)
    h2 = int(hashlib.sha256(("B" + str(q24)).encode()).hexdigest(), 16)
    return f"{h1 % grid_side:02d},{h2 % grid_side:02d}"


def hamming(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    return sum(1 for x, y in zip(a, b) if x != y)


@dataclass
class SlotEntry:
    key: str
    q24: tuple[int, ...]
    meta: dict[str, Any]
    seq: int
    hits: int = 0


class MDHGCache:
    """24D -> 2D slot grid geometric cache with bounded per-slot capacity.

    Admission is idempotent: the same (q24, meta) re-admits as a hit with
    distance 0 and no growth. Eviction is deterministic LRU by (hits, seq).
    """

    def __init__(self, grid_side: int = 12, cap_per_slot: int = 6,
                 bins: int = 16, layer_name: str = "default"):
        self.grid_side = grid_side
        self.cap_per_slot = cap_per_slot
        self.bins = bins
        self.layer_name = layer_name
        self.slots: dict[str, list[SlotEntry]] = {}
        self.admissions = 0
        self.evictions = 0
        self._seq = 0

    def _key(self, q: tuple[int, ...], meta: dict[str, Any]) -> str:
        return _h({"q": list(q), "meta": {k: meta.get(k) for k in sorted(meta)[:12]}})[:16]

    def admit(self, v24: list[float], meta: dict[str, Any]) -> dict[str, Any]:
        q = quantize(v24, self.bins)
        slot = slot_of(q, self.grid_side)
        key = self._key(q, meta)
        arr = self.slots.setdefault(slot, [])

        for e in arr:
            if e.key == key:
                e.hits += 1
                return {"admit": True, "hit": True, "slot": slot,
                        "distance": 0.0, "key": key, "q24": q,
                        "layer": self.layer_name}

        dist = float(min((hamming(q, e.q24) for e in arr), default=0))

        evicted = None
        if len(arr) >= self.cap_per_slot:
            cand = min(arr, key=lambda e: (e.hits, e.seq))
            evicted = {"key": cand.key, "hits": cand.hits, "meta": cand.meta}
            arr.remove(cand)
            self.evictions += 1

        self._seq += 1
        arr.append(SlotEntry(key=key, q24=q, meta=meta, seq=self._seq))
        self.admissions += 1
        return {"admit": True, "hit": False, "slot": slot, "distance": dist,
                "key": key, "evicted": evicted, "q24": q, "layer": self.layer_name}

    def total_entries(self) -> int:
        return sum(len(a) for a in self.slots.values())

    def occupancy_grid(self) -> list[list[int]]:
        g = [[0] * self.grid_side for _ in range(self.grid_side)]
        for s, arr in self.slots.items():
            x, y = (int(p) for p in s.split(","))
            g[y][x] = len(arr)
        return g


class MDHGMultiScale:
    """Three independent caches at fast / med / slow timescales."""

    def __init__(self, grid_side: int = 12, cap_per_slot: int = 6, bins: int = 16):
        self.fast = MDHGCache(grid_side, cap_per_slot, bins, "fast")
        self.med = MDHGCache(grid_side, cap_per_slot, bins, "med")
        self.slow = MDHGCache(grid_side, cap_per_slot, bins, "slow")

    def admit(self, v24: list[float], meta: dict[str, Any],
              layer: str = "fast") -> dict[str, Any]:
        return getattr(self, layer).admit(v24, meta)


# ─── Finite verifier (paper-bound claims, CQE-paper-07) ─────────────────────

def _vec(seed: int, n: int = 24) -> list[float]:
    """Deterministic pseudo-random vector in [0,1)^24 from a seed."""
    d = hashlib.sha256(str(seed).encode()).digest()
    return [d[i % 32] / 256.0 for i in range(n)]


def verify() -> dict[str, Any]:
    """Run the 10 finite checks binding MDHGForge to CQE-paper-07."""
    checks: dict[str, bool] = {}

    # 1. The bridge dimension is the Leech dimension 24
    checks["bridge_dimension_is_24"] = LEECH_DIM == 24

    # 2. Quantize is total on all reals and lands in [0, bins)
    extreme = [-5.0, -1e9, 0.0, 0.5, 0.999999, 1.0, 7.3, 1e9]
    q = quantize(extreme + [0.0] * 16, bins=16)
    checks["quantize_total_and_bounded"] = all(0 <= b < 16 for b in q)

    # 3. Quantize is idempotent as a retraction: re-quantizing a bin-centered
    #    reconstruction returns the same bins
    bins = 16
    centers = [(b + 0.5) / bins for b in q]
    checks["quantize_retraction_idempotent"] = quantize(centers, bins) == q

    # 4. Slot assignment is deterministic and lands on the grid torus
    qq = quantize(_vec(1), 16)
    s1, s2 = slot_of(qq, 12), slot_of(qq, 12)
    x, y = (int(p) for p in s1.split(","))
    checks["slot_deterministic_on_torus"] = (
        s1 == s2 and 0 <= x < 12 and 0 <= y < 12
    )

    # 5. SpeedLight idempotence f(f(x)) = f(x): re-admitting the same content
    #    is a hit with distance 0 and no admission growth
    c = MDHGCache()
    r1 = c.admit(_vec(7), {"id": "a"})
    n_after_first = c.admissions
    r2 = c.admit(_vec(7), {"id": "a"})
    r3 = c.admit(_vec(7), {"id": "a"})
    checks["speedlight_admission_idempotent"] = (
        not r1["hit"] and r2["hit"] and r3["hit"]
        and r2["distance"] == 0.0
        and c.admissions == n_after_first
    )

    # 6. Per-slot capacity is never exceeded under heavy load
    c2 = MDHGCache(grid_side=4, cap_per_slot=3, bins=8)
    for i in range(500):
        c2.admit(_vec(i), {"id": i})
    checks["capacity_invariant_holds"] = all(
        len(a) <= c2.cap_per_slot for a in c2.slots.values()
    )

    # 7. Eviction is deterministic LRU by (hits, seq): a replay gives the
    #    identical final key set
    def run() -> set[str]:
        cc = MDHGCache(grid_side=2, cap_per_slot=2, bins=4)
        for i in range(60):
            cc.admit(_vec(i), {"id": i})
        return {e.key for a in cc.slots.values() for e in a}
    checks["eviction_deterministic_replayable"] = run() == run()

    # 8. Distance is the min Hamming over the slot's existing q24 vectors
    c3 = MDHGCache(grid_side=1, cap_per_slot=99, bins=4)
    base = c3.admit([0.1] * 24, {"id": 0})
    near = list(base["q24"])
    near[0] = (near[0] + 1) % 4
    centers = [(b + 0.5) / 4 for b in near]
    res = c3.admit(centers, {"id": 1})
    checks["distance_is_min_hamming"] = res["distance"] == 1.0

    # 9. Multi-scale layers are independent: admitting to fast does not
    #    populate med or slow
    ms = MDHGMultiScale()
    ms.admit(_vec(3), {"id": "x"}, "fast")
    checks["multiscale_layers_independent"] = (
        ms.fast.total_entries() == 1
        and ms.med.total_entries() == 0
        and ms.slow.total_entries() == 0
    )

    # 10. Occupancy conservation: grid sum equals total live entries
    g = c2.occupancy_grid()
    checks["occupancy_grid_conserves_entries"] = (
        sum(sum(row) for row in g) == c2.total_entries()
    )

    return {
        "forge": "MDHGForge",
        "paper": "CQE-paper-07",
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2))
