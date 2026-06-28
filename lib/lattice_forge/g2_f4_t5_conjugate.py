"""Bounded G2/F4/T5A route classifier for the standalone proof surface.

This module classifies an already-enumerated Rule 30 bit. It does not derive
the bit from depth N. The explicit boundary fields prevent the bounded route
witness from being promoted into a cold-start nth-bit theorem.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Callable

from .block_tower import rule30_center_column
from .chart_codec_d4 import ANTIPODAL_LABEL, SHEET_SIGN
from .octonion import O_ONE, Octonion
from .oloid_octonionic import OctonionicOloidState
from .rule30 import canonical_rows


G2_REPRESENTATIVE_PERMUTATION: tuple[int, ...] = (0, 2, 3, 1, 4, 6, 7, 5)
F4_REPRESENTATIVE_AXIS_CYCLE: dict[int, int] = {0: 0, 1: 2, 2: 3, 3: 1}
T_5A_COEFFICIENTS: tuple[int, ...] = (
    134,
    760,
    3345,
    12256,
    39350,
    113935,
    303248,
    755820,
    1782496,
    4011164,
    8676544,
    18108960,
    36667986,
    72145460,
    138588460,
    260603320,
)


def g2_representative_permutation(state: OctonionicOloidState) -> OctonionicOloidState:
    """Apply the representative order-three basis permutation."""
    components = state.octonion.components
    moved = tuple(components[G2_REPRESENTATIVE_PERMUTATION[i]] for i in range(8))
    return OctonionicOloidState(Octonion(moved))


def f4_representative_chart_cycle(chart_axis: int) -> int:
    """Apply the representative fixed-axis plus three-cycle action."""
    if chart_axis not in F4_REPRESENTATIVE_AXIS_CYCLE:
        raise ValueError(f"chart_axis must be in {{0,1,2,3}}, got {chart_axis}")
    return F4_REPRESENTATIVE_AXIS_CYCLE[chart_axis]


def t5_modular_conjugate(k: int) -> int:
    """Return parity of the bounded hardcoded T5A coefficient at index k."""
    if not (1 <= k <= len(T_5A_COEFFICIENTS)):
        raise ValueError(f"k must be in [1, {len(T_5A_COEFFICIENTS)}], got {k}")
    return T_5A_COEFFICIENTS[k - 1] & 1


def conjugate_triple_route(
    n: int,
    enumeration_bit_fn: Callable[[int], int],
    coefficient_table_size: int = 16,
) -> dict[str, Any]:
    """Classify an oracle-enumerated bit into a route of at most three stages."""
    if n < 1:
        raise ValueError("n must be >= 1")
    if not (1 <= coefficient_table_size <= len(T_5A_COEFFICIENTS)):
        raise ValueError("coefficient_table_size is outside the bounded T5A table")

    bit = enumeration_bit_fn(n)
    if bit not in (0, 1):
        raise ValueError("enumeration_bit_fn must return a binary bit")

    row = canonical_rows(n)[n]
    state = (row.get(-1, 0), row.get(0, 0), row.get(1, 0))
    axis = ANTIPODAL_LABEL[state]
    sheet = SHEET_SIGN[state]
    paths = {
        0: [],
        1: ["G2"],
        2: ["G2", "F4"],
        3: ["G2", "F4", "T5A"],
    }
    path = paths[axis]
    route: dict[str, Any] = {
        "N": n,
        "bit_at_N": bit,
        "bit_at_minus_N": 1 - bit,
        "chart_axis": axis,
        "chart_sheet": sheet,
        "moves_to_resolution": len(path),
        "conjugate_path": path,
        "resolved_bit": bit,
        "oracle_backed": True,
        "depth_only_bridge": False,
        "proof_boundary": "route classifies an enumerated bit; it does not derive the bit from N",
    }
    if axis >= 2:
        route["f4_routed_axis"] = f4_representative_chart_cycle(axis)
    if axis == 3:
        k = min(n, coefficient_table_size)
        route["t5_k"] = k
        route["t5_parity"] = t5_modular_conjugate(k)
    return route


def verify_conjugate_triple(max_depth: int = 256) -> dict[str, Any]:
    """Run the bounded classifier and report its explicit honesty boundary."""
    bits = rule30_center_column(max_depth)
    enum = lambda n: bits[n - 1]
    depths: Counter[int] = Counter()
    axes: Counter[int] = Counter()
    matches = 0

    for n in range(1, max_depth + 1):
        route = conjugate_triple_route(n, enum)
        depths[route["moves_to_resolution"]] += 1
        axes[route["chart_axis"]] += 1
        matches += route["resolved_bit"] == enum(n)

    g2_state = OctonionicOloidState(Octonion((0, 1, 0, 0, 0, 0, 0, 0)))
    g2_e1_maps_to_e3 = (
        g2_representative_permutation(g2_state).octonion.components
        == (0, 0, 0, 1, 0, 0, 0, 0)
    )
    f4_cycle_correct = [f4_representative_chart_cycle(axis) for axis in range(4)] == [
        0,
        2,
        3,
        1,
    ]
    all_resolved_in_3_or_less = all(depth in (0, 1, 2, 3) for depth in depths)
    status = "pass" if g2_e1_maps_to_e3 and f4_cycle_correct and all_resolved_in_3_or_less else "fail"
    return {
        "status": status,
        "honesty": "bounded_route_classifier",
        "max_depth_tested": max_depth,
        "oracle_backed": True,
        "depth_only_bridge": False,
        "g2_e1_maps_to_e3": g2_e1_maps_to_e3,
        "f4_chart_cycle_correct": f4_cycle_correct,
        "resolution_depth_distribution": dict(depths),
        "chart_axis_distribution": dict(axes),
        "all_resolved_in_3_or_less": all_resolved_in_3_or_less,
        "matches_enumeration_count": matches,
        "matches_enumeration_rate": matches / max_depth if max_depth else 0.0,
        "proof_boundary": "oracle-backed route classifier; cold-start depth-only bridge remains open",
    }
