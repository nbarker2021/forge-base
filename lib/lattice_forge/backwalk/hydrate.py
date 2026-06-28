from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .schema import WorkStore


def hydrate(
    work_db: Path | str,
    terminal_id: str,
    *,
    include_exceptional: bool = True,
) -> dict[str, Any]:
    """Load backward category slice for a terminal from the work DB (phase-2 API stub)."""
    store = WorkStore(Path(work_db))
    try:
        conn = store._conn
        objects = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM category_object WHERE terminal_id=? ORDER BY slice_rank",
                [terminal_id],
            ).fetchall()
        ]
        morphisms = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM category_morphism WHERE terminal_id=? ORDER BY morphism_kind, morphism_id",
                [terminal_id],
            ).fetchall()
        ]
        for row in objects + morphisms:
            if "payload_json" in row:
                row["payload"] = json.loads(row.pop("payload_json"))

        exceptional: dict[str, Any] = {}
        if include_exceptional:
            exceptional["nodes"] = [
                dict(r)
                for r in conn.execute("SELECT * FROM exceptional_node ORDER BY rank").fetchall()
            ]
            exceptional["morphisms"] = [
                dict(r)
                for r in conn.execute("SELECT * FROM exceptional_morphism ORDER BY morphism_id").fetchall()
            ]
            for row in exceptional["nodes"] + exceptional["morphisms"]:
                if "payload_json" in row:
                    row["payload"] = json.loads(row.pop("payload_json"))

        checkpoint = conn.execute(
            "SELECT * FROM run_checkpoint WHERE terminal_id=?",
            [terminal_id],
        ).fetchone()

        return {
            "terminal_id": terminal_id,
            "objects": objects,
            "morphisms": morphisms,
            "exceptional": exceptional,
            "checkpoint": dict(checkpoint) if checkpoint else None,
        }
    finally:
        store.close()
