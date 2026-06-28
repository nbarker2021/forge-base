"""
Tests for the L/C/R typed-kernel contract.

Coverage:
  * Lane enum and its role/policy-action/policy-field mapping
  * lane_of_lcr classifier (boundary pair, uniform, chiral pair)
  * Policy gains the three new fields with strict defaults
  * Policy.check recognises the three new actions
  * TypedKernel.check_lane denies by default, passes when granted
  * TypedKernel.grants reports the current grant table
  * LaneGrant serialises to a dict
  * LAdapter / CKernel / RChannel Protocols are runtime-checkable
  * The existing 8-gate Policy still works (regression test)

All tests are stdlib-only.
"""

import unittest

from cqekernel import Kernel, Policy
from cqekernel.core.errors import KernelPolicyError
from cqekernel.lcr import (
    CKernel,
    LAdapter,
    Lane,
    LaneGrant,
    RChannel,
    TypedKernel,
    lane_of_lcr,
    lane_role_string,
)


class TestLaneEnum(unittest.TestCase):
    """The three-lane identity and its policy mapping."""

    def test_three_lanes(self):
        self.assertEqual({Lane.L.value, Lane.C.value, Lane.R.value}, {"L", "C", "R"})

    def test_role_mapping(self):
        self.assertEqual(Lane.L.role, "adapter")
        self.assertEqual(Lane.C.role, "kernel")
        self.assertEqual(Lane.R.role, "channel")

    def test_policy_action_mapping(self):
        self.assertEqual(Lane.L.policy_action, "left_io")
        self.assertEqual(Lane.C.policy_action, "center_dispatch")
        self.assertEqual(Lane.R.policy_action, "right_emit")

    def test_policy_field_mapping(self):
        self.assertEqual(Lane.L.policy_field, "allow_left_io")
        self.assertEqual(Lane.C.policy_field, "allow_center_dispatch")
        self.assertEqual(Lane.R.policy_field, "allow_right_emit")

    def test_typed_kernel_check_rejects_non_lane(self):
        k = Kernel()
        tk = TypedKernel(kernel=k, policy=k.policy)
        with self.assertRaises(TypeError):
            tk.check_lane("any_op", "C")  # type: ignore[arg-type]


class TestLCRLaneClassifier(unittest.TestCase):
    """lane_of_lcr maps an (L, C, R) triple to its dominant lane.

    The classifier is used for type-aware error messages and
    obligation reporting, not for any policy decision. The
    classifier is intentionally auditable: every branch has a
    plain-English rule.
    """

    def test_boundary_pair_010_is_C(self):
        # (0, 1, 0): L == R, C is the lone bit. The carrier is C.
        self.assertEqual(lane_of_lcr((0, 1, 0)), Lane.C)

    def test_boundary_pair_101_is_C(self):
        # (1, 0, 1): L == R, C is the lone bit. The carrier is C.
        self.assertEqual(lane_of_lcr((1, 0, 1)), Lane.C)

    def test_uniform_000_is_C(self):
        # (0, 0, 0): all agree. C arbitrated admission; C owns.
        self.assertEqual(lane_of_lcr((0, 0, 0)), Lane.C)

    def test_uniform_111_is_C(self):
        self.assertEqual(lane_of_lcr((1, 1, 1)), Lane.C)

    def test_chiral_pair_001_is_C(self):
        # (0, 0, 1): L != R. The disagreement is in L and R;
        # C arbitrates. Dominant lane: C.
        self.assertEqual(lane_of_lcr((0, 0, 1)), Lane.C)

    def test_chiral_pair_110_is_C(self):
        self.assertEqual(lane_of_lcr((1, 1, 0)), Lane.C)

    def test_chiral_pair_100_is_C(self):
        self.assertEqual(lane_of_lcr((1, 0, 0)), Lane.C)

    def test_chiral_pair_011_is_C(self):
        self.assertEqual(lane_of_lcr((0, 1, 1)), Lane.C)

    def test_eight_lane_classifications(self):
        # Sanity: all 8 LCR states map to *some* lane.
        lanes_seen = set()
        for L in (0, 1):
            for C in (0, 1):
                for R in (0, 1):
                    lanes_seen.add(lane_of_lcr((L, C, R)))
        # Every state maps to a lane (currently all C per the
        # classifier heuristic; the test is that the function
        # is total).
        self.assertEqual(len(lanes_seen), 1)
        self.assertIn(Lane.C, lanes_seen)

    def test_lane_role_string_format(self):
        s = lane_role_string((0, 1, 0))
        self.assertIn("C", s)
        self.assertIn("kernel", s)


