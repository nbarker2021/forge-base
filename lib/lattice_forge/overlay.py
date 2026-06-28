from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

STATE_DIR_NAME = ".lattice_forge"
OVERLAY_DB_NAME = "overlay.sqlite"

OVERLAY_SCHEMA = """
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS receipts (
  receipt_id TEXT PRIMARY KEY,
  operation TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY,
  event_kind TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  evidence_level TEXT,
  receipt_id TEXT,
  created_at TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  FOREIGN KEY(receipt_id) REFERENCES receipts(receipt_id)
);

CREATE TABLE IF NOT EXISTS query_cache (
  query_id TEXT PRIMARY KEY,
  query_kind TEXT NOT NULL,
  query_json TEXT NOT NULL,
  answer TEXT,
  evidence_level TEXT,
  result_hash TEXT NOT NULL,
  event_id TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(event_id) REFERENCES events(event_id)
);

CREATE TABLE IF NOT EXISTS handoffs (
  handoff_id TEXT PRIMARY KEY,
  need TEXT NOT NULL,
  command_json TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'planned',
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS imports (
  import_id TEXT PRIMARY KEY,
  source_uri TEXT,
  placement TEXT NOT NULL DEFAULT 'raw',
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_kind ON events(event_kind);
CREATE INDEX IF NOT EXISTS idx_receipts_operation ON receipts(operation);
CREATE INDEX IF NOT EXISTS idx_query_cache_kind ON query_cache(query_kind);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(payload: Any, prefix: str) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}:{sha256(data.encode('utf-8')).hexdigest()}"


@dataclass(frozen=True)
class OverlayStore:
    """Writable project-local interaction state."""

    root: Path
    state_dir: Path
    db_path: Path

    @classmethod
    def open(cls, root: str | Path | None = None) -> "OverlayStore":
        project_root = Path(root or Path.cwd()).resolve()
        state_dir = project_root / STATE_DIR_NAME
        state_dir.mkdir(parents=True, exist_ok=True)
        store = cls(project_root, state_dir, state_dir / OVERLAY_DB_NAME)
        store.init()
        return store

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(OVERLAY_SCHEMA)
            conn.execute(
                "INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)",
                ("schema_version", "0.1.0"),
            )
            conn.commit()

    def record_receipt(self, operation: str, payload: dict[str, Any]) -> str:
        created = utc_now()
        payload_hash = stable_hash({"operation": operation, "payload": payload}, "receipt")
        receipt_id = payload_hash
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO receipts
                (receipt_id,operation,payload_json,created_at,payload_hash)
                VALUES (?,?,?,?,?)
                """,
                (receipt_id, operation, json.dumps(payload, sort_keys=True), created, payload_hash),
            )
            conn.commit()
        return receipt_id

    def record_event(
        self,
        event_kind: str,
        payload: dict[str, Any],
        *,
        evidence_level: str | None = None,
        receipt_id: str | None = None,
    ) -> str:
        created = utc_now()
        payload_hash = stable_hash({"event_kind": event_kind, "payload": payload}, "event")
        event_id = payload_hash
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO events
                (event_id,event_kind,payload_json,evidence_level,receipt_id,created_at,payload_hash)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    event_id,
                    event_kind,
                    json.dumps(payload, sort_keys=True, default=str),
                    evidence_level,
                    receipt_id,
                    created,
                    payload_hash,
                ),
            )
            conn.commit()
        return event_id

    def record_query(
        self,
        query_kind: str,
        query: dict[str, Any],
        result: Any,
        *,
        answer: str | None,
        evidence_level: str,
        event_id: str,
    ) -> str:
        result_hash = stable_hash(result, "result")
        query_id = stable_hash(
            {"query_kind": query_kind, "query": query, "result_hash": result_hash},
            "query",
        )
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO query_cache
                (query_id,query_kind,query_json,answer,evidence_level,result_hash,event_id,created_at)
                VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    query_id,
                    query_kind,
                    json.dumps(query, sort_keys=True),
                    answer,
                    evidence_level,
                    result_hash,
                    event_id,
                    utc_now(),
                ),
            )
            conn.commit()
        return query_id

    def latest_events(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def latest_receipts(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM receipts ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def snapshot(self, limit: int = 100) -> dict[str, Any]:
        with self.connect() as conn:
            tables = ["meta", "receipts", "events", "query_cache", "handoffs", "imports"]
            out: dict[str, Any] = {}
            for table in tables:
                rows = conn.execute(
                    f"SELECT * FROM {table} LIMIT ?",
                    (limit,),
                ).fetchall()
                out[table] = [dict(row) for row in rows]
        return {
            "root": str(self.root),
            "state_dir": str(self.state_dir),
            "db_path": str(self.db_path),
            "tables": out,
        }
