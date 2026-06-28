"""CrystalForge.schema — SQLite persistence for the TMN crystal/brain
memory system.

This is a SQLite port of the real, working TMN services
(tmn_source/CMPLX-TMN-main-main/src/crystal/crystal.py and
src/brain/brain.py), not a new design -- the table layout matches
forge_dbs/tmn_unified.db exactly (the schema TMN1-ARCHITECTURE.md
already documents as part of databases/tmn1.db's 21 tables), and the
crystal/brain logic in this package is ported from those two real
FastAPI services, not invented.

Backend note (the operator's own framing): start as SQLite now,
Postgres later. The DDL below is deliberately written in a dialect
that is valid in both engines wherever practical (TEXT for JSON blobs
instead of JSONB, INTEGER PRIMARY KEY AUTOINCREMENT instead of SERIAL)
so a future PostgresBackend implementing the same connection-returning
interface as get_connection() below is a drop-in swap, not a rewrite.
The auto-generated TMN_*.py stubs in papers_tool_solvers/generated_tools
are NOT the source for this schema -- they are template placeholders
that were never substituted; the real source is the FastAPI services'
own CREATE TABLE statements.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

# Relative to this package, matching the same fix applied to
# crystal_library/schema.py earlier this session (a hardcoded absolute
# path there made its committed .db dead weight on every rebuild).
DB_PATH_DEFAULT = Path(__file__).resolve().parent / "crystal_vault.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS crystals (
    crystal_id      TEXT PRIMARY KEY,
    name            TEXT NOT NULL DEFAULT '',
    crystal_type    TEXT NOT NULL DEFAULT 'knowledge',
    state           TEXT NOT NULL DEFAULT 'growing',
    e8_root         TEXT NOT NULL DEFAULT '[]',
    meaning_levels  TEXT NOT NULL DEFAULT '[]',
    level_config    TEXT NOT NULL DEFAULT '[]',
    owner           TEXT NOT NULL DEFAULT '',
    snap_address    TEXT NOT NULL DEFAULT '',
    receipt_chain   TEXT NOT NULL DEFAULT '',
    node_count      INTEGER NOT NULL DEFAULT 0,
    total_mass      REAL NOT NULL DEFAULT 0,
    created_at      REAL NOT NULL DEFAULT 0,
    committed_at    REAL,
    activated_at    REAL
);

CREATE TABLE IF NOT EXISTS e8_nodes (
    node_id         TEXT PRIMARY KEY,
    crystal_id      TEXT NOT NULL REFERENCES crystals(crystal_id),
    content         TEXT NOT NULL DEFAULT '',
    content_type    TEXT NOT NULL DEFAULT 'atom',
    e8_coords       TEXT NOT NULL DEFAULT '[]',
    snap_labels     TEXT NOT NULL DEFAULT '[]',
    mdhg_address    TEXT NOT NULL DEFAULT '{}',
    importance      REAL NOT NULL DEFAULT 0.5,
    meaning_level   INTEGER NOT NULL DEFAULT 0,
    mass            REAL NOT NULL DEFAULT 0,
    created_at      REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_e8n_crystal ON e8_nodes(crystal_id);

CREATE TABLE IF NOT EXISTS agent_brains (
    agent_id            TEXT PRIMARY KEY,
    dims                INTEGER NOT NULL DEFAULT 24,
    epoch               INTEGER NOT NULL DEFAULT 0,
    tier                TEXT NOT NULL DEFAULT 'nascent',
    mutual_information  REAL NOT NULL DEFAULT 0,
    energy              REAL NOT NULL DEFAULT 0,
    frozen              INTEGER NOT NULL DEFAULT 0,
    specialist_profile  TEXT NOT NULL DEFAULT '{}',
    mi_history          TEXT NOT NULL DEFAULT '[]',
    step_count          INTEGER NOT NULL DEFAULT 0,
    registered_at       REAL NOT NULL DEFAULT 0,
    forked_from         TEXT,
    forked_at_epoch     INTEGER
);

CREATE TABLE IF NOT EXISTS brain_contributions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id        TEXT NOT NULL,
    domain          TEXT NOT NULL DEFAULT '',
    snap_labels     TEXT NOT NULL DEFAULT '[]',
    mi_score        REAL NOT NULL DEFAULT 0,
    epoch           INTEGER NOT NULL DEFAULT 0,
    tier            TEXT NOT NULL DEFAULT 'nascent',
    dims            INTEGER NOT NULL DEFAULT 24,
    contributed_at  REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_contrib_agent ON brain_contributions(agent_id);

-- L3a weight-learner snapshots (the TMNBrain image), SQLite port of the
-- original psycopg2 tmn_brains table in personal_node/brain.py. The full
-- brain (8 E8-root experts, gating, 3 triads, mi_history) is stored as a
-- single JSON image blob, matching the original to_image() contract.
CREATE TABLE IF NOT EXISTS tmn_brains (
    brain_id    TEXT PRIMARY KEY,
    agent_id    TEXT NOT NULL DEFAULT '',
    dims        INTEGER NOT NULL DEFAULT 24,
    epoch       INTEGER NOT NULL DEFAULT 0,
    frozen      INTEGER NOT NULL DEFAULT 0,
    image       TEXT NOT NULL DEFAULT '{}',
    created_at  REAL NOT NULL DEFAULT 0,
    updated_at  REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_tmn_agent ON tmn_brains(agent_id);

-- SplatForge Field Runtime: persistent field receipts and crystal lineage.
-- The SpatialField itself is NOT stored (it is regenerable from the crystal +
-- a render profile, per the field-runtime contract); only its receipt and the
-- parent->child crystal lineage of semantic edits are persisted.
CREATE TABLE IF NOT EXISTS field_receipts (
    receipt_hash        TEXT PRIMARY KEY,
    field_id            TEXT NOT NULL DEFAULT '',
    crystal_id          TEXT NOT NULL DEFAULT '',
    crystal_revision    TEXT NOT NULL DEFAULT '',
    grammar             TEXT NOT NULL DEFAULT '',
    scene_graph_hash    TEXT NOT NULL DEFAULT '',
    splat_buffer_hash   TEXT NOT NULL DEFAULT '',
    application_frame_hash TEXT NOT NULL DEFAULT '',
    render_backend      TEXT NOT NULL DEFAULT 'cpu_reference',
    visibility_policy   TEXT NOT NULL DEFAULT 'default',
    prev_hash           TEXT NOT NULL DEFAULT '',
    payload             TEXT NOT NULL DEFAULT '{}',
    created_at          REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_field_receipts_crystal ON field_receipts(crystal_id);

CREATE TABLE IF NOT EXISTS field_lineage (
    edge_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_crystal  TEXT NOT NULL,
    child_crystal   TEXT NOT NULL,
    relation        TEXT NOT NULL DEFAULT 'semantic_edit',
    op              TEXT NOT NULL DEFAULT '',
    receipt_hash    TEXT NOT NULL DEFAULT '',
    created_at      REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_field_lineage_parent ON field_lineage(parent_crystal);
CREATE INDEX IF NOT EXISTS idx_field_lineage_child ON field_lineage(child_crystal);
"""


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open (creating if needed) the crystal vault database."""
    path = Path(db_path) if db_path else DB_PATH_DEFAULT
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
