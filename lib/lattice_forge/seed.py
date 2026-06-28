from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from typing import Iterator

from .ledger import Ledger

SEED_DB_NAME = "cmplx_morphism_ledger_seed_v0_6.db"


class SeedStore:
    """Read-only access to the bundled lattice/morphism seed database."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    @classmethod
    def packaged(cls) -> "SeedStore":
        seed = resources.files("lattice_forge.ledger").joinpath(f"data/{SEED_DB_NAME}")
        with resources.as_file(seed) as path:
            return cls(Path(path))

    @contextmanager
    def ledger(self) -> Iterator[Ledger]:
        uri = f"file:{self.db_path.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        ledger = Ledger(conn)
        try:
            yield ledger
        finally:
            ledger.close()

    def integrity_check(self) -> str:
        uri = f"file:{self.db_path.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        try:
            return str(conn.execute("PRAGMA integrity_check").fetchone()[0])
        finally:
            conn.close()

    def sha256(self) -> str:
        h = hashlib.sha256()
        with self.db_path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def summary(self) -> dict[str, int]:
        with self.ledger() as ledger:
            return ledger.summary()

    def verify(self) -> dict:
        with self.ledger() as ledger:
            return ledger.verify()
