from __future__ import annotations

from typing import Any

from ..g2_f4_t5_conjugate import (
    F4_REPRESENTATIVE_AXIS_CYCLE,
    G2_REPRESENTATIVE_PERMUTATION,
)
from ..ledger.roots import root_system_E6, root_system_E7, root_system_E8
from .schema import WorkStore


def _e6_e7_cartan_delta() -> list[tuple[int, int]]:
    """Edges present in E7 but extending E6 (rank 6 -> 7)."""
    e6_edges = {(2, 0), (0, 1), (2, 3), (3, 4), (2, 5)}
    e7_edges = {(2, 0), (0, 1), (2, 3), (3, 4), (4, 6), (2, 5)}
    return sorted(e7_edges - e6_edges)


def _e7_e8_cartan_delta() -> list[tuple[int, int]]:
    e7_edges = {(2, 0), (0, 1), (2, 3), (3, 4), (4, 6), (2, 5)}
    e8_edges = {(2, 0), (0, 1), (2, 3), (3, 4), (4, 6), (6, 7), (2, 5)}
    return sorted(e8_edges - e7_edges)


def materialize_exceptional_spine(
    store: WorkStore,
    *,
    include: set[str],
) -> dict[str, Any]:
    """Populate exceptional_node / exceptional_morphism for G2, F4, E6, E7, E8."""
    include_norm = {x.strip().upper().replace("₂", "2").replace("₄", "4") for x in include}
    # Accept g2, G2, etc.
    def wants(label: str) -> bool:
        key = label.upper().replace("₂", "2").replace("₄", "4").replace("₆", "6").replace("₇", "7").replace("₈", "8")
        return key in include_norm or label.lower() in {x.lower() for x in include}

    inserted_nodes: list[str] = []
    inserted_morphisms: list[str] = []

    if wants("G2"):
        store.insert_exceptional_node(
            "G2",
            rank=2,
            parent_id=None,
            payload={
                "dim_lie_algebra": 14,
                "representative": "octonion_automorphism_order3",
                "permutation": list(G2_REPRESENTATIVE_PERMUTATION),
            },
        )
        inserted_nodes.append("G2")

    if wants("F4"):
        store.insert_exceptional_node(
            "F4",
            rank=4,
            parent_id="G2",
            payload={
                "dim_lie_algebra": 52,
                "representative": "jordan_algebra_chart_cycle",
                "axis_cycle": dict(F4_REPRESENTATIVE_AXIS_CYCLE),
            },
        )
        inserted_nodes.append("F4")
        if "G2" in inserted_nodes:
            store.insert_exceptional_morphism(
                source_id="G2",
                target_id="F4",
                morphism_kind="weyl_conjugate",
                operator_ref="g2_f4_t5:conjugate_pairing",
                evidence_level="exact",
                payload={"conjugate_path": ["G2", "F4"]},
            )
            inserted_morphisms.append("G2->F4")

    if wants("E6"):
        e6 = root_system_E6()
        store.insert_exceptional_node(
            "E6",
            rank=e6.rank,
            parent_id=None,
            payload={"name": e6.name, "root_count": len(e6.roots), "simple_root_count": e6.rank},
        )
        inserted_nodes.append("E6")

    if wants("E7"):
        e7 = root_system_E7()
        store.insert_exceptional_node(
            "E7",
            rank=e7.rank,
            parent_id="E6" if "E6" in inserted_nodes else None,
            payload={"name": e7.name, "root_count": len(e7.roots)},
        )
        inserted_nodes.append("E7")
        if "E6" in inserted_nodes:
            store.insert_exceptional_morphism(
                source_id="E6",
                target_id="E7",
                morphism_kind="cartan_extension",
                operator_ref="roots:E6_to_E7",
                evidence_level="template",
                payload={"added_edges": _e6_e7_cartan_delta()},
            )
            inserted_morphisms.append("E6->E7")

    if wants("E8"):
        e8 = root_system_E8()
        store.insert_exceptional_node(
            "E8",
            rank=e8.rank,
            parent_id="E7" if "E7" in inserted_nodes else ("E6" if "E6" in inserted_nodes else None),
            payload={"name": e8.name, "root_count": len(e8.roots)},
        )
        inserted_nodes.append("E8")
        if "E7" in inserted_nodes:
            store.insert_exceptional_morphism(
                source_id="E7",
                target_id="E8",
                morphism_kind="cartan_extension",
                operator_ref="roots:E7_to_E8",
                evidence_level="template",
                payload={"added_edges": _e7_e8_cartan_delta()},
            )
            inserted_morphisms.append("E7->E8")

    store.flush()
    return {
        "nodes": inserted_nodes,
        "morphisms": inserted_morphisms,
        "g2_f4_path": store.has_exceptional_path(["G2", "F4"]) if {"G2", "F4"}.issubset(set(inserted_nodes)) else False,
    }
