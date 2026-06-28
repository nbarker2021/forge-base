"""
Local test runner for the CQE kernel.

This is a stdlib-only test entry point. It is intentionally separate
from ``unittest`` so the kernel can be tested without depending on
test-runner conventions a host may not have.
"""

import sys
import unittest

from . import test_request, test_carrier, test_ribbon, test_receipts, test_replay


def suite() -> unittest.TestSuite:
    loader = unittest.TestLoader()
    s = unittest.TestSuite()
    for mod in (test_request, test_carrier, test_ribbon, test_receipts, test_replay):
        s.addTests(loader.loadTestsFromModule(mod))
    return s


def main(argv=None) -> int:
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite())
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
