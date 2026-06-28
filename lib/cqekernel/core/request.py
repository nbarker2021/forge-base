"""
The ``ObservedRequest`` object.

In this system "no request, no C" — every kernel operation begins with an
observation that becomes part of the state. The request is hashed
immediately so that any later change to the raw text invalidates the
carrier.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class RequestMode(str, Enum):
    """Minimum set of request modes the kernel supports."""

    READ_ONLY = "READ_ONLY"
    LOOKUP_ONLY = "LOOKUP_ONLY"
    COMPUTE_IF_NEEDED = "COMPUTE_IF_NEEDED"
    REPLAY_ONLY = "REPLAY_ONLY"
    AUDIT = "AUDIT"
    WORKBOOK = "WORKBOOK"
    HOST_INSERT = "HOST_INSERT"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass
class ObservedRequest:
    """A request that has been observed by the kernel.

    The raw text is hashed at construction time. Mutating
    ``raw_text`` after construction does **not** update the hash; the
    request must be re-observed to change the carrier.
    """

    raw_text: str
    source_type: str = "text"
    observer_id: Optional[str] = None
    mode: RequestMode = RequestMode.READ_ONLY
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=_utcnow_iso)
    policy: Dict[str, Any] = field(default_factory=dict)
    raw_bytes: bytes = field(default=b"")
    raw_hash: str = field(default="")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.mode, str):
            self.mode = RequestMode(self.mode)
        # If raw_bytes was provided, use it; otherwise compute from raw_text
        if self.raw_bytes:
            self.raw_hash = _stable_hash(self.raw_bytes)
        else:
            self.raw_bytes = self.raw_text.encode("utf-8")
            self.raw_hash = _stable_hash(self.raw_bytes)

    def with_mode(self, mode: RequestMode) -> "ObservedRequest":
        """Return a new request with a different mode (immutable update)."""
        return ObservedRequest(
            raw_text=self.raw_text,
            source_type=self.source_type,
            observer_id=self.observer_id,
            mode=mode,
            policy=dict(self.policy),
            metadata=dict(self.metadata),
            raw_bytes=self.raw_bytes,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "raw_text": self.raw_text,
            "source_type": self.source_type,
            "timestamp": self.timestamp,
            "observer_id": self.observer_id,
            "mode": self.mode.value,
            "policy": dict(self.policy),
            "raw_hash": self.raw_hash,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ObservedRequest":
        return cls(
            raw_text=data["raw_text"],
            source_type=data.get("source_type", "text"),
            observer_id=data.get("observer_id"),
            mode=RequestMode(data.get("mode", "READ_ONLY")),
            request_id=data.get("request_id") or str(uuid.uuid4()),
            timestamp=data.get("timestamp") or _utcnow_iso(),
            policy=dict(data.get("policy", {})),
            metadata=dict(data.get("metadata", {})),
            raw_bytes=b"",  # will be computed from raw_text in __post_init__
        )
