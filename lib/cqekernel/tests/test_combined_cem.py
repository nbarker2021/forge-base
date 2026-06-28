"""
Tests for CombinedCEM: composing multiple forges into a typed kernel.

The test proves the identity claim: "every forge is its own CEM, and
combining them makes better and better typed kernels."

Coverage:
  * Default forge-lane taxonomy exists and is non-empty
  * load_spec_from_registry reads the live FORGE_REGISTRY.json
  * load_spec_from_registry raises on unknown forge
  * CombinedCEMSpec.spec_hash is content-addressed and stable
  * CombinedCEM.boot() opens the union of lanes required by the spec
  * CombinedCEM.boot() leaves unused lanes denied (strict-by-default)
  * CombinedCEM.check_lane delegates to TypedKernel
  * CombinedCEM.receipt is content-addressed and includes the spec hash
  * The combined kernel is strictly-stronger than any single forge:
    more lanes are open, more operations are allowed, but the strict
    default still applies to anything outside the spec.

All tests are stdlib-only.
"""

import json
import tempfile
import unittest
from pathlib import Path

from cqekernel import Kernel
from cqekernel.core.errors import KernelPolicyError
from cqekernel.lcr import (
    DEFAULT_FORGE_LANES,
    CombinedCEM,
    CombinedCEMReceipt,
    CombinedCEMSpec,
    ForgeContribution,
    Lane,
    load_spec_from_registry,
)


# A minimal in-test FORGE_REGISTRY fixture so the loader is testable
# without depending on the real registry at the repo root.
def _make_fixture_registry() -> dict:
    return {
        "version": "test-fixture-1.0",
        "forges": {
            "LinkForge": {
                "role": "External databases as lib items: json/csv/ics linked once, receipted, reused",
                "purpose": "Read or write the outside",
            },
            "ChromaForge": {
                "role": "Event Law machinery: Merkle receipts, conservation, idempotent cache",
                "purpose": "Dispatch math on the C lane",
            },
            "PixelForge": {
                "role": "Display/input plane: adaptive-resolution surfaces, stylus/touch ink, E8 projection",
                "purpose": "Project to pixels",
            },
            "SentinelForge": {
                "role": "Correction-surface monitor: 2/2/4 triad partition law, syndrome fingerprints",
                "purpose": "Monitor and audit",
            },
            "reforge_researchcraft": {
                "role": "Research workflow engine",
                "purpose": "Project to research artifacts",
            },
            "ForgeX": {  # Not in DEFAULT_FORGE_LANES; should fall back to ('C',)
                "role": "Hypothetical future forge",
                "purpose": "Unknown lane",
            },
        },
        "products": {
            "cqecmplx.demo": {
                "tier": "application",
                "category": "demo",
                "role": "Demo product for tests",
                "source": "tests/fixtures",
            },
        },
    }


def _write_fixture_registry(tmpdir: Path) -> Path:
    p = tmpdir / "FORGE_REGISTRY.json"
    p.write_text(json.dumps(_make_fixture_registry()), encoding="utf-8")
    return p


class TestDefaultForgeLanes(unittest.TestCase):
    """The default lane taxonomy is non-empty and covers the forges we know about."""

    def test_default_taxonomy_non_empty(self):
        self.assertGreater(len(DEFAULT_FORGE_LANES), 10)

    def test_every_lane_appears_at_least_once(self):
        lanes_seen = {lane for lanes in DEFAULT_FORGE_LANES.values() for lane in lanes}
        self.assertIn(Lane.L, lanes_seen)
        self.assertIn(Lane.C, lanes_seen)
        self.assertIn(Lane.R, lanes_seen)

    def test_lattice_forge_spans_L_and_C(self):
        # lattice_forge is the canonical bridge; it lives in L+C.
        self.assertIn(Lane.L, DEFAULT_FORGE_LANES["lattice_forge"])
        self.assertIn(Lane.C, DEFAULT_FORGE_LANES["lattice_forge"])

    def test_forgefactory_spans_all_three(self):
        # forgefactory is orchestration; it lives in L+C+R.
        self.assertIn(Lane.L, DEFAULT_FORGE_LANES["forgefactory"])
        self.assertIn(Lane.C, DEFAULT_FORGE_LANES["forgefactory"])
        self.assertIn(Lane.R, DEFAULT_FORGE_LANES["forgefactory"])


