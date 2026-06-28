"""
Tests for the OloidChart: the 8-state chart the oloid winding
classifies over a pre-existing rule-30 bit at position n.

Coverage:
  * OloidMode enum has the 8 expected lanes.
  * build_oloid_chart(n) for n=0 returns a degenerate chart.
  * build_oloid_chart(n) for n>=1 returns a chart with 8 states.
  * Exactly one lane per chart is best (is_best=True).
  * The chart's content_hash is content-addressed: same n -> same hash.
  * Different n -> different hash.
  * The chart's to_dict() round-trips through json.dumps.
  * The chart's center_bit matches the CAME bit at n (when CAME
    is materialised).
  * The chart's best_lane is one of the 8 OloidMode values.
  * The chart's antipodal_definition is non-empty.
  * The chart's states all have a valid OloidMode.
  * The 8 states carry the same reference_vector except view_axis
    (which is the antipode's).
  * The OLOID_CHART_LANES tuple has exactly 8 entries.
  * chart.lane(mode) returns the right state.
  * chart.best_state returns the lane(mode) for best_lane.

All tests are stdlib-only. The chart's lattice_forge
dependency is lazy and may be skipped if not on sys.path.
"""

import json
import unittest
from pathlib import Path
import sys

# Make the cqekernel package importable from this test file's location.
_THIS = Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS.parents[1]))

from cqekernel.lcr.oloid import (
    OLOID_CHART_LANES,
    OloidChart,
    OloidMode,
    OloidState,
    build_oloid_chart,
)


class TestOloidModeEnum(unittest.TestCase):
    """The 8 OloidMode values are stable and ordered."""

    def test_eight_modes(self):
        self.assertEqual(len(list(OloidMode)), 8)

    def test_mode_names(self):
        self.assertEqual(
            {m.value for m in OloidMode},
            {
                "forward", "antipode", "xor", "or", "and",
                "parity_corrected_forward", "side_corrected_forward",
                "view_axis",
            },
        )

    def test_oloid_chart_lanes_matches_modes(self):
        self.assertEqual(len(OLOID_CHART_LANES), 8)
        self.assertEqual(set(OLOID_CHART_LANES), set(OloidMode))


class TestOloidChartShape(unittest.TestCase):
    """The chart's shape and dataclass invariants."""

    def test_chart_has_8_states(self):
        c = build_oloid_chart(16)
        self.assertEqual(c.state_count, 8)
        self.assertEqual(len(c.states), 8)

    def test_chart_states_cover_all_modes(self):
        c = build_oloid_chart(16)
        lane_values = {s.lane for s in c.states}
        self.assertEqual(lane_values, set(OloidMode))

    def test_exactly_one_best_per_chart(self):
        for n in (0, 1, 16, 100, 1000, 10000):
            c = build_oloid_chart(n)
            bests = [s for s in c.states if s.is_best]
            self.assertEqual(
                len(bests), 1,
                f"chart for n={n} has {len(bests)} best lanes, expected 1",
            )
            # The best state matches the chart's best_lane.
            self.assertEqual(bests[0].lane, c.best_lane)

    def test_best_lane_is_valid_mode(self):
        for n in (0, 1, 16, 100, 1000):
            c = build_oloid_chart(n)
            self.assertIn(c.best_lane, OloidMode)

    def test_antipodal_definition_non_empty(self):
        c = build_oloid_chart(16)
        self.assertGreater(len(c.antipodal_definition), 0)
        # The "meaning" key is always present.
        self.assertIn("meaning", c.antipodal_definition)

    def test_notes_non_empty(self):
        c = build_oloid_chart(16)
        self.assertGreater(len(c.notes), 0)
        # The notes mention the pre-existing rule-30 bit.
        self.assertIn("rule-30", c.notes)

    def test_chart_id_format(self):
        c = build_oloid_chart(42)
        # chart_id is "oloid:<n>:<best_lane>".
        self.assertTrue(c.chart_id.startswith("oloid:42:"))


class TestOloidChartContentAddressed(unittest.TestCase):
    """The chart's content_hash is content-addressed."""

    def test_same_n_same_hash(self):
        c1 = build_oloid_chart(16)
        c2 = build_oloid_chart(16)
        self.assertEqual(c1.content_hash, c2.content_hash)
        self.assertEqual(c1.chart_id, c2.chart_id)

    def test_different_n_different_hash(self):
        c16 = build_oloid_chart(16)
        c17 = build_oloid_chart(17)
        self.assertNotEqual(c16.content_hash, c17.content_hash)
        self.assertNotEqual(c16.chart_id, c17.chart_id)

    def test_hash_is_sha256_hex(self):
        c = build_oloid_chart(16)
        self.assertEqual(len(c.content_hash), 64)
        int(c.content_hash, 16)  # raises if not valid hex


