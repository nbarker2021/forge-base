from __future__ import annotations

from typing import Any

from ..substrate_map import WEYL_13_TABLE
from .schema import WorkStore


def glue_project_weyl(
    store: WorkStore,
    open_edge: dict[str, Any],
    terminal_id: str,
) -> dict[str, Any]:
    """Apply Weyl involution routing + record as bounded_exec glue morphism."""
    src = int(open_edge.get("chart_state", open_edge.get("source_chart_state", 0)))
    if src < 0 or src > 7:
        raise ValueError(f"chart_state must be in 0..7, got {src}")
    tgt = WEYL_13_TABLE[src]
    payload = {
        "terminal_id": terminal_id,
        "open_edge": open_edge,
        "weyl_partner": tgt,
        "weyl_table": list(WEYL_13_TABLE),
        "interpretation": "rotated Weyl involution partner on 8-state chart substrate",
    }
    morphism_id = store.insert_morphism(
        terminal_id=terminal_id,
        source_id=open_edge.get("source_state_id", f"chart:{src}"),
        target_id=open_edge.get("target_state_id", f"chart:{tgt}"),
        morphism_kind="weyl_glue",
        operator_ref=f"substrate_map:WEYL_13[{src}]",
        evidence_level="bounded_exec",
        payload=payload,
    )
    store.flush()
    return {"morphism_id": morphism_id, "weyl_partner": tgt, "evidence_level": "bounded_exec", **payload}
