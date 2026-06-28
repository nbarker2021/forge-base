from __future__ import annotations
import json, sqlite3
from pathlib import Path
from typing import Dict, Any
from .fumu import analyze_work

SCHEMA = """
CREATE TABLE IF NOT EXISTS glyph_runs (
  run_id TEXT PRIMARY KEY,
  source_title TEXT,
  analysis_json TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS glyph_fragments (
  fragment_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  fragment_type TEXT,
  color_state TEXT,
  proof_state TEXT,
  language_demand TEXT,
  text TEXT,
  receipt_id TEXT
);
"""

def persist_analysis(db_path: str | Path, run_id: str, source_title: str, analysis: Dict[str, Any]) -> None:
    db_path = Path(db_path); db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        con.executescript(SCHEMA)
        con.execute("INSERT OR REPLACE INTO glyph_runs(run_id, source_title, analysis_json) VALUES(?,?,?)", (run_id, source_title, json.dumps(analysis)))
        for f in analysis.get("fragments", []):
            con.execute("""INSERT OR REPLACE INTO glyph_fragments(fragment_id, run_id, fragment_type, color_state, proof_state, language_demand, text, receipt_id)
            VALUES(?,?,?,?,?,?,?,?)""", (f["fragment_id"], run_id, f["fragment_type"], f["color_state"], f["proof_state"], f["language_demand"], f["text"], f.get("receipt_id")))
        con.commit()
    finally:
        con.close()
