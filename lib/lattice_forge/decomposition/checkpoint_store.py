"""
checkpoint_store.py — Self-contained block-checkpoint extractor
(Construction 7.1 of PAPER.md).

Stores a Rule 30 row at every multiple of `base_page` up to `max_depth`.
Queries replay at most `base_page` Rule 30 steps from the nearest stored
row. Per-query work is bounded independent of N.

Dependency-free; Python standard library only.
"""
from __future__ import annotations

import time
from typing import Any


def _rule30_step(row: list[int]) -> list[int]:
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
    width = 2 * depth + 3
    center = width // 2
    row = [0] * width
    row[center] = 1
    bits: list[int] = []
    for _ in range(depth):
        row = _rule30_step(row)
        bits.append(row[center])
    return bits


class Rule30Checkpoints:
    """Hierarchical row checkpoints for the Rule 30 single-cell seed.

    Stores the full row at every `base_page`-boundary up to `max_depth`.
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
        }


def verify_checkpoint_store(max_depth: int = 4096) -> dict[str, Any]:
    """Build a store and verify against direct simulation."""
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

    # Per-query timing
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
    import json
    print(json.dumps(verify_checkpoint_store(max_depth=4096), indent=2))