class TestPolicyNewGates(unittest.TestCase):
    """The three new policy gates exist and default to False."""

    def test_strict_default_denies_all_three_lanes(self):
        p = Policy.strict()
        self.assertFalse(p.allow_left_io)
        self.assertFalse(p.allow_center_dispatch)
        self.assertFalse(p.allow_right_emit)

    def test_check_left_io_denied_by_default(self):
        p = Policy.strict()
        with self.assertRaises(KernelPolicyError):
            p.check("left_io")

    def test_check_center_dispatch_denied_by_default(self):
        p = Policy.strict()
        with self.assertRaises(KernelPolicyError):
            p.check("center_dispatch")

    def test_check_right_emit_denied_by_default(self):
        p = Policy.strict()
        with self.assertRaises(KernelPolicyError):
            p.check("right_emit")

    def test_check_left_io_passes_when_granted(self):
        p = Policy.strict()
        p.allow_left_io = True
        p.check("left_io")  # must not raise

    def test_check_center_dispatch_passes_when_granted(self):
        p = Policy.strict()
        p.allow_center_dispatch = True
        p.check("center_dispatch")  # must not raise

    def test_check_right_emit_passes_when_granted(self):
        p = Policy.strict()
        p.allow_right_emit = True
        p.check("right_emit")  # must not raise

    def test_from_dict_recognises_new_gates(self):
        p = Policy.from_dict({
            "allow_left_io": True,
            "allow_center_dispatch": True,
            "allow_right_emit": False,
        })
        self.assertTrue(p.allow_left_io)
        self.assertTrue(p.allow_center_dispatch)
        self.assertFalse(p.allow_right_emit)

    def test_to_dict_includes_new_gates(self):
        p = Policy.strict()
        d = p.to_dict()
        self.assertIn("allow_left_io", d)
        self.assertIn("allow_center_dispatch", d)
        self.assertIn("allow_right_emit", d)
        self.assertFalse(d["allow_left_io"])
        self.assertFalse(d["allow_center_dispatch"])
        self.assertFalse(d["allow_right_emit"])

    def test_regression_original_eight_gates_still_work(self):
        """Make sure the new gates did not break the original gates."""
        p = Policy.strict()
        for action in (
            "firmware", "external_io", "mutation", "compute",
            "conjecture", "host_write",
        ):
            with self.assertRaises(KernelPolicyError):
                p.check(action)


class TestTypedKernelEnforcement(unittest.TestCase):
    """TypedKernel.check_lane enforces the lane policy."""

    def setUp(self):
        self.k = Kernel()
        self.tk_strict = TypedKernel(kernel=self.k, policy=self.k.policy)

    def test_strict_default_denies_all_three_lanes(self):
        for lane in (Lane.L, Lane.C, Lane.R):
            with self.assertRaises(KernelPolicyError):
                self.tk_strict.check_lane("observe", lane)

    def test_grant_lane_c_passes_lane_c(self):
        self.k.policy.allow_center_dispatch = True
        grant = self.tk_strict.check_lane("observe_audit", Lane.C)
        self.assertIsInstance(grant, LaneGrant)
        self.assertTrue(grant.granted)
        self.assertEqual(grant.lane, Lane.C)
        self.assertEqual(grant.operation, "observe_audit")

    def test_grant_lane_c_does_not_grant_lane_r(self):
        self.k.policy.allow_center_dispatch = True
        with self.assertRaises(KernelPolicyError):
            self.tk_strict.check_lane("emit_receipt", Lane.R)

    def test_grant_lane_l_passes_lane_l_only(self):
        self.k.policy.allow_left_io = True
        self.tk_strict.check_lane("read_source", Lane.L)
        with self.assertRaises(KernelPolicyError):
            self.tk_strict.check_lane("read_source", Lane.C)
        with self.assertRaises(KernelPolicyError):
            self.tk_strict.check_lane("read_source", Lane.R)

    def test_grant_all_three_passes_all_three(self):
        self.k.policy.allow_left_io = True
        self.k.policy.allow_center_dispatch = True
        self.k.policy.allow_right_emit = True
        for lane in (Lane.L, Lane.C, Lane.R):
            grant = self.tk_strict.check_lane("any_op", lane)
            self.assertTrue(grant.granted)
            self.assertEqual(grant.lane, lane)

    def test_grants_reports_current_state(self):
        self.k.policy.allow_center_dispatch = True
        table = self.tk_strict.grants()
        # 3 entries, in L, C, R order
        self.assertEqual(len(table), 3)
        self.assertEqual([g.lane for g in table], [Lane.L, Lane.C, Lane.R])
        granted = [g for g in table if g.granted]
        self.assertEqual(len(granted), 1)
        self.assertEqual(granted[0].lane, Lane.C)

    def test_grants_default_all_denied(self):
        table = self.tk_strict.grants()
        self.assertTrue(all(not g.granted for g in table))

    def test_error_message_names_the_lane_and_field(self):
        try:
            self.tk_strict.check_lane("my_op", Lane.C)
        except KernelPolicyError as e:
            msg = str(e)
            self.assertIn("center_dispatch", msg)
            self.assertIn("my_op", msg)
            self.assertIn("allow_center_dispatch", msg)
        else:
            self.fail("expected KernelPolicyError")


