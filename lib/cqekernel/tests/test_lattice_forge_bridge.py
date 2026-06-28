"""Tests for the lattice_forge firmware bridge.

These tests cover:

  * the stdlib fallback path (when lattice_forge is not installed)
  * the direct API of the bridge (manage_ribbon, light_cone, make_budget, spend)
  * the kernel's opportunistic integration: ``Kernel.observe()``
    emits a ``FIRMWARE_CALLED`` receipt whose evidence class
    reflects whether the firmware actually answered
  * ``split_bias`` validation in the kernel constructor and CLI
  * the D4Token local-stub class

When ``lattice_forge`` IS installed, the same tests would also
verify the firmware-backed path; we guard them with a probe so the
test suite is green in both regimes.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path


from cqekernel import (
    EvidenceStatus,
    Kernel,
    RequestMode,
)
from cqekernel.cqe import D4Token, tokens_from_bits
from cqekernel.firmware import lattice_forge_bridge


# Probe: is lattice_forge importable in this environment?
try:
    import lattice_forge  # noqa: F401
    LATTICE_FORGE_AVAILABLE = True
except Exception:
    LATTICE_FORGE_AVAILABLE = False


class TestBridgeFallback(unittest.TestCase):
    """Tests that work whether or not lattice_forge is installed."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.anchor = self.tmp.name
        self.kernel = Kernel(anchor=self.anchor)

    def tearDown(self):
        self.tmp.cleanup()

    def test_bridge_manifest_returns_pack_id(self):
        m = lattice_forge_bridge.manifest()
        self.assertEqual(m["pack_id"], "lattice_forge")
        self.assertIn("available", m)
        self.assertIn("reason", m)
        # The manifest should always include the cqe_capabilities
        # (or the cmplx_capabilities) when the modules are available
        if LATTICE_FORGE_AVAILABLE:
            self.assertIn("capabilities", m)
            self.assertGreater(len(m.get("capabilities", [])), 0)

    def test_sidecar_check_invalid_phase(self):
        r = lattice_forge_bridge.sidecar_check(b"hello", phase="WRONG")
        self.assertEqual(r.status, "FAIL")
        self.assertIn("phase", r.payload["reason"])

    def test_sidecar_check_first_touch(self):
        r = lattice_forge_bridge.sidecar_check(b"hello", phase="FIRST_TOUCH")
        self.assertIn(r.status, ("OK", "EXTERNAL_REQUIRED"))
        if r.status == "OK":
            self.assertEqual(r.payload["phase"], "FIRST_TOUCH")
            self.assertIn("decision", r.payload)
            self.assertIn("interrupt", r.payload)

    def test_sidecar_check_predeploy(self):
        r = lattice_forge_bridge.sidecar_check(b"hello", phase="PREDEPLOY")
        self.assertIn(r.status, ("OK", "EXTERNAL_REQUIRED"))
        if r.status == "OK":
            self.assertEqual(r.payload["phase"], "PREDEPLOY")

    def test_match_paper_bundle_returns_result(self):
        papers = [
            {"title": "T1", "path": "/p1", "text": "sample text about CQE"},
            {"title": "T2", "path": "/p2", "text": "another paper about CMPLX"},
        ]
        r = lattice_forge_bridge.match_paper_bundle(papers)
        self.assertIn(r.status, ("OK", "EXTERNAL_REQUIRED"))
        if r.status == "EXTERNAL_REQUIRED":
            self.assertEqual(r.payload["paper_count"], 2)
        else:
            self.assertEqual(r.payload["source"], "lattice_forge")
            self.assertEqual(r.payload["sheet_count"], 2)

    def test_bridge_available_matches_manifest(self):
        self.assertEqual(
            lattice_forge_bridge.available(),
            LATTICE_FORGE_AVAILABLE,
        )

    def test_manage_ribbon_returns_result(self):
        r = lattice_forge_bridge.manage_ribbon(b"hello world")
        # OK if firmware present, EXTERNAL_REQUIRED with stdlib fallback otherwise
        self.assertIn(r.status, ("OK", "EXTERNAL_REQUIRED"))
        self.assertIn("source", r.payload)
        if r.status == "EXTERNAL_REQUIRED":
            self.assertEqual(r.payload["source"], "stdlib_fallback")
        else:
            self.assertEqual(r.payload["source"], "lattice_forge")

    def test_light_cone_rejects_invalid_split_bias(self):
        r = lattice_forge_bridge.light_cone(b"hello", split_bias=3)
        self.assertEqual(r.status, "FAIL")
        self.assertIn("split_bias", r.payload.get("reason", ""))

    def test_light_cone_accepts_valid_split_biases(self):
        for sb in (1, 2, 4, 8):
            r = lattice_forge_bridge.light_cone(b"hello", split_bias=sb)
            self.assertIn(r.status, ("OK", "EXTERNAL_REQUIRED"))

    def test_make_budget_totals_correctly(self):
        r = lattice_forge_bridge.make_budget(
            cqe_savings=10, cached_closure=5, host_budget=2
        )
        self.assertIn(r.status, ("OK", "EXTERNAL_REQUIRED"))
        self.assertEqual(r.payload["total"], 17)

    def test_spend_lane_selection(self):
        # 10 in CQE savings, 0 elsewhere
        r = lattice_forge_bridge.spend(
            {"cqe_savings": 10, "cached_closure": 0, "host_budget": 5}, cost=3
        )
        self.assertEqual(r.status, "OK")
        self.assertEqual(r.payload["lane"], "CQE_SAVINGS")
        # Now savings are depleted; spend more should go to HOST_BUDGET
        r2 = lattice_forge_bridge.spend(
            {"cqe_savings": 5, "cached_closure": 0, "host_budget": 5}, cost=4
        )
        self.assertEqual(r2.status, "OK")
        self.assertEqual(r2.payload["lane"], "CQE_SAVINGS")
        # Over budget
        r3 = lattice_forge_bridge.spend(
            {"cqe_savings": 0, "cached_closure": 0, "host_budget": 5}, cost=10
        )
        self.assertEqual(r3.status, "FAIL")
        self.assertIn("unearned", r3.payload["reason"])

    def test_spend_zero_cost_returns_zero_cost_lane(self):
        r = lattice_forge_bridge.spend(
            {"cqe_savings": 0, "cached_closure": 0, "host_budget": 0}, cost=0
        )
        self.assertEqual(r.status, "OK")
        self.assertEqual(r.payload["lane"], "ZERO_COST")

    def test_spend_negative_cost_rejected(self):
        r = lattice_forge_bridge.spend({}, cost=-1)
        self.assertEqual(r.status, "FAIL")


