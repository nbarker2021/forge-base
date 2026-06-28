"""
Optional SQLite-backed store. The kernel does not depend on this
module; it is provided for hosts that prefer SQL queries over the
JSONL default. Even when used, the JSONL ledger remains the
authoritative record.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from ..ledger.receipt import Receipt


_SCHEMA = """
CREATE TABLE IF NOT EXISTS receipts (
  receipt_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  output_hash TEXT NOT NULL,
  status TEXT NOT NULL,
  evidence_class TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  payload TEXT NOT NULL,
  receipt_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_receipts_event_type ON receipts(event_type);
"""


class SqliteReceiptStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def append(self, receipt: Receipt) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO receipts VALUES (?,?,?,?,?,?,?,?,?)",
            (
                receipt.receipt_id,
                receipt.event_type,
                receipt.input_hash,
                receipt.output_hash,
                receipt.status.value,
                receipt.evidence_class.value,
                receipt.timestamp,
                json.dumps(receipt.payload, sort_keys=True, separators=(",", ":")),
                receipt.receipt_hash,
            ),
        )
        self._conn.commit()

    def get(self, receipt_id: str) -> Optional[Receipt]:
        cur = self._conn.execute(
            "SELECT * FROM receipts WHERE receipt_id = ?", (receipt_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return Receipt(
            receipt_id=row[0],
            event_type=row[1],
            input_hash=row[2],
            output_hash=row[3],
            status=row[4],
            evidence_class=row[5],
            timestamp=row[6],
            payload=json.loads(row[7]),
        )

    def by_event_type(self, event_type: str) -> List[Receipt]:
        cur = self._conn.execute(
            "SELECT * FROM receipts WHERE event_type = ?", (event_type,)
        )
        out: List[Receipt] = []
        for row in cur.fetchall():
            out.append(
                Receipt(
                    receipt_id=row[0],
                    event_type=row[1],
                    input_hash=row[2],
                    output_hash=row[3],
                    status=row[4],
                    evidence_class=row[5],
                    timestamp=row[6],
                    payload=json.loads(row[7]),
                )
            )
        return out

    def size(self) -> int:
        cur = self._conn.execute("SELECT COUNT(*) FROM receipts")
        return int(cur.fetchone()[0])

    def close(self) -> None:
        self._conn.close()
