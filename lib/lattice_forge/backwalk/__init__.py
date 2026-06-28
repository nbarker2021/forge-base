"""Backward Niemeier category materialization (writable overlay over seed ledger)."""

from .generator import materialize_terminal, materialize_terminals
from .glue_weyl import glue_project_weyl
from .hydrate import hydrate
from .schema import PILOT_TERMINAL_IDS, WorkStore, all_niemeier_terminal_ids
from .exceptional_spine import materialize_exceptional_spine
from .weyl_bond_quadrant import concatenate_quadrant_trees
from .lattice_space_job import run_lattice_space_exhaustion
from .lattice_catalog import materialize_lattice_catalog
from .e8_weyl_pod import E8_WEYL_ORDER, materialize_pod_assignments_for_lattice
from .proof_capture import materialize_proof_capture_queue

__all__ = [
    "PILOT_TERMINAL_IDS",
    "WorkStore",
    "all_niemeier_terminal_ids",
    "glue_project_weyl",
    "hydrate",
    "materialize_exceptional_spine",
    "materialize_terminal",
    "materialize_terminals",
    "concatenate_quadrant_trees",
    "run_lattice_space_exhaustion",
    "materialize_lattice_catalog",
    "E8_WEYL_ORDER",
    "materialize_pod_assignments_for_lattice",
    "materialize_proof_capture_queue",
]