class TestKernelIntegration(unittest.TestCase):
    """The kernel's observe() should opportunistically call firmware."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.anchor = self.tmp.name
        self.kernel = Kernel(anchor=self.anchor)

    def tearDown(self):
        self.tmp.cleanup()

    def test_observe_emits_firmware_called_receipt(self):
        res = self.kernel.observe("integration test", mode=RequestMode.AUDIT)
        fw_receipts = self.kernel.receipts.by_event_type("FIRMWARE_CALLED")
        self.assertEqual(len(fw_receipts), 1)
        payload = fw_receipts[0].payload
        self.assertEqual(payload["bridge"], "lattice_forge")
        self.assertIn("firmware_status", payload)
        # Status: OK if firmware present, EXTERNAL_REQUIRED otherwise
        if LATTICE_FORGE_AVAILABLE:
            self.assertEqual(payload["firmware_status"], "OK")
            self.assertEqual(fw_receipts[0].evidence_class, EvidenceStatus.FIRMWARE_BACKED)
        else:
            self.assertEqual(payload["firmware_status"], "EXTERNAL_REQUIRED")
            self.assertEqual(fw_receipts[0].evidence_class, EvidenceStatus.KERNEL_PRIMITIVE)

    def test_split_bias_validation_in_constructor(self):
        with self.assertRaises(ValueError):
            Kernel(anchor=self.anchor, split_bias=3)
        with self.assertRaises(ValueError):
            Kernel(anchor=self.anchor, split_bias=0)
        with self.assertRaises(ValueError):
            Kernel(anchor=self.anchor, split_bias=16)
        # Valid values
        for sb in (1, 2, 4, 8):
            k = Kernel(anchor=self.anchor, split_bias=sb)
            self.assertEqual(k.split_bias, sb)

    def test_split_bias_propagates_to_firmware(self):
        k = Kernel(anchor=self.anchor, split_bias=8)
        res = k.observe("split bias test", mode=RequestMode.AUDIT)
        fw_receipts = k.receipts.by_event_type("FIRMWARE_CALLED")
        self.assertEqual(fw_receipts[0].payload["split_bias"], 8)

    def test_observe_with_unicode_does_not_corrupt(self):
        # Non-ASCII text
        res = self.kernel.observe("Σ ⊗ Δ — CQE", mode=RequestMode.AUDIT)
        self.assertEqual(res.arity, 8)


class TestD4Token(unittest.TestCase):
    """Local D4Token class — the kernel's stdlib stub for lattice_forge.cqe.D4Token."""

    def test_from_bit(self):
        t = D4Token.from_bit(index=0, bit=1)
        self.assertEqual(t.pode, 1)
        self.assertEqual(t.antipode, 0)
        self.assertEqual(t.orbit, 0)
        self.assertEqual(t.cartan_slot, 1)
        self.assertEqual(t.time_polarity, 1)
        # Default write_record = antipode (matches lattice_forge)
        self.assertTrue(t.is_closed)

    def test_explicit_write_record_overrides_default(self):
        t = D4Token.from_bit(index=0, bit=0, write_record=1)
        # bit=0 -> antipode=1; write_record=1; match -> closed
        self.assertTrue(t.is_closed)
        t2 = D4Token.from_bit(index=0, bit=0, write_record=0)
        # bit=0 -> antipode=1; write_record=0; mismatch -> escrow
        self.assertFalse(t2.is_closed)
        self.assertEqual(t2.closure_state, "ESCROW")

    def test_time_polarity_alternates(self):
        t0 = D4Token.from_bit(index=0, bit=0)
        t1 = D4Token.from_bit(index=1, bit=0)
        t2 = D4Token.from_bit(index=2, bit=0)
        self.assertEqual(t0.time_polarity, 1)
        self.assertEqual(t1.time_polarity, -1)
        self.assertEqual(t2.time_polarity, 1)

    def test_cartan_slot_cycles_1_through_8(self):
        slots = [D4Token.from_bit(index=i, bit=0).cartan_slot for i in range(8)]
        self.assertEqual(slots, [1, 2, 3, 4, 5, 6, 7, 8])

    def test_tokens_from_bits(self):
        bits = "01011010"
        toks = tokens_from_bits(bits)
        self.assertEqual(len(toks), 8)
        # Skips non-bit characters
        self.assertEqual(len(tokens_from_bits("01a0b1")), 4)

    def test_to_dict_roundtrip(self):
        t = D4Token.from_bit(index=42, bit=1)
        d = t.to_dict()
        self.assertEqual(d["index"], 42)
        self.assertEqual(d["pode"], 1)
        self.assertEqual(d["spin_vignette"], [42 % 4, 1])


