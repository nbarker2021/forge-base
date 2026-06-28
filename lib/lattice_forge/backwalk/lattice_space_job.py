from __future__ import annotations

import gc
import time
from pathlib import Path
from typing import Any

from .e8_weyl_pod import E8_WEYL_ORDER, materialize_pod_assignments_for_lattice
from .lattice_catalog import materialize_lattice_catalog
from .proof_capture import materialize_proof_capture_queue
from .schema import WorkStore
from .weyl_bond_dual import QUADRANT_COUNT, WeylBondBatchSpec, iter_batch_specs, materialize_weyl_bond_batch
from .weyl_bond_quadrant import concatenate_quadrant_trees


def _sort_weyl_specs(specs: list[WeylBondBatchSpec]) -> list[WeylBondBatchSpec]:
    def key(s: WeylBondBatchSpec) -> tuple:
        depth_key = -s.dual_depth if s.direction == "construct_in" else s.dual_depth
        return (s.quadrant, s.direction, depth_key, s.source_group, s.target_group)

    return sorted(specs, key=key)


def run_lattice_space_exhaustion(
    store: WorkStore,
    *,
    resume: bool = False,
    max_rows_per_weyl_batch: int = 64,
    weyl_sleep_ms: int = 50,
    mirror_oloid: bool = True,
    max_library_needs: int = 200,
    max_pod_per_lattice: int | None = None,
) -> dict[str, Any]:
    """Full job: lattice catalog → quadrant weyl → E8 pod assignments → proof capture → concat."""
    t0 = time.perf_counter()
    phases: dict[str, Any] = {}

    # Phase 1: lattice forms
    bid = "phase:lattice_catalog"
    if not resume or not store.is_lattice_space_batch_done(bid):
        phases["lattice_catalog"] = materialize_lattice_catalog(store)
        store.lattice_space_batch_done(bid, "lattice_catalog", phases["lattice_catalog"]["lattice_forms_written"])
    else:
        phases["lattice_catalog"] = {"skipped": True, "count": store.count_lattice_forms()}

    # Phase 2: quadrant weyl (only method)
    weyl_specs = _sort_weyl_specs(list(iter_batch_specs(include_read_out=True)))
    weyl_completed = 0
    weyl_rows = 0
    for spec in weyl_specs:
        wb = f"phase:weyl:{spec.batch_id}"
        if resume and (
            store.is_lattice_space_batch_done(wb) or store.is_weyl_batch_done(spec.batch_id)
        ):
            continue
        stats = materialize_weyl_bond_batch(
            store, spec, max_rows=max_rows_per_weyl_batch, mirror_oloid=mirror_oloid
        )
        store.weyl_batch_done(spec.batch_id, spec.wave_id, stats["rows_written"])
        store.lattice_space_batch_done(wb, "weyl_quadrant", stats["rows_written"])
        weyl_completed += 1
        weyl_rows += stats["rows_written"]
        if weyl_sleep_ms > 0:
            time.sleep(weyl_sleep_ms / 1000.0)
    phases["weyl_quadrant"] = {
        "batches": len(weyl_specs),
        "completed": weyl_completed,
        "rows": weyl_rows,
    }

    tree_root = concatenate_quadrant_trees(store, tree_path="weyl_bond_result_tree.json")
    phases["weyl_concat"] = {"total_bonds": tree_root.get("total_bonds")}

    # Phase 3: E8 pod assignments per lattice form (batched by terminal)
    pod_total = 0
    lattice_ids = [
        r[0]
        for r in store._conn.execute(
            """
            SELECT lattice_form_id FROM lattice_form_registry
            WHERE access_kind IN ('terminal_24d', 'product')
            ORDER BY lattice_form_id
            """
        ).fetchall()
    ]
    for lf_id in lattice_ids:
        pb = f"phase:pod:{lf_id}"
        if resume and store.is_lattice_space_batch_done(pb):
            continue
        stats = materialize_pod_assignments_for_lattice(
            store, lf_id, max_assignments=max_pod_per_lattice
        )
        store.lattice_space_batch_done(pb, "e8_pod_assign", stats["assignments_written"])
        pod_total += stats["assignments_written"]
        if len(lattice_ids) > 50:
            gc.collect()
    phases["e8_pod_assign"] = {
        "lattice_forms": len(lattice_ids),
        "assignments_written": pod_total,
        "e8_weyl_order": E8_WEYL_ORDER,
        "bijection_note": "surjective index; full 696729600 not stored literally",
    }

    # Phase 4: proof / capture queue
    bid = "phase:proof_capture"
    if not resume or not store.is_lattice_space_batch_done(bid):
        phases["proof_capture"] = materialize_proof_capture_queue(
            store, max_rows=max_library_needs
        )
        store.lattice_space_batch_done(bid, "proof_capture", phases["proof_capture"]["written"])
    else:
        phases["proof_capture"] = {"skipped": True, "count": store.count_proof_captures()}

    return {
        "wall_seconds": time.perf_counter() - t0,
        "phases": phases,
        "lattice_form_count": store.count_lattice_forms(),
        "weyl_bond_count": store.count_weyl_bonds(),
        "pod_assignment_count": store.count_pod_assignments(),
        "proof_capture_count": store.count_proof_captures(),
        "quadrant_count": QUADRANT_COUNT,
        "result_tree": tree_root,
    }
