"""Exact structural 3-body / 5-slot observer bridge for Kp3.05.

This module promotes the already-executed Formal Suite bridge into the Git
runtime. It closes only the representation-level carrier. Numeric couplings,
RG thresholds, mixing matrices, masses, and SU(5) phenomenology remain open.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Sequence

from .reduced_nbody import ReducedNBodyState, lagrangian_value, verify_reduced_nbody
from .voa_harness import LANE_PARTITION, VALID_CLASSES, five_lane_router


SU5_HYPERCHARGE = (
    Fraction(-1, 3), Fraction(-1, 3), Fraction(-1, 3),
    Fraction(1, 2), Fraction(1, 2),
)


def su5_traceless_balance(generator: Sequence[Fraction] = SU5_HYPERCHARGE) -> Fraction:
    return sum(generator, start=Fraction(0))


def su5_observer_decomposition(generator: Sequence[Fraction] = SU5_HYPERCHARGE) -> dict[str, Any]:
    if len(generator) != 5:
        raise ValueError("SU(5) observer carrier requires exactly five slots")
    color, weak = tuple(generator[:3]), tuple(generator[3:])
    if len(set(color)) != 1 or len(set(weak)) != 1:
        raise ValueError("S(U(3)xU(2)) block weights must be constant within each block")
    if su5_traceless_balance(generator) != 0:
        raise ValueError("SU(5) generator must be traceless")
    dimensions = {"su5": 24, "su3": 8, "su2": 3, "u1": 1, "complement": 12}
    if dimensions["su5"] != sum(dimensions[key] for key in ("su3", "su2", "u1", "complement")):
        raise AssertionError("Lie algebra dimension decomposition failed")
    return {
        "ordinary_math": "su(5) = su(3) + su(2) + u(1) + (3,2) + (bar3,2)",
        "cqe_reading": "SU(3)_observer + C(U(1)) + L(SU(2)) + open complement",
        "generator": [str(value) for value in generator],
        "color_slots": 3,
        "weak_slots": 2,
        "dimensions": dimensions,
        "normalization_boundary": (
            "The 3:2 traceless ratio is forced by block multiplicities. "
            "The displayed absolute scale uses the standard weak-doublet convention b=+1/2."
        ),
    }


def verify_nbody_3_5_hierarchy(max_depth: int = 256) -> dict[str, Any]:
    nbody = verify_reduced_nbody(max_depth=max_depth)
    lagrangian_values = sorted({
        lagrangian_value(ReducedNBodyState(1, 0, 0, axis, sheet))
        for axis in range(4) for sheet in range(2)
    })
    decomposition = su5_observer_decomposition()
    router = five_lane_router(max_depth=max_depth)
    core = sorted(name for name, lane in LANE_PARTITION.items() if lane == "C")
    boundary = sorted(name for name, lane in LANE_PARTITION.items() if lane in {"L", "R"})

    negative_tests = {
        "nontraceless_generator_rejected": False,
        "wrong_slot_count_rejected": False,
        "nonconstant_block_rejected": False,
    }
    for key, candidate in (
        ("nontraceless_generator_rejected", (*SU5_HYPERCHARGE[:-1], Fraction(2, 3))),
        ("wrong_slot_count_rejected", SU5_HYPERCHARGE[:-1]),
        ("nonconstant_block_rejected", (Fraction(-1, 2), *SU5_HYPERCHARGE[1:])),
    ):
        try:
            su5_observer_decomposition(candidate)
        except ValueError:
            negative_tests[key] = True

    checks = {
        "reduced_nbody_computed": nbody.get("status") == "pass",
        "center_chart_exact_at_tested_depth": nbody.get("chart_match_rate") == 1.0,
        "state_has_five_integer_coordinates": nbody.get("state_dimension_per_step") == 5,
        "m3_weyl_average_values": lagrangian_values == [0.0, 1 / 3, 2 / 3, 1.0],
        "su5_is_three_plus_two_slots": decomposition["color_slots"] == 3 and decomposition["weak_slots"] == 2,
        "su5_generator_is_exactly_traceless": su5_traceless_balance() == 0,
        "lie_dimensions_close": decomposition["dimensions"]["su5"] == 24,
        "five_lane_scaffold_is_three_plus_two": core == ["1A", "2A", "3A"] and boundary == ["5A", "7A"],
        "negative_tests_pass": all(negative_tests.values()),
    }
    passed = all(checks.values())
    return {
        "schema": "Kp3.05-NBodySU5Bridge/1.0",
        "verifier": "verify_nbody_3_5_hierarchy",
        "status": "PASS_WITH_OPEN_NUMERIC_PROJECTIONS" if passed else "FAIL",
        "claim_class": "structural_bridge",
        "three_body_kernel": {
            "ordinary_form": "M3=(T12+T13+T23)/3",
            "lagrangian_sample_values": lagrangian_values,
            "tested_depth": max_depth,
            "chart_match_rate": nbody.get("chart_match_rate"),
            "coordinate_count": nbody.get("state_dimension_per_step"),
        },
        "five_slot_orderer": decomposition,
        "projection_scaffold": {
            "classes": sorted(VALID_CLASSES),
            "partition": LANE_PARTITION,
            "triadic_core": core,
            "pentic_boundary": boundary,
            "empirical_router_match_rate": router.get("overall_match_rate"),
            "boundary": "Router execution is retained as a scaffold; its low match rate is not promoted to a coefficient proof.",
        },
        "checks": checks,
        "negative_tests": negative_tests,
        "exports": ["M3 collective kernel", "SU5 3+2 observer orderer", "traceless hypercharge direction"],
        "open_obligations": [
            "derive the complete one-generation field and charge table",
            "verify gauge and mixed anomaly cancellation",
            "separate exact 3/5 normalization from calibrated low-energy couplings",
            "compute one-loop RG flow and explicit threshold models",
            "assign physical status to the 12-generator off-diagonal complement",
        ],
        "honesty_boundary": (
            "This closes the structural M3-to-SU(5) 3+2 observer bridge only. "
            "It does not derive numeric Standard Model parameters or SU(5) phenomenology."
        ),
    }
