"""
fast_rule30.py — Fast-bit Rule 30 evolution via Python big-int bitwise
operations. Each row is a single Python integer, the i-th cell stored as
bit i.

Useful for empirical entropy and density measurements at large depths.
"""
from __future__ import annotations

from typing import Generator


def fast_rule30(max_depth: int) -> Generator[int, None, None]:
    """Yield the center bit at each depth 1..max_depth from the single-cell
    seed, using Python big-int bitwise ops for the row evolution."""
    width = 2 * max_depth + 3
    center = width // 2
    mask = (1 << width) - 1
    row = 1 << center
    for _ in range(max_depth):
        # Rule 30: new[i] = old[i-1] XOR (old[i] OR old[i+1])
        # With cell i at bit i: left-neighbor is at bit (i-1), needed at
        # bit i, so shift left by 1. Right-neighbor shift right by 1.
        row = ((row << 1) ^ (row | (row >> 1))) & mask
        yield (row >> center) & 1


def fast_rule30_chart(max_depth: int) -> Generator[tuple[int, int, int], None, None]:
    """Yield (L, C, R) at center+/-1 for each depth 1..max_depth."""
    width = 2 * max_depth + 3
    center = width // 2
    mask = (1 << width) - 1
    row = 1 << center
    for _ in range(max_depth):
        row = ((row << 1) ^ (row | (row >> 1))) & mask
        L = (row >> (center - 1)) & 1
        C = (row >> center) & 1
        R = (row >> (center + 1)) & 1
        yield (L, C, R)
