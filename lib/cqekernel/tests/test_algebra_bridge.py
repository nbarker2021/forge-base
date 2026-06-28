"""Tests for the algebra bridge (stdlib vs lattice_forge diff)."""

import sys
import types
import unittest

from cqekernel.firmware import algebra_bridge


# Probe
try:
    import lattice_forge  # noqa: F401
    LATTICE_FORGE_AVAILABLE = True
except Exception:
    LATTICE_FORGE_AVAILABLE = False


def _install_fake_lattice_forge(*, agreement: bool = True):
    """Install fake lattice_forge modules into sys.modules.

    When ``agreement=True`` the fakes return values that match the
    stdlib; when False, they deliberately diverge. Used to exercise
    the diff layer.
    """
    from cqekernel.algebra import (
        closed_form_rule30_8x8_transition,
        closed_form_shell2_3x3,
        verify_j3o_axioms,
        verify_n3_su3_closure,
        verify_octonion_axioms,
    )
    fake_oct = types.ModuleType("lattice_forge.octonion")
    fake_j3 = types.ModuleType("lattice_forge.jordan_j3")
    fake_f4 = types.ModuleType("lattice_forge.f4_action")
    if agreement:
        fake_oct.verify_octonion_axioms = verify_octonion_axioms
        fake_j3.verify_j3o_axioms = verify_j3o_axioms
        fake_f4.closed_form_shell2_3x3 = closed_form_shell2_3x3
        fake_f4.closed_form_rule30_8x8_transition = closed_form_rule30_8x8_transition
        fake_f4.verify_n3_su3_closure_exact = verify_n3_su3_closure
    else:
        # Force a divergence
        fake_oct.verify_octonion_axioms = lambda: {"status": "fail", "from": "fake-divergent"}
        fake_j3.verify_j3o_axioms = lambda: {"status": "fail", "from": "fake-divergent"}
        fake_f4.closed_form_shell2_3x3 = lambda: {
            "matrix": [[0.0, 0.0, 0.0]] * 3,
        }
        fake_f4.closed_form_rule30_8x8_transition = lambda: {
            "matrix": [[0.0] * 8] * 8,
        }
        fake_f4.verify_n3_su3_closure_exact = lambda: {"status": "fail", "from": "fake-divergent"}
    sys.modules["lattice_forge"] = types.ModuleType("lattice_forge")
    sys.modules["lattice_forge.octonion"] = fake_oct
    sys.modules["lattice_forge.jordan_j3"] = fake_j3
    sys.modules["lattice_forge.f4_action"] = fake_f4
    # Reset bridge caches
    algebra_bridge._discovery_done = False
    algebra_bridge._lf_octonion = None
    algebra_bridge._lf_jordan = None
    algebra_bridge._lf_f4 = None
    algebra_bridge._discovery_error = None


def _uninstall_fake_lattice_forge():
    for k in ("lattice_forge", "lattice_forge.octonion", "lattice_forge.jordan_j3",
             "lattice_forge.f4_action"):
        if k in sys.modules:
            del sys.modules[k]
    algebra_bridge._discovery_done = False
    algebra_bridge._lf_octonion = None
    algebra_bridge._lf_jordan = None
    algebra_bridge._lf_f4 = None
    algebra_bridge._discovery_error = None


class TestAlgebraBridge(unittest.TestCase):
    def test_manifest_without_lf(self):
        _uninstall_fake_lattice_forge()
        # Patch available() to return False for this test
        original_available = algebra_bridge.available
        algebra_bridge.available = lambda: False
        algebra_bridge._discovery_done = True  # Skip discovery
        algebra_bridge._lf_octonion = None
        algebra_bridge._lf_jordan = None
        algebra_bridge._lf_f4 = None
        algebra_bridge._discovery_error = None
        try:
            m = algebra_bridge.manifest()
            self.assertFalse(m["available"])
        finally:
            algebra_bridge.available = original_available
            algebra_bridge._discovery_done = False
            import importlib
            importlib.invalidate_caches()

    def test_manifest_with_fake_lf(self):
        _install_fake_lattice_forge(agreement=True)
        try:
            m = algebra_bridge.manifest()
            self.assertTrue(m["available"])
        finally:
            _uninstall_fake_lattice_forge()

    def test_diff_all_stdlib_alone(self):
        _uninstall_fake_lattice_forge()
        # Patch available() to return False for this test
        original_available = algebra_bridge.available
        algebra_bridge.available = lambda: False
        algebra_bridge._discovery_done = True  # Skip discovery
        algebra_bridge._lf_octonion = None
        algebra_bridge._lf_jordan = None
        algebra_bridge._lf_f4 = None
        algebra_bridge._discovery_error = None
        try:
            r = algebra_bridge.diff_all()
            self.assertFalse(r["available"])
            self.assertIn("stdlib_alone", r)
            self.assertEqual(r["stdlib_alone"]["octonion"], "pass")
            self.assertEqual(r["stdlib_alone"]["j3o"], "pass")
            self.assertEqual(r["stdlib_alone"]["su3_closure"], "pass")
        finally:
            algebra_bridge.available = original_available
            algebra_bridge._discovery_done = False
            import importlib
            importlib.invalidate_caches()

    def test_diff_all_with_agreement(self):
        _install_fake_lattice_forge(agreement=True)
        try:
            r = algebra_bridge.diff_all()
            self.assertTrue(r["available"])
            self.assertTrue(r["all_agree"])
            for surface, info in r["diffs"].items():
                self.assertTrue(info["agree"],
                                msg=f"{surface} disagreed: {info['diff']}")
        finally:
            _uninstall_fake_lattice_forge()

    def test_diff_all_with_divergence(self):
        _install_fake_lattice_forge(agreement=False)
        try:
            r = algebra_bridge.diff_all()
            self.assertTrue(r["available"])
            self.assertFalse(r["all_agree"])
            # The diff dict should be present for at least one surface
            for surface, info in r["diffs"].items():
                if not info["agree"]:
                    self.assertIn("diff", info)
                    self.assertIsNotNone(info["diff"])
        finally:
            _uninstall_fake_lattice_forge()

    def test_diff_individual_calls(self):
        _install_fake_lattice_forge(agreement=True)
        try:
            r = algebra_bridge.diff_octonion_axioms()
            self.assertIsNotNone(r)
            self.assertTrue(r.agree)
            r = algebra_bridge.diff_j3o_axioms()
            self.assertTrue(r.agree)
            r = algebra_bridge.diff_closed_form_3x3()
            self.assertTrue(r.agree)
            r = algebra_bridge.diff_closed_form_8x8()
            self.assertTrue(r.agree)
            r = algebra_bridge.diff_su3_closure()
            self.assertTrue(r.agree)
        finally:
            _uninstall_fake_lattice_forge()

    @unittest.skipUnless(LATTICE_FORGE_AVAILABLE, "real lattice_forge not installed")
    def test_diff_all_with_real_lattice_forge(self):
        # If real lattice_forge is in the venv, run a real diff
        r = algebra_bridge.diff_all()
        self.assertTrue(r["available"])
        # We don't assert all_agree here — the real upstream may
        # legitimately differ from the stdlib at this stage. The
        # value is that the bridge runs and returns a structured
        # diff dict.
        self.assertIn("diffs", r)
        self.assertIn("all_agree", r)


if __name__ == "__main__":
    unittest.main()
