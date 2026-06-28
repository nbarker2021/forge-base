"""Vendored Rule 30 decomposition paper (Sections 1–10; separate from PROVEN lattice-forge proofs)."""

from .checkpoint_store import Rule30Checkpoints, rule30_center_column, verify_checkpoint_store
from .empirical import (
    center_density,
    chart_conditional_entropy,
    chart_periodicity_scan,
    lucas_sparsity_at,
)
from .rule30_decomposition import (
    CHART_STATES,
    CORRECTION_FIRING_CHART_STATES,
    correction,
    correction_from_chart,
    linearization_identity_holds,
    lucas_bit,
    rule30,
    rule30_center_via_decomposition,
    rule30_full_grid,
    rule90,
    rule90_full_grid,
    verify_all_theorems,
)

__all__ = [
    "CHART_STATES",
    "CORRECTION_FIRING_CHART_STATES",
    "Rule30Checkpoints",
    "center_density",
    "chart_conditional_entropy",
    "chart_periodicity_scan",
    "correction",
    "correction_from_chart",
    "linearization_identity_holds",
    "lucas_bit",
    "lucas_sparsity_at",
    "rule30",
    "rule30_center_column",
    "rule30_center_via_decomposition",
    "rule30_full_grid",
    "rule90",
    "rule90_full_grid",
    "verify_all_theorems",
    "verify_checkpoint_store",
]
