"""
Snapshot store.

A snapshot bundles the source-bound hashes of a single observation
and writes them to ``.cqe/snapshots/<snapshot_id>.json``. A snapshot
is the unit of replay.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _stable_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Snapshot:
    """A single observation snapshot."""

    snapshot_id: str
    request_id: str
    source_hash: str
    carrier_hash: str
    ribbon_hash: str
    ledger_hash: str
    created_at: str
    parent_snapshot: Optional[str] = None
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "request_id": self.request_id,
            "source_hash": self.source_hash,
            "carrier_hash": self.carrier_hash,
            "ribbon_hash": self.ribbon_hash,
            "ledger_hash": self.ledger_hash,
            "created_at": self.created_at,
            "parent_snapshot": self.parent_snapshot,
            "extras": dict(self.extras),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Snapshot":
        return cls(
            snapshot_id=data["snapshot_id"],
            request_id=data["request_id"],
            source_hash=data["source_hash"],
            carrier_hash=data["carrier_hash"],
            ribbon_hash=data["ribbon_hash"],
            ledger_hash=data["ledger_hash"],
            created_at=data["created_at"],
            parent_snapshot=data.get("parent_snapshot"),
            extras=dict(data.get("extras", {})),
        )


def make_snapshot(
    *,
    request_id: str,
    source_hash: str,
    carrier_hash: str,
    ribbon_hash: str,
    ledger_hash: str,
    parent_snapshot: Optional[str] = None,
) -> Snapshot:
    return Snapshot(
        snapshot_id=str(uuid.uuid4()),
        request_id=request_id,
        source_hash=source_hash,
        carrier_hash=carrier_hash,
        ribbon_hash=ribbon_hash,
        ledger_hash=ledger_hash,
        created_at=_utcnow_iso(),
        parent_snapshot=parent_snapshot,
    )


def write_snapshot(snapshots_dir: Path, snapshot: Snapshot) -> Path:
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    path = snapshots_dir / f"{snapshot.snapshot_id}.json"
    path.write_text(
        json.dumps(snapshot.to_dict(), sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    return path


def read_snapshot(snapshots_dir: Path, snapshot_id: str) -> Snapshot:
    path = snapshots_dir / f"{snapshot_id}.json"
    return Snapshot.from_dict(json.loads(path.read_text(encoding="utf-8")))


def list_snapshots(snapshots_dir: Path) -> List[str]:
    if not snapshots_dir.exists():
        return []
    return sorted(p.stem for p in snapshots_dir.glob("*.json"))