class TestLaneGrantSerialization(unittest.TestCase):
    """LaneGrant serialises to a JSON-friendly dict."""

    def test_to_dict(self):
        g = LaneGrant(
            operation="observe_audit",
            lane=Lane.C,
            granted=True,
            reason="granted by allow_center_dispatch=True",
        )
        d = g.to_dict()
        self.assertEqual(d["operation"], "observe_audit")
        self.assertEqual(d["lane"], "C")
        self.assertEqual(d["lane_role"], "kernel")
        self.assertTrue(d["granted"])
        self.assertIn("center_dispatch", d["reason"])

    def test_to_dict_frozen(self):
        g = LaneGrant(operation="x", lane=Lane.L, granted=False)
        with self.assertRaises(Exception):
            g.operation = "y"  # type: ignore[misc]


class TestProtocolRuntimeCheckability(unittest.TestCase):
    """LAdapter / CKernel / RChannel are runtime-checkable Protocols.

    The @runtime_checkable decorator means isinstance(obj, Protocol)
    works at runtime against the *shape* of obj's public methods.
    """

    def setUp(self):
        self.k = Kernel()

    def test_ladapter_shape_recognised(self):
        class _MockLAdapter:
            def adapt(self, source): return source
        self.assertIsInstance(_MockLAdapter(), LAdapter)

    def test_ladapter_missing_adapt_rejected(self):
        class _NotAnAdapter:
            pass
        self.assertNotIsInstance(_NotAnAdapter(), LAdapter)

    def test_ckernel_shape_recognised(self):
        class _MockCKernel:
            def observe(self, payload, **kw): return None
            def observe_packet(self, packet): return None
            def dispatch(self, firmware_call, payload): return None
            def firmware_manifest(self): return {}
            def cqe_info(self): return {}
            def replay(self, snapshot_id): return None
            def verify_kernel(self): return {}
            def workbook_check(self): return {}
            def get_snapshot(self, snapshot_id): return None
            def list_snapshots(self): return []
        self.assertIsInstance(_MockCKernel(), CKernel)

    def test_ckernel_missing_dispatch_rejected(self):
        class _MissingDispatch:
            def observe(self, payload, **kw): return None
            def firmware_manifest(self): return {}
        self.assertNotIsInstance(_MissingDispatch(), CKernel)

    def test_real_kernel_satisfies_ckernel_protocol(self):
        """The real cqekernel.Kernel should be a CKernel.

        This is the live integration check: the existing Kernel
        already implements every CKernel method, so the typed
        contract is satisfied out-of-the-box.
        """
        self.assertIsInstance(self.k, CKernel)

    def test_rchannel_shape_recognised(self):
        class _MockRChannel:
            def emit(self, receipt): return None
            def project(self, snapshot): return None
        self.assertIsInstance(_MockRChannel(), RChannel)

    def test_rchannel_missing_project_rejected(self):
        class _MissingProject:
            def emit(self, receipt): return None
        self.assertNotIsInstance(_MissingProject(), RChannel)


class TestRealKernelAsTypedKernel(unittest.TestCase):
    """The real Kernel can be wrapped in a TypedKernel, and the real
    Policy works under the new gates without modification."""

    def test_real_kernel_with_strict_policy_denies_everything(self):
        k = Kernel()  # default Kernel uses Policy.strict()
        tk = TypedKernel(kernel=k, policy=k.policy)
        for op in ("observe", "dispatch", "emit", "read_source"):
            for lane in (Lane.L, Lane.C, Lane.R):
                with self.assertRaises(KernelPolicyError):
                    tk.check_lane(op, lane)

    def test_real_kernel_can_open_lane_c_for_observe(self):
        k = Kernel()
        k.policy.allow_center_dispatch = True
        tk = TypedKernel(kernel=k, policy=k.policy)
        # Lane C for observe must pass.
        tk.check_lane("observe", Lane.C)
        # Lane R for emit must still fail.
        with self.assertRaises(KernelPolicyError):
            tk.check_lane("emit", Lane.R)

    def test_existing_kernel_observe_still_works_under_strict(self):
        """Strict policy does not block the canonical read-only observe.

        The original Kernel.observe() does not call
        TypedKernel.check_lane, so the existing read-only flow is
        unaffected. This is the regression test: nothing about the
        existing Kernel API changed.
        """
        k = Kernel()
        result = k.observe("hello world")
        # No exception; the result is the canonical ObservationResult.
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
