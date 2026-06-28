"""Unit tests for the carrier layer (binary boundary, fourbit, LCR, correction)."""

import unittest
from cqekernel.carrier.binary_boundary import make_frame, verify_frame
from cqekernel.carrier.cform import place, swap_lr
from cqekernel.carrier.correction import (
    correction_table,
    verify_correction_identity,
)
from cqekernel.carrier.fourbit import from_bytes
from cqekernel.carrier.lcr import gluon_from_lcr, truth_table, admit


class TestBinaryBoundary(unittest.TestCase):
    def test_roundtrip(self):
        f = make_frame(payload=b"hello", source_type="text", adapter="TextAdapter")
        self.assertTrue(verify_frame(f))
        self.assertEqual(f.byte_count, 5)
        self.assertEqual(len(f.sha256), 64)
        self.assertEqual(f.payload_b64, "aGVsbG8=")


class TestFourBit(unittest.TestCase):
    def test_known_nibbles(self):
        c = from_bytes("src", b"\xAC")  # 0xAC = 1010 1100
        self.assertEqual(c.head_4bit, "1010")
        self.assertEqual(c.tail_4bit, "1100")
        self.assertEqual(c.nibble_count, 2)
        self.assertEqual(c.nibbles, ["1010", "1100"])
        # cyclic windows
        self.assertIn("10101100", c.windows)

    def test_canonical_hash_stable(self):
        c1 = from_bytes("src", b"hello")
        c2 = from_bytes("src", b"hello")
        self.assertEqual(c1.canonical_hash, c2.canonical_hash)


class TestLCR(unittest.TestCase):
    def test_truth_table_length_8(self):
        self.assertEqual(len(truth_table()), 8)

    def test_classification(self):
        g_b = gluon_from_lcr(0, (1, 0, 1))
        self.assertEqual(g_b.state_class, "boundary")
        g_f = gluon_from_lcr(0, (0, 0, 0))
        self.assertEqual(g_f.state_class, "fixed_center")
        g_c = gluon_from_lcr(0, (1, 0, 0))
        self.assertEqual(g_c.state_class, "chiral_pair")

    def test_admit(self):
        g = gluon_from_lcr(0, (1, 0, 1))
        a = admit(g)
        self.assertTrue(a.admitted)
        self.assertEqual(a.admission_class.value, "BOUNDARY")


class TestCForm(unittest.TestCase):
    def test_swap_preserves_center(self):
        g = gluon_from_lcr(0, (1, 0, 1))
        p = place(g, "r1")
        ps = swap_lr(p)
        self.assertEqual(p.center, ps.center)
        self.assertEqual(ps.orientation, "swapped")
        self.assertNotEqual(p.left, ps.left)


class TestCorrection(unittest.TestCase):
    def test_correction_identity(self):
        self.assertTrue(verify_correction_identity())

    def test_correction_values(self):
        ct = correction_table()
        # 010 -> correction 1, 110 -> correction 1, rest 0
        self.assertEqual(ct[2].correction, 1)  # 010
        self.assertEqual(ct[6].correction, 1)  # 110
        self.assertEqual(ct[0].correction, 0)  # 000
        self.assertEqual(ct[7].correction, 0)  # 111


if __name__ == "__main__":
    unittest.main()
