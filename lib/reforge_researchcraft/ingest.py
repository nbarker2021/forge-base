from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from .db import utcnow, jdump
from reforge_kimi_adapter.adapter import adapt_work_fragment


def _id(prefix: str, text: str) -> str:
    return f"{prefix}_{hashlib.sha256(text.encode('utf-8', errors='ignore')).hexdigest()[:16]}"


def ingest_fragment(conn: sqlite3.Connection, *, journal_id: str, title: str, body: str, window: int = 64, workspace: str | None = None) -> dict[str, Any]:
    """Persist a fragment, run the Kimi adapter, persist graph nodes/edges/obligations."""
    now = utcnow()
    sha = hashlib.sha256(body.encode('utf-8', errors='ignore')).hexdigest()
    frag_id = _id("frag", title + "\n" + body)
    conn.execute(
        "INSERT OR REPLACE INTO source_fragments(id,journal_id,title,body,sha256,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
        (frag_id, journal_id, title, body, sha, now, now),
    )
    receipt = adapt_work_fragment(body, window=window, workspace=workspace)
    rid = _id("rcpt", frag_id + receipt.get("input_sha256", sha) + str(window))
    conn.execute(
        "INSERT OR REPLACE INTO receipts(id,journal_id,fragment_id,receipt_type,proof_count,obligation_count,carry_density,payload_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (
            rid,
            journal_id,
            frag_id,
            receipt.get("receipt_type", "reforge_kimi_adapter"),
            int(receipt.get("proof_continuation_count", 0)),
            int(receipt.get("obligation_count", 0)),
            float(receipt.get("carry_density", 0.0)),
            jdump(receipt),
            now,
        ),
    )
    graph = receipt.get("worldforge_graph", {})
    for n in graph.get("nodes", []):
        nid = str(n.get("id"))
        conn.execute(
            "INSERT OR REPLACE INTO graph_nodes(id,journal_id,receipt_id,label,kind,color_state,paper_state,proof_status,x,y,payload_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                nid,
                journal_id,
                rid,
                str(n.get("label", nid)),
                str(n.get("kind", "node")),
                str(n.get("color_state", "grey")),
                str(n.get("paper_state", "unknown")),
                str(n.get("proof_status", "unknown")),
                float(n.get("x", 0.0)),
                float(n.get("y", 0.0)),
                jdump(n.get("payload", {})),
            ),
        )
        if str(n.get("proof_status")) == "obligation":
            oid = _id("ob", rid + nid)
            payload = n.get("payload", {})
            conn.execute(
                "INSERT OR REPLACE INTO obligations(id,journal_id,node_id,receipt_id,status,title,payload_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (oid, journal_id, nid, rid, "open", f"Resolve {n.get('label', nid)}", jdump(payload), now, now),
            )
    for i, e in enumerate(graph.get("edges", [])):
        eid = _id("edge", rid + str(i) + str(e.get("source")) + str(e.get("target")))
        conn.execute(
            "INSERT OR REPLACE INTO graph_edges(id,journal_id,receipt_id,source,target,kind,color_state,payload_json) VALUES(?,?,?,?,?,?,?,?)",
            (
                eid,
                journal_id,
                rid,
                str(e.get("source")),
                str(e.get("target")),
                str(e.get("kind", "edge")),
                str(e.get("color_state", "grey")),
                jdump(e.get("payload", {})),
            ),
        )
    conn.commit()
    return {"fragment_id": frag_id, "receipt_id": rid, "receipt": receipt}


def export_journal(conn: sqlite3.Connection, journal_id: str) -> dict[str, Any]:
    from .db import rows, one, jload
    journal = one(conn, "SELECT * FROM journals WHERE id=?", (journal_id,))
    fragments = rows(conn, "SELECT id,title,sha256,created_at,updated_at FROM source_fragments WHERE journal_id=? ORDER BY created_at", (journal_id,))
    receipts = rows(conn, "SELECT id,fragment_id,receipt_type,proof_count,obligation_count,carry_density,created_at FROM receipts WHERE journal_id=? ORDER BY created_at", (journal_id,))
    nodes = rows(conn, "SELECT * FROM graph_nodes WHERE journal_id=?", (journal_id,))
    edges = rows(conn, "SELECT * FROM graph_edges WHERE journal_id=?", (journal_id,))
    obligations = rows(conn, "SELECT * FROM obligations WHERE journal_id=?", (journal_id,))
    return {"journal": journal, "fragments": fragments, "receipts": receipts, "nodes": nodes, "edges": edges, "obligations": obligations}
