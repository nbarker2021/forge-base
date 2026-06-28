"""Prediction-first Rule 30 readout receipts.

This module separates the proven constant-time local Rule 30 readout from the
stronger, still-open depth-only shortcut claim. The predictor must produce its
bit from a supplied representative before the ordinary Rule 30 oracle is run.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .block_tower import rule30_center_column
from .cqe.hypervisor import D4Token
from .cqe.light_cone import CQELightConeHypervisor
from .rule30 import rule30_bit

Representative = tuple[int, int, int]
Trial = tuple[int, Representative, str]
CQE_CHAIN = ("D1/A3", "D4/F4", "J3(O)", "D12/D16", "reverse_to_-N")


def _validate_bit(value: int, name: str) -> int:
    if value not in (0, 1):
        raise ValueError(f"{name} must be 0 or 1")
    return value


def _validate_depth(n: int) -> int:
    if not isinstance(n, int):
        raise TypeError("n must be an integer depth")
    if n < 1:
        raise ValueError("n must be at least 1")
    return n


def predict_from_representative(representative: Representative) -> int:
    """Return the next center bit from a local ``(left, center, right)`` state."""

    left, center, right = representative
    return rule30_bit(
        _validate_bit(left, "left"),
        _validate_bit(center, "center"),
        _validate_bit(right, "right"),
    )


def oracle_center_bit(n: int) -> int:
    """Run the ordinary Rule 30 center-column computation for validation."""

    depth = _validate_depth(n)
    return rule30_center_column(depth)[depth - 1]


def predict_then_oracle(
    n: int,
    representative: Representative | None = None,
    *,
    representative_source: str = "provided",
) -> dict[str, Any]:
    """Predict an nth center bit first, then run the Rule 30 oracle.

    Without a representative, this function refuses to claim a depth-only
    sub-logarithmic predictor. That missing depth-to-representative map is the
    active open obligation in the current lattice-forge proof stack.
    """

    depth = _validate_depth(n)
    if representative is None:
        return {
            "status": "open_obligation",
            "n": depth,
            "prediction_made": False,
            "oracle_ran": False,
            "oracle_ran_after_prediction": False,
            "complexity_claim": "NO_DEPTH_ONLY_PREDICTOR",
            "sublog_depth_only_status": "NOT_PROVEN",
            "open_gap": "DEPTH_TO_REPRESENTATIVE_SHORTCUT_MISSING",
        }

    predicted_bit = predict_from_representative(representative)
    oracle_bit = oracle_center_bit(depth)
    match = predicted_bit == oracle_bit

    return {
        "status": "verified" if match else "mismatch",
        "n": depth,
        "representative": representative,
        "representative_source": representative_source,
        "prediction_made": True,
        "predicted_bit": predicted_bit,
        "oracle_ran": True,
        "oracle_ran_after_prediction": True,
        "oracle_bit": oracle_bit,
        "match": match,
        "complexity_claim": "O(1)_GIVEN_REPRESENTATIVE",
        "sublog_depth_only_status": "NOT_CLAIMED",
        "local_operation_count_bound": "constant",
        "oracle_role": "post_prediction_validation",
    }


def enumerate_prediction_trials(trials: Iterable[Trial]) -> dict[str, Any]:
    """Verify several prediction-first trials without promoting the open claim."""

    results = [
        predict_then_oracle(n, representative, representative_source=source)
        for n, representative, source in trials
    ]
    matches = sum(1 for result in results if result.get("match") is True)
    failures = len(results) - matches

    return {
        "status": "pass" if failures == 0 else "fail",
        "trials": len(results),
        "matches": matches,
        "failures": failures,
        "results": results,
        "constant_time_local_readout_proven": failures == 0,
        "depth_only_sublog_proven": False,
        "sublog_depth_only_status": "OPEN_OBLIGATION",
        "open_gap": "DEPTH_TO_REPRESENTATIVE_SHORTCUT_MISSING",
    }


def transport_rule30_representative(
    n: int,
    ribbon: str,
    *,
    rotation: int = 0,
    split_bias: int = 1,
) -> dict[str, Any]:
    """Build a CQE transport receipt, then run prediction-first verification.

    The input ribbon is a known local sheet, not a depth-only derivation from
    ``n``. This applies the CQE chain to the available string and records that
    it has not solved the stronger depth-to-representative problem.
    """

    depth = _validate_depth(n)
    if not ribbon or set(ribbon) - {"0", "1"}:
        raise ValueError("ribbon must be a non-empty binary string")
    if len(ribbon) < 3:
        raise ValueError("ribbon must contain at least three bits")

    normalized_rotation = rotation % 360
    if normalized_rotation not in {0, 90, 180, 270}:
        raise ValueError("rotation must land on 0, 90, 180, or 270 degrees")

    frame = CQELightConeHypervisor(split_bias=split_bias).sample(ribbon, tick=depth)
    base = _centered_lcr(frame.full)
    representative = _rotate_lcr(base, normalized_rotation)
    prediction = predict_then_oracle(
        depth,
        representative,
        representative_source="cqe_transport_from_supplied_ribbon",
    )
    tokens = tuple(
        D4Token.from_bit(index, bit)
        for index, bit in enumerate(representative)
    )
    d16_window = representative + tuple(token.antipode for token in tokens)

    return {
        "status": prediction["status"],
        "n": depth,
        "source_ribbon": frame.full,
        "representative": representative,
        "chain": CQE_CHAIN,
        "d1_a3": {
            "centered_lcr": {"L": representative[0], "C": representative[1], "R": representative[2]},
            "anf": "L XOR C XOR R XOR (C AND R)",
            "spine": ("L", "C", "R"),
            "base_centered_lcr": {"L": base[0], "C": base[1], "R": base[2]},
        },
        "d4_f4": {
            "axes": tuple(token.orbit for token in tokens),
            "cartan_slots": tuple(token.cartan_slot for token in tokens),
            "closures": tuple(token.closure_state for token in tokens),
            "orbit_cycle": ("C", "L", "C", "R", "C"),
        },
        "jordan": {
            "class": _jordan_class(representative),
            "trace": sum(representative),
            "idempotent_diagonal": representative,
        },
        "d12_d16": {
            "action_envelope": "D12_ACTS_ON_D4_AXIS_CLASSES",
            "conjugate_axis_swap": (1, 3),
            "d16_window": d16_window,
            "antipodal_half": d16_window[3:],
        },
        "rotation": {
            "degrees": normalized_rotation,
            "landing": _rotation_landing(normalized_rotation),
            "meaning": _rotation_meaning(normalized_rotation),
        },
        "reverse": {
            "target": "-N",
            "readout_bit": prediction.get("predicted_bit"),
            "oracle_role": prediction.get("oracle_role"),
        },
        "prediction": prediction,
        "n_reduction_status": "RIBBON_TO_REPRESENTATIVE_ONLY",
        "sublog_depth_only_status": "NOT_PROVEN",
        "open_gap": "DEPTH_TO_REPRESENTATIVE_SHORTCUT_MISSING",
    }


def _centered_lcr(ribbon: str) -> Representative:
    center = len(ribbon) // 2
    left = int(ribbon[(center - 1) % len(ribbon)])
    middle = int(ribbon[center])
    right = int(ribbon[(center + 1) % len(ribbon)])
    return left, middle, right


def _rotate_lcr(representative: Representative, rotation: int) -> Representative:
    left, center, right = representative
    if rotation == 0:
        return representative
    if rotation == 90:
        return center, right, left
    if rotation == 180:
        return 1 - right, 1 - center, 1 - left
    return right, left, center


def _rotation_landing(rotation: int) -> str:
    return {
        0: "C",
        90: "L",
        180: "-C",
        270: "R",
    }[rotation]


def _rotation_meaning(rotation: int) -> str:
    return {
        0: "coast on centered representative",
        90: "read left-of-center and write toward C",
        180: "turn to antipodal representative",
        270: "read right-of-center and write toward C",
    }[rotation]


def _jordan_class(representative: Representative) -> str:
    trace = sum(representative)
    if trace in {0, 3}:
        return "terminal_idempotent_candidate"
    return f"rank_{trace}_idempotent_candidate"
