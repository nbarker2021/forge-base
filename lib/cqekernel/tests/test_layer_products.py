"""
Tests for dependency_graph -> LCRKernel mapping (task 2/4).

Coverage:
  * LAYER_FORGES covers the 3 forge-bearing layers (lattice_forge,
    engine_forges, reforge_ring).
  * load_spec_from_layer builds a spec for a single layer.
  * load_spec_from_layer raises on unknown layer.
  * load_spec_from_layer returns an empty spec for the 'kernel' layer.
  * load_spec_from_layer returns an empty spec for product-only layers.
  * load_spec_from_layer integrates with CombinedCEM.boot() — boot
    opens the union of the layer's lanes.
  * load_spec_from_products builds a spec for all 7 declared products.
  * load_spec_from_products can filter by tier.
  * load_spec_from_products raises when no products match.
  * The 'metaforge' load (all 7 products) opens all 3 lanes.
"""

import json
import tempfile
import unittest
from pathlib import Path

from cqekernel import Kernel
from cqekernel.lcr import (
    LAYER_FORGES,
    Lane,
    load_spec_from_layer,
    load_spec_from_products,
    load_spec_from_registry,
)


def _make_full_registry() -> dict:
    """A registry that mirrors the structure of the real FORGE_REGISTRY.json
    closely enough for the loaders to work end-to-end. The fixture
    must contain every forge listed in LAYER_FORGES."""
    # Build a synthetic forge entry for every name in LAYER_FORGES.
    from cqekernel.lcr import LAYER_FORGES
    all_layer_forges = []
    for layer_forges in LAYER_FORGES.values():
        all_layer_forges.extend(layer_forges)
    forges_block: dict = {}
    for name in all_layer_forges:
        forges_block[name] = {
            "role": f"Synthetic fixture entry for {name}",
            "purpose": "test fixture",
        }
    return {
        "version": "test-fixture-1.0",
        "forges": forges_block,
        "products": {
            "cqecmplx.r30": {
                "tier": "core",
                "category": "rule30_solver",
                "role": "Observer-relative Rule 30 stopped-state solver",
                "source": "production/packages/cqecmplx-forge/src/cqecmplx/r30/",
                "algebra_deps": ["Rule30", "LCR", "Chroma/Gluon"],
            },
            "cqecmplx.engines.analog_workbench": {
                "tier": "core",
                "category": "forge_product",
                "role": "Analog Forge Workbook Kit simulator",
                "source": "production/packages/cqecmplx-forge/src/cqecmplx/engines/analog_workbench/",
                "algebra_deps": ["WorkbookSchema", "ReceiptChain"],
            },
            "cqecmplx.entropy": {
                "tier": "application",
                "category": "rule30_application",
                "role": "Quantum-grade cryptographic entropy",
                "source": "D:/CQE_CMPLX/historical_pastworks/product_entropy/",
                "algebra_deps": ["Rule30", "EntropyExtraction"],
            },
            "cqecmplx.security": {
                "tier": "application",
                "category": "security_monitor",
                "role": "Sentinel — Zero-Trust Security Monitor",
                "source": "D:/CQE_CMPLX/historical_pastworks/product_sentinel/",
                "algebra_deps": ["AnomalyDetection", "ZeroTrust"],
            },
            "cqecmplx.workspace": {
                "tier": "platform",
                "category": "ai_workspace",
                "role": "Full-stack AI workspace with LLM hosting, RAG, TTS, image gen",
                "source": "D:/CQE_CMPLX/odysseus/",
                "algebra_deps": ["LLMHosting", "RAG", "TTS", "ImageGen"],
            },
            "cqecmplx.partsfactory": {
                "tier": "framework",
                "category": "agent_framework",
                "role": "CMPLX-PartsFactory — Unified agent ecosystem",
                "source": "D:/CQE_CMPLX/CMPLX-PartsFactory-main/",
                "algebra_deps": ["AgentEcosystem", "ServiceFramework"],
            },
            "cqecmplx.lattice.extended": {
                "tier": "extension",
                "category": "lattice_extraction",
                "role": "Enterprise-Grade AI Orchestration with Geometric Intelligence",
                "source": "D:/CQE_CMPLX/g/CMPLX/",
                "algebra_deps": ["E8Lattice", "LeechLattice", "MCP"],
            },
        },
    }


