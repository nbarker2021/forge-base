"""CMPLX lookup/cache chain for Rule 30 and exceptional-form data.

This module attaches local reference surfaces to lattice-forge:

* Wolfram Rule 30 center-column dataset window.
* Atlas exceptional-group unipotent orbit tables.
* Niemeier terminal lattice forms.
* UMRK and LMFDB source registers.

It is a lookup substrate for Prize 3 work. It is not a proof that the cold-start
map `N -> chart axis/sheet` or `N -> Weyl fingerprint` has been closed.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cayley_dickson_oloid import cayley_dickson_oloid_normal_form
from .ledger.build import NIEMEIER_FORMS
from .unipotent_orbits import closure_landing_candidates, get_unipotent_orbit


def _find_data_root() -> Path:
    module = Path(__file__).resolve()
    packaged_data = module.parent / "data"

    def _anc(n: int):
        # Safe ancestor: None instead of IndexError at shallow install depths.
        return module.parents[n] if n < len(module.parents) else None

    env_candidates = [
        os.environ.get("CQECMPLX_DATA_ROOT"),
        os.environ.get("CMPLX_R30_DATA_ROOT"),
    ]
    root_candidates = [
        *(Path(value) for value in env_candidates if value),
        packaged_data,
        *(a / "DATA" for a in (_anc(3), _anc(2)) if a is not None),
        Path.cwd() / "DATA",
        Path("D:/CQE_CMPLX/CMPLX-R30-main/DATA"),
        Path("D:/CQE_CMPLX/g/CMPLX-R30/DATA"),
    ]
    for candidate in root_candidates:
        if (candidate / "wolfram-rule30-center" / "wolfram_rule30_center_1m.json").exists():
            return candidate
    return packaged_data


DATA_ROOT = _find_data_root()
RULE30_JSON = DATA_ROOT / "wolfram-rule30-center" / "wolfram_rule30_center_1m.json"
UMRK_SCHEMA = DATA_ROOT / "umrk" / "umrk_schema.json"
LMFDB_SOURCES = DATA_ROOT / "lmfdb" / "lmfdb_sources.json"
ATLAS_ORBITS = DATA_ROOT / "atlas-unipotent-orbits" / "unipotent_orbits.json"


@dataclass(frozen=True)
class LookupReceipt:
    kind: str
    key: str
    value: Any
    source_id: str
    evidence_level: str
    complexity_claim: str


def _load_wolfram_million_bits() -> str:
    raw = json.loads(RULE30_JSON.read_text(encoding="utf-8-sig"))
    if isinstance(raw, dict):
        for value in raw.values():
            if isinstance(value, list):
                raw = value
                break
    if not isinstance(raw, list):
        raise ValueError(f"Expected list payload in {RULE30_JSON}")
    if raw and raw[0] == "List":
        raw = raw[1:]
    bitstring = "".join(str(int(bit)) for bit in raw)
    if set(bitstring) - {"0", "1"}:
        raise ValueError("Rule 30 dataset contains non-binary values")
    return bitstring


def _json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


class CmplxLookupCache:
    """SQLite-backed cache chain with local in-memory hot lanes."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._bits: str | None = None
        self._ensure_schema()

    def close(self) -> None:
        self._conn.commit()
        self._conn.close()

    def _ensure_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS source_register (
                source_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rule30_window (
                source_id TEXT PRIMARY KEY,
                bit_count INTEGER NOT NULL,
                bits TEXT NOT NULL,
                evidence_level TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS unipotent_orbit (
                orbit_id TEXT PRIMARY KEY,
                group_name TEXT NOT NULL,
                orbit_name TEXT NOT NULL,
                dimension INTEGER NOT NULL,
                special INTEGER NOT NULL,
                dual TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_unipotent_group ON unipotent_orbit(group_name);

            CREATE TABLE IF NOT EXISTS lattice_form (
                terminal_id TEXT PRIMARY KEY,
                root_system TEXT NOT NULL,
                coxeter_number INTEGER,
                note TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def materialize(self, force: bool = False) -> CmplxLookupCache:
        if force:
            self._conn.executescript(
                """
                DELETE FROM source_register;
                DELETE FROM rule30_window;
                DELETE FROM unipotent_orbit;
                DELETE FROM lattice_form;
                """
            )
            self._conn.commit()
            self._bits = None
        self._materialize_rule30()
        self._materialize_unipotent_orbits()
        self._materialize_lattice_forms()
        self._materialize_source_registers()
        return self

    def _materialize_rule30(self) -> None:
        row = self._conn.execute(
            "SELECT bits FROM rule30_window WHERE source_id=?",
            ["wolfram-rule30-center-million"],
        ).fetchone()
        if row is not None:
            self._bits = str(row["bits"])
            return
        bitstring = _load_wolfram_million_bits()
        self._conn.execute(
            "INSERT OR REPLACE INTO rule30_window VALUES (?,?,?,?)",
            [
                "wolfram-rule30-center-million",
                len(bitstring),
                bitstring,
                "external_dataset",
            ],
        )
        self._conn.commit()
        self._bits = bitstring

    def _materialize_unipotent_orbits(self) -> None:
        count = self._conn.execute("SELECT COUNT(*) FROM unipotent_orbit").fetchone()[0]
        if count:
            return
        payload = json.loads(ATLAS_ORBITS.read_text(encoding="utf-8"))
        rows = []
        for record in payload["records"]:
            orbit_id = f"{record['group']}:{record['name']}"
            rows.append(
                [
                    orbit_id,
                    record["group"],
                    record["name"],
                    int(record["dimension"]),
                    1 if record["special"] else 0,
                    record["dual"],
                    _json(record),
                ]
            )
        self._conn.executemany(
            "INSERT OR REPLACE INTO unipotent_orbit VALUES (?,?,?,?,?,?,?)",
            rows,
        )
        self._conn.commit()

    def _materialize_lattice_forms(self) -> None:
        count = self._conn.execute("SELECT COUNT(*) FROM lattice_form").fetchone()[0]
        if count:
            return
        rows = []
        for terminal_id, root_system, coxeter_number, note in NIEMEIER_FORMS:
            payload = {
                "terminal_id": terminal_id,
                "root_system": root_system,
                "coxeter_number": coxeter_number,
                "note": note,
                "formal_role": "24D terminal lattice landing form",
            }
            rows.append([terminal_id, root_system, coxeter_number, note, _json(payload)])
        self._conn.executemany(
            "INSERT OR REPLACE INTO lattice_form VALUES (?,?,?,?,?)",
            rows,
        )
        self._conn.commit()

    def _materialize_source_registers(self) -> None:
        sources = {
            "umrk": json.loads(UMRK_SCHEMA.read_text(encoding="utf-8")),
            "lmfdb": json.loads(LMFDB_SOURCES.read_text(encoding="utf-8")),
        }
        for source_id, payload in sources.items():
            self._conn.execute(
                "INSERT OR REPLACE INTO source_register VALUES (?,?)",
                [source_id, _json(payload)],
            )
        self._conn.commit()

    def status(self) -> dict[str, Any]:
        rule30 = self._conn.execute(
            "SELECT bit_count FROM rule30_window WHERE source_id=?",
            ["wolfram-rule30-center-million"],
        ).fetchone()
        return {
            "cache_exists": self.db_path.exists(),
            "rule30_bits": int(rule30["bit_count"]) if rule30 else 0,
            "unipotent_orbits": self._count("unipotent_orbit"),
            "lattice_forms": self._count("lattice_form"),
            "source_registers": {
                "umrk": self._source_exists("umrk"),
                "lmfdb": self._source_exists("lmfdb"),
            },
        }

    def _count(self, table: str) -> int:
        return int(self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    def _source_exists(self, source_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM source_register WHERE source_id=?",
            [source_id],
        ).fetchone()
        return row is not None

    def _bitstring(self) -> str:
        if self._bits is not None:
            return self._bits
        row = self._conn.execute(
            "SELECT bits FROM rule30_window WHERE source_id=?",
            ["wolfram-rule30-center-million"],
        ).fetchone()
        if row is None:
            self._materialize_rule30()
            return self._bits or ""
        self._bits = str(row["bits"])
        return self._bits

    def lookup_rule30_bit(self, n: int) -> LookupReceipt:
        bits = self._bitstring()
        if n < 0 or n >= len(bits):
            raise IndexError(
                f"N={n} outside materialized Rule 30 window 0..{len(bits) - 1}"
            )
        return LookupReceipt(
            kind="rule30.center_bit",
            key=str(n),
            value=int(bits[n]),
            source_id="wolfram-rule30-center-million",
            evidence_level="external_dataset",
            complexity_claim="O(1) cache lookup inside materialized dataset window",
        )

    def lookup_unipotent_orbit(self, group: str, name: str) -> LookupReceipt:
        orbit = get_unipotent_orbit(group, name)
        value = {
            "group": orbit.group,
            "name": orbit.name,
            "diagram": orbit.diagram,
            "dimension": orbit.dimension,
            "special": orbit.special,
            "dual": orbit.dual,
            "component_group_quotient": orbit.component_group_quotient,
        }
        return LookupReceipt(
            kind="unipotent.orbit",
            key=orbit.orbit_id,
            value=value,
            source_id="atlas-unipotent-orbits",
            evidence_level="parsed_reference_table",
            complexity_claim="O(1) indexed record lookup after materialization",
        )

    def lookup_unipotent_dual(self, group: str, name: str) -> LookupReceipt:
        orbit = get_unipotent_orbit(group, name)
        return self.lookup_unipotent_orbit(orbit.group, orbit.dual)

    def lookup_lattice_form(self, terminal_id: str) -> LookupReceipt:
        row = self._conn.execute(
            "SELECT payload_json FROM lattice_form WHERE terminal_id=?",
            [terminal_id],
        ).fetchone()
        if row is None:
            raise KeyError(f"No lattice form {terminal_id}")
        payload = json.loads(row["payload_json"])
        return LookupReceipt(
            kind="lattice.form",
            key=terminal_id,
            value=payload,
            source_id="lattice-forge-niemeier-forms",
            evidence_level="local_exact_registry",
            complexity_claim="O(1) indexed record lookup after materialization",
        )

    def lookup_source_register(self, source_id: str) -> LookupReceipt:
        row = self._conn.execute(
            "SELECT payload_json FROM source_register WHERE source_id=?",
            [source_id],
        ).fetchone()
        if row is None:
            raise KeyError(f"No source register {source_id}")
        return LookupReceipt(
            kind="source.register",
            key=source_id,
            value=json.loads(row["payload_json"]),
            source_id=source_id,
            evidence_level="source_contract",
            complexity_claim="O(1) indexed source metadata lookup",
        )

    def prize3_lookup_receipt(self, n: int, group: str = "F4") -> LookupReceipt:
        bit_receipt = self.lookup_rule30_bit(n)
        candidates = closure_landing_candidates(group, special_only=True)
        normal_form = cayley_dickson_oloid_normal_form(n, energy_terms=8)
        return LookupReceipt(
            kind="prize3.lookup_substrate",
            key=f"N={n};group={group.upper()}",
            value={
                "N": n,
                "center_bit": bit_receipt.value,
                "dataset_window": bit_receipt.source_id,
                "normal_form": {
                    "podal_pair": normal_form.podal_pair,
                    "cayley_dickson_doubling_order": normal_form.cayley_dickson_doubling_order,
                    "network_weights": normal_form.network_weights,
                    "total_network_weight": normal_form.total_network_weight,
                    "honesty": normal_form.honesty,
                },
                "orbit_group": group.upper(),
                "orbit_candidate_count": len(candidates),
                "orbit_candidates": [orbit.name for orbit in candidates],
                "closed_form_claim": False,
                "remaining_obligation": "prove cold-start N-to-axis/sheet or N-to-Weyl fingerprint",
            },
            source_id="cmplx-lookup-cache-chain",
            evidence_level="materialized_lookup_substrate",
            complexity_claim=(
                "O(1) for materialized bit and indexed local records; no cold-start "
                "closed-form N-to-fingerprint claim"
            ),
        )


def build_default_cache(db_path: Path | None = None, *, force: bool = False) -> CmplxLookupCache:
    if db_path is None:
        db_path = DATA_ROOT / "cache" / "cmplx_lookup.sqlite"
    cache = CmplxLookupCache(Path(db_path))
    return cache.materialize(force=force)
