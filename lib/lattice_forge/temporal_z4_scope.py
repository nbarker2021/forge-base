"""Separate the static Z4 chart-label template from Rule 30 time dynamics."""
from __future__ import annotations

from typing import Any

from .centroid_voa import four_frame_label, verify_z4_period_template
from .rule30 import canonical_rows


def _first_period_mismatch(values: list[Any], period: int) -> dict[str, Any] | None:
    for index in range(period, len(values)):
        if values[index] != values[index - period]:
            return {
                "period": period,
                "index": index,
                "current": values[index],
                "prior": values[index - period],
            }
    return None


def verify_temporal_z4_scope(max_depth: int = 512) -> dict[str, Any]:
    """Check whether static Z4 periods extend to the actual Rule 30 trace."""
    if max_depth < 8:
        raise ValueError("max_depth must be >= 8")
    rows = canonical_rows(max_depth)
    predecessor_states = [
        (
            rows[n - 1].get(-1, 0),
            rows[n - 1].get(0, 0),
            rows[n - 1].get(1, 0),
        )
        for n in range(1, max_depth + 1)
    ]
    labels = [four_frame_label(state) for state in predecessor_states]
    center_bits = [rows[n].get(0, 0) for n in range(1, max_depth + 1)]
    periods = (1, 2, 4)
    label_counterexamples = {
        period: mismatch
        for period in periods
        if (mismatch := _first_period_mismatch(labels, period)) is not None
    }
    center_counterexamples = {
        period: mismatch
        for period in periods
        if (mismatch := _first_period_mismatch(center_bits, period)) is not None
    }
    label_periodic = {period: period not in label_counterexamples for period in periods}
    center_periodic = {period: period not in center_counterexamples for period in periods}
    temporal_period_claim_supported = any(label_periodic.values()) or any(center_periodic.values())
    return {
        "status": "static_template_only" if not temporal_period_claim_supported else "review_required",
        "max_depth_tested": max_depth,
        "static_template": verify_z4_period_template(),
        "temporal_label_trace_periodic": label_periodic,
        "center_column_periodic": center_periodic,
        "label_counterexamples": label_counterexamples,
        "center_counterexamples": center_counterexamples,
        "temporal_period_claim_supported": temporal_period_claim_supported,
        "proof_boundary": (
            "The static four-frame label has a Z4 orbit template. The tested Rule 30 "
            "label trace and center column do not inherit periods 1, 2, or 4."
        ),
    }