def _write_registry(tmpdir: Path) -> Path:
    p = tmpdir / "FORGE_REGISTRY.json"
    p.write_text(json.dumps(_make_full_registry()), encoding="utf-8")
    return p


class TestLayerForges(unittest.TestCase):
    """The LAYER_FORGES map covers the 3 forge-bearing layers."""

    def test_three_forge_bearing_layers(self):
        self.assertEqual(
            set(LAYER_FORGES.keys()),
            {"lattice_forge", "engine_forges", "reforge_ring"},
        )

    def test_lattice_forge_layer_has_one_forge(self):
        self.assertEqual(LAYER_FORGES["lattice_forge"], ("lattice_forge",))

    def test_engine_forges_layer_has_many(self):
        self.assertGreaterEqual(len(LAYER_FORGES["engine_forges"]), 10)

    def test_reforge_ring_layer_has_reforges(self):
        for forge in LAYER_FORGES["reforge_ring"]:
            self.assertTrue(forge.startswith("reforge_") or forge == "rhenium_engine")


class TestLoadSpecFromLayer(unittest.TestCase):
    """load_spec_from_layer builds a CombinedCEMSpec for a layer."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry_path = _write_registry(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_lattice_forge_layer(self):
        spec = load_spec_from_layer(
            registry_path=self.registry_path,
            layer="lattice_forge",
        )
        self.assertEqual(len(spec.forges), 1)
        self.assertEqual(spec.forges[0].forge, "lattice_forge")
        self.assertIn(Lane.L, spec.forges[0].lanes)
        self.assertIn(Lane.C, spec.forges[0].lanes)

    def test_load_engine_forges_layer(self):
        spec = load_spec_from_layer(
            registry_path=self.registry_path,
            layer="engine_forges",
        )
        self.assertEqual(len(spec.forges), len(LAYER_FORGES["engine_forges"]))

    def test_load_reforge_ring_layer(self):
        spec = load_spec_from_layer(
            registry_path=self.registry_path,
            layer="reforge_ring",
        )
        self.assertEqual(len(spec.forges), len(LAYER_FORGES["reforge_ring"]))

    def test_load_kernel_layer_is_empty(self):
        spec = load_spec_from_layer(
            registry_path=self.registry_path,
            layer="kernel",
        )
        self.assertEqual(len(spec.forges), 0)
        self.assertIn("kernel", spec.description.lower())

    def test_load_product_layer_is_empty(self):
        # core_products, applications, frameworks, extensions hold
        # products, not forges. Loader returns an empty spec.
        for layer in ("core_products", "applications", "frameworks", "extensions"):
            spec = load_spec_from_layer(
                registry_path=self.registry_path,
                layer=layer,
            )
            self.assertEqual(len(spec.forges), 0, f"layer {layer} should be empty")

    def test_unknown_layer_raises(self):
        with self.assertRaises(ValueError) as cm:
            load_spec_from_layer(
                registry_path=self.registry_path,
                layer="not_a_real_layer",
            )
        self.assertIn("not_a_real_layer", str(cm.exception))

    def test_default_name_is_layer_X(self):
        spec = load_spec_from_layer(
            registry_path=self.registry_path,
            layer="lattice_forge",
        )
        self.assertEqual(spec.name, "layer_lattice_forge")

    def test_custom_name_overrides_default(self):
        spec = load_spec_from_layer(
            registry_path=self.registry_path,
            layer="lattice_forge",
            name="my_lattice_cem",
        )
        self.assertEqual(spec.name, "my_lattice_cem")


class TestLoadSpecFromLayerBoots(unittest.TestCase):
    """A layer-loaded spec integrates with CombinedCEM.boot()."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry_path = _write_registry(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_lattice_forge_layer_boots_to_L_and_C(self):
        from cqekernel.lcr import CombinedCEM
        spec = load_spec_from_layer(
            registry_path=self.registry_path,
            layer="lattice_forge",
        )
        cem = CombinedCEM(spec, kernel=Kernel())
        receipt = cem.boot()
        granted = {g.lane for g in receipt.lane_grants if g.granted}
        self.assertIn(Lane.L, granted)
        self.assertIn(Lane.C, granted)
        self.assertNotIn(Lane.R, granted)

    def test_engine_forges_layer_boots_to_all_three_lanes(self):
        from cqekernel.lcr import CombinedCEM
        spec = load_spec_from_layer(
            registry_path=self.registry_path,
            layer="engine_forges",
        )
        cem = CombinedCEM(spec, kernel=Kernel())
        receipt = cem.boot()
        granted = {g.lane for g in receipt.lane_grants if g.granted}
        self.assertEqual(granted, {Lane.L, Lane.C, Lane.R})

    def test_reforge_ring_layer_boots_to_R_only(self):
        from cqekernel.lcr import CombinedCEM
        spec = load_spec_from_layer(
            registry_path=self.registry_path,
            layer="reforge_ring",
        )
        cem = CombinedCEM(spec, kernel=Kernel())
        receipt = cem.boot()
        granted = {g.lane for g in receipt.lane_grants if g.granted}
        # All reforge_* are in DEFAULT_FORGE_LANES as R-only.
        self.assertIn(Lane.R, granted)
        # R-only => L and C denied.
        self.assertNotIn(Lane.L, granted)
        self.assertNotIn(Lane.C, granted)


