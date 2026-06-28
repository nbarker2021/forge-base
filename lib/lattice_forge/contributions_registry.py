"""
contributions_registry.py — Persistent registry for validated session
contributions to the lattice-forge exact-data backbone.

Design contract
---------------
The umbrella's seed database (`ledger/data/cmplx_morphism_ledger_seed_v0_6.db`)
is the *immutable* root of trust: classical root systems, Niemeier
terminals, admissibility edges, NSL residues. Anything new found during
a session that the lib's proofs depend on must be persisted somewhere
auditable, but the seed DB stays untouched.

The contributions registry is the mutable companion. Each entry records:
    (kind, key, value, provenance, validated_by, validated_at)

where:
    kind         — class of contribution ("lucas_term", "f2_arf",
                   "mckay_thompson_coeff", "weyl_orbit_id", ...)
    key          — JSON-serialized identifying tuple (kind-specific)
    value        — JSON-serialized payload (kind-specific)
    provenance   — free-form text describing how it was derived
    validated_by — name of the validation gate that accepted it (e.g.
                   "f2_majorana_arf", "lucas_recurrence",
                   "round_trip_chart_codec_d4")
    validated_at — UTC ISO 8601 timestamp

Governance
----------
Entries enter the registry only via `Registry.propose(...)` followed by
acceptance from a validator. A registry without a validator is read-only
once frozen. A validator that accepts an entry MUST run a deterministic
check returning a boolean and a rationale; the registry stores both.

This is the T_F2_BRIDGE governance layer: every new fact about the
lattice-forge substrate must pass a F_2-deterministic gate before
becoming durable. The gate's identity is recorded with each entry so
later audits can trace the chain of trust.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import sqlite3
from typing import Any, Callable, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS contributions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    key_json TEXT NOT NULL,
    value_json TEXT NOT NULL,
    provenance TEXT NOT NULL,
    validated_by TEXT NOT NULL,
    validation_rationale TEXT NOT NULL,
    validated_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    UNIQUE(kind, key_json)
);
CREATE INDEX IF NOT EXISTS idx_contributions_kind ON contributions(kind);
CREATE INDEX IF NOT EXISTS idx_contributions_hash ON contributions(content_hash);

CREATE TABLE IF NOT EXISTS proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    key_json TEXT NOT NULL,
    value_json TEXT NOT NULL,
    provenance TEXT NOT NULL,
    proposed_at TEXT NOT NULL,
    status TEXT NOT NULL,            -- 'pending' | 'accepted' | 'rejected'
    rejection_reason TEXT,
    decided_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status);
"""


Validator = Callable[[str, Any, Any], tuple[bool, str]]
"""A validator takes (kind, key, value) and returns (accepted, rationale)."""


class Registry:
    """A SQLite-backed registry of validated session contributions.

    Open a registry with `Registry(path)`. The schema is created lazily.
    """

    def __init__(self, path: str | pathlib.Path):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._validators: dict[str, Validator] = {}

    def register_validator(self, name: str, validator: Validator) -> None:
        """Register a named validator. Callers reference it by name when
        proposing entries; the same name is recorded with each accepted
        entry for audit."""
        self._validators[name] = validator

    def propose(
        self,
        kind: str,
        key: Any,
        value: Any,
        provenance: str,
        validator_name: str,
    ) -> dict[str, Any]:
        """Propose an entry. The validator runs immediately; if it accepts,
        the entry is committed; otherwise the proposal is recorded as
        rejected with the validator's rationale."""
        if validator_name not in self._validators:
            raise KeyError(
                f"no validator named {validator_name!r}; call "
                f"register_validator() first"
            )
        key_json = json.dumps(key, sort_keys=True, default=str)
        value_json = json.dumps(value, sort_keys=True, default=str)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat(
            timespec="seconds"
        )

        accepted, rationale = self._validators[validator_name](kind, key, value)
        if accepted:
            content_hash = hashlib.sha256(
                (kind + key_json + value_json).encode("utf-8")
            ).hexdigest()[:16]
            try:
                self.conn.execute(
                    "INSERT INTO contributions (kind, key_json, value_json, "
                    "provenance, validated_by, validation_rationale, "
                    "validated_at, content_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (kind, key_json, value_json, provenance, validator_name,
                     rationale, now, content_hash),
                )
                self.conn.execute(
                    "INSERT INTO proposals (kind, key_json, value_json, "
                    "provenance, proposed_at, status, decided_at) "
                    "VALUES (?, ?, ?, ?, ?, 'accepted', ?)",
                    (kind, key_json, value_json, provenance, now, now),
                )
                self.conn.commit()
                return {
                    "status": "accepted",
                    "content_hash": content_hash,
                    "validated_by": validator_name,
                    "rationale": rationale,
                }
            except sqlite3.IntegrityError:
                # Already exists; treat as idempotent accept.
                return {
                    "status": "already_present",
                    "validated_by": validator_name,
                    "rationale": "entry already in registry",
                }
        else:
            self.conn.execute(
                "INSERT INTO proposals (kind, key_json, value_json, "
                "provenance, proposed_at, status, rejection_reason, "
                "decided_at) "
                "VALUES (?, ?, ?, ?, ?, 'rejected', ?, ?)",
                (kind, key_json, value_json, provenance, now, rationale, now),
            )
            self.conn.commit()
            return {
                "status": "rejected",
                "validated_by": validator_name,
                "rationale": rationale,
            }

    def lookup(self, kind: str, key: Any) -> Optional[dict[str, Any]]:
        """Retrieve a validated entry by (kind, key) or None."""
        key_json = json.dumps(key, sort_keys=True, default=str)
        row = self.conn.execute(
            "SELECT value_json, provenance, validated_by, "
            "validation_rationale, validated_at, content_hash "
            "FROM contributions WHERE kind=? AND key_json=?",
            (kind, key_json),
        ).fetchone()
        if row is None:
            return None
        return {
            "value": json.loads(row[0]),
            "provenance": row[1],
            "validated_by": row[2],
            "rationale": row[3],
            "validated_at": row[4],
            "content_hash": row[5],
        }

    def all_entries(self, kind: Optional[str] = None) -> list[dict[str, Any]]:
        if kind:
            cursor = self.conn.execute(
                "SELECT kind, key_json, value_json, provenance, "
                "validated_by, validation_rationale, validated_at, "
                "content_hash FROM contributions WHERE kind=? ORDER BY id",
                (kind,),
            )
        else:
            cursor = self.conn.execute(
                "SELECT kind, key_json, value_json, provenance, "
                "validated_by, validation_rationale, validated_at, "
                "content_hash FROM contributions ORDER BY id"
            )
        return [
            {
                "kind": r[0],
                "key": json.loads(r[1]),
                "value": json.loads(r[2]),
                "provenance": r[3],
                "validated_by": r[4],
                "rationale": r[5],
                "validated_at": r[6],
                "content_hash": r[7],
            }
            for r in cursor.fetchall()
        ]

    def stats(self) -> dict[str, Any]:
        accepted = self.conn.execute(
            "SELECT COUNT(*) FROM contributions"
        ).fetchone()[0]
        proposals = self.conn.execute(
            "SELECT status, COUNT(*) FROM proposals GROUP BY status"
        ).fetchall()
        return {
            "path": str(self.path),
            "accepted_count": accepted,
            "proposals_by_status": dict(proposals),
            "validators_registered": sorted(self._validators.keys()),
        }

    def close(self) -> None:
        self.conn.close()
