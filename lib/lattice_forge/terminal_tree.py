from __future__ import annotations

import hashlib
import json
from typing import Any


def _json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _hash(kind: str, payload: Any) -> str:
    body = json.dumps({"kind": kind, "payload": payload}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _component_name(row: dict[str, Any]) -> str:
    return f"{row['component_family']}{row['component_rank']}"


def _component_rank(component_name: str) -> int | None:
    try:
        return int(component_name[1:])
    except (IndexError, ValueError):
        return None


def _component_determinant(component_name: str) -> int | None:
    family = component_name[0]
    rank = _component_rank(component_name)
    if rank is None:
        return None
    if family == "A":
        return rank + 1
    if family == "D":
        return 4
    if component_name == "E6":
        return 3
    if component_name == "E7":
        return 2
    if component_name == "E8":
        return 1
    return None


def _diagram_involutions(component_name: str) -> list[dict[str, Any]]:
    rank = _component_rank(component_name)
    if rank is None:
        return []
    family = component_name[0]
    if family == "A" and rank >= 2:
        return [
            {
                "operator": f"diagram:{component_name}:chain_reversal",
                "order": 2,
                "status": "computed_profile_diagram_involution",
            }
        ]
    if family == "D" and rank == 4:
        return [
            {
                "operator": "diagram:D4:fork_swap",
                "order": 2,
                "status": "computed_profile_diagram_involution",
            },
            {
                "operator": "diagram:D4:triality_transposition_alpha_beta",
                "order": 2,
                "status": "computed_profile_triality_order2_summary",
            },
            {
                "operator": "diagram:D4:triality_transposition_beta_gamma",
                "order": 2,
                "status": "computed_profile_triality_order2_summary",
            },
        ]
    if family == "D" and rank >= 5:
        return [
            {
                "operator": f"diagram:{component_name}:fork_swap",
                "order": 2,
                "status": "computed_profile_diagram_involution",
            }
        ]
    if component_name == "E6":
        return [
            {
                "operator": "diagram:E6:diagram_flip",
                "order": 2,
                "status": "computed_profile_diagram_involution",
            }
        ]
    return []


def terminal_tree_summary(tree: dict[str, Any]) -> dict[str, Any]:
    return {
        "terminal_id": tree.get("terminal_id"),
        "name": (tree.get("object") or {}).get("name"),
        "root_system": (tree.get("terminal") or {}).get("root_system"),
        "status": tree.get("status"),
        "composition_model": tree.get("composition_model"),
        "route_uniqueness": tree.get("route_uniqueness"),
        "ambient_dimension": tree.get("ambient_dimension"),
        "root_rank": tree.get("root_rank"),
        "component_action_count": tree.get("component_action_count", len(tree.get("action_edges", []))),
        "compact_involution_count": tree.get(
            "compact_involution_count",
            (tree.get("involution_tree") or {}).get("compact_edge_count", 0),
        ),
        "residue_status": tree.get("residue_status", (tree.get("closure_residue") or {}).get("status")),
        "evidence_level": tree.get("evidence_level"),
    }


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_terminal_composition_tree(ledger: Any, terminal_id: str) -> dict[str, Any]:
    """Generate the canonical terminal composition tree from seed records.

    This is intentionally a generated view over the immutable seed DB, not a
    stored table. A terminal such as Niemeier:A2^12 is treated as a categorical
    construction request: expand component instances, add them in canonical
    rank-offset order, attach compact local involution generators, and emit the
    residue trace that old prose called "glue".
    """
    terminal_rows = ledger.query("SELECT * FROM terminal_24d_forms WHERE terminal_id=?", [terminal_id])
    terminal = terminal_rows[0] if terminal_rows else None
    obj = ledger.object(terminal_id)
    if not terminal:
        return {
            "terminal_id": terminal_id,
            "status": "missing_terminal",
            "answer": "missing",
            "composition_route": [],
            "action_edges": [],
            "residue_trace": [],
        }

    ambient_dimension = int((obj or {}).get("dimension") or 24)
    components = ledger.components(terminal_id)
    embeddings = ledger.terminal_component_embeddings(terminal_id=terminal_id, limit=None)
    embeddings = sorted(
        embeddings,
        key=lambda row: (
            int(row.get("rank_offset") or 0),
            int(row.get("component_instance_index") or 0),
            row.get("component_label") or "",
        ),
    )

    route: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    residue_trace: list[dict[str, Any]] = []
    source_component_counts: dict[str, int] = {}
    source_rank_cache: dict[str, int] = {}
    cumulative_det = 1
    is_rootless = terminal_id == "Niemeier:Leech" or not embeddings

    root_state_payload = {"terminal_id": terminal_id, "components": []}
    route.append(
        {
            "state_index": 0,
            "state_id": "state:" + _hash("terminal_root", root_state_payload),
            "label": "empty_terminal_context",
            "rank": 0,
            "ambient_dimension": ambient_dimension,
            "component_count": 0,
            "canonical_components": [],
            "status": "rootless_terminal_seed" if is_rootless else "canonical_seed",
        }
    )

    for index, emb in enumerate(embeddings, start=1):
        component_label = emb["component_label"]
        source_id = emb["source_id"]
        if source_id not in source_rank_cache:
            source_obj = ledger.object(source_id) or {}
            source_rank_cache[source_id] = int(source_obj.get("rank") or 0)
        source_component_counts[source_id] = source_component_counts.get(source_id, 0) + 1
        canonical_components = [
            {
                "source_id": prev["source_id"],
                "component_label": prev["component_label"],
                "component_instance_index": prev["component_instance_index"],
                "rank_offset": prev["rank_offset"],
            }
            for prev in embeddings[:index]
        ]
        state_payload = {"terminal_id": terminal_id, "components": canonical_components}
        state = {
            "state_index": index,
            "state_id": "state:" + _hash("terminal_state", state_payload),
            "label": " + ".join(
                f"{count}x{source}" if count > 1 else source
                for source, count in sorted(source_component_counts.items())
            ),
            "rank": sum(source_rank_cache.get(item["source_id"], 0) for item in embeddings[:index]),
            "ambient_dimension": ambient_dimension,
            "component_count": index,
            "canonical_components": canonical_components,
            "status": "canonical_composition_state",
        }
        route.append(state)

        determinant = _component_determinant(component_label)
        if determinant is not None:
            cumulative_det *= determinant
        residue = {
            "state_id": state["state_id"],
            "action": "add_component",
            "component_label": component_label,
            "source_id": source_id,
            "component_instance_index": emb["component_instance_index"],
            "rank_offset": emb["rank_offset"],
            "determinant_multiplier": determinant,
            "cumulative_root_lattice_determinant": cumulative_det if determinant is not None else None,
            "status": "emergent_residue_from_component_action",
        }
        residue_trace.append(residue)
        edges.append(
            {
                "edge_id": "tree_edge:" + _hash("add_component", residue),
                "source_state_id": route[index - 1]["state_id"],
                "target_state_id": state["state_id"],
                "action_type": "add_component",
                "operator": f"embed:{source_id}[{emb['component_instance_index']}]",
                "embedding_id": emb["embedding_id"],
                "residue_delta": residue,
                "status": "legal_canonical_action",
            }
        )

    involution_families: list[dict[str, Any]] = []
    compact_involution_edge_count = 0
    for emb in embeddings:
        source_id = emb["source_id"]
        component_label = emb["component_label"]
        source_obj = ledger.object(source_id) or {}
        source_rank = int(source_obj.get("rank") or _component_rank(component_label) or 0)
        generators = ledger.query(
            """
            SELECT generator_index, COUNT(*) AS action_count
            FROM reflection_action_registry
            WHERE object_id=?
            GROUP BY generator_index
            ORDER BY generator_index
            """,
            [source_id],
        )
        if generators:
            generator_rows = [
                {
                    "generator_index": row["generator_index"],
                    "action_count": row["action_count"],
                    "operator": f"local_reflection:{source_id}:s{row['generator_index']}",
                    "status": "seeded_exact_source_action_lifted_to_terminal_component",
                }
                for row in generators
            ]
        else:
            generator_rows = [
                {
                    "generator_index": idx,
                    "action_count": None,
                    "operator": f"local_reflection:{source_id}:s{idx}",
                    "status": "computed_profile_simple_reflection_generator",
                }
                for idx in range(source_rank)
            ]
        diagrams = _diagram_involutions(component_label)
        family = {
            "component_instance_index": emb["component_instance_index"],
            "component_label": component_label,
            "source_id": source_id,
            "embedding_id": emb["embedding_id"],
            "generator_count": len(generator_rows),
            "generators": generator_rows,
            "diagram_involution_count": len(diagrams),
            "diagram_involutions": diagrams,
            "evidence_level": "exact" if generators else "computed_profile",
        }
        compact_involution_edge_count += len(generator_rows) + len(diagrams)
        involution_families.append(family)

    terminal_disc = ledger.discriminant_profile(terminal_id)
    root_det = _int_or_none((terminal_disc or {}).get("root_lattice_determinant"))
    required_index = _int_or_none((terminal_disc or {}).get("required_overlattice_index"))
    computed_det = cumulative_det if embeddings else root_det
    closes_by_index = (
        required_index is not None
        and computed_det is not None
        and required_index * required_index == computed_det
    )
    closure_residue = {
        "root_lattice_determinant": computed_det,
        "required_overlattice_index": required_index,
        "index_square": required_index * required_index if required_index is not None else None,
        "status": "residue_closes_by_required_index" if closes_by_index else "residue_trace_unresolved",
        "interpretation": (
            "Glue is represented as the canonical residue trace emitted by component actions; "
            "legacy glue rows remain compatibility evidence."
        ),
    }
    root_rank = int(route[-1]["rank"]) if route else 0
    rootful = bool(embeddings)
    evidence = "pending_import" if is_rootless else "template"
    status = "generated_canonical_composition_tree"
    composition_model = "component_action_tree_with_emergent_residue"
    route_uniqueness = "single_canonical_route_after_component_ordering_and_orbit_quotient"
    if is_rootless:
        status = "rootless_terminal_pending_import"
        composition_model = "rootless_terminal_no_component_action_tree"
        route_uniqueness = "single_rootless_terminal_state"
    legacy_glue = ledger.query("SELECT * FROM glue_requirements WHERE target_id=? ORDER BY source_id", [terminal_id])
    component_summary = [
        {
            **component,
            "component_name": _component_name(component),
            "determinant_each": _component_determinant(_component_name(component)),
        }
        for component in components
    ]

    return {
        "terminal_id": terminal_id,
        "ambient_dimension": ambient_dimension,
        "root_rank": root_rank,
        "component_action_count": len(edges),
        "compact_involution_count": compact_involution_edge_count,
        "residue_status": closure_residue["status"],
        "evidence_level": evidence,
        "is_rootful": rootful,
        "object": obj,
        "terminal": {
            **terminal,
            "glue_code": _json(terminal.get("glue_code_json"), {}),
            "known_construction": _json(terminal.get("known_construction_json"), {}),
        },
        "status": status,
        "route_uniqueness": route_uniqueness,
        "composition_model": composition_model,
        "components": component_summary,
        "component_instances": embeddings,
        "composition_route": route,
        "action_edges": edges,
        "residue_trace": residue_trace,
        "closure_residue": closure_residue,
        "involution_tree": {
            "status": "compact_lifted_source_involutions",
            "interpretation": (
                "Each component instance lifts the source root-system reflection/involution generators; "
                "raw vector actions are compressed by generator and component orbit."
            ),
            "component_family_count": len(involution_families),
            "compact_edge_count": compact_involution_edge_count,
            "families": involution_families,
        },
        "legacy_glue_records": legacy_glue,
    }
