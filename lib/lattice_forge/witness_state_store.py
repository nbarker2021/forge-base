"""Witnessed-state table — in-memory with optional SQLite persistence."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class WitnessStateStore:
    """O(1) lookup for regime-encode payloads keyed by canonical state keys."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._entries: dict[str, dict[str, Any]] = {}
        self._db_path: Path | None = Path(db_path) if db_path else None
        if self._db_path is not None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_db()
            self._load_from_db()

    def _init_db(self) -> None:
        assert self._db_path is not None
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS witness_state (
                    state_key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _load_from_db(self) -> None:
        assert self._db_path is not None
        if not self._db_path.is_file():
            return
        with sqlite3.connect(self._db_path) as conn:
            for key, payload_json in conn.execute(
                "SELECT state_key, payload_json FROM witness_state"
            ):
                self._entries[key] = json.loads(payload_json)

    def put(self, state_key: str, payload: dict[str, Any]) -> None:
        self._entries[state_key] = dict(payload)
        if self._db_path is not None:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO witness_state (state_key, payload_json)
                    VALUES (?, ?)
                    ON CONFLICT(state_key) DO UPDATE SET payload_json=excluded.payload_json
                    """,
                    (state_key, json.dumps(payload, default=str)),
                )
                conn.commit()

    def get(self, state_key: str) -> dict[str, Any] | None:
        return self._entries.get(state_key)

    def has(self, state_key: str) -> bool:
        return state_key in self._entries

    @property
    def persistent(self) -> bool:
        return self._db_path is not None
