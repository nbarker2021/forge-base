"""
Local falsifier for the kernel's own primitives.

This is a stdlib-only falsifier harness that runs the kernel's
self-tests. The deeper math falsifiers live in optional firmware.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

from ..carrier.correction import verify_correction_identity
from ..carrier.cform import place, swap_lr
from ..carrier.fourbit import _nibbles_from_bytes  # type: ignore
from ..carrier.lcr import gluon_from_lcr, truth_table
from ..ledger.receipt import Receipt
from ..projection.observer_frame import check_governance, four_frames
from ..ribbon.slot import SLOT_NAMES, arity_report, make_ribbon, make_slot
from .honesty import summarize
from ..core.status import EvidenceStatus, ReceiptStatus


@dataclass
class FalsifierReport:
    name: str
    passed: bool
    details: Dict[str, object]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "details": dict(self.details),
        }


# Each test returns (passed: bool, details: dict)
TestFn = Callable[[], Tuple[bool, Dict[str, object]]]


def _test_lcr_truth_table() -> Tuple[bool, Dict[str, object]]:
    rows = truth_table()
    passed = len(rows) == 8 and all(r.window_key for r in rows)
    return passed, {"rows": len(rows)}


def _test_correction_identity() -> Tuple[bool, Dict[str, object]]:
    passed = bool(verify_correction_identity())
    return passed, {"checked": 8}


def _test_lr_swap_preserves_c() -> Tuple[bool, Dict[str, object]]:
    g = gluon_from_lcr(0, (1, 0, 1))
    p = place(g, "req-x")
    ps = swap_lr(p)
    passed = p.center == ps.center and ps.orientation == "swapped"
    return passed, {"orientation_after": ps.orientation}


def _test_shell_classification() -> Tuple[bool, Dict[str, object]]:
    counts = {"fixed_center": 0, "chiral_pair": 0, "boundary": 0}
    for r in truth_table():
        counts[r.state_class] = counts.get(r.state_class, 0) + 1
    passed = counts["boundary"] >= 1 and counts["fixed_center"] >= 1
    return passed, counts


def _test_head_tail_4bit() -> Tuple[bool, Dict[str, object]]:
    # bytes b"\xAC" -> nibbles 1010 1100
    nibbles = _nibbles_from_bytes(b"\xAC")
    head, tail = nibbles[0], nibbles[-1]
    passed = head == "1010" and tail == "1100"
    return passed, {"head": head, "tail": tail, "n": len(nibbles)}


def _test_receipt_hash_consistency() -> Tuple[bool, Dict[str, object]]:
    r1 = Receipt.new(
        event_type="TEST", input_hash="i", output_hash="o",
        status=ReceiptStatus.PASS, evidence_class=EvidenceStatus.KERNEL_PRIMITIVE,
        payload={"k": "v"},
    )
    j = r1.to_dict()
    r2 = Receipt.from_dict(j)
    passed = r1.receipt_hash == r2.receipt_hash
    return passed, {"hash": r1.receipt_hash[:16]}


def _test_ledger_replay() -> Tuple[bool, Dict[str, object]]:
    from pathlib import Path
    from tempfile import TemporaryDirectory

    from ..ledger.event import Event
    from ..ledger.replay import replay
    from ..ledger.snapshot import make_snapshot, write_snapshot
    from ..ledger.store import EventStore

    with TemporaryDirectory() as td:
        p = Path(td)
        s = EventStore(p / "events.jsonl")
        s.append(Event(event_type="REQUEST_OBSERVED"))
        s.append(Event(event_type="RIBBON_CREATED"))
        snap = make_snapshot(
            request_id="r", source_hash="s", carrier_hash="c",
            ribbon_hash="r", ledger_hash=s.hash_chain(),
        )
        write_snapshot(p / "snapshots", snap)
        res = replay(
            p / "snapshots", snap.snapshot_id,
            lambda sh: {"source_hash": sh, "carrier_hash": "c",
                        "ribbon_hash": "r", "ledger_hash": s.hash_chain()},
            ledger=s,
        )
        return res.passed, {"mismatches": res.mismatches}


def _test_ribbon_arity() -> Tuple[bool, Dict[str, object]]:
    slots = {k: make_slot(k, {"v": 1}) for k in SLOT_NAMES}
    rb = make_ribbon(source_hash="s", created_by_request="r", slots=slots)
    rep = arity_report(rb)
    passed = rep.is_complete and rep.arity == 8
    return passed, {"arity": rep.arity, "complete": rep.is_complete}


def _test_observer_governance() -> Tuple[bool, Dict[str, object]]:
    frames = four_frames("c", selected_index=2, obligation_id_prefix="obl")
    passed = check_governance(frames)
    return passed, {"selected": [f.frame_name for f in frames if f.selected]}


def _test_honesty_classifier() -> Tuple[bool, Dict[str, object]]:
    s1 = summarize(EvidenceStatus.KERNEL_PRIMITIVE, ReceiptStatus.PASS, [])
    s2 = summarize(EvidenceStatus.CONJ, ReceiptStatus.PASS, [])
    s3 = summarize(EvidenceStatus.SPEC_ONLY, ReceiptStatus.PARTIAL, [])
    passed = s1.honesty == "PASS" and s2.honesty == "DEFERRED" and s3.honesty == "PARTIAL"
    return passed, {"s1": s1.honesty, "s2": s2.honesty, "s3": s3.honesty}


def run_all() -> List[FalsifierReport]:
    """Run the full falsifier suite and return a list of reports."""
    tests: List[Tuple[str, TestFn]] = [
        ("lcr_truth_table", _test_lcr_truth_table),
        ("correction_identity", _test_correction_identity),
        ("lr_swap_preserves_c", _test_lr_swap_preserves_c),
        ("shell_classification", _test_shell_classification),
        ("head_tail_4bit", _test_head_tail_4bit),
        ("receipt_hash_consistency", _test_receipt_hash_consistency),
        ("ledger_replay", _test_ledger_replay),
        ("ribbon_arity", _test_ribbon_arity),
        ("observer_governance", _test_observer_governance),
        ("honesty_classifier", _test_honesty_classifier),
    ]
    reports: List[FalsifierReport] = []
    for name, fn in tests:
        try:
            passed, details = fn()
        except Exception as e:
            passed, details = False, {"error": str(e)}
        reports.append(FalsifierReport(name=name, passed=passed, details=details))
    return reports


def all_passed(reports: List[FalsifierReport]) -> bool:
    return all(r.passed for r in reports)
