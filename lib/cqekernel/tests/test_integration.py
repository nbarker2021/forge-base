"""End-to-end kernel integration tests.

These tests cover the full observe -> ribbon -> replay pipeline,
the gate, the 2x2 boundary aperture, the determinism invariants
for both text and bytes payloads, and the bidirectional query API.
"""

import tempfile
import unittest
from pathlib import Path

from cqekernel import (
    EvidenceStatus,
    Kernel,
    ObservedRequest,
    Policy,
    ReceiptStatus,
    RequestMode,
)
from cqekernel.carrier.lcr import admit, gluon_from_lcr
from cqekernel.projection.boundary_aperture import detect_from_gluons


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.anchor = self.tmp.name
        self.kernel = Kernel(anchor=self.anchor)

    def tearDown(self):
        self.tmp.cleanup()

    def test_observe_produces_full_8_ribbon(self):
        res = self.kernel.observe("integration test", mode=RequestMode.AUDIT)
        self.assertEqual(res.arity, 8)
        self.assertEqual(len(res.gluons), len(res.cforms))
        self.assertTrue(res.extras["frame_governance_ok"])
        self.assertTrue(res.extras["closure_closed"])

    def test_admission_class_counts_are_real(self):
        """The gate must actually run, not return a placeholder."""
        res = self.kernel.observe("gate test", mode=RequestMode.AUDIT)
        counts = res.extras["admission_class_counts"]
        # At least one class should be non-zero
        self.assertGreater(sum(counts.values()), 0)
        # All counts should sum to total gluon count
        self.assertEqual(
            sum(counts.values()),
            len(res.gluons),
        )

    def test_determinism_text_payload(self):
        r1 = self.kernel.observe("same input", mode=RequestMode.AUDIT)
        r2 = self.kernel.observe("same input", mode=RequestMode.AUDIT)
        self.assertEqual(r1.ribbon_hash, r2.ribbon_hash)
        # Different input -> different ribbon hash
        r3 = self.kernel.observe("different input", mode=RequestMode.AUDIT)
        self.assertNotEqual(r1.ribbon_hash, r3.ribbon_hash)

    def test_determinism_bytes_payload(self):
        """Bytes payloads must also be deterministic."""
        data = b"\x00\x01\x02\x03binary payload"
        r1 = self.kernel.observe(data, mode=RequestMode.READ_ONLY)
        r2 = self.kernel.observe(data, mode=RequestMode.READ_ONLY)
        self.assertEqual(r1.ribbon_hash, r2.ribbon_hash)

    def test_bytes_payload_does_not_roundtrip_through_utf8(self):
        """Non-UTF-8 bytes must survive observe() without corruption."""
        # Construct bytes that are NOT valid UTF-8
        bad = b"\xff\xfe\xfd\xfc"
        res = self.kernel.observe(bad, mode=RequestMode.READ_ONLY)
        # The frame byte_count should equal 4 (the original size)
        self.assertEqual(res.frame.byte_count, 4)
        # The carrier canonical hash should be deterministic
        r2 = self.kernel.observe(bad, mode=RequestMode.READ_ONLY)
        self.assertEqual(res.carrier.canonical_hash, r2.carrier.canonical_hash)

    def test_request_modes(self):
        for mode in (RequestMode.READ_ONLY, RequestMode.LOOKUP_ONLY,
                     RequestMode.COMPUTE_IF_NEEDED, RequestMode.REPLAY_ONLY,
                     RequestMode.AUDIT, RequestMode.WORKBOOK, RequestMode.HOST_INSERT):
            res = self.kernel.observe(f"mode {mode.value}", mode=mode)
            self.assertEqual(res.request.mode, mode)

    def test_host_insert_mode_end_to_end(self):
        """HOST_INSERT mode is the JSON packet protocol path."""
        res = self.kernel.observe_packet({
            "op": "observe",
            "payload": "host insert test",
            "mode": "HOST_INSERT",
        })
        self.assertEqual(res.arity, 8)
        self.assertEqual(res.request.mode, RequestMode.HOST_INSERT)
        self.assertEqual(res.request.source_type, "host_packet")

    def test_receipts_for_request(self):
        res = self.kernel.observe("query test", mode=RequestMode.AUDIT)
        req_receipts = self.kernel.receipts_for_request(res.request.request_id)
        # Should include all 12 event types for this observation
        self.assertGreaterEqual(len(req_receipts), 12)
        event_types = {r.event_type for r in req_receipts}
        for et in ("REQUEST_OBSERVED", "RIBBON_CREATED", "SNAPSHOT_CREATED",
                   "ADMISSION_SPLIT", "OBLIGATION_CREATED"):
            self.assertIn(et, event_types)

    def test_receipts_for_snapshot(self):
        res = self.kernel.observe("snapshot query test", mode=RequestMode.AUDIT)
        snap_receipts = self.kernel.receipts_for_snapshot(res.snapshot_id)
        self.assertEqual(len(snap_receipts), 1)
        self.assertEqual(snap_receipts[0].event_type, "SNAPSHOT_CREATED")

    def test_obligations_for_request(self):
        res = self.kernel.observe("obligations query test", mode=RequestMode.AUDIT)
        obs = self.kernel.obligations_for_request(res.request.request_id)
        self.assertEqual(len(obs), 3)
        for ob in obs:
            self.assertEqual(ob["status"], "OPEN")
            self.assertEqual(ob["source_request_id"], res.request.request_id)

    def test_get_snapshot_roundtrip(self):
        res = self.kernel.observe("snapshot roundtrip", mode=RequestMode.AUDIT)
        snap = self.kernel.get_snapshot(res.snapshot_id)
        self.assertEqual(snap.snapshot_id, res.snapshot_id)
        self.assertEqual(snap.ribbon_hash, res.ribbon_hash)
        self.assertEqual(snap.request_id, res.request.request_id)

    def test_event_type_validator_rejects_unknown(self):
        """The Event constructor must reject unknown event types."""
        from cqekernel.core.errors import KernelPolicyError
        from cqekernel.ledger.event import Event
        with self.assertRaises(KernelPolicyError):
            Event(event_type="UNKNOWN_TYPE")
        # But a real one is fine
        ev = Event(event_type="REQUEST_OBSERVED")
        self.assertEqual(ev.event_type, "REQUEST_OBSERVED")

    def test_lcr_swap_preserves_center(self):
        """swap_lr should preserve the center state."""
        g = gluon_from_lcr(0, (1, 0, 1))
        from cqekernel.carrier.cform import place, swap_lr
        p = place(g, "req")
        ps = swap_lr(p)
        self.assertEqual(p.center, ps.center)
        self.assertNotEqual(p.left, ps.left)

    def test_2x2_boundary_aperture_detection(self):
        """Craft a gluon stream that should fire the 2x2 cell detector."""
        # (0,1,0) and (0,1,0) are both boundary cells. The 2x2 join
        # condition is R==L' AND cell in {(0,1,0,1,0,1), (1,0,1,0,1,0)}.
        # Here R=0 and L'=0, so the join holds but the cell value is
        # (0,1,0,0,1,0) which is NOT in the (0,1,0,1,0,1) pattern.
        # So adjacent_lcr does NOT fire — only head_tail_4bit and
        # the per-gluon apertures do.
        gluons = [
            gluon_from_lcr(0, (0, 1, 0)),
            gluon_from_lcr(1, (0, 1, 0)),
        ]
        apertures = detect_from_gluons(gluons, tail_4bit="0000")
        kinds = {a.kind for a in apertures}
        # Per-gluon apertures: (0,1,0) has correction=1 (C=1, NOT R=1=1)
        self.assertIn("correction_firing", kinds)
        # head_tail_4bit is always emitted
        self.assertIn("head_tail_4bit", kinds)

    def test_2x2_actual_join_pattern(self):
        """The 2x2 detector requires the (0,1,0,1,0,1) or (1,0,1,0,1,0)
        alternating pattern to fire."""
        # (0,1,0) then (1,0,1) is the canonical alternating boundary
        # cell pattern.
        gluons = [
            gluon_from_lcr(0, (0, 1, 0)),
            gluon_from_lcr(1, (1, 0, 1)),
        ]
        apertures = detect_from_gluons(gluons, tail_4bit="0000")
        kinds = {a.kind for a in apertures}
        self.assertIn("adjacent_lcr", kinds)

    def test_admit_classifies_each_lcr_triple(self):
        """The gate returns a real classification for every triple."""
        for lcr in [(0,0,0), (0,0,1), (0,1,0), (0,1,1),
                    (1,0,0), (1,0,1), (1,1,0), (1,1,1)]:
            g = gluon_from_lcr(0, lcr)
            r = admit(g)
            # The result must be a real AdmissionResult
            self.assertIsNotNone(r.admission_class)
            # The complement should always be present
            self.assertIn("value", r.complement)

    def test_falsifier_suite_via_kernel(self):
        """Kernel.verify_kernel() runs the 10 falsifier tests."""
        v = self.kernel.verify_kernel()
        all_ok = all(r["passed"] for r in v["reports"])
        self.assertTrue(all_ok, f"falsifier reports: {v['reports']}")
        self.assertEqual(len(v["reports"]), 10)

    def test_workbook_default_validates(self):
        wb = self.kernel.workbook_check()
        # workbook_check() returns WorkbookCheck object, not dict
        self.assertEqual(wb.valid, 6)
        self.assertEqual(wb.invalid, 0)

    def test_firmware_manifest_discovered(self):
        fm = self.kernel.firmware_manifest()
        # firmware_manifest returns dict keyed by pack_id, test expects "packs" list
        packs = fm.get("packs") or list(fm.values())
        self.assertGreater(len(packs), 0)
        for p in packs:
            self.assertIn("pack_id", p)
            self.assertIn("available", p)


if __name__ == "__main__":
    unittest.main()
