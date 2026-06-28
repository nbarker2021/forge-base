from __future__ import annotations

from typing import Any

from ..algebra.o1_registry import E8_WEYL_ORDER
from ..ledger.exact import stable_hash
from .schema import WorkStore


def weyl_element_index(
    *,
    lattice_form_id: str,
    bond_id: str,
    quadrant: int,
    chart_src: int,
    chart_tgt: int,
    mirror: bool = False,
) -> int:
    """Surjective index into [0, |W(E8)|) for bijection bookkeeping (witness shard)."""
    digest = stable_hash(
        "E8_pod_bijection_v1",
        lattice_form_id,
        bond_id,
        quadrant,
        chart_src,
        chart_tgt,
        mirror,
    )
    return int(digest[:16], 16) % E8_WEYL_ORDER


def materialize_pod_assignments_for_lattice(
    store: WorkStore,
    lattice_form_id: str,
    *,
    max_assignments: int | None = None,
) -> dict[str, Any]:
    """Assign E8 Weyl indices to every materialized weyl bond for one lattice form."""
    written = 0
    bonds = store.iter_weyl_bonds()
    for row in bonds:
        if max_assignments is not None and written >= max_assignments:
            break
        bond_id = row["bond_id"]
        quadrant = int(row["quadrant"])
        chart_src = int(row["chart_src"])
        chart_tgt = int(row["chart_tgt"])
        idx = weyl_element_index(
            lattice_form_id=lattice_form_id,
            bond_id=bond_id,
            quadrant=quadrant,
            chart_src=chart_src,
            chart_tgt=chart_tgt,
            mirror=False,
        )
        aid = f"pod:{stable_hash(lattice_form_id, bond_id)[:32]}"
        store.insert_pod_assignment(
            assignment_id=aid,
            lattice_form_id=lattice_form_id,
            bond_id=bond_id,
            quadrant=quadrant,
            weyl_element_index=idx,
            evidence_level="bounded_exec",
            payload={
                "bijection_kind": "chart_quadrant_pod_shard_surjection",
                "e8_weyl_order": E8_WEYL_ORDER,
                "chart_src": chart_src,
                "chart_tgt": chart_tgt,
            },
        )
        written += 1
        mirror_idx = weyl_element_index(
            lattice_form_id=lattice_form_id,
            bond_id=bond_id,
            quadrant=quadrant,
            chart_src=chart_src,
            chart_tgt=chart_tgt,
            mirror=True,
        )
        if mirror_idx != idx:
            store.insert_pod_assignment(
                assignment_id=f"podm:{stable_hash(lattice_form_id, bond_id, 'm')[:32]}",
                lattice_form_id=lattice_form_id,
                bond_id=bond_id,
                quadrant=quadrant,
                weyl_element_index=mirror_idx,
                evidence_level="bounded_exec",
                payload={
                    "mirror_oloid": True,
                    "e8_weyl_order": E8_WEYL_ORDER,
                },
            )
            written += 1
    store.flush()
    return {"lattice_form_id": lattice_form_id, "assignments_written": written}
