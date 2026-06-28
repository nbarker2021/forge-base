"""
Correction surface engine.

This is a kernel primitive: the local truth table for the correction
identity ``correction = C AND NOT R`` over all 8 LCR states. Even if
the full Rule 30 / Rule 90 proofs live outside the kernel, this local
truth table belongs inside.

Exposes:

  * ``correction_table()`` — the 8-row table
  * ``compute_correction(lcr)`` — single-row computation
  * ``correction_surface(gluons)`` — apply to a stream of gluons
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

from .lcr import LocalGluon, truth_table


@dataclass
class CorrectionRow:
    lcr: Tuple[int, int, int]
    correction: int
    rule30: int
    rule90: int

    def to_dict(self) -> dict:
        return {
            "lcr": list(self.lcr),
            "correction": self.correction,
            "rule30": self.rule30,
            "rule90": self.rule90,
        }


def compute_correction(lcr: Tuple[int, int, int]) -> int:
    """Return ``C AND NOT R`` for the triple (L, C, R)."""
    _L, C, R = lcr  # noqa: F841 (L is part of the triple identity)
    return C & (1 - R)


def correction_table() -> List[CorrectionRow]:
    """Build the full 8-row correction table."""
    out: List[CorrectionRow] = []
    for g in truth_table():
        out.append(
            CorrectionRow(
                lcr=(g.left, g.center, g.right),
                correction=g.correction,
                rule30=g.rule30,
                rule90=g.rule90,
            )
        )
    return out


def correction_surface(gluons: Iterable[LocalGluon]) -> List[CorrectionRow]:
    """Apply the correction identity to a stream of gluons."""
    out: List[CorrectionRow] = []
    for g in gluons:
        out.append(
            CorrectionRow(
                lcr=(g.left, g.center, g.right),
                correction=g.correction,
                rule30=g.rule30,
                rule90=g.rule90,
            )
        )
    return out


def verify_correction_identity() -> bool:
    """Verify ``correction == C AND NOT R`` on every LCR state."""
    for row in correction_table():
        L, C, R = row.lcr
        assert row.correction == (C & (1 - R)), (row, C, R)
    return True
