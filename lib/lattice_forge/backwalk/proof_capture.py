from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import WorkStore


def materialize_proof_capture_queue(
    store: WorkStore,
    *,
    library_needs_path: Path | None = None,
    max_rows: int = 200,
) -> dict[str, Any]:
    """Ingest prior capture requests (library needs) into proof_capture_queue."""
    if library_needs_path is None:
        library_needs_path = (
            Path(__file__).resolve().parents[3] / "claims" / "library_needs.jsonl"
        )
    written = 0
    if not library_needs_path.is_file():
        return {"written": 0, "path": str(library_needs_path), "status": "missing"}

    with library_needs_path.open(encoding="utf-8") as f:
        for line in f:
            if written >= max_rows:
                break
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            need_id = row.get("need_id") or row.get("claim_id") or f"need_{written}"
            store.insert_proof_capture(
                capture_id=f"capture:{need_id}",
                source_kind="library_needs",
                need_id=need_id,
                honesty_current=str(row.get("honesty_current") or ""),
                honesty_target=str(row.get("honesty_target") or ""),
                harness_id=row.get("harness_id"),
                status="queued",
                payload=row,
            )
            written += 1

    # Ring-2 / backwalk proof obligations (structural, not PROVEN unless harness says so)
    for oid, stmt in (
        ("backwalk.niemeier_peel", "Backward peel matches forward terminal_tree depth"),
        ("backwalk.weyl_quadrant_shard", "Quadrant shard covers all 8 chart states via D4 axes"),
        ("backwalk.e8_pod_bijection", "Pod index surjects into |W(E8)| representative class"),
        ("backwalk.lattice_access", "Every 24D terminal exposes terminal/product/byproduct forms"),
    ):
        store.insert_proof_capture(
            capture_id=f"capture:{oid}",
            source_kind="lattice_space_obligation",
            need_id=oid,
            honesty_current="BOUNDED_EXEC",
            honesty_target="PROVEN",
            harness_id=None,
            status="open",
            payload={"statement": stmt},
        )
        written += 1

    store.flush()
    return {"written": written, "path": str(library_needs_path)}