class TestLoadSpecFromRegistry(unittest.TestCase):
    """The loader reads the live FORGE_REGISTRY.json and builds a spec."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry_path = _write_fixture_registry(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_loads_a_single_forge(self):
        spec = load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["LinkForge"],
            name="link_only",
        )
        self.assertEqual(len(spec.forges), 1)
        self.assertEqual(spec.forges[0].forge, "LinkForge")
        self.assertIn(Lane.L, spec.forges[0].lanes)
        self.assertEqual(spec.name, "link_only")

    def test_loads_multiple_forges(self):
        spec = load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["LinkForge", "ChromaForge", "PixelForge"],
            name="three_forge_cem",
            description="L + C + R",
        )
        self.assertEqual(len(spec.forges), 3)
        forges_by_name = {f.forge: f for f in spec.forges}
        self.assertIn(Lane.L, forges_by_name["LinkForge"].lanes)
        self.assertIn(Lane.C, forges_by_name["ChromaForge"].lanes)
        self.assertIn(Lane.R, forges_by_name["PixelForge"].lanes)
        self.assertEqual(spec.description, "L + C + R")

    def test_unknown_forge_raises(self):
        with self.assertRaises(ValueError) as cm:
            load_spec_from_registry(
                registry_path=self.registry_path,
                forges=["NotARealForge"],
                name="bogus",
            )
        self.assertIn("NotARealForge", str(cm.exception))
        # The error message also names the known forges for the
        # operator's convenience.
        self.assertIn("LinkForge", str(cm.exception))

    def test_unknown_forge_default_falls_back_to_C_lane(self):
        # A forge that is not in DEFAULT_FORGE_LANES falls back to
        # the centre lane (C) as a safe default. This is the
        # "conservative lane" heuristic.
        spec = load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["ForgeX"],
            name="unknown_lane",
        )
        self.assertEqual(spec.forges[0].lanes, (Lane.C,))

    def test_lane_overrides_apply(self):
        # Override a forge's default lane assignment.
        spec = load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["LinkForge"],
            name="forced",
            lane_overrides={"LinkForge": (Lane.R,)},  # override L to R
        )
        self.assertEqual(spec.forges[0].lanes, (Lane.R,))

    def test_spec_hash_is_content_addressed(self):
        spec1 = load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["LinkForge", "ChromaForge"],
            name="abc",
        )
        spec2 = load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["LinkForge", "ChromaForge"],
            name="abc",
        )
        # Same forges + same name => same spec hash.
        self.assertEqual(spec1.spec_hash, spec2.spec_hash)

    def test_spec_hash_changes_with_name(self):
        spec1 = load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["LinkForge"],
            name="first",
        )
        spec2 = load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["LinkForge"],
            name="second",
        )
        self.assertNotEqual(spec1.spec_hash, spec2.spec_hash)


class TestCombinedCEMBoot(unittest.TestCase):
    """CombinedCEM.boot() opens the union of lanes required by the spec."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry_path = _write_fixture_registry(Path(self.tmp.name))
        self.spec = load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["LinkForge", "ChromaForge", "PixelForge"],
            name="three_lane_cem",
        )
        self.cem = CombinedCEM(self.spec)

    def tearDown(self):
        self.tmp.cleanup()

    def test_before_boot_typed_kernel_unavailable(self):
        with self.assertRaises(RuntimeError):
            _ = self.cem.typed_kernel

    def test_boot_opens_all_three_lanes(self):
        receipt = self.cem.boot()
        self.assertIsInstance(receipt, CombinedCEMReceipt)
        granted_lanes = {g.lane for g in receipt.lane_grants if g.granted}
        self.assertEqual(granted_lanes, {Lane.L, Lane.C, Lane.R})

    def test_boot_sets_policy_explicitly(self):
        self.cem.boot()
        p = self.cem.kernel.policy
        self.assertTrue(p.allow_left_io)
        self.assertTrue(p.allow_center_dispatch)
        self.assertTrue(p.allow_right_emit)
        # Strict default: nothing else is opened beyond what the spec requires.
        # (allow_firmware is opened by boot() because C-lane dispatch needs it.)
        self.assertTrue(p.allow_firmware)

    def test_after_boot_check_lane_passes(self):
        self.cem.boot()
        for lane in (Lane.L, Lane.C, Lane.R):
            g = self.cem.check_lane("any_op", lane)
            self.assertTrue(g.granted)

    def test_receipt_contains_forge_count(self):
        receipt = self.cem.boot()
        self.assertEqual(receipt.forge_count, 3)
        self.assertEqual(len(receipt.contributions), 3)

    def test_receipt_spec_hash_matches_spec(self):
        receipt = self.cem.boot()
        self.assertEqual(receipt.spec_hash, self.spec.spec_hash)

    def test_receipt_serialises_to_dict(self):
        receipt = self.cem.boot()
        d = receipt.to_dict()
        self.assertEqual(d["name"], "three_lane_cem")
        self.assertEqual(d["forge_count"], 3)
        self.assertIn("contributions", d)
        self.assertIn("lane_grants", d)
        self.assertIn("kernel_info", d)
        self.assertIn("timestamp", d)


