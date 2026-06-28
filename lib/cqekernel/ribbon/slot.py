"""
8-slot ribbon: slot, ribbon, arity report, hydrate, transport.

Slots::

    C — Center
    L — Left boundary
    R — Right boundary
    B — Boundary rule
    T — Tool transform
    O — Obligation set
    W — Workbook analogue
    A — Anchor / citation / source
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Canonical 8-slot names. Order is part of the public ABI.
SLOT_NAMES: List[str] = ["C", "L", "R", "B", "T", "O", "W", "A"]


def _stable_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Slot
# ---------------------------------------------------------------------------


@dataclass
class RibbonSlot:
    """One slot in an 8-slot ribbon."""

    name: str
    value: Any
    source_kind: str
    provenance: str
    hash: str
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "source_kind": self.source_kind,
            "provenance": self.provenance,
            "hash": self.hash,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RibbonSlot":
        return cls(
            name=data["name"],
            value=data["value"],
            source_kind=data["source_kind"],
            provenance=data["provenance"],
            hash=data["hash"],
            status=data["status"],
        )


def make_slot(
    name: str,
    value: Any,
    *,
    source_kind: str = "kernel_primitive",
    provenance: str = "",
    status: str = "FILLED",
) -> RibbonSlot:
    """Build a ``RibbonSlot``.

    The slot's ``hash`` is the structural identity hash: it covers
    ``(name, source_kind, provenance, status)`` only. The ``value``
    field carries data (and may include runtime UUIDs); it is the
    *content* of the slot, not its identity. This is what makes the
    ribbon a deterministic function of the request: the same request
    always produces the same slot identities and therefore the same
    ribbon hash, regardless of the random UUIDs in the value.
    """
    body = json.dumps(
        {"name": name, "source_kind": source_kind,
         "provenance": provenance, "status": status},
        sort_keys=True, default=str, separators=(",", ":"),
    ).encode("utf-8")
    return RibbonSlot(
        name=name,
        value=value,
        source_kind=source_kind,
        provenance=provenance,
        hash=_stable_hash(body),
        status=status,
    )


# ---------------------------------------------------------------------------
# Ribbon
# ---------------------------------------------------------------------------


@dataclass
class Ribbon:
    """An 8-slot ribbon: C, L, R, B, T, O, W, A."""

    ribbon_id: str
    slots: Dict[str, RibbonSlot]
    arity: int
    source_hash: str
    created_by_request: str
    created_at: str = ""
    ribbon_hash: str = field(init=False)

    def __post_init__(self) -> None:
        # Default created_at to a deterministic marker so the same
        # input produces the same ribbon_hash. Callers that want a
        # wall-clock timestamp can set it explicitly after construction.
        if not self.created_at:
            self.created_at = "deterministic"
        # Ribbon hash is over the slot IDENTITIES (name, hash,
        # source_kind, provenance, status) and the source_hash only.
        # ``ribbon_id`` and ``created_by_request`` are LABELS — they
        # are not part of the ribbon's identity. This is what makes
        # the ribbon a deterministic function of the request: the
        # same request always produces the same slot identities and
        # the same source_hash, therefore the same ribbon_hash.
        slots_for_hash = {
            k: {
                "name": self.slots[k].name,
                "hash": self.slots[k].hash,
                "source_kind": self.slots[k].source_kind,
                "provenance": self.slots[k].provenance,
                "status": self.slots[k].status,
            }
            for k in SLOT_NAMES if k in self.slots
        }
        body = json.dumps(
            {
                "slots": slots_for_hash,
                "source_hash": self.source_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.ribbon_hash = _stable_hash(body)
        # Compute arity
        self.arity = sum(
            1 for k in SLOT_NAMES if k in self.slots and self.slots[k].status == "FILLED"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ribbon_id": self.ribbon_id,
            "slots": {k: self.slots[k].to_dict() for k in self.slots},
            "arity": self.arity,
            "source_hash": self.source_hash,
            "created_by_request": self.created_by_request,
            "created_at": self.created_at,
            "ribbon_hash": self.ribbon_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Ribbon":
        slots = {k: RibbonSlot.from_dict(v) for k, v in data["slots"].items()}
        r = cls(
            ribbon_id=data["ribbon_id"],
            slots=slots,
            arity=int(data["arity"]),
            source_hash=data["source_hash"],
            created_by_request=data["created_by_request"],
            created_at=data.get("created_at", ""),
        )
        if data.get("ribbon_hash") and data["ribbon_hash"] != r.ribbon_hash:
            from ..core.errors import ReplayMismatch

            raise ReplayMismatch(
                f"ribbon {r.ribbon_id} hash mismatch"
            )
        return r


def make_ribbon(
    *,
    source_hash: str,
    created_by_request: str,
    slots: Optional[Dict[str, RibbonSlot]] = None,
    ribbon_id: Optional[str] = None,
) -> Ribbon:
    """Create a ribbon from a slots dict (or an empty 0/8 ribbon).

    If ``ribbon_id`` is not given, derive a deterministic id from the
    source hash and request id so that the same input produces the
    same ribbon hash.
    """
    if slots is None:
        slots = {}
    if ribbon_id is None:
        import hashlib as _hl
        d = _hl.sha256(
            (source_hash + "|" + created_by_request).encode("utf-8")
        ).hexdigest()
        ribbon_id = f"ribbon-{d[:16]}"
    return Ribbon(
        ribbon_id=ribbon_id,
        slots=dict(slots),
        arity=0,  # recomputed in __post_init__
        source_hash=source_hash,
        created_by_request=created_by_request,
    )


# ---------------------------------------------------------------------------
# Arity report
# ---------------------------------------------------------------------------


@dataclass
class ArityReport:
    """An arity report for a ribbon."""

    ribbon_id: str
    filled: List[str]
    missing: List[str]
    proof_bearing: List[str]
    obligated: List[str]
    arity: int
    is_complete: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ribbon_id": self.ribbon_id,
            "filled": list(self.filled),
            "missing": list(self.missing),
            "proof_bearing": list(self.proof_bearing),
            "obligated": list(self.obligated),
            "arity": self.arity,
            "is_complete": self.is_complete,
        }


# Slots that, when filled, count as proof-bearing
PROOF_BEARING = {"C", "L", "R", "B", "A"}
# Slots that, when missing, become obligations
OBLIGATED = {"C", "L", "R", "B", "A"}


def arity_report(ribbon: Ribbon) -> ArityReport:
    """Return the arity report for a ribbon."""
    filled = [k for k in SLOT_NAMES if k in ribbon.slots and ribbon.slots[k].status == "FILLED"]
    missing = [k for k in SLOT_NAMES if k not in filled]
    proof_bearing = [k for k in filled if k in PROOF_BEARING]
    obligated = [k for k in missing if k in OBLIGATED]
    return ArityReport(
        ribbon_id=ribbon.ribbon_id,
        filled=filled,
        missing=missing,
        proof_bearing=proof_bearing,
        obligated=obligated,
        arity=len(filled),
        is_complete=(len(missing) == 0),
    )
