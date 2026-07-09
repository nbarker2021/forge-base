"""
Receipt types.

Every kernel operation must produce a ``Receipt``. A receipt records
the input/output hashes, a status, an evidence class, and a payload
that downstream readers (socratic wrappers, replay engines, verifiers)
can inspect.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..core.status import EvidenceStatus, ReceiptStatus


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _receipt_id(
    event_type: str,
    input_hash: str,
    output_hash: str,
    request_id: Optional[str] = None,
) -> str:
    body = json.dumps(
        {
            "event_type": event_type,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "request_id": request_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _stable_hash(body)[:32]


@dataclass
class Receipt:
    """A single proof-bearing receipt."""

    receipt_id: str
    event_type: str
    input_hash: str
    output_hash: str
    status: ReceiptStatus
    evidence_class: EvidenceStatus
    timestamp: str
    payload: Dict[str, Any]
    receipt_hash: str = field(init=False)
    request_id: Optional[str] = None

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            self.status = ReceiptStatus(self.status)
        if isinstance(self.evidence_class, str):
            self.evidence_class = EvidenceStatus(self.evidence_class)
        body = json.dumps(
            {
                "receipt_id": self.receipt_id,
                "event_type": self.event_type,
                "input_hash": self.input_hash,
                "output_hash": self.output_hash,
                "status": self.status.value,
                "evidence_class": self.evidence_class.value,
                "timestamp": self.timestamp,
                "payload": self.payload,
                "request_id": self.request_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.receipt_hash = _stable_hash(body)

    @classmethod
    def new(
        cls,
        *,
        event_type: str,
        input_hash: str,
        output_hash: str,
        status: ReceiptStatus,
        evidence_class: EvidenceStatus,
        payload: Optional[Dict[str, Any]] = None,
        receipt_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> "Receipt":
        return cls(
            receipt_id=receipt_id or _receipt_id(event_type, input_hash, output_hash, request_id),
            event_type=event_type,
            input_hash=input_hash,
            output_hash=output_hash,
            status=status,
            evidence_class=evidence_class,
            timestamp=_utcnow_iso(),
            payload=dict(payload or {}),
            request_id=request_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "event_type": self.event_type,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "status": self.status.value,
            "evidence_class": self.evidence_class.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
            "receipt_hash": self.receipt_hash,
            "request_id": self.request_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Receipt":
        r = cls(
            receipt_id=data["receipt_id"],
            event_type=data["event_type"],
            input_hash=data["input_hash"],
            output_hash=data["output_hash"],
            status=ReceiptStatus(data["status"]),
            evidence_class=EvidenceStatus(data["evidence_class"]),
            timestamp=data["timestamp"],
            payload=dict(data.get("payload", {})),
            request_id=data.get("request_id"),
        )
        expected = data.get("receipt_hash")
        if expected and expected != r.receipt_hash:
            from ..core.errors import ReplayMismatch

            raise ReplayMismatch(
                f"receipt {r.receipt_id} hash mismatch: {expected} != {r.receipt_hash}"
            )
        return r
