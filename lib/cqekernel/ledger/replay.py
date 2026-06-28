"""
Replay engine.

Replay rebuilds the state from a snapshot + a function that re-observes
the source, then compares the recomputed hashes against the snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .snapshot import read_snapshot
from .store import EventStore


@dataclass
class ReplayResult:
    snapshot_id: str
    passed: bool
    expected_hashes: Dict[str, str]
    actual_hashes: Dict[str, str]
    mismatches: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "passed": self.passed,
            "expected_hashes": dict(self.expected_hashes),
            "actual_hashes": dict(self.actual_hashes),
            "mismatches": list(self.mismatches),
        }


# A "rebuild" callable takes a snapshot's source_hash and returns the
# recomputed hashes. The kernel wires this in via the observe flow.
RebuildFn = Callable[[str], Dict[str, str]]


def replay(
    snapshots_dir: Path,
    snapshot_id: str,
    rebuild: RebuildFn,
    *,
    ledger: Optional[EventStore] = None,
) -> ReplayResult:
    """Replay a snapshot.

    1. Load the snapshot
    2. Re-derive the recomputed hashes via ``rebuild(source_hash)``
    3. Optionally also recompute the ledger hash chain
    4. Compare and return a ``ReplayResult``
    """
    snap = read_snapshot(snapshots_dir, snapshot_id)
    actual = rebuild(snap.source_hash)
    if ledger is not None:
        actual["ledger_hash"] = ledger.hash_chain()
    expected = {
        "source_hash": snap.source_hash,
        "carrier_hash": snap.carrier_hash,
        "ribbon_hash": snap.ribbon_hash,
        "ledger_hash": snap.ledger_hash,
    }
    mismatches: List[str] = []
    for k in expected:
        if expected[k] != actual.get(k):
            mismatches.append(f"{k}: expected={expected[k]} actual={actual.get(k)}")
    return ReplayResult(
        snapshot_id=snapshot_id,
        passed=(len(mismatches) == 0),
        expected_hashes=expected,
        actual_hashes=actual,
        mismatches=mismatches,
    )
