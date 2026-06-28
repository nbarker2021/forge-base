from __future__ import annotations

import json
from typing import Any

from pathlib import Path

from .schema import WorkStore
from .weyl_bond_dual import QUADRANT_CHART_INDICES, QUADRANT_COUNT, chart_axis


def quadrant_for_chart(chart_idx: int) -> int:
    return chart_axis(chart_idx)


def concatenate_quadrant_trees(
    store: WorkStore,
    *,
    tree_path: str | None = None,
) -> dict[str, Any]:
    """Merge per-quadrant bond forests into one ordered result tree (middle-out read order)."""
    quadrants: list[dict[str, Any]] = []
    total_bonds = 0

    for q in range(QUADRANT_COUNT):
        rows = store._conn.execute(
            """
            SELECT bond_id, batch_id, wave_id, source_group, target_group,
                   chart_src, chart_tgt, bond_kind, evidence_level, payload_json
            FROM exceptional_weyl_bond
            WHERE quadrant=?
            ORDER BY wave_id, batch_id, chart_src
            """,
            [q],
        ).fetchall()
        branches = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            branches.append(
                {
                    "bond_id": row["bond_id"],
                    "batch_id": row["batch_id"],
                    "wave_id": row["wave_id"],
                    "source_group": row["source_group"],
                    "target_group": row["target_group"],
                    "chart_src": row["chart_src"],
                    "chart_tgt": row["chart_tgt"],
                    "bond_kind": row["bond_kind"],
                    "evidence_level": row["evidence_level"],
                    "payload": payload,
                }
            )
        total_bonds += len(branches)
        quad_meta = {
            "quadrant": q,
            "axis_label": q,
            "chart_indices": list(QUADRANT_CHART_INDICES[q]),
            "branch_count": len(branches),
            "branches": branches,
        }
        quadrants.append(quad_meta)
        store.insert_result_tree_node(
            tree_id=f"weyl_quadrant:{q}",
            quadrant=q,
            parent_tree_id="weyl_bond_root",
            sort_key=q,
            payload=quad_meta,
        )

    root = {
        "tree_id": "weyl_bond_root",
        "quadrant_count": QUADRANT_COUNT,
        "total_bonds": total_bonds,
        "concat_order": list(range(QUADRANT_COUNT)),
        "interpretation": (
            "Four independent D4 quadrant searches (2 chart states each) "
            "concatenated in axis order 0..3 for middle-out hydration."
        ),
        "quadrants": quadrants,
    }
    store.insert_result_tree_node(
        tree_id="weyl_bond_root",
        quadrant=-1,
        parent_tree_id=None,
        sort_key=0,
        payload=root,
    )
    store.flush()

    if tree_path:
        out = Path(tree_path)
        if not out.is_absolute():
            out = store.db_path.parent / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(root, indent=2), encoding="utf-8")

    return root
