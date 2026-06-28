"""
D4 token: kernel-side D4 plot token compatible with
``lattice_forge.cqe.D4Token``.

The D4Token is the local 8-tuple representation of a CQE state at
one bit position. The fields are designed to be ABI-compatible with
lattice_forge.cqe.D4Token — when lattice_forge is installed, the
firmware bridge wraps the kernel's tokens in the upstream type;
when it isn't, this stub is the local authority.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class D4Token:
    """A D4 plot token that always carries a pode and its antipode.

    Fields are designed to be ABI-compatible with
    ``lattice_forge.cqe.D4Token``. The ``spin_vignette`` is a
    ``(orbit, sheet)`` pair; ``cartan_slot`` is the 1..8 slot index
    in the D4 Dynkin diagram; ``time_polarity`` is +1 / -1; and
    ``write_record`` is the antipode bit that was actually written
    (0 or 1).
    """

    index: int
    pode: int
    antipode: int
    orbit: int
    sheet: int
    spin_vignette: tuple  # (orbit, sheet)
    cartan_slot: int
    time_polarity: int
    write_record: int

    @classmethod
    def from_bit(cls, index: int, bit: int, write_record: Optional[int] = None) -> "D4Token":
        pode = int(bit) & 1
        antipode = 1 - pode
        recorded = antipode if write_record is None else int(write_record) & 1
        return cls(
            index=int(index),
            pode=pode,
            antipode=antipode,
            orbit=int(index) % 4,
            sheet=pode,
            spin_vignette=(int(index) % 4, pode),
            cartan_slot=(int(index) % 8) + 1,
            time_polarity=1 if int(index) % 2 == 0 else -1,
            write_record=recorded,
        )

    @property
    def is_closed(self) -> bool:
        """A computation closes only when the write recorded the antipode."""
        return self.write_record == self.antipode

    @property
    def closure_state(self) -> str:
        return "CLOSED" if self.is_closed else "ESCROW"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "pode": self.pode,
            "antipode": self.antipode,
            "orbit": self.orbit,
            "sheet": self.sheet,
            "spin_vignette": list(self.spin_vignette),
            "cartan_slot": self.cartan_slot,
            "time_polarity": self.time_polarity,
            "write_record": self.write_record,
            "closure_state": self.closure_state,
        }


def tokens_from_bits(bits: str) -> list:
    """Build a list of D4Token from a binary string ``bits``.

    Each bit becomes one D4Token at its bit index. The default
    ``write_record`` defaults to the antipode (so the token starts
    in the "CLOSED" state), matching ``lattice_forge.cqe.D4Token``.
    """
    out = []
    for i, b in enumerate(bits):
        if b in ("0", "1"):
            out.append(D4Token.from_bit(index=i, bit=int(b)))
    return out


__all__ = ["D4Token", "tokens_from_bits"]