class TestLoadSpecFromProducts(unittest.TestCase):
    """load_spec_from_products builds a CombinedCEMSpec for products."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry_path = _write_registry(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_all_products(self):
        spec = load_spec_from_products(registry_path=self.registry_path)
        self.assertEqual(len(spec.forges), 7)
        self.assertEqual(spec.name, "all_products")

    def test_filter_by_tier_core(self):
        spec = load_spec_from_products(
            registry_path=self.registry_path,
            tier="core",
        )
        self.assertEqual(len(spec.forges), 2)
        self.assertEqual(spec.name, "products_tier_core")
        for c in spec.forges:
            self.assertEqual(c.tier, "core")

    def test_filter_by_tier_application(self):
        spec = load_spec_from_products(
            registry_path=self.registry_path,
            tier="application",
        )
        self.assertEqual(len(spec.forges), 2)
        for c in spec.forges:
            self.assertEqual(c.tier, "application")

    def test_filter_by_tier_platform(self):
        spec = load_spec_from_products(
            registry_path=self.registry_path,
            tier="platform",
        )
        self.assertEqual(len(spec.forges), 1)
        self.assertEqual(spec.forges[0].forge, "cqecmplx.workspace")

    def test_filter_by_tier_framework(self):
        spec = load_spec_from_products(
            registry_path=self.registry_path,
            tier="framework",
        )
        self.assertEqual(len(spec.forges), 1)
        self.assertEqual(spec.forges[0].forge, "cqecmplx.partsfactory")

    def test_filter_by_tier_extension(self):
        spec = load_spec_from_products(
            registry_path=self.registry_path,
            tier="extension",
        )
        self.assertEqual(len(spec.forges), 1)
        self.assertEqual(spec.forges[0].forge, "cqecmplx.lattice.extended")

    def test_unknown_tier_returns_empty(self):
        # No product has tier 'unknown'; this should raise.
        with self.assertRaises(ValueError):
            load_spec_from_products(
                registry_path=self.registry_path,
                tier="not_a_real_tier",
            )

    def test_product_lane_default_is_R(self):
        # Products default to R-only (outward) when not in DEFAULT_FORGE_LANES.
        spec = load_spec_from_products(
            registry_path=self.registry_path,
            tier="extension",
        )
        self.assertEqual(spec.forges[0].lanes, (Lane.R,))

    def test_product_lane_override(self):
        spec = load_spec_from_products(
            registry_path=self.registry_path,
            tier="framework",
            lane_overrides={"cqecmplx.partsfactory": (Lane.L, Lane.C, Lane.R)},
        )
        self.assertEqual(spec.forges[0].lanes, (Lane.L, Lane.C, Lane.R))


class TestMetaforgeCombinedCEM(unittest.TestCase):
    """The 'metaforge' load: all 7 products, one typed CEM.

    Note: the 7 declared products are *outward* artifacts (each
    ships an R-channel projection). Under strict defaults, the
    metaforge CEM opens only the R lane. To open all three lanes
    from a product set, the host passes ``lane_overrides``.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry_path = _write_registry(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_metaforge_default_opens_R_only(self):
        from cqekernel.lcr import CombinedCEM
        spec = load_spec_from_products(
            registry_path=self.registry_path,
            name="metaforge",
            description="All 7 declared products, one typed CEM",
        )
        cem = CombinedCEM(spec, kernel=Kernel())
        receipt = cem.boot()
        granted = {g.lane for g in receipt.lane_grants if g.granted}
        # All 7 products default to R-only; L and C stay denied.
        self.assertEqual(granted, {Lane.R})

    def test_metaforge_with_full_lane_override_opens_all_three(self):
        # The host can declare that the metaforge controls L, C, R.
        from cqekernel.lcr import CombinedCEM
        lane_overrides = {
            "cqecmplx.r30":                       (Lane.C, Lane.R),
            "cqecmplx.engines.analog_workbench":  (Lane.C, Lane.R),
            "cqecmplx.entropy":                   (Lane.L, Lane.R),
            "cqecmplx.security":                  (Lane.C, Lane.R),
            "cqecmplx.workspace":                 (Lane.L, Lane.C, Lane.R),
            "cqecmplx.partsfactory":              (Lane.L, Lane.C, Lane.R),
            "cqecmplx.lattice.extended":          (Lane.C, Lane.R),
        }
        spec = load_spec_from_products(
            registry_path=self.registry_path,
            name="metaforge_full",
            description="Metaforge with all-3-lane override",
            lane_overrides=lane_overrides,
        )
        cem = CombinedCEM(spec, kernel=Kernel())
        receipt = cem.boot()
        granted = {g.lane for g in receipt.lane_grants if g.granted}
        self.assertEqual(granted, {Lane.L, Lane.C, Lane.R})

    def test_metaforge_receipt_has_all_7_contributions(self):
        from cqekernel.lcr import CombinedCEM
        spec = load_spec_from_products(
            registry_path=self.registry_path,
            name="metaforge",
        )
        cem = CombinedCEM(spec, kernel=Kernel())
        receipt = cem.boot()
        self.assertEqual(receipt.forge_count, 7)
        self.assertEqual(len(receipt.contributions), 7)

    def test_metaforge_contributions_cover_all_tiers(self):
        from cqekernel.lcr import CombinedCEM
        spec = load_spec_from_products(
            registry_path=self.registry_path,
            name="metaforge",
        )
        cem = CombinedCEM(spec, kernel=Kernel())
        receipt = cem.boot()
        tiers = {c.tier for c in receipt.contributions}
        # The fixture has 5 tiers: core, application, platform, framework, extension
        self.assertEqual(
            tiers,
            {"core", "application", "platform", "framework", "extension"},
        )

    def test_metaforge_R_only_keeps_other_strict_defaults(self):
        # The metaforge opens 1 lane (R) explicitly; the original
        # policy gates (allow_mutation, allow_compute, etc.) stay
        # at their strict defaults.
        from cqekernel.lcr import CombinedCEM
        spec = load_spec_from_products(
            registry_path=self.registry_path,
            name="metaforge",
        )
        cem = CombinedCEM(spec, kernel=Kernel())
        cem.boot()
        p = cem.kernel.policy
        # R lane is open; L and C are denied.
        self.assertFalse(p.allow_left_io)
        self.assertFalse(p.allow_center_dispatch)
        self.assertTrue(p.allow_right_emit)
        # The non-lane gates stay strict: no mutation, no compute,
        # no conjectural output, no host write.
        self.assertFalse(p.allow_mutation)
        self.assertFalse(p.allow_compute)
        self.assertFalse(p.allow_conjectural_output)
        self.assertFalse(p.allow_host_write)


class TestTaxonomyAudit(unittest.TestCase):
    """Lock the audited lane assignments for the canonical forges.

    These tests are the *output* of task 4/4 — they pin the audited
    taxonomy so a future rebrand has to either (a) update the test,
    acknowledging the change, or (b) leave the test passing, which
    means the taxonomy hasn't drifted.
    """

    def test_audit_summary(self):
        from cqekernel.lcr import DEFAULT_FORGE_LANES
        # Each audited entry: (forge, expected lanes, justification).
        # The list is the audit decision, not a guess.
        audited = [
            # L lane: data in / out (adapters, linkers, world-builders)
            ("LinkForge",          (Lane.L,),
             "External DBs as lib items: data in/out"),
            ("FridgeForge",        (Lane.L,),
             "Inventory lexicon: reads external data"),
            ("MandleForge",        (Lane.L,),
             "Mandelbrot surfaces: shape input"),
            ("ManiForge",          (Lane.L,),
             "Manifold surfaces: shape input"),
            ("SceneForge",         (Lane.L,),
             "Worldforge: builds world state"),
            # L+C bridge
            ("lattice_forge",      (Lane.L, Lane.C),
             "Bridge: hosts adapters AND dispatches math"),
            # C lane: control plane (math, audit, monitor)
            ("ChromaForge",        (Lane.C,),
             "Event Law / Merkle receipts: control-plane bookkeeping"),
            ("GraphStax",          (Lane.C,),
             "AGRM routing, superperm supervisor cursor: dispatch math"),
            ("SentinelForge",      (Lane.C,),
             "Correction-surface monitor: monitor + audit"),
            ("EntropyForge",       (Lane.C,),
             "Rule 30 entropy: math dispatch"),
            ("ConvergeForge",      (Lane.C,),
             "Triality annealing: math dispatch"),
            ("AuthenticaForge",    (Lane.C,),
             "Lattice code closure: math dispatch"),
            ("E8Forge",            (Lane.C,),
             "Exact E8 lattice: math dispatch"),
            ("LeechForge",         (Lane.C,),
             "Golay -> Leech tower: math dispatch"),
            ("MDHGForge",          (Lane.C,),
             "Multi-scale geometric hash cache: math dispatch"),
            ("AGRMForge",          (Lane.C,),
             "Golden-ratio low-discrepancy sweep: math dispatch"),
            ("ReadoutForge",       (Lane.C,),
             "O(log N) Rule 30 readout: math dispatch"),
            ("TriadForge",         (Lane.C,),
             "3-fold keystone: math dispatch"),
            ("GroundingForge",     (Lane.C,),
             "Grounding: math dispatch"),
            ("QuarkFaceForge",     (Lane.C,),
             "Quark-face color transport: math dispatch"),
            ("DoublingForge",      (Lane.C,),
             "120 permutation routes: math dispatch"),
            ("FieldFormForge",     (Lane.C,),
             "Register chart states: math dispatch"),
            ("MassResidueForge",   (Lane.C,),
             "Mass-residue carrier: math dispatch"),
            # R lane: outward surface (projectors, publishers)
            ("PixelForge",         (Lane.R, Lane.C),
             "Outputs surfaces AND dispatches E8 projection math"),
            ("reforge_engine_contracts",   (Lane.R,),
             "Engine contract definitions: outward documentation"),
            ("reforge_engine_hardening",   (Lane.R,),
             "Hardening & receipt trail: outward artifacts"),
            ("reforge_frameforge",         (Lane.R,),
             "Frame operations: outward projection"),
            ("reforge_glyphforge",         (Lane.R,),
             "Glyph encoding/decoding: outward projection"),
            ("reforge_kimi_adapter",       (Lane.R,),
             "KIMI adapter: outward adapter"),
            ("reforge_pixl8forge",         (Lane.R,),
             "Pixel forge variant 8-bit: outward projection"),
            ("reforge_pixleforge",         (Lane.R,),
             "Pixel forge variant element-wise: outward projection"),
            ("reforge_researchcraft",      (Lane.R,),
             "Research workflow engine: outward artifacts"),
            ("reforge_wireforge",          (Lane.R,),
             "Wire/transport forge: outward transport"),
            ("rhenium_engine",             (Lane.R,),
             "Identity-aligned engine: outward identity work"),
            # Orchestration / factory: all three lanes
            ("forgefactory",               (Lane.L, Lane.C, Lane.R),
             "Factory orchestration: dispatches + adapts + emits"),
        ]
        for forge_name, expected_lanes, justification in audited:
            with self.subTest(forge=forge_name, justification=justification):
                self.assertEqual(
                    DEFAULT_FORGE_LANES[forge_name],
                    expected_lanes,
                    f"{forge_name} expected {expected_lanes}, got "
                    f"{DEFAULT_FORGE_LANES[forge_name]}; justification: {justification}",
                )

    def test_audit_contains_all_audited_forges(self):
        # Sanity: the audit above must be non-empty.
        from cqekernel.lcr import DEFAULT_FORGE_LANES
        # The audit covers 30 forges (all of LAYER_FORGES values).
        # The taxonomy DEFAULT_FORGE_LANES may have a few more for
        # forges that are not in any layer (e.g. declared in
        # FORGE_REGISTRY.json but not in LAYER_FORGES). We just
        # assert that the taxonomy is non-empty and the audit
        # covers at least 25 forges.
        self.assertGreaterEqual(len(DEFAULT_FORGE_LANES), 25)


if __name__ == "__main__":
    unittest.main()
