"""Immutable syndrome checkpoint log with 64-bit IDs.

Every system state transition is recorded with a tamper-evident 64-bit ID
that encodes: source syndrome (3 bits), target syndrome (3 bits),
chart state source (4 bits), chart state target (4 bits), and a
monotonic sequence number (50 bits).

The checkpoint ledger is append-only and cryptographically chained
like a blockchain — each checkpoint includes the hash of the previous,
making tampering detectable.
"""

from __future__ import annotations

import hashlib
import json
import struct
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Checkpoint:
    """One immutable syndrome checkpoint.

    Each checkpoint represents a detected system state and its
    mathematical signature at a point in time.
    """

    sequence: int                          # monotonic sequence number
    timestamp: float                       # Unix timestamp with microsecond precision
    syndrome_index: int                    # 0-7: which of the 8 syndromes
    triad: tuple[int, int, int]            # the actual LCR triad
    chart_state: str                       # current chart state name
    emission: int                          # Rule 30 emission bit
    correction: int                        # correction against Rule 90
    lie_conjugate: bool                    # whether triad is Lie-conjugate stable
    geometry_level: int                    # 0=deep invariant, 1=level1, 2=variable
    previous_hash: str                     # SHA-256 of previous checkpoint (empty for genesis)
    metadata: dict[str, Any] = field(default_factory=dict)  # extra system data

    @property
    def checkpoint_id(self) -> int:
        """Compute the 64-bit checkpoint ID.

        Layout (64 bits):
            bits 63-61 : syndrome_index (3 bits)
            bits 60-58 : geometry_level (3 bits)
            bits 57-50 : emission << 1 | correction (2 bits) + chart index (6 bits)
            bits 49-0  : sequence number (50 bits)
        """
        chart_idx = self._chart_index()
        sig_bits = (self.syndrome_index << 61) | (self.geometry_level << 58)
        sig_bits |= ((self.emission << 1) | self.correction) << 56
        sig_bits |= chart_idx << 50
        sig_bits |= self.sequence & ((1 << 50) - 1)
        return sig_bits

    def _chart_index(self) -> int:
        chart_states = [
            "rotate_0", "rotate_90", "rotate_180", "rotate_270",
            "mirror_rotate_0", "mirror_rotate_90", "mirror_rotate_180", "mirror_rotate_270",
        ]
        try:
            return chart_states.index(self.chart_state)
        except ValueError:
            return 0

    @property
    def hash(self) -> str:
        """SHA-256 of this checkpoint's canonical serialization."""
        payload = {
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "syndrome_index": self.syndrome_index,
            "triad": list(self.triad),
            "chart_state": self.chart_state,
            "emission": self.emission,
            "correction": self.correction,
            "lie_conjugate": self.lie_conjugate,
            "geometry_level": self.geometry_level,
            "previous_hash": self.previous_hash,
            "metadata": self.metadata,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "hash": self.hash,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "syndrome_index": self.syndrome_index,
            "triad": list(self.triad),
            "chart_state": self.chart_state,
            "emission": self.emission,
            "correction": self.correction,
            "lie_conjugate": self.lie_conjugate,
            "geometry_level": self.geometry_level,
            "previous_hash": self.previous_hash,
            "metadata": self.metadata,
        }


def compute_64bit_id(
    syndrome_index: int,
    geometry_level: int,
    emission: int,
    correction: int,
    chart_index: int,
    sequence: int,
) -> int:
    """Compute a 64-bit ID encoding all syndrome state components."""
    cid = (syndrome_index << 61) | (geometry_level << 58)
    cid |= ((emission << 1) | correction) << 56
    cid |= chart_index << 50
    cid |= sequence & ((1 << 50) - 1)
    return cid


class CheckpointLedger:
    """Append-only, tamper-evident checkpoint ledger.

    Every checkpoint includes the hash of the previous checkpoint,
    forming a cryptographic chain. If any checkpoint is modified,
    all subsequent hashes become invalid.
    """

    def __init__(self, path: Path | None = None):
        self.path = path
        self.checkpoints: list[Checkpoint] = []
        self._sequence = 0
        if path is not None and path.exists():
            self._load()

    @property
    def last_hash(self) -> str:
        if not self.checkpoints:
            return ""
        return self.checkpoints[-1].hash

    def append(
        self,
        syndrome_index: int,
        triad: tuple[int, int, int],
        chart_state: str,
        emission: int,
        correction: int,
        lie_conjugate: bool,
        geometry_level: int,
        metadata: dict[str, Any] | None = None,
    ) -> Checkpoint:
        """Append a new checkpoint to the ledger."""
        self._sequence += 1
        cp = Checkpoint(
            sequence=self._sequence,
            timestamp=time.time(),
            syndrome_index=syndrome_index,
            triad=triad,
            chart_state=chart_state,
            emission=emission,
            correction=correction,
            lie_conjugate=lie_conjugate,
            geometry_level=geometry_level,
            previous_hash=self.last_hash,
            metadata=metadata or {},
        )
        self.checkpoints.append(cp)
        if self.path is not None:
            self._persist()
        return cp

    def verify_chain(self) -> dict[str, Any]:
        """Verify the cryptographic integrity of the checkpoint chain."""
        if not self.checkpoints:
            return {"status": "empty", "valid": True, "checkpoints": 0}

        broken_at: list[int] = []
        for i in range(1, len(self.checkpoints)):
            if self.checkpoints[i].previous_hash != self.checkpoints[i - 1].hash:
                broken_at.append(i)

        # Also verify that checkpoint IDs are monotonically increasing
        non_monotonic: list[int] = []
        for i in range(1, len(self.checkpoints)):
            if self.checkpoints[i].checkpoint_id <= self.checkpoints[i - 1].checkpoint_id:
                non_monotonic.append(i)

        return {
            "status": "pass" if not broken_at and not non_monotonic else "tampered",
            "valid": not broken_at and not non_monotonic,
            "checkpoints": len(self.checkpoints),
            "chain_breaks": broken_at,
            "non_monotonic_ids": non_monotonic,
            "latest_hash": self.last_hash,
        }

    def get_range(self, start: int, end: int) -> list[Checkpoint]:
        return self.checkpoints[start:end]

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_count": len(self.checkpoints),
            "latest_sequence": self._sequence,
            "latest_hash": self.last_hash,
            "chain_integrity": self.verify_chain(),
            "checkpoints": [cp.to_dict() for cp in self.checkpoints[-100:]],  # last 100
        }

    def _persist(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "ledger": [cp.to_dict() for cp in self.checkpoints],
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _load(self) -> None:
        if self.path is None or not self.path.exists():
            return
        payload = json.loads(self.path.read_text())
        if payload.get("schema_version") != 1:
            raise ValueError("unsupported checkpoint ledger schema")
        for item in payload.get("ledger", []):
            cp = Checkpoint(
                sequence=item["sequence"],
                timestamp=item["timestamp"],
                syndrome_index=item["syndrome_index"],
                triad=tuple(item["triad"]),
                chart_state=item["chart_state"],
                emission=item["emission"],
                correction=item["correction"],
                lie_conjugate=item["lie_conjugate"],
                geometry_level=item["geometry_level"],
                previous_hash=item["previous_hash"],
                metadata=item.get("metadata", {}),
            )
            self.checkpoints.append(cp)
            self._sequence = max(self._sequence, cp.sequence)
