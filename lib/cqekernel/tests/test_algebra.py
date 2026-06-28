"""Tests for the stdlib algebra stub layer.

These tests cover:
  * the octonion axiom verifier
  * the J3O Jordan product + axioms
  * the F4/SU3 closed-form 3x3 and 8x8 matrices
  * the S3 permutation matrices on the 3-fundamental
  * the N3/SU3 closure verifier (doubly-stochastic + symmetric)

When lattice_forge is installed, additional tests diff the
stdlib and upstream surfaces (see test_algebra_bridge.py).
"""

import math
import unittest

from cqekernel.algebra import (
    J3O,
    Octonion,
    S3_PERMUTATION_NAMES,
    S3_PERMUTATIONS,
    closed_form_rule30_8x8_transition,
    closed_form_shell2_3x3,
    s3_permutation_matrices,
    verify_j3o_axioms,
    verify_n3_su3_closure,
    verify_octonion_axioms,
)


class TestOctonion(unittest.TestCase):
    def test_basis(self):
        for i in range(8):
            b = Octonion.basis(i)
            self.assertEqual(len(b.components), 8)
            self.assertEqual(b.components[i], 1.0)
            for j in range(8):
                if j != i:
                    self.assertEqual(b.components[j], 0.0)

    def test_zero_and_one(self):
        z = Octonion.zero()
        for c in z.components:
            self.assertEqual(c, 0.0)
        o = Octonion.one()
        self.assertEqual(o.components[0], 1.0)
        for i in range(1, 8):
            self.assertEqual(o.components[i], 0.0)

    def test_canonical_multiplications(self):
        # Use the actual Fano-plane outcomes (1,2,3), (1,4,5), (1,7,6),
        # (2,4,6), (2,5,7), (3,4,7), (3,6,5) with cyclic +reverse propagation.
        e = [Octonion.basis(i) for i in range(8)]
        cases = [
            (0, 0, 1.0, 0),   # 1*1 = 1
            (1, 1, -1.0, 0),  # i*i = -1
            (1, 2, 1.0, 3),   # i*j = k  (Fano (1,2,3))
            (2, 1, -1.0, 3),  # j*i = -k
            (2, 4, 1.0, 6),   # j*l = jl  (Fano (2,4,6))
            (1, 4, 1.0, 5),   # i*l = il  (Fano (1,4,5))
            (5, 6, -1.0, 3),  # il*jl = -k  (Fano (3,6,5) cyclic propagation)
        ]
        for i, j, sign, k in cases:
            prod = e[i] * e[j]
            self.assertAlmostEqual(prod.components[k], sign,
                                   msg=f"e[{i}]*e[{j}] should have {'+' if sign > 0 else '-'}e[{k}]")
            for slot in range(8):
                if slot != k:
                    self.assertAlmostEqual(prod.components[slot], 0.0,
                                           msg=f"e[{i}]*e[{j}] slot {slot} should be 0")

    def test_conjugate(self):
        o = Octonion((1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0))
        c = o.conjugate()
        self.assertEqual(c.components[0], 1.0)
        for i in range(1, 8):
            self.assertEqual(c.components[i], -o.components[i])

    def test_norm_squared(self):
        o = Octonion((1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0))
        # 1+4+9+16+25+36+49+64 = 204
        self.assertEqual(o.norm_squared(), 204.0)

    def test_verify_octonion_axioms(self):
        r = verify_octonion_axioms()
        self.assertEqual(r["status"], "pass")
        self.assertEqual(r["failures"], [])

    def test_associator_nonzero(self):
        # Octonions are non-associative; find a witness triple.
        e = [Octonion.basis(i) for i in range(8)]
        # Try (e1, e2, e4): e1*(e2*e4) vs (e1*e2)*e4
        a = e[1] * (e[2] * e[4])
        b = (e[1] * e[2]) * e[4]
        # The associator is generally non-zero
        self.assertFalse(a.components == b.components)