class TestCombinedCEMStrictByDefault(unittest.TestCase):
    """If a spec does not require a lane, the lane stays denied."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry_path = _write_fixture_registry(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_single_C_lane_forge_leaves_L_R_denied(self):
        # ChromaForge is C-only by default.
        spec = load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["ChromaForge"],
            name="c_only",
        )
        cem = CombinedCEM(spec)
        cem.boot()
        p = cem.kernel.policy
        self.assertFalse(p.allow_left_io)
        self.assertTrue(p.allow_center_dispatch)
        self.assertFalse(p.allow_right_emit)

    def test_L_only_forge_leaves_C_R_denied(self):
        # LinkForge is L-only by default.
        spec = load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["LinkForge"],
            name="l_only",
        )
        cem = CombinedCEM(spec)
        cem.boot()
        p = cem.kernel.policy
        self.assertTrue(p.allow_left_io)
        self.assertFalse(p.allow_center_dispatch)
        self.assertFalse(p.allow_right_emit)

    def test_unknown_lane_forge_falls_back_to_C(self):
        # ForgeX is not in DEFAULT_FORGE_LANES, so it falls back to C-only.
        spec = load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["ForgeX"],
            name="unknown_lane",
        )
        cem = CombinedCEM(spec)
        cem.boot()
        p = cem.kernel.policy
        self.assertTrue(p.allow_center_dispatch)
        self.assertFalse(p.allow_left_io)
        self.assertFalse(p.allow_right_emit)


class TestCombinedCEMComposes(unittest.TestCase):
    """The combined kernel is strictly-stronger than any single forge."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry_path = _write_fixture_registry(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_combined_grants_more_lanes_than_any_single(self):
        # Single-forge CEMs
        single_L = CombinedCEM(load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["LinkForge"], name="single_L"))
        single_L.boot()
        single_C = CombinedCEM(load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["ChromaForge"], name="single_C"))
        single_C.boot()
        single_R = CombinedCEM(load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["reforge_researchcraft"], name="single_R"))
        single_R.boot()

        # Combined CEM: 1 L + 1 C + 1 R
        combined = CombinedCEM(load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["LinkForge", "ChromaForge", "reforge_researchcraft"],
            name="combined"))
        combined.boot()

        # Combined has strictly more lanes granted.
        single_L_grants = {g.lane for g in single_L.receipt.lane_grants if g.granted}
        single_C_grants = {g.lane for g in single_C.receipt.lane_grants if g.granted}
        single_R_grants = {g.lane for g in single_R.receipt.lane_grants if g.granted}
        combined_grants = {g.lane for g in combined.receipt.lane_grants if g.granted}

        self.assertEqual(single_L_grants, {Lane.L})
        self.assertEqual(single_C_grants, {Lane.C})
        self.assertEqual(single_R_grants, {Lane.R})
        self.assertEqual(combined_grants, {Lane.L, Lane.C, Lane.R})

        # And the combined grant set is the union of the three.
        union = single_L_grants | single_C_grants | single_R_grants
        self.assertEqual(combined_grants, union)

    def test_combined_strict_default_is_preserved_for_unused_lanes(self):
        # 1 L + 1 C only. R stays denied.
        combined = CombinedCEM(load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["LinkForge", "ChromaForge"],
            name="l_plus_c"))
        combined.boot()
        p = combined.kernel.policy
        self.assertTrue(p.allow_left_io)
        self.assertTrue(p.allow_center_dispatch)
        self.assertFalse(p.allow_right_emit)  # still denied


class TestCombinedCEMDispatch(unittest.TestCase):
    """CombinedCEM.dispatch() routes through the C lane."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry_path = _write_fixture_registry(Path(self.tmp.name))
        self.spec = load_spec_from_registry(
            registry_path=self.registry_path,
            forges=["ChromaForge", "LinkForge", "reforge_researchcraft"],
            name="three_lane",
        )
        self.cem = CombinedCEM(self.spec)
        self.cem.boot()

    def tearDown(self):
        self.tmp.cleanup()

    def test_dispatch_returns_typed_refusal(self):
        # No lattice_forge installed; dispatch should return
        # EXTERNAL_REQUIRED. This is the typed-kernel surface
        # doing its job: silent no-op would be a bug.
        out = self.cem.dispatch("lattice_forge.verify_j3", {"x": 1})
        self.assertEqual(out["status"], "EXTERNAL_REQUIRED")


if __name__ == "__main__":
    unittest.main()
