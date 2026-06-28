"""
Binary boundary adapter.

Every input must cross a stable binary boundary. The adapter takes
host objects, turns them into bytes, hashes them, and produces a
canonical payload frame that the rest of the kernel can ingest
deterministically.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


def _stable_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass
class BinaryBoundaryFrame:
    """Canonical payload frame.

    Example::

        {
          "frame_id": "...",
          "encoding": "utf-8",
          "byte_count": 1234,
          "sha256": "...",
          "payload_b64": "...",
          "source_type": "text",
          "adapter": "TextAdapter",
          "adapter_version": "0.1"
        }
    """

    frame_id: str
    encoding: str
    byte_count: int
    sha256: str
    payload_b64: str
    source_type: str
    adapter: str
    adapter_version: str
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "encoding": self.encoding,
            "byte_count": self.byte_count,
            "sha256": self.sha256,
            "payload_b64": self.payload_b64,
            "source_type": self.source_type,
            "adapter": self.adapter,
            "adapter_version": self.adapter_version,
            "extras": dict(self.extras),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BinaryBoundaryFrame":
        return cls(
            frame_id=data["frame_id"],
            encoding=data["encoding"],
            byte_count=int(data["byte_count"]),
            sha256=data["sha256"],
            payload_b64=data["payload_b64"],
            source_type=data["source_type"],
            adapter=data["adapter"],
            adapter_version=data.get("adapter_version", "0.1"),
            extras=dict(data.get("extras", {})),
        )

    def decode(self) -> bytes:
        return base64.b64decode(self.payload_b64.encode("ascii"))


def make_frame(
    *,
    payload: bytes,
    source_type: str,
    adapter: str,
    encoding: str = "utf-8",
    adapter_version: str = "0.1",
    extras: Optional[Dict[str, Any]] = None,
    frame_id: Optional[str] = None,
) -> BinaryBoundaryFrame:
    """Build a ``BinaryBoundaryFrame`` from raw bytes.

    If ``frame_id`` is not given, it is derived deterministically
    from the SHA256 of the payload. This keeps the frame identity
    a deterministic function of the request, so a ribbon's slot
    identities (and therefore the ribbon hash) are also
    deterministic.
    """
    if frame_id is None:
        frame_id = f"frame-{_stable_hash(payload)[:16]}"
    return BinaryBoundaryFrame(
        frame_id=frame_id,
        encoding=encoding,
        byte_count=len(payload),
        sha256=_stable_hash(payload),
        payload_b64=base64.b64encode(payload).decode("ascii"),
        source_type=source_type,
        adapter=adapter,
        adapter_version=adapter_version,
        extras=dict(extras or {}),
    )


def frame_to_json(frame: BinaryBoundaryFrame) -> str:
    return json.dumps(frame.to_dict(), sort_keys=True, separators=(",", ":"))


def verify_frame(frame: BinaryBoundaryFrame) -> bool:
    """Recompute the sha256 of the payload and compare to ``frame.sha256``."""
    raw = base64.b64decode(frame.payload_b64.encode("ascii"))
    return _stable_hash(raw) == frame.sha256 and len(raw) == frame.byte_count