class TestJ3O(unittest.TestCase):
    def test_diag_only(self):
        m = J3O.diag_only(1.0, 2.0, 3.0)
        self.assertEqual(m.diag, (1.0, 2.0, 3.0))
        for u in m.upper:
            for c in u.components:
                self.assertEqual(c, 0.0)

    def test_trace(self):
        m = J3O.diag_only(1.0, 2.0, 3.0)
        self.assertEqual(m.trace(), 6.0)

    def test_jordan_product_diagonals(self):
        # Jordan product of two diagonal J3Os is element-wise on diagonals
        a = J3O.diag_only(1.0, 2.0, 3.0)
        b = J3O.diag_only(0.5, 1.5, 2.5)
        ab = a.jordan_product(b)
        self.assertAlmostEqual(ab.diag[0], 0.5)
        self.assertAlmostEqual(ab.diag[1], 3.0)
        self.assertAlmostEqual(ab.diag[2], 7.5)
        # Off-diagonals remain 0
        for u in ab.upper:
            for c in u.components:
                self.assertEqual(c, 0.0)

    def test_jordan_product_is_commutative(self):
        a = J3O.diag_only(1.0, 2.0, 3.0)
        b = J3O.diag_only(0.5, 1.5, 2.5)
        ab = a.jordan_product(b)
        ba = b.jordan_product(a)
        self.assertEqual(ab.diag, ba.diag)
        for k in range(3):
            self.assertEqual(ab.upper[k].components, ba.upper[k].components)

    def test_verify_j3o_axioms(self):
        r = verify_j3o_axioms()
        self.assertEqual(r["status"], "pass", msg=f"failures: {r['failures']}")
        self.assertEqual(r["j3o_dimension"], 27)


class TestS3Permutations(unittest.TestCase):
    def test_six_permutations(self):
        self.assertEqual(len(S3_PERMUTATION_NAMES), 6)
        self.assertEqual(len(S3_PERMUTATIONS), 6)
        for perm in S3_PERMUTATIONS:
            self.assertEqual(sorted(perm), [1, 2, 3])

    def test_identity_is_identity_matrix(self):
        m = s3_permutation_matrices()["id"]
        for i in range(3):
            for j in range(3):
                expected = 1.0 if i == j else 0.0
                self.assertEqual(m[i][j], expected)

    def test_all_matrices_are_permutations(self):
        mats = s3_permutation_matrices()
        for name, m in mats.items():
            # Row sums must all be 1
            for row in m:
                self.assertAlmostEqual(sum(row), 1.0,
                                       msg=f"{name}: row sum {sum(row)}")
            # Col sums must all be 1
            for j in range(3):
                s = sum(m[i][j] for i in range(3))
                self.assertAlmostEqual(s, 1.0,
                                       msg=f"{name}: col {j} sum {s}")
            # Each row has exactly one 1
            for i, row in enumerate(m):
                ones = sum(1 for x in row if x == 1.0)
                self.assertEqual(ones, 1, msg=f"{name}: row {i} has {ones} ones")


class TestClosedForm(unittest.TestCase):
    def test_8x8_row_stochastic(self):
        cf = closed_form_rule30_8x8_transition()
        self.assertEqual(cf["state_count"], 8)
        for i, row in enumerate(cf["matrix"]):
            self.assertAlmostEqual(sum(row), 1.0,
                                   msg=f"row {i} sum {sum(row)}")
            for j, p in enumerate(row):
                self.assertGreaterEqual(p, 0.0)
                self.assertLessEqual(p, 1.0)

    def test_8x8_first_state(self):
        # State (0,0,0) -> most likely to stay near origin
        cf = closed_form_rule30_8x8_transition()
        # The matrix is 8x8 indexed by state enumeration
        # State 0 is (0,0,0)
        row0 = cf["matrix"][0]
        # The first row should have entries corresponding to
        # the 4 possible next states given LL,RR uniform
        # (because each of LL,RR gives 1/4 weight)
        # At least some probability should flow to each L',C',R'
        # such that L' = Rule30(LL, 0, 0) = LL, C' = 0, R' = Rule30(0, 0, RR) = RR
        # So next states are (LL, 0, RR) for (LL, RR) in {0,1}^2
        # which are (0,0,0), (0,0,1), (1,0,0), (1,0,1)
        # These are states 0, 1, 4, 5 (in canonical enumeration order)
        self.assertAlmostEqual(row0[0], 0.25)
        self.assertAlmostEqual(row0[1], 0.25)
        self.assertAlmostEqual(row0[4], 0.25)
        self.assertAlmostEqual(row0[5], 0.25)
        self.assertEqual(row0[2], 0.0)
        self.assertEqual(row0[3], 0.0)
        self.assertEqual(row0[6], 0.0)
        self.assertEqual(row0[7], 0.0)

    def test_3x3_is_doubly_stochastic_uniform(self):
        cf = closed_form_shell2_3x3()
        for row in cf["matrix"]:
            for v in row:
                self.assertAlmostEqual(v, 1.0 / 3.0)
        # Verify it's a permutation (sum of any row = 1)
        for row in cf["matrix"]:
            self.assertAlmostEqual(sum(row), 1.0)

    def test_verify_n3_su3_closure(self):
        r = verify_n3_su3_closure()
        self.assertEqual(r["status"], "pass", msg=f"failures: {r['failures']}")


if __name__ == "__main__":
    unittest.main()
