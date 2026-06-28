"""Depth ladders and exhaustion modes for empirical platforms."""

from __future__ import annotations

EXHAUSTION_LADDERS: dict[str, list[int]] = {
    "quick": [256],
    "standard": [64, 256, 1024],
    "exhaustive": [64, 256, 1024, 4096],
    "full": [64, 256, 1024, 4096, 8192],
}


def ladder_for_mode(mode: str) -> list[int]:
    return list(EXHAUSTION_LADDERS.get(mode, EXHAUSTION_LADDERS["standard"]))
