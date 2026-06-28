"""Observer-relative stopped-state normal form."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class EvidenceClass(str, Enum):
    """Evidence levels returned by the production solver."""

    MATERIALIZED_EXACT = "materialized_exact"
    VERIFIED_CONTINUATION = "verified_continuation"
    BOUNDED_NORMALIZED = "bounded_normalized"
    REGISTERED_ROUTE = "registered_route"
    ESCROW_OPEN = "escrow_open"


def _validate_bit(bit: int) -> None:
    if bit not in (0, 1):
        raise ValueError(f"expected binary bit, got {bit!r}")


@dataclass(frozen=True)
class LocalTriad:
    """One local LCR read."""

    left: int
    center: int
    right: int

    def __post_init__(self) -> None:
        for bit in (self.left, self.center, self.right):
            _validate_bit(bit)


@dataclass(frozen=True)
class StoppedState:
    """Prior, current, and future triads at one in-sheet address."""

    past: LocalTriad
    current: LocalTriad
    future: LocalTriad

    @property
    def center(self) -> int:
        return self.current.center


@dataclass(frozen=True)
class SolverReceipt:
    """Serializable `C_idem(N|-N,k+t)` solver printout."""

    n: int
    antipode_n: int
    sheet: int
    offset: int
    bit: int | None
    evidence: EvidenceClass
    actions: tuple[str, ...]
    local_closure: bool
    continuation_verified: bool
    message: str = ""
    root_template: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "normal_form": "C_idem(N|-N,k+t)",
            "address": {
                "N": self.n,
                "-N": self.antipode_n,
                "k": self.sheet,
                "t": self.offset,
            },
            "bit": self.bit,
            "evidence": self.evidence.value,
            "actions": list(self.actions),
            "local_closure": self.local_closure,
            "continuation_verified": self.continuation_verified,
            "root_template": self.root_template,
            "message": self.message,
        }


def decompose_address(n: int, sheet_width: int) -> tuple[int, int]:
    """Return `(sheet, offset)` for signed address `n`."""
    if sheet_width <= 0:
        raise ValueError("sheet_width must be > 0")
    return divmod(n, sheet_width)
