"""Disjoint-window evaluation for depth-only Oloid Rule 30 candidates."""
from __future__ import annotations

from typing import Any

from .rule30 import canonical_rows, rule30_oloid_winding_from_n


SESSION3_CANDIDATES: tuple[dict[str, Any], ...] = (
    {"candidate_id": "default_identity"},
    {
        "candidate_id": "session3_scan_best_phi",
        "axis_angle": 2.0943951023931953,
        "pattern": "alternating_xy",
        "parameterization": "phi",
        "shell_axis": "z",
        "side_axis": "x",
        "shell_offset": -0.125,
    },
    {
        "candidate_id": "perpendicular_double",
        "axis_angle": 0.5235987755982988,
        "pattern": "perpendicular_pair",
        "parameterization": "double",
        "shell_axis": "z",
        "side_axis": "x",
        "shell_offset": -0.125,
    },
    {
        "candidate_id": "golden_angle_identity",
        "axis_angle": 2.3999632297286535,
        "pattern": "alternating_xy",
        "parameterization": "identity",
        "shell_axis": "z",
        "side_axis": "y",
        "shell_offset": -0.125,
    },
)


def _validate_window(window: tuple[int, int]) -> None:
    start, end = window
    if start < 1 or end < start:
        raise ValueError(f"invalid positive inclusive window: {window}")


def _window_result(
    config: dict[str, Any],
    window: tuple[int, int],
    rows: list[dict[int, int]],
) -> dict[str, Any]:
    start, end = window
    defects: list[int] = []
    for n in range(start, end + 1):
        witness = rule30_oloid_winding_from_n(n, **config)
        expected = rows[n].get(0, 0)
        if witness["emitted_bit"] != expected:
            defects.append(n)
    depth_count = end - start + 1
    return {
        "window": [start, end],
        "depths": depth_count,
        "defects": len(defects),
        "accuracy": (depth_count - len(defects)) / depth_count,
        "first_defects": defects[:16],
    }


def evaluate_candidate(
    config: dict[str, Any],
    *,
    train_window: tuple[int, int],
    validation_window: tuple[int, int],
) -> dict[str, Any]:
    """Evaluate one candidate without allowing train/validation overlap."""
    _validate_window(train_window)
    _validate_window(validation_window)
    train_start, train_end = train_window
    validation_start, validation_end = validation_window
    if not (train_end < validation_start or validation_end < train_start):
        raise ValueError("train and validation windows must be disjoint")

    candidate_id = str(config.get("candidate_id", "anonymous"))
    winding_config = {key: value for key, value in config.items() if key != "candidate_id"}
    rows = canonical_rows(max(train_end, validation_end))
    train = _window_result(winding_config, train_window, rows)
    validation = _window_result(winding_config, validation_window, rows)
    zero_defect_train = train["defects"] == 0
    zero_defect_validation = validation["defects"] == 0
    promotable = zero_defect_train and zero_defect_validation
    return {
        "candidate_id": candidate_id,
        "config": winding_config,
        "train_window": train["window"],
        "validation_window": validation["window"],
        "train_depths": train["depths"],
        "validation_depths": validation["depths"],
        "train_defects": train["defects"],
        "validation_defects": validation["defects"],
        "train_accuracy": train["accuracy"],
        "validation_accuracy": validation["accuracy"],
        "train_first_defects": train["first_defects"],
        "validation_first_defects": validation["first_defects"],
        "zero_defect_train": zero_defect_train,
        "zero_defect_validation": zero_defect_validation,
        "promotable_depth_only_bridge": promotable,
        "classification": "promotable_bounded_witness" if promotable else "rejected",
    }


def rank_candidates(
    candidates: tuple[dict[str, Any], ...],
    *,
    train_window: tuple[int, int],
    validation_window: tuple[int, int],
) -> list[dict[str, Any]]:
    """Evaluate and rank candidates by held-out defects, then train defects."""
    rows = [
        evaluate_candidate(
            candidate,
            train_window=train_window,
            validation_window=validation_window,
        )
        for candidate in candidates
    ]
    return sorted(
        rows,
        key=lambda row: (
            row["validation_defects"],
            row["train_defects"],
            row["candidate_id"],
        ),
    )


def verify_oloid_model_selection(
    *,
    train_window: tuple[int, int] = (1, 64),
    validation_window: tuple[int, int] = (65, 128),
) -> dict[str, Any]:
    """Run the Session 3 candidates and report whether any bridge generalizes."""
    ranked = rank_candidates(
        SESSION3_CANDIDATES,
        train_window=train_window,
        validation_window=validation_window,
    )
    any_promotable = any(row["promotable_depth_only_bridge"] for row in ranked)
    return {
        "status": "pass_with_bounded_witness" if any_promotable else "pass_with_open_bridge",
        "candidate_count": len(ranked),
        "train_window": list(train_window),
        "validation_window": list(validation_window),
        "any_promotable_depth_only_bridge": any_promotable,
        "best_candidate": ranked[0],
        "ranked_candidates": ranked,
        "proof_boundary": (
            "A bounded witness is not a theorem for arbitrary N. Promotion to a "
            "prize claim still requires a derived t(N) or fingerprint function "
            "and validation beyond fitted windows."
        ),
    }

