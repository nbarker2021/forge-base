from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1.0"

def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()

SCHEMA = r"""
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS journals (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_fragments (
  id TEXT PRIMARY KEY,
  journal_id TEXT NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS receipts (
  id TEXT PRIMARY KEY,
  journal_id TEXT NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
  fragment_id TEXT NOT NULL REFERENCES source_fragments(id) ON DELETE CASCADE,
  receipt_type TEXT NOT NULL,
  proof_count INTEGER NOT NULL DEFAULT 0,
  obligation_count INTEGER NOT NULL DEFAULT 0,
  carry_density REAL NOT NULL DEFAULT 0,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS graph_nodes (
  id TEXT PRIMARY KEY,
  journal_id TEXT NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
  receipt_id TEXT NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
  label TEXT NOT NULL,
  kind TEXT NOT NULL,
  color_state TEXT NOT NULL,
  paper_state TEXT NOT NULL,
  proof_status TEXT NOT NULL,
  x REAL DEFAULT 0,
  y REAL DEFAULT 0,
  payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS graph_edges (
  id TEXT PRIMARY KEY,
  journal_id TEXT NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
  receipt_id TEXT NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
  source TEXT NOT NULL,
  target TEXT NOT NULL,
  kind TEXT NOT NULL,
  color_state TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS obligations (
  id TEXT PRIMARY KEY,
  journal_id TEXT NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
  node_id TEXT NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
  receipt_id TEXT NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'open',
  title TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fragments_journal ON source_fragments(journal_id);
CREATE INDEX IF NOT EXISTS idx_receipts_journal ON receipts(journal_id);
CREATE INDEX IF NOT EXISTS idx_nodes_journal ON graph_nodes(journal_id);
CREATE INDEX IF NOT EXISTS idx_edges_journal ON graph_edges(journal_id);
CREATE INDEX IF NOT EXISTS idx_obligations_journal ON obligations(journal_id);
"""

def connect(path: str | Path) -> sqlite3.Connection:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("schema_version", SCHEMA_VERSION))
    conn.commit()
    return conn

def ensure_default_journal(conn: sqlite3.Connection) -> str:
    jid = "default"
    now = utcnow()
    conn.execute(
        "INSERT OR IGNORE INTO journals(id,title,description,created_at,updated_at) VALUES(?,?,?,?,?)",
        (jid, "Default Research Manifold", "Local-first ReForge/ResearchCraft workspace", now, now),
    )
    conn.commit()
    return jid

def rowdict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}

def rows(conn: sqlite3.Connection, sql: str, args: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [rowdict(r) for r in conn.execute(sql, args).fetchall()]

def one(conn: sqlite3.Connection, sql: str, args: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    r = conn.execute(sql, args).fetchone()
    return rowdict(r) if r else None

def jdump(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, default=str)

def jload(text: str) -> Any:
    return json.loads(text)
