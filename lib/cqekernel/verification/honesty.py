"""
Honesty classifier.

A small helper that turns an evidence class and a slot list into a
single honesty summary: PASS / PARTIAL / DEFERRED / SPEC_ONLY.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..core.status import EvidenceStatus, ReceiptStatus


@dataclass
class HonestySummary:
    honesty: str
    evidence: str
    receipt: str
    notes: List[str]

    def to_dict(self) -> dict:
        return {
            "honesty": self.honesty,
            "evidence": self.evidence,
            "receipt": self.receipt,
            "notes": list(self.notes),
        }


_PASS = {EvidenceStatus.KERNEL_PRIMITIVE, EvidenceStatus.BOUNDED_EXEC,
         EvidenceStatus.LOOKUP_BACKED, EvidenceStatus.FIRMWARE_BACKED,
         EvidenceStatus.WORKBOOK_BACKED}
_PARTIAL = {EvidenceStatus.PASS_WITH_OPEN_GAPS, EvidenceStatus.SPEC_ONLY}
_DEFERRED = {EvidenceStatus.CONJ, EvidenceStatus.EXTERNAL_REQUIRED}


def summarize(
    evidence: EvidenceStatus,
    receipt: ReceiptStatus,
    notes: List[str],
) -> HonestySummary:
    """Map an evidence class and receipt status to an honesty string."""
    if receipt == ReceiptStatus.FAIL:
        h = "FAIL"
    elif evidence in _PASS and receipt == ReceiptStatus.PASS:
        h = "PASS"
    elif evidence in _PARTIAL:
        h = "PARTIAL"
    elif evidence in _DEFERRED:
        h = "DEFERRED"
    elif receipt == ReceiptStatus.UNKNOWN:
        h = "UNKNOWN"
    else:
        h = "PASS_WITH_OPEN_GAPS"
    return HonestySummary(honesty=h, evidence=evidence.value, receipt=receipt.value, notes=notes)
