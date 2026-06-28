"""
Append-only event types for the kernel ledger.

Every event is a small dict that is appended as a single JSON line to
``runtime/ledger/events.jsonl`` (or wherever the workspace is
configured).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


# Canonical event types. Adding a new event? Add it here AND to the
# kernel's emitter so receipts stay consistent.
EVENT_TYPES: List[str] = [
    "REQUEST_OBSERVED",
    "BOUNDARY_FRAME_CREATED",
    "FOURBIT_ENCODED",
    "C_FORM_CREATED",
    "ADMISSION_SPLIT",
    "LCR_GLUON_STREAM",
    "LCR_ENVELOPE",
    "LCR_PLACED",
    "CORRECTION_COMPUTED",
    "RIBBON_CREATED",
    "FRAME_PROJECTED",
    "BOUNDARY_APERTURE_DETECTED",
    "FIRMWARE_CALLED",
    "RECEIPT_WRITTEN",
    "SNAPSHOT_CREATED",
    "REPLAY_VERIFIED",
    "OBLIGATION_CREATED",
]


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Event:
    """One append-only ledger event.

    The ``event_type`` is validated against the canonical
    ``EVENT_TYPES`` registry at construction time. This is a
    kernel-level invariant: the ledger is a closed type system, and
    an event whose type is not in the registry cannot be replayed,
    cannot be queried, and is a sign of a buggy emitter.
    """

    event_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=_utcnow_iso)
    request_id: Optional[str] = None
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None

    def __post_init__(self) -> None:
        if self.event_type not in EVENT_TYPES:
            from ..core.errors import KernelPolicyError
            raise KernelPolicyError(
                f"unknown event_type {self.event_type!r}; "
                f"must be one of {EVENT_TYPES}"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
            "request_id": self.request_id,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            event_type=data["event_type"],
            payload=dict(data.get("payload", {})),
            event_id=data.get("event_id") or str(uuid.uuid4()),
            timestamp=data.get("timestamp") or _utcnow_iso(),
            request_id=data.get("request_id"),
            input_hash=data.get("input_hash"),
            output_hash=data.get("output_hash"),
        )
