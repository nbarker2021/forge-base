"""Unit tests for the replay engine."""

import tempfile
import unittest
from pathlib import Path

from cqekernel.ledger.event import Event
from cqekernel.ledger.replay import replay
from cqekernel.ledger.snapshot import make_snapshot, write_snapshot
from cqekernel.ledger.store import EventStore


class TestReplay(unittest.TestCase):
    def test_replay_pass(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            s = EventStore(p / "events.jsonl")
            s.append(Event(event_type="REQUEST_OBSERVED"))
            s.append(Event(event_type="RIBBON_CREATED"))
            snap = make_snapshot(
                request_id="r", source_hash="S", carrier_hash="C",
                ribbon_hash="R", ledger_hash=s.hash_chain(),
            )
            write_snapshot(p / "snapshots", snap)
            res = replay(
                p / "snapshots", snap.snapshot_id,
                rebuild=lambda sh: {
                    "source_hash": sh, "carrier_hash": "C",
                    "ribbon_hash": "R", "ledger_hash": s.hash_chain(),
                },
                ledger=s,
            )
            self.assertTrue(res.passed)
            self.assertEqual(res.mismatches, [])

    def test_replay_mismatch_detected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            s = EventStore(p / "events.jsonl")
            s.append(Event(event_type="REQUEST_OBSERVED"))
            snap = make_snapshot(
                request_id="r", source_hash="S", carrier_hash="C",
                ribbon_hash="R", ledger_hash=s.hash_chain(),
            )
            write_snapshot(p / "snapshots", snap)
            res = replay(
                p / "snapshots", snap.snapshot_id,
                rebuild=lambda sh: {
                    "source_hash": "WRONG", "carrier_hash": "C",
                    "ribbon_hash": "R", "ledger_hash": s.hash_chain(),
                },
                ledger=s,
            )
            self.assertFalse(res.passed)
            self.assertTrue(any("source_hash" in m for m in res.mismatches))

    def test_ledger_chain_changes_with_event(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            s = EventStore(p / "events.jsonl")
            s.append(Event(event_type="REQUEST_OBSERVED"))
            h1 = s.hash_chain()
            s.append(Event(event_type="RIBBON_CREATED"))
            h2 = s.hash_chain()
            self.assertNotEqual(h1, h2)


if __name__ == "__main__":
    unittest.main()
