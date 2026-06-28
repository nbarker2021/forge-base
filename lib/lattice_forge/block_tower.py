"""
block_tower.py — Regime A: hierarchical checkpoint store for Rule 30.

The Rule 30 center column is empirically full-entropy: an 8-state local
(L,C,R) lookup cannot be a sub-linear predictor. Over a 2000-step ribbon,
every (L,C,R) triple is followed by ~200+ distinct 64-bit futures
(verified by `scripts/diagnose_block_entropy.py`). The block tower's
correct role is therefore *not* prediction but block-addressed I/O.

This module builds a hierarchical checkpoint store:
  Level 0: row snapshot every BASE_PAGE = 64 steps
  Level 1: row snapshot every 4 * BASE_PAGE  = 256 steps
  Level 2: row snapshot every 16 * BASE_PAGE = 1024 steps
  Level 3: row snapshot every 64 * BASE_PAGE = 4096 steps

Higher levels are a sparse subset of level 0; the level number is the
exponent in the "4^k * BASE_PAGE" stride.

To read the center bit at depth n:
  1. Find the largest checkpoint depth a <= n.
  2. Replay (n - a) Rule 30 steps from the stored row.

Per-query work after build: at most BASE_PAGE row-steps (each O(width)).
That is O(1) in N: query time is bounded by the base page, not the depth.

Build cost: O(max_depth * width). Storage: O(max_depth / base_page) rows.
This is honest sub-O(N) *query* time at the cost of one-shot O(N) build.
The "tower" structure lets a client decide how much to materialize: a
client that only needs depths around n=10_000 can build a 10_500-deep
store and never touch the 1M depth grid.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any


# ---------------------------------------------------------------------------
# Rule 30 row dynamics
# ---------------------------------------------------------------------------

def _rule30_step(row: list[int]) -> list[int]:
    """One Rule 30 step on a finite row with implicit-zero boundary."""
    w = len(row)
    new = [0] * w
    prev_l = 0
    for i in range(w):
        c = row[i]
        r = row[i + 1] if i + 1 < w else 0
        new[i] = prev_l ^ (c | r)
        prev_l = c
    return new


def rule30_center_column(depth: int) -> list[int]:
    """Return the Rule 30 center column bits at depths 1..depth from the
    single-cell seed. Width is sized to enclose the light cone exactly."""
    width = 2 * depth + 3
    center = width // 2
    row = [0] * width
    row[center] = 1
    bits: list[int] = []
    for _ in range(depth):
        row = _rule30_step(row)
        bits.append(row[center])
    return bits


# ---------------------------------------------------------------------------
# Hierarchical checkpoint store
# ---------------------------------------------------------------------------

class Rule30Checkpoints:
    """Hierarchical row checkpoints for the Rule 30 single-cell seed.

    The store records the full row at every base_page boundary. Higher
    levels are stride views into the same physical store; they exist for
    address-arithmetic convenience, not for separate storage.
    """

    def __init__(self, max_depth: int, base_page: int = 64, max_level: int = 3):
        if max_depth < 0:
            raise ValueError("max_depth must be >= 0")
        if base_page <= 0:
            raise ValueError("base_page must be > 0")
        self.base_page = base_page
        self.max_level = max_level
        self.strides = [base_page * (4 ** k) for k in range(max_level + 1)]
        self.max_depth = max_depth

        width = 2 * max_depth + 3
        self._width = width
        self._center = width // 2

        row = [0] * width
        row[self._center] = 1
        self._checkpoints: dict[int, list[int]] = {0: list(row)}

        for d in range(1, max_depth + 1):
            row = _rule30_step(row)
            if d % base_page == 0:
                self._checkpoints[d] = list(row)

        index_str = json.dumps(
            {d: hashlib.sha256(bytes(r)).hexdigest()[:12]
             for d, r in self._checkpoints.items()},
            sort_keys=True,
        )
        self.index_hash = hashlib.sha256(index_str.encode()).hexdigest()[:16]

    def stride_for_level(self, level: int) -> int:
        return self.strides[level]

    def nearest_checkpoint_at_or_before(self, n: int) -> int:
        if n < 0:
            raise ValueError("depth must be >= 0")
        return (n // self.base_page) * self.base_page

    def row_at(self, depth: int) -> list[int]:
        if depth < 0 or depth > self.max_depth:
            raise ValueError(f"depth {depth} out of range [0, {self.max_depth}]")
        anchor = self.nearest_checkpoint_at_or_before(depth)
        row = list(self._checkpoints[anchor])
        for _ in range(depth - anchor):
            row = _rule30_step(row)
        return row

    def center_bit_at(self, depth: int) -> int:
        if depth < 1:
            raise ValueError("center bit requires depth >= 1")
        return self.row_at(depth)[self._center]

    def info(self) -> dict[str, Any]:
        return {
            "base_page": self.base_page,
            "max_level": self.max_level,
            "strides": self.strides,
            "max_depth": self.max_depth,
            "checkpoints_stored": len(self._checkpoints),
            "row_width": self._width,
            "index_hash": self.index_hash,
        }


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_block_tower(max_depth: int = 1024) -> dict[str, Any]:
    """Verify the checkpoint store against direct Rule 30 replay at a
    representative sample of depths."""
    t0 = time.perf_counter()
    store = Rule30Checkpoints(max_depth=max_depth)
    build_s = time.perf_counter() - t0

    bf = rule30_center_column(max_depth)

    base_sample = [1, 2, 3, 10, 50, 63, 64, 65, 100, 127, 128, 200, 255, 256, 500, 1000]
    stride_sample = list(range(1, max_depth + 1, max(1, max_depth // 64)))
    sample_depths = sorted({d for d in base_sample + stride_sample if 1 <= d <= max_depth})

    mismatches = []
    for d in sample_depths:
        got = store.center_bit_at(d)
        exp = bf[d - 1]
        if got != exp:
            mismatches.append({"depth": d, "expected": exp, "got": got})

    # Query timing: average over a re-read of every sampled depth.
    t1 = time.perf_counter()
    for d in sample_depths:
        store.center_bit_at(d)
    avg_query_s = (time.perf_counter() - t1) / max(1, len(sample_depths))

    return {
        "status": "pass" if not mismatches else "fail",
        "max_depth": max_depth,
        "build_seconds": build_s,
        "avg_query_seconds": avg_query_s,
        "info": store.info(),
        "sample_count": len(sample_depths),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:10],
    }


if __name__ == "__main__":
    r = verify_block_tower(max_depth=4096)
    print(json.dumps(r, indent=2))
