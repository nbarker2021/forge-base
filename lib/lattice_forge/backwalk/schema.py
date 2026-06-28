from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from ..ledger.build import NIEMEIER_FORMS
from ..ledger.exact import stable_hash

PILOT_TERMINAL_IDS: tuple[str, ...] = (
    "Niemeier:Leech",
    "Niemeier:D4^6",
    "Niemeier:A2^12",
    "Niemeier:A1^24",
)


def all_niemeier_terminal_ids() -> list[str]:
    return [row[0] for row in NIEMEIER_FORMS]


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS backwalk_run (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    phase TEXT NOT NULL,
    config_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS category_object (
    object_id TEXT PRIMARY KEY,
    terminal_id TEXT NOT NULL,
    slice_rank INTEGER NOT NULL,
    ambient_dim INTEGER NOT NULL DEFAULT 24,
    state_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    evidence_level TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_category_object_terminal ON category_object(terminal_id);

CREATE TABLE IF NOT EXISTS category_morphism (
    morphism_id TEXT PRIMARY KEY,
    terminal_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    morphism_kind TEXT NOT NULL,
    operator_ref TEXT NOT NULL,
    evidence_level TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_category_morphism_terminal ON category_morphism(terminal_id);
CREATE INDEX IF NOT EXISTS idx_category_morphism_kind ON category_morphism(morphism_kind);

CREATE TABLE IF NOT EXISTS exceptional_node (
    node_id TEXT PRIMARY KEY,
    rank INTEGER NOT NULL,
    parent_id TEXT,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exceptional_morphism (
    morphism_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    morphism_kind TEXT NOT NULL,
    operator_ref TEXT NOT NULL,
    evidence_level TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_checkpoint (
    terminal_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    state_count INTEGER NOT NULL,
    peel_morphism_count INTEGER NOT NULL,
    involution_morphism_count INTEGER NOT NULL,
    max_rank INTEGER NOT NULL,
    slice_sha256 TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS exceptional_weyl_bond (
    bond_id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    wave_id TEXT NOT NULL,
    lane_index INTEGER NOT NULL,
    pole TEXT NOT NULL,
    source_group TEXT NOT NULL,
    target_group TEXT NOT NULL,
    chart_src INTEGER NOT NULL,
    chart_tgt INTEGER NOT NULL,
    middle_chart INTEGER NOT NULL,
    depth_from_middle INTEGER NOT NULL,
    bond_kind TEXT NOT NULL,
    evidence_level TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_weyl_bond_batch ON exceptional_weyl_bond(batch_id);
CREATE INDEX IF NOT EXISTS idx_weyl_bond_wave ON exceptional_weyl_bond(wave_id);
CREATE INDEX IF NOT EXISTS idx_weyl_bond_groups ON exceptional_weyl_bond(source_group, target_group);

CREATE TABLE IF NOT EXISTS weyl_bond_batch_checkpoint (
    batch_id TEXT PRIMARY KEY,
    wave_id TEXT NOT NULL,
    status TEXT NOT NULL,
    rows_written INTEGER NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS weyl_bond_result_tree (
    tree_id TEXT PRIMARY KEY,
    quadrant INTEGER NOT NULL,
    parent_tree_id TEXT,
    sort_key INTEGER NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_weyl_tree_parent ON weyl_bond_result_tree(parent_tree_id);

CREATE TABLE IF NOT EXISTS lattice_form_registry (
    lattice_form_id TEXT PRIMARY KEY,
    terminal_24d_id TEXT NOT NULL,
    access_kind TEXT NOT NULL,
    root_system_label TEXT,
    payload_json TEXT NOT NULL,
    evidence_level TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lattice_form_terminal ON lattice_form_registry(terminal_24d_id);

CREATE TABLE IF NOT EXISTS proof_capture_queue (
    capture_id TEXT PRIMARY KEY,
    source_kind TEXT NOT NULL,
    need_id TEXT,
    honesty_current TEXT,
    honesty_target TEXT,
    harness_id TEXT,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS e8_weyl_group_catalog (
    group_id TEXT PRIMARY KEY,
    rank INTEGER NOT NULL,
    weyl_order INTEGER NOT NULL,
    bijection_kind TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS podal_side_bond_assignment (
    assignment_id TEXT PRIMARY KEY,
    lattice_form_id TEXT NOT NULL,
    bond_id TEXT NOT NULL,
    quadrant INTEGER NOT NULL,
    weyl_element_index INTEGER NOT NULL,
    evidence_level TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pod_assign_lattice ON podal_side_bond_assignment(lattice_form_id);
CREATE INDEX IF NOT EXISTS idx_pod_assign_weyl ON podal_side_bond_assignment(weyl_element_index);

CREATE TABLE IF NOT EXISTS lattice_space_batch_checkpoint (
    batch_id TEXT PRIMARY KEY,
    phase TEXT NOT NULL,
    status TEXT NOT NULL,
    rows_written INTEGER NOT NULL,
    completed_at TEXT
);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


@dataclass
class TerminalStats:
    terminal_id: str
    state_count: int
    peel_morphism_count: int
    involution_morphism_count: int
    max_rank: int
    slice_sha256: str
    wall_seconds: float


class WorkStore:
    """Writable SQLite store for backward category enumeration."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA_SQL)
        self._migrate_weyl_bond_schema()
        self._migrate_lattice_space_schema()
        self._conn.commit()
        self._pending_morphisms = 0

    def _migrate_weyl_bond_schema(self) -> None:
        cols = {row[1] for row in self._conn.execute("PRAGMA table_info(exceptional_weyl_bond)")}
        if cols and "quadrant" not in cols:
            self._conn.execute(
                "ALTER TABLE exceptional_weyl_bond ADD COLUMN quadrant INTEGER NOT NULL DEFAULT -1"
            )
        if cols:
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_weyl_bond_quadrant ON exceptional_weyl_bond(quadrant)"
            )

    def close(self) -> None:
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None  # type: ignore[assignment]

    def __enter__(self) -> WorkStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def start_run(self, run_id: str, phase: str, config: dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO backwalk_run(run_id, started_at, phase, config_json) VALUES (?,?,?,?)",
            [run_id, _utc_now(), phase, _json(config)],
        )
        self._conn.commit()

    def checkpoint_done(self, stats: TerminalStats) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO run_checkpoint
            (terminal_id, status, state_count, peel_morphism_count,
             involution_morphism_count, max_rank, slice_sha256, completed_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            [
                stats.terminal_id,
                "done",
                stats.state_count,
                stats.peel_morphism_count,
                stats.involution_morphism_count,
                stats.max_rank,
                stats.slice_sha256,
                _utc_now(),
            ],
        )
        self._conn.commit()

    def checkpoint_status(self, terminal_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT status FROM run_checkpoint WHERE terminal_id=?",
            [terminal_id],
        ).fetchone()
        return str(row["status"]) if row else None

    def is_terminal_done(self, terminal_id: str) -> bool:
        return self.checkpoint_status(terminal_id) == "done"

    def insert_object(
        self,
        *,
        terminal_id: str,
        slice_rank: int,
        ambient_dim: int,
        state_id: str,
        payload: dict[str, Any],
        evidence_level: str,
    ) -> str:
        object_id = f"bobj:{stable_hash(terminal_id, state_id, 'category_object')[:32]}"
        self._conn.execute(
            """
            INSERT OR REPLACE INTO category_object
            (object_id, terminal_id, slice_rank, ambient_dim, state_id, payload_json, evidence_level)
            VALUES (?,?,?,?,?,?,?)
            """,
            [object_id, terminal_id, slice_rank, ambient_dim, state_id, _json(payload), evidence_level],
        )
        return object_id

    def insert_morphism(
        self,
        *,
        terminal_id: str,
        source_id: str,
        target_id: str,
        morphism_kind: str,
        operator_ref: str,
        evidence_level: str,
        payload: dict[str, Any],
    ) -> str:
        morphism_id = f"bmor:{stable_hash(terminal_id, source_id, target_id, morphism_kind, operator_ref)[:32]}"
        self._conn.execute(
            """
            INSERT OR REPLACE INTO category_morphism
            (morphism_id, terminal_id, source_id, target_id, morphism_kind, operator_ref, evidence_level, payload_json)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            [
                morphism_id,
                terminal_id,
                source_id,
                target_id,
                morphism_kind,
                operator_ref,
                evidence_level,
                _json(payload),
            ],
        )
        self._pending_morphisms += 1
        if self._pending_morphisms >= 500:
            self._conn.commit()
            self._pending_morphisms = 0
        return morphism_id

    def flush(self) -> None:
        self._conn.commit()
        self._pending_morphisms = 0

    def insert_exceptional_node(
        self,
        node_id: str,
        rank: int,
        parent_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO exceptional_node(node_id, rank, parent_id, payload_json)
            VALUES (?,?,?,?)
            """,
            [node_id, rank, parent_id, _json(payload)],
        )

    def insert_exceptional_morphism(
        self,
        *,
        source_id: str,
        target_id: str,
        morphism_kind: str,
        operator_ref: str,
        evidence_level: str,
        payload: dict[str, Any],
    ) -> str:
        morphism_id = f"exmor:{stable_hash(source_id, target_id, morphism_kind, operator_ref)[:32]}"
        self._conn.execute(
            """
            INSERT OR REPLACE INTO exceptional_morphism
            (morphism_id, source_id, target_id, morphism_kind, operator_ref, evidence_level, payload_json)
            VALUES (?,?,?,?,?,?,?)
            """,
            [morphism_id, source_id, target_id, morphism_kind, operator_ref, evidence_level, _json(payload)],
        )
        return morphism_id

    def terminal_stats(self, terminal_id: str) -> dict[str, int]:
        state_count = self._conn.execute(
            "SELECT COUNT(*) FROM category_object WHERE terminal_id=?",
            [terminal_id],
        ).fetchone()[0]
        peel = self._conn.execute(
            "SELECT COUNT(*) FROM category_morphism WHERE terminal_id=? AND morphism_kind='remove_component'",
            [terminal_id],
        ).fetchone()[0]
        inv = self._conn.execute(
            "SELECT COUNT(*) FROM category_morphism WHERE terminal_id=? AND morphism_kind IN ('local_reflection','diagram_involution')",
            [terminal_id],
        ).fetchone()[0]
        max_rank = self._conn.execute(
            "SELECT COALESCE(MAX(slice_rank),0) FROM category_object WHERE terminal_id=?",
            [terminal_id],
        ).fetchone()[0]
        return {
            "state_count": int(state_count),
            "peel_morphism_count": int(peel),
            "involution_morphism_count": int(inv),
            "max_rank": int(max_rank),
        }

    def slice_sha256(self, terminal_id: str) -> str:
        objects = self._conn.execute(
            "SELECT object_id FROM category_object WHERE terminal_id=? ORDER BY object_id",
            [terminal_id],
        ).fetchall()
        morphisms = self._conn.execute(
            "SELECT morphism_id FROM category_morphism WHERE terminal_id=? ORDER BY morphism_id",
            [terminal_id],
        ).fetchall()
        return stable_hash(
            [r["object_id"] for r in objects],
            [r["morphism_id"] for r in morphisms],
        )

    def query_checkpoints(self) -> list[dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM run_checkpoint ORDER BY terminal_id").fetchall()
        return [dict(r) for r in rows]

    def count_exceptional_morphisms(self, morphism_kind: str | None = None) -> int:
        if morphism_kind:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM exceptional_morphism WHERE morphism_kind=?",
                [morphism_kind],
            ).fetchone()
        else:
            row = self._conn.execute("SELECT COUNT(*) FROM exceptional_morphism").fetchone()
        return int(row[0])

    def has_exceptional_path(self, path: list[str]) -> bool:
        """True if consecutive exceptional nodes exist for each step in path labels."""
        for i in range(len(path) - 1):
            src, tgt = path[i], path[i + 1]
            row = self._conn.execute(
                """
                SELECT 1 FROM exceptional_morphism
                WHERE source_id=? AND target_id=?
                """,
                [src, tgt],
            ).fetchone()
            if not row:
                return False
        return len(path) >= 2

    def insert_weyl_bond(
        self,
        *,
        bond_id: str,
        batch_id: str,
        wave_id: str,
        quadrant: int,
        lane_index: int,
        pole: str,
        source_group: str,
        target_group: str,
        chart_src: int,
        chart_tgt: int,
        middle_chart: int,
        depth_from_middle: int,
        bond_kind: str,
        evidence_level: str,
        payload: dict[str, Any],
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO exceptional_weyl_bond
            (bond_id, batch_id, wave_id, quadrant, lane_index, pole, source_group, target_group,
             chart_src, chart_tgt, middle_chart, depth_from_middle, bond_kind, evidence_level, payload_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            [
                bond_id,
                batch_id,
                wave_id,
                quadrant,
                lane_index,
                pole,
                source_group,
                target_group,
                chart_src,
                chart_tgt,
                middle_chart,
                depth_from_middle,
                bond_kind,
                evidence_level,
                _json(payload),
            ],
        )
        self._pending_morphisms += 1
        if self._pending_morphisms >= 500:
            self._conn.commit()
            self._pending_morphisms = 0

    def weyl_batch_done(self, batch_id: str, wave_id: str, rows_written: int) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO weyl_bond_batch_checkpoint
            (batch_id, wave_id, status, rows_written, completed_at)
            VALUES (?,?,?,?,?)
            """,
            [batch_id, wave_id, "done", rows_written, _utc_now()],
        )
        self._conn.commit()

    def is_weyl_batch_done(self, batch_id: str) -> bool:
        row = self._conn.execute(
            "SELECT status FROM weyl_bond_batch_checkpoint WHERE batch_id=?",
            [batch_id],
        ).fetchone()
        return bool(row and row["status"] == "done")

    def count_weyl_bonds(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM exceptional_weyl_bond").fetchone()
        return int(row[0])

    def count_weyl_batches_done(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM weyl_bond_batch_checkpoint WHERE status='done'"
        ).fetchone()
        return int(row[0])

    def _migrate_lattice_space_schema(self) -> None:
        self._conn.execute(
            """
            INSERT OR IGNORE INTO e8_weyl_group_catalog
            (group_id, rank, weyl_order, bijection_kind, payload_json)
            VALUES (?,?,?,?,?)
            """,
            [
                "E8",
                8,
                696729600,
                "chart_quadrant_pod_shard_surjection",
                _json({
                    "interpretation": (
                        "Full |W(E8)| indexed by surjective map from "
                        "(lattice_form, quadrant, chart bond, mirror); "
                        "materialized witnesses are quadrant-sharded, not 696M literal rows."
                    ),
                    "reference_order": 696729600,
                }),
            ],
        )

    def insert_lattice_form(
        self,
        lattice_form_id: str,
        terminal_24d_id: str,
        access_kind: str,
        root_system_label: str | None,
        payload: dict[str, Any],
        evidence_level: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO lattice_form_registry
            (lattice_form_id, terminal_24d_id, access_kind, root_system_label, payload_json, evidence_level)
            VALUES (?,?,?,?,?,?)
            """,
            [
                lattice_form_id,
                terminal_24d_id,
                access_kind,
                root_system_label,
                _json(payload),
                evidence_level,
            ],
        )

    def insert_proof_capture(
        self,
        capture_id: str,
        source_kind: str,
        need_id: str | None,
        honesty_current: str,
        honesty_target: str,
        harness_id: str | None,
        status: str,
        payload: dict[str, Any],
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO proof_capture_queue
            (capture_id, source_kind, need_id, honesty_current, honesty_target, harness_id, status, payload_json)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            [
                capture_id,
                source_kind,
                need_id,
                honesty_current,
                honesty_target,
                harness_id,
                status,
                _json(payload),
            ],
        )

    def insert_pod_assignment(
        self,
        *,
        assignment_id: str,
        lattice_form_id: str,
        bond_id: str,
        quadrant: int,
        weyl_element_index: int,
        evidence_level: str,
        payload: dict[str, Any],
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO podal_side_bond_assignment
            (assignment_id, lattice_form_id, bond_id, quadrant, weyl_element_index, evidence_level, payload_json)
            VALUES (?,?,?,?,?,?,?)
            """,
            [
                assignment_id,
                lattice_form_id,
                bond_id,
                quadrant,
                weyl_element_index,
                evidence_level,
                _json(payload),
            ],
        )
        self._pending_morphisms += 1
        if self._pending_morphisms >= 500:
            self._conn.commit()
            self._pending_morphisms = 0

    def lattice_space_batch_done(self, batch_id: str, phase: str, rows_written: int) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO lattice_space_batch_checkpoint
            (batch_id, phase, status, rows_written, completed_at)
            VALUES (?,?,?,?,?)
            """,
            [batch_id, phase, "done", rows_written, _utc_now()],
        )
        self._conn.commit()

    def is_lattice_space_batch_done(self, batch_id: str) -> bool:
        row = self._conn.execute(
            "SELECT status FROM lattice_space_batch_checkpoint WHERE batch_id=?",
            [batch_id],
        ).fetchone()
        return bool(row and row["status"] == "done")

    def count_lattice_forms(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM lattice_form_registry").fetchone()[0])

    def count_pod_assignments(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM podal_side_bond_assignment").fetchone()[0])

    def count_proof_captures(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM proof_capture_queue").fetchone()[0])

    def iter_weyl_bonds(self, quadrant: int | None = None):
        sql = "SELECT bond_id, quadrant, chart_src, chart_tgt, batch_id FROM exceptional_weyl_bond"
        params: list[Any] = []
        if quadrant is not None:
            sql += " WHERE quadrant=?"
            params.append(quadrant)
        sql += " ORDER BY bond_id"
        return self._conn.execute(sql, params).fetchall()

    def insert_result_tree_node(
        self,
        *,
        tree_id: str,
        quadrant: int,
        parent_tree_id: str | None,
        sort_key: int,
        payload: dict[str, Any],
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO weyl_bond_result_tree
            (tree_id, quadrant, parent_tree_id, sort_key, payload_json)
            VALUES (?,?,?,?,?)
            """,
            [tree_id, quadrant, parent_tree_id, sort_key, _json(payload)],
        )
