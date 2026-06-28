"""
Tests for the CQE / LCR / CMPLX-1T identity chain.

These tests do NOT exercise any new behavior. They lock the
identity-chain constants declared in ``cqekernel.__init__`` so
that the brand cannot drift accidentally and the chain stays
auditable. Any change to a __substrate__ / __kernel__ / __product__
value is a deliberate rebrand, not a silent mutation.
"""

import unittest

import cqekernel
from cqekernel import (
    __brand__,
    __brand_promise__,
    __brand_spoken__,
    __identity_chain__,
    __kernel__,
    __product__,
    __substrate__,
)


class TestIdentityChain(unittest.TestCase):
    """The three-layer identity chain is locked."""

    def test_substrate_is_CQEEngine(self):
        self.assertEqual(__substrate__, "CQEEngine")

    def test_kernel_is_LCRKernel(self):
        self.assertEqual(__kernel__, "LCRKernel")

    def test_product_is_CMPLX_1T(self):
        self.assertEqual(__product__, "CMPLX-1T")

    def test_brand_is_CMPLX_1T(self):
        self.assertEqual(__brand__, "CMPLX-1T")

    def test_brand_spoken_is_Complexity(self):
        self.assertEqual(__brand_spoken__, "Complexity")

    def test_brand_promise_is_reducing_complexity(self):
        self.assertIn("reducing complexity", __brand_promise__)
        self.assertIn("additive simplicity", __brand_promise__)

    def test_identity_chain_is_three_layer_tuple(self):
        self.assertEqual(
            __identity_chain__,
            ("CQEEngine", "LCRKernel", "CMPLX-1T"),
        )

    def test_identity_chain_order_is_substrate_kernel_product(self):
        # The order is load-bearing: substrate -> kernel -> product.
        self.assertEqual(
            list(__identity_chain__),
            [__substrate__, __kernel__, __product__],
        )

    def test_hyphen_in_CMPLX_1T(self):
        # The hyphen is load-bearing; "CMPLX1T" without a hyphen is a
        # different brand. The repo's public surface (e.g.
        # core/cmplx-1t-showroom/) uses the hyphenated form throughout.
        self.assertIn("-", __product__)

    def test_no_external_imports(self):
        """The identity constants do not pull in any new dependency.

        This test must be run in an isolated subprocess because the
        test suite shares ``sys.modules`` with the other tests
        (notably ``test_combined_cem``, which transitively imports
        several forges and may register them in ``sys.modules``).
        """
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; "
             "import cqekernel; "
             "mods = [m for m in sys.modules if m in "
             "('numpy','pandas','pydantic','fastapi','sympy',"
             "'networkx','lattice_forge')]; "
             "print(' '.join(mods))"],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0)
        # If any forbidden module is loaded, the output will be non-empty.
        self.assertEqual(
            result.stdout.strip(), "",
            f"identity constants should not import any of these; got: {result.stdout.strip()!r}",
        )


class TestIdentityChainExports(unittest.TestCase):
    """The identity constants are in __all__ so ``from cqekernel import *`` carries them."""

    def test_substrate_in_all(self):
        self.assertIn("__substrate__", cqekernel.__all__)

    def test_kernel_in_all(self):
        self.assertIn("__kernel__", cqekernel.__all__)

    def test_product_in_all(self):
        self.assertIn("__product__", cqekernel.__all__)

    def test_brand_in_all(self):
        self.assertIn("__brand__", cqekernel.__all__)

    def test_identity_chain_in_all(self):
        self.assertIn("__identity_chain__", cqekernel.__all__)


class TestIdentityImportable(unittest.TestCase):
    """The brand is importable from the top level without surprises."""

    def test_substrate_as_attribute(self):
        self.assertEqual(cqekernel.__substrate__, "CQEEngine")

    def test_kernel_as_attribute(self):
        self.assertEqual(cqekernel.__kernel__, "LCRKernel")

    def test_product_as_attribute(self):
        self.assertEqual(cqekernel.__product__, "CMPLX-1T")

    def test_brand_promise_as_attribute(self):
        self.assertTrue(
            cqekernel.__brand_promise__.startswith("reducing complexity")
        )


if __name__ == "__main__":
    unittest.main()