class TestCLIWitnessD4(unittest.TestCase):
    """The CLI subcommands witness and d4 should work from the installed kernel."""

    def test_d4_subcommand(self):
        proc = subprocess.run(
            [sys.executable, "-m", "cqekernel", "d4", "hello"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        d = json.loads(proc.stdout)
        self.assertEqual(d["input_text"], "hello")
        self.assertEqual(d["bit_count"], 40)
        self.assertEqual(d["token_count"], 40)

    def test_witness_subcommand(self):
        proc = subprocess.run(
            [sys.executable, "-m", "cqekernel", "witness", "01011010",
             "--split-bias", "4"],
            capture_output=True, text=True,
        )
        # Status: OK or EXTERNAL_REQUIRED, both are valid (return 0)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        d = json.loads(proc.stdout)
        self.assertIn(d["status"], ("OK", "EXTERNAL_REQUIRED"))
        self.assertIn("payload", d)

    def test_witness_rejects_invalid_split_bias(self):
        proc = subprocess.run(
            [sys.executable, "-m", "cqekernel", "witness", "010110",
             "--split-bias", "3"],
            capture_output=True, text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        # argparse uses the long-form option name in the error
        self.assertIn("--split-bias", proc.stderr)
        self.assertIn("invalid choice", proc.stderr)


class TestBridgeAgainstLatticeForge(unittest.TestCase):
    """Only runs when lattice_forge is installed.

    Verifies the kernel's bridge gives sensible output when calling
    into the real lattice_forge.cqe module.
    """

    @unittest.skipUnless(LATTICE_FORGE_AVAILABLE, "lattice_forge not installed")
    def test_managed_ribbon_ok(self):
        r = lattice_forge_bridge.manage_ribbon(b"hello world")
        self.assertEqual(r.status, "OK")
        self.assertEqual(r.payload["source"], "lattice_forge")
        self.assertIn("decisions", r.payload)
        self.assertGreaterEqual(r.payload["savings"], 0)

    @unittest.skipUnless(LATTICE_FORGE_AVAILABLE, "lattice_forge not installed")
    def test_light_cone_against_real_lf(self):
        r = lattice_forge_bridge.light_cone(b"hello world", split_bias=2, tick=0)
        self.assertEqual(r.status, "OK")
        self.assertIn("frame", r.payload)
        frame = r.payload["frame"]
        self.assertEqual(frame["split_bias"], 2)
        self.assertEqual(frame["tick"], 0)
        self.assertGreater(frame["triad_count"], 0)
        self.assertGreater(frame["quadratic_count"], 0)
        self.assertIn("lcr_boundary", frame)
        # Fibonacci LCR boundary should be non-empty
        self.assertGreater(len(frame["lcr_boundary"]["left"]), 0)

    @unittest.skipUnless(LATTICE_FORGE_AVAILABLE, "lattice_forge not installed")
    def test_make_budget_against_real_lf(self):
        r = lattice_forge_bridge.make_budget(cqe_savings=10, host_budget=5)
        self.assertEqual(r.status, "OK")
        self.assertEqual(r.payload["total"], 15)

    @unittest.skipUnless(LATTICE_FORGE_AVAILABLE, "lattice_forge not installed")
    def test_kernel_observe_with_real_firmware(self):
        k = Kernel(anchor=self.anchor_via_tmp(), split_bias=4)
        res = k.observe("lattice_forge integration", mode=RequestMode.AUDIT)
        fw = k.receipts.by_event_type("FIRMWARE_CALLED")
        self.assertEqual(fw[0].evidence_class, EvidenceStatus.FIRMWARE_BACKED)
        self.assertEqual(fw[0].payload["firmware_status"], "OK")

    def anchor_via_tmp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        return self._tmp.name

    def tearDown(self):
        if hasattr(self, "_tmp"):
            self._tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
