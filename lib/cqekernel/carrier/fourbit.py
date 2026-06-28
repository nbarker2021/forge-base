"""
Canonical 4-bit carrier.

Takes a binary boundary frame and produces a deterministic nibble
sequence. The carrier always knows the first 4 bits, the last 4 bits,
all 4-bit windows, and the cyclic head/tail relation.
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


def _nibbles_from_bytes(data: bytes) -> List[str]:
    """Convert ``bytes`` to a list of 4-bit nibble strings, MSB first per byte."""
    out: List[str] = []
    for b in data:
        out.append(f"{(b >> 4) & 0xF:04b}")
        out.append(f"{b & 0xF:04b}")
    return out


def _stable_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass
class FourBitCarrier:
    """A canonical 4-bit carrier over a binary payload.

    The carrier always knows:

      * first 4 bits (``head_4bit``)
      * last 4 bits (``tail_4bit``)
      * all 4-bit windows (cyclic)
      * the canonical hash over the entire nibble stream
    """

    carrier_id: str
    source_hash: str
    nibbles: List[str]
    nibble_count: int
    head_4bit: str
    tail_4bit: str
    canonical_hash: str
    windows: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "carrier_id": self.carrier_id,
            "source_hash": self.source_hash,
            "nibbles": list(self.nibbles),
            "nibble_count": self.nibble_count,
            "head_4bit": self.head_4bit,
            "tail_4bit": self.tail_4bit,
            "canonical_hash": self.canonical_hash,
            "windows": list(self.windows),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FourBitCarrier":
        return cls(
            carrier_id=data["carrier_id"],
            source_hash=data["source_hash"],
            nibbles=list(data["nibbles"]),
            nibble_count=int(data["nibble_count"]),
            head_4bit=data["head_4bit"],
            tail_4bit=data["tail_4bit"],
            canonical_hash=data["canonical_hash"],
            windows=list(data.get("windows", [])),
        )


def from_bytes(source_hash: str, data: bytes) -> FourBitCarrier:
    """Build a ``FourBitCarrier`` from raw bytes."""
    nibbles = _nibbles_from_bytes(data)
    head = nibbles[0] if nibbles else "0000"
    tail = nibbles[-1] if nibbles else "0000"
    # All 4-bit windows of length 2 (head,tail), in cyclic form
    windows: List[str] = []
    if len(nibbles) >= 2:
        n = len(nibbles)
        for i in range(n):
            a = nibbles[i]
            b = nibbles[(i + 1) % n]
            windows.append(f"{a}{b}")
    canonical = json.dumps(
        {
            "source_hash": source_hash,
            "nibbles": nibbles,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return FourBitCarrier(
        carrier_id=str(uuid.uuid4()),
        source_hash=source_hash,
        nibbles=nibbles,
        nibble_count=len(nibbles),
        head_4bit=head,
        tail_4bit=tail,
        canonical_hash=_stable_hash(canonical),
        windows=windows,
    )


def from_payload_b64(source_hash: str, payload_b64: str) -> FourBitCarrier:
    """Build a ``FourBitCarrier`` from a base64 payload."""
    data = base64.b64decode(payload_b64.encode("ascii"))
    return from_bytes(source_hash, data)
