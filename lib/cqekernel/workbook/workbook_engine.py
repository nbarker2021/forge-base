"""
Workbook engine: produce and verify the workbook protocol.

The kernel does not see the paper. It produces the protocol as a list
of ``AnalogStep`` records and verifies that each expected_receipt
event_type is among the kernel's known event types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..ledger.event import EVENT_TYPES
from .analog_schema import DEFAULT_WORKBOOK, AnalogStep


@dataclass
class WorkbookProtocol:
    name: str
    steps: List[AnalogStep]
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "steps": [s.to_dict() for s in self.steps],
            "extras": dict(self.extras),
        }


def default_workbook() -> WorkbookProtocol:
    """Return the default 6-step protocol."""
    return WorkbookProtocol(name="cqe-default", steps=list(DEFAULT_WORKBOOK))


@dataclass
class WorkbookCheck:
    protocol: str
    steps: int
    valid: int
    invalid: int
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol": self.protocol,
            "steps": self.steps,
            "valid": self.valid,
            "invalid": self.invalid,
            "notes": list(self.notes),
        }


def check_protocol(protocol: WorkbookProtocol) -> WorkbookCheck:
    """Verify the protocol: every expected_receipt must be a known event type."""
    valid = 0
    invalid = 0
    notes: List[str] = []
    for s in protocol.steps:
        if s.expected_receipt in EVENT_TYPES:
            valid += 1
        else:
            invalid += 1
            notes.append(f"step {s.step_id[:8]} expects unknown event {s.expected_receipt!r}")
    if invalid:
        notes.append("protocol has unresolved event-type references")
    return WorkbookCheck(
        protocol=protocol.name,
        steps=len(protocol.steps),
        valid=valid,
        invalid=invalid,
        notes=notes,
    )
