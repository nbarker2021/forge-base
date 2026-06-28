from __future__ import annotations

import time
from typing import Any

from ..seed import SeedStore
from ..terminal_tree import build_terminal_composition_tree, terminal_tree_summary
from .schema import TerminalStats, WorkStore


def _active_component_keys(state: dict[str, Any]) -> set[tuple[str, int]]:
    out: set[tuple[str, int]] = set()
    for comp in state.get("canonical_components") or []:
        out.add((comp.get("source_id", ""), int(comp.get("component_instance_index") or 0)))
    return out


def _involution_evidence(generator_status: str) -> str:
    if "seeded_exact" in generator_status:
        return "exact"
    if "computed_profile" in generator_status:
        return "computed_profile"
    return "template"


def materialize_terminal(
    store: WorkStore,
    ledger: Any,
    terminal_id: str,
    *,
    involution_limit: int | None = None,
) -> TerminalStats:
    """Materialize backward peel + involution morphisms for one Niemeier terminal."""
    t0 = time.perf_counter()
    tree = build_terminal_composition_tree(ledger, terminal_id)
    route = tree.get("composition_route") or []
    action_edges = tree.get("action_edges") or []
    inv_tree = tree.get("involution_tree") or {}
    families = inv_tree.get("families") or []
    ambient = int(tree.get("ambient_dimension") or 24)

    family_by_instance: dict[tuple[str, int], dict[str, Any]] = {}
    for fam in families:
        key = (fam.get("source_id", ""), int(fam.get("component_instance_index") or 0))
        family_by_instance[key] = fam

    peel_count = 0
    inv_count = 0

    for state in route:
        state_id = state["state_id"]
        slice_rank = int(state.get("rank") or 0)
        evidence = "exact" if state.get("status") in (
            "canonical_composition_state",
            "canonical_seed",
            "rootless_terminal_seed",
        ) else "template"
        payload = {
            "state_index": state.get("state_index"),
            "label": state.get("label"),
            "component_count": state.get("component_count"),
            "canonical_components": state.get("canonical_components"),
            "closure_residue": tree.get("closure_residue"),
            "terminal_tree_summary": terminal_tree_summary(tree),
        }
        if state.get("state_index") == len(route) - 1:
            payload["glue_requirements"] = tree.get("legacy_glue_records")
            payload["discriminant_closure"] = tree.get("closure_residue")

        store.insert_object(
            terminal_id=terminal_id,
            slice_rank=slice_rank,
            ambient_dim=ambient,
            state_id=state_id,
            payload=payload,
            evidence_level=evidence,
        )

        active = _active_component_keys(state)
        for key in sorted(active):
            fam = family_by_instance.get(key)
            if not fam:
                continue
            generators = list(fam.get("generators") or [])
            diagrams = list(fam.get("diagram_involutions") or [])
            if involution_limit is not None:
                generators = generators[:involution_limit]
                diagrams = diagrams[:involution_limit]

            for gen in generators:
                op = gen.get("operator") or f"local_reflection:{key[0]}:s{gen.get('generator_index')}"
                store.insert_morphism(
                    terminal_id=terminal_id,
                    source_id=state_id,
                    target_id=state_id,
                    morphism_kind="local_reflection",
                    operator_ref=op,
                    evidence_level=_involution_evidence(str(gen.get("status") or "")),
                    payload={
                        "component_instance_index": key[1],
                        "source_id": key[0],
                        "generator_index": gen.get("generator_index"),
                        "action_count": gen.get("action_count"),
                    },
                )
                inv_count += 1

            for diag in diagrams:
                op = diag.get("operator") or "diagram_involution"
                store.insert_morphism(
                    terminal_id=terminal_id,
                    source_id=state_id,
                    target_id=state_id,
                    morphism_kind="diagram_involution",
                    operator_ref=op,
                    evidence_level=_involution_evidence(str(diag.get("status") or "")),
                    payload={
                        "component_instance_index": key[1],
                        "order": diag.get("order"),
                    },
                )
                inv_count += 1

    for edge in action_edges:
        if edge.get("action_type") != "add_component":
            continue
        store.insert_morphism(
            terminal_id=terminal_id,
            source_id=edge["target_state_id"],
            target_id=edge["source_state_id"],
            morphism_kind="remove_component",
            operator_ref=edge.get("operator") or "peel_component",
            evidence_level="exact",
            payload={
                "forward_edge_id": edge.get("edge_id"),
                "residue_delta": edge.get("residue_delta"),
                "embedding_id": edge.get("embedding_id"),
            },
        )
        peel_count += 1

    store.flush()
    wall = time.perf_counter() - t0
    stats = TerminalStats(
        terminal_id=terminal_id,
        state_count=len(route),
        peel_morphism_count=peel_count,
        involution_morphism_count=inv_count,
        max_rank=max(int(s.get("rank") or 0) for s in route) if route else 0,
        slice_sha256=store.slice_sha256(terminal_id),
        wall_seconds=wall,
    )
    store.checkpoint_done(stats)
    return stats


def materialize_terminals(
    store: WorkStore,
    terminal_ids: list[str],
    *,
    involution_limit: int | None = None,
    resume: bool = False,
) -> list[TerminalStats]:
    results: list[TerminalStats] = []
    with SeedStore.packaged().ledger() as ledger:
        for terminal_id in terminal_ids:
            if resume and store.is_terminal_done(terminal_id):
                counts = store.terminal_stats(terminal_id)
                results.append(
                    TerminalStats(
                        terminal_id=terminal_id,
                        state_count=counts["state_count"],
                        peel_morphism_count=counts["peel_morphism_count"],
                        involution_morphism_count=counts["involution_morphism_count"],
                        max_rank=counts["max_rank"],
                        slice_sha256=store.slice_sha256(terminal_id),
                        wall_seconds=0.0,
                    )
                )
                continue
            results.append(
                materialize_terminal(
                    store,
                    ledger,
                    terminal_id,
                    involution_limit=involution_limit,
                )
            )
    return results
