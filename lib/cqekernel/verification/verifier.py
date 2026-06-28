"""
Verifier: a thin wrapper that runs the falsifier suite and produces a
single ``Receipt`` that downstream readers can consume.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..core.status import EvidenceStatus, ReceiptStatus
from ..ledger.receipt import Receipt
from .falsifier import FalsifierReport, all_passed, run_all


@dataclass
class VerifierResult:
    receipt: Receipt
    reports: List[FalsifierReport]

    def to_dict(self) -> dict:
        return {
            "receipt": self.receipt.to_dict(),
            "reports": [r.to_dict() for r in self.reports],
        }


def verify(input_hash: str = "kernel", output_hash: str = "kernel") -> VerifierResult:
    """Run all kernel falsifiers and produce a verifying receipt."""
    reports = run_all()
    passed = all_passed(reports)
    status = ReceiptStatus.PASS if passed else ReceiptStatus.FAIL
    payload = {"reports": [r.to_dict() for r in reports]}
    receipt = Receipt.new(
        event_type="KERNEL_VERIFIED",
        input_hash=input_hash,
        output_hash=output_hash,
        status=status,
        evidence_class=EvidenceStatus.KERNEL_PRIMITIVE,
        payload=payload,
    )
    return VerifierResult(receipt=receipt, reports=reports)
