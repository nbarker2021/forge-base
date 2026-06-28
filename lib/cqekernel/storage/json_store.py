"""
JSONL-backed key-value store for receipts.

The store writes one JSON line per receipt and keeps an in-memory
index for fast ``by_event_type`` queries.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from ..ledger.receipt import Receipt


class ReceiptStore:
    """JSONL-backed receipt store with an in-memory index.

    The in-memory index is built once on construction and is updated
    on every ``append``. Reads are O(1) for ``get``, O(N) for
    ``by_event_type`` (a scan, not a tree).
    """

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()
        self._index: Dict[str, Receipt] = {}
        self._reload()

    def _reload(self) -> None:
        self._index.clear()
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                r = Receipt.from_dict(json.loads(raw))
                self._index[r.receipt_id] = r

    def append(self, receipt: Receipt) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(receipt.to_dict(), sort_keys=True, separators=(",", ":")) + "\n"
            )
        self._index[receipt.receipt_id] = receipt

    def get(self, receipt_id: str) -> Optional[Receipt]:
        return self._index.get(receipt_id)

    def all(self) -> List[Receipt]:
        return list(self._index.values())

    def by_event_type(self, event_type: str) -> List[Receipt]:
        return [r for r in self._index.values() if r.event_type == event_type]

    def size(self) -> int:
        return len(self._index)
