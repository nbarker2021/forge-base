"""Kp3.05.03: exact SU(5) normalization and bounded coupling readouts."""
from __future__ import annotations

import math
from fractions import Fraction as F
from typing import Any, Mapping

from .sm_nbody_bridge import SU5_HYPERCHARGE, su5_traceless_balance


LOCAL_REFERENCE_SNAPSHOT: dict[str, Any] = {
    "dataset_id": "CQECMPLX-Formal-Suite-local-PDG-CODATA-snapshot",
    "source_locator": "CQECMPLX-Formal-Suite/lib/lattice_forge/verify_standard_form_parameter_estimates.py",
    "scale_gev": 91.1876,
    "scale_label": "mZ",
    "scheme": "mixed local snapshot: effective weak angle and low-energy alpha_em",
    "alpha_em_inverse": 137.035999084,
    "sin2_theta": 0.23122,
    "alpha_s": 0.1179,
    "uncertainties": None,
}


def exact_su5_normalization() -> dict[str, F]:
    trace_y2 = sum(value * value for value in SU5_HYPERCHARGE)
    normalization_squared = F(1, 2) / trace_y2
    gy2_over_g2 = normalization_squared
    return {
        "trace_y_squared": trace_y2,
        "normalization_squared": normalization_squared,
        "gY_squared_over_g2_squared": gy2_over_g2,
        "sin2_theta_unification": gy2_over_g2 / (1 + gy2_over_g2),
    }


def calibrated_standard_form(reference: Mapping[str, Any]) -> dict[str, Any]:
    """Convert declared measured anchors into gauge couplings at one scale.

    This is an algebraic readout of inputs, not a prediction of those inputs.
    Mixed schemes are accepted for diagnostic replay but block promotion.
    """
    required = {"dataset_id", "scale_gev", "scheme", "alpha_em_inverse", "sin2_theta", "alpha_s"}
    missing = sorted(required - set(reference))
    if missing:
        raise ValueError(f"missing calibration fields: {', '.join(missing)}")
    alpha_em = 1.0 / float(reference["alpha_em_inverse"])
    sin2 = float(reference["sin2_theta"])
    alpha_s = float(reference["alpha_s"])
    if not (0 < sin2 < 1 and alpha_em > 0 and alpha_s > 0 and float(reference["scale_gev"]) > 0):
        raise ValueError("calibration values lie outside their physical domains")
    cos2 = 1.0 - sin2
    alpha_y = alpha_em / cos2
    alpha_1 = F(5, 3).__float__() * alpha_y
    alpha_2 = alpha_em / sin2
    outputs = {
        "alpha_em": alpha_em,
        "alphaY": alpha_y,
        "alpha1_GUT": alpha_1,
        "alpha2": alpha_2,
        "alpha3": alpha_s,
        "gY": math.sqrt(4 * math.pi * alpha_y),
        "g1_GUT": math.sqrt(4 * math.pi * alpha_1),
        "g2": math.sqrt(4 * math.pi * alpha_2),
        "g3": math.sqrt(4 * math.pi * alpha_s),
    }
    uncertainties = reference.get("uncertainties")
    scheme = str(reference["scheme"]).lower()
    promotable = bool(uncertainties) and "mixed" not in scheme
    return {
        "classification": "calibrated" if promotable else "best_estimate_unpromoted",
        "dataset_id": reference["dataset_id"],
        "source_locator": reference.get("source_locator"),
        "scale": {"value": float(reference["scale_gev"]), "unit": "GeV", "label": reference.get("scale_label")},
        "scheme": reference["scheme"],
        "input_uncertainties": uncertainties,
        "outputs": outputs,
        "residual": None,
        "falsifier": "Recompute from a single-scheme primary dataset; disagreement beyond propagated uncertainty falsifies the readout.",
        "boundary": "All numeric low-energy values are input-derived. No no-fit prediction or RG evolution is claimed.",
    }


def verify_coupling_bridge() -> dict[str, Any]:
    exact = exact_su5_normalization()
    estimate = calibrated_standard_form(LOCAL_REFERENCE_SNAPSHOT)
    checks = {
        "generator_traceless": su5_traceless_balance() == 0,
        "five_slot_orderer": len(SU5_HYPERCHARGE) == 5,
        "trace_y2_is_5_over_6": exact["trace_y_squared"] == F(5, 6),
        "normalization_is_3_over_5": exact["normalization_squared"] == F(3, 5),
        "unification_sin2_is_3_over_8": exact["sin2_theta_unification"] == F(3, 8),
        "calibrated_outputs_positive": all(value > 0 for value in estimate["outputs"].values()),
        "mixed_snapshot_not_promoted": estimate["classification"] == "best_estimate_unpromoted",
    }
    return {
        "schema": "Kp3.05.03-CouplingBridge/1.0",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "exact": {key: str(value) for key, value in exact.items()},
        "calibrated_example": estimate,
        "checks": checks,
        "open": ["primary single-scheme dataset with uncertainty", "physical unification scale", "RG thresholds", "absolute no-fit coupling scale"],
    }
