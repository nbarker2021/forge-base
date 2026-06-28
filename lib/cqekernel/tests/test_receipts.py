"""Unit tests for the receipt system."""

import unittest
from cqekernel import EvidenceStatus, ReceiptStatus
from cqekernel.ledger.receipt import Receipt
from cqekernel.core.errors import ReplayMismatch


class TestReceipt(unittest.TestCase):
    def test_hash_is_stable(self):
        r1 = Receipt.new(
            event_type="X", input_hash="i", output_hash="o",
            status=ReceiptStatus.PASS, evidence_class=EvidenceStatus.KERNEL_PRIMITIVE,
            payload={"a": 1, "b": [1, 2, 3]},
        )
        d = r1.to_dict()
        r2 = Receipt.from_dict(d)
        self.assertEqual(r1.receipt_hash, r2.receipt_hash)

    def test_status_enum_roundtrip(self):
        r = Receipt.new(
            event_type="X", input_hash="i", output_hash="o",
            status="PARTIAL", evidence_class="conj", payload={},
        )
        self.assertEqual(r.status, ReceiptStatus.PARTIAL)
        self.assertEqual(r.evidence_class, EvidenceStatus.CONJ)

    def test_tamper_detection(self):
        r = Receipt.new(
            event_type="X", input_hash="i", output_hash="o",
            status=ReceiptStatus.PASS, evidence_class=EvidenceStatus.KERNEL_PRIMITIVE,
            payload={"a": 1},
        )
        d = r.to_dict()
        d["receipt_hash"] = "0" * 64
        with self.assertRaises(ReplayMismatch):
            Receipt.from_dict(d)

    def test_payload_changes_hash(self):
        r1 = Receipt.new(event_type="X", input_hash="i", output_hash="o",
                          status=ReceiptStatus.PASS,
                          evidence_class=EvidenceStatus.KERNEL_PRIMITIVE,
                          payload={"x": 1})
        r2 = Receipt.new(event_type="X", input_hash="i", output_hash="o",
                          status=ReceiptStatus.PASS,
                          evidence_class=EvidenceStatus.KERNEL_PRIMITIVE,
                          payload={"x": 2})
        self.assertNotEqual(r1.receipt_hash, r2.receipt_hash)


if __name__ == "__main__":
    unittest.main()