class TestOloidChartSerialization(unittest.TestCase):
    """to_dict round-trips; the hash is well-defined (no self-ref)."""

    def test_to_dict_round_trips(self):
        c = build_oloid_chart(16)
        d = c.to_dict()
        # The dict is JSON-serialisable.
        body = json.dumps(d, sort_keys=True)
        # Re-parse and check the key invariants.
        parsed = json.loads(body)
        self.assertIn("content_hash", parsed)
        self.assertEqual(parsed["content_hash"], c.content_hash)
        self.assertEqual(parsed["n"], 16)
        self.assertEqual(parsed["state_count"], 8)
        self.assertEqual(len(parsed["states"]), 8)

    def test_to_dict_no_self_reference(self):
        """If to_dict() put content_hash *inside* the body it
        hashes, the hash would recurse. Verify the canonical
        body (without content_hash) hashes to the same value
        as content_hash."""
        c = build_oloid_chart(16)
        # The content_hash property uses
        #   json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        # We re-derive the expected hash with the exact same
        # encoding to confirm the canonical body (which
        # _canonical_dict() builds) is what gets hashed.
        import hashlib
        body = json.dumps(
            c._canonical_dict(), sort_keys=True, separators=(",", ":")
        )
        expected = hashlib.sha256(body.encode("utf-8")).hexdigest()
        self.assertEqual(c.content_hash, expected)


class TestOloidChartLaneAccess(unittest.TestCase):
    """chart.lane(mode) and chart.best_state are the access surface."""

    def test_lane_returns_correct_state(self):
        c = build_oloid_chart(16)
        for mode in OloidMode:
            s = c.lane(mode)
            self.assertEqual(s.lane, mode)

    def test_unknown_mode_raises(self):
        c = build_oloid_chart(16)
        with self.assertRaises(KeyError):
            # Use a non-existent mode by hand-rolling
            class _FakeMode:
                value = "not_a_real_mode"
            c.lane(_FakeMode())

    def test_best_state_matches_best_lane(self):
        c = build_oloid_chart(16)
        self.assertEqual(c.best_state.lane, c.best_lane)


class TestOloidChartReferenceVector(unittest.TestCase):
    """The 8 states share the forward reference vector; view_axis
    carries the antipode's reference vector."""

    def test_seven_modes_share_forward_reference_vector(self):
        for n in (1, 16, 100, 1000):
            c = build_oloid_chart(n)
            fwd_rv = c.lane(OloidMode.FORWARD).reference_vector
            for mode in OloidMode:
                if mode == OloidMode.VIEW_AXIS:
                    continue
                self.assertEqual(
                    c.lane(mode).reference_vector, fwd_rv,
                    f"mode {mode.value} for n={n} does not share the "
                    f"forward reference vector",
                )

    def test_view_axis_carries_antipode_reference_vector(self):
        for n in (1, 16, 100, 1000):
            c = build_oloid_chart(n)
            view_rv = c.lane(OloidMode.VIEW_AXIS).reference_vector
            fwd_rv = c.lane(OloidMode.FORWARD).reference_vector
            # The view_axis reference vector is the antipode's,
            # which is the forward's sign-flipped (or a different
            # vector entirely). At minimum, it should differ from
            # the forward reference vector.
            self.assertNotEqual(
                view_rv, fwd_rv,
                f"view_axis should not equal forward at n={n}",
            )


class TestOloidChartDegenerate(unittest.TestCase):
    """n=0 is degenerate (the oloid's n must be >= 1)."""

    def test_n_zero_returns_degenerate_chart(self):
        c = build_oloid_chart(0)
        self.assertEqual(c.n, 0)
        self.assertEqual(c.center_bit, 0)
        self.assertEqual(c.state_count, 8)
        # All 8 states have the same emit bit (0) and the same
        # shell (0) and the same side (0).
        for s in c.states:
            self.assertEqual(s.emitted_bit, 0)
            self.assertEqual(s.shell, 0)
            self.assertEqual(s.side, 0)
        # The best lane is FORWARD (the default fallback).
        self.assertEqual(c.best_lane, OloidMode.FORWARD)

    def test_negative_n_raises(self):
        with self.assertRaises(ValueError):
            build_oloid_chart(-1)


class TestOloidChartIntegrationWithCAME(unittest.TestCase):
    """The chart's center_bit matches the CAME bit at the same n.

    This test only runs if the CAME is on disk (it is, in the
    packaged data). The lookup is O(1) after materialise.
    """

    def test_center_bit_matches_came_bit(self):
        try:
            import lattice_forge as lf
            from pathlib import Path
            import tempfile
            db = Path(tempfile.gettempdir()) / "amk_test_oloid" / "cache.sqlite"
            db.parent.mkdir(parents=True, exist_ok=True)
            cache = lf.CmplxLookupCache(db)
            cache.materialize()
        except Exception as e:
            self.skipTest(f"CAME not available: {e}")

        for n in (1, 16, 100, 1000, 10000):
            with self.subTest(n=n):
                came_bit = cache.lookup_rule30_bit(n).value
                chart = build_oloid_chart(n)
                self.assertEqual(
                    chart.center_bit, came_bit,
                    f"oloid center_bit ({chart.center_bit}) "
                    f"!= CAME bit ({came_bit}) at n={n}",
                )
        cache.close()


if __name__ == "__main__":
    unittest.main()
