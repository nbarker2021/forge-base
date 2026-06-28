"""Unit tests for ObservedRequest and policy."""

import unittest
from cqekernel import ObservedRequest, RequestMode, Policy
from cqekernel.core.errors import KernelPolicyError


class TestRequest(unittest.TestCase):
    def test_request_is_hashed(self):
        r = ObservedRequest(raw_text="hello")
        self.assertEqual(len(r.raw_hash), 64)
        # same input -> same hash
        r2 = ObservedRequest(raw_text="hello")
        self.assertEqual(r.raw_hash, r2.raw_hash)
        # different input -> different hash
        r3 = ObservedRequest(raw_text="world")
        self.assertNotEqual(r.raw_hash, r3.raw_hash)

    def test_request_modes(self):
        for m in (RequestMode.READ_ONLY, RequestMode.LOOKUP_ONLY,
                  RequestMode.COMPUTE_IF_NEEDED, RequestMode.REPLAY_ONLY,
                  RequestMode.AUDIT, RequestMode.WORKBOOK, RequestMode.HOST_INSERT):
            r = ObservedRequest(raw_text="x", mode=m)
            self.assertEqual(r.mode, m)

    def test_policy_strict_defaults(self):
        p = Policy.strict()
        self.assertFalse(p.allow_firmware)
        self.assertFalse(p.allow_external_io)
        self.assertFalse(p.allow_mutation)
        self.assertFalse(p.allow_compute)
        self.assertFalse(p.allow_conjectural_output)
        self.assertTrue(p.require_receipts)
        self.assertTrue(p.require_replay)

    def test_policy_check_blocks(self):
        p = Policy.strict()
        with self.assertRaises(KernelPolicyError):
            p.check("firmware")
        with self.assertRaises(KernelPolicyError):
            p.check("external_io")
        with self.assertRaises(KernelPolicyError):
            p.check("mutation")
        with self.assertRaises(KernelPolicyError):
            p.check("compute")

    def test_policy_from_dict(self):
        p = Policy.from_dict({"allow_firmware": True, "unknown_key": 42})
        self.assertTrue(p.allow_firmware)
        self.assertEqual(p.extras.get("unknown_key"), 42)


if __name__ == "__main__":
    unittest.main()
