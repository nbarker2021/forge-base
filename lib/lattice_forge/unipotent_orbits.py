"""Atlas unipotent-orbit table accessors for exceptional groups.

The packaged data is sourced from the Atlas of Lie Groups and Representations:
http://www.liegroups.org/tables/unipotentOrbits/

This module intentionally exposes lookup and classification helpers only. It
does not assert that an orbit label by itself closes a CMPLX proof obligation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_PATH = Path(__file__).resolve().parent / "data" / "unipotent_orbits.json"
EXCEPTIONAL_GROUPS = ("G2", "F4", "E6", "E7", "E8")


@dataclass(frozen=True)
class UnipotentOrbit:
    group: str
    name: str
    diagram: str
    dimension: int
    special: bool
    dual: str
    component_group_quotient: str
    source_file: str
    source_url: str
    row_index: int

    @property
    def orbit_id(self) -> str:
        return f"{self.group}:{self.name}"

    @property
    def dual_id(self) -> str:
        return f"{self.group}:{self.dual}"


@lru_cache(maxsize=1)
def _payload() -> dict[str, Any]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def all_unipotent_orbits() -> tuple[UnipotentOrbit, ...]:
    return tuple(UnipotentOrbit(**row) for row in _payload()["records"])


def unipotent_orbits_for_group(group: str) -> tuple[UnipotentOrbit, ...]:
    normalized = group.upper()
    if normalized not in EXCEPTIONAL_GROUPS:
        raise ValueError(f"group must be one of {EXCEPTIONAL_GROUPS}, got {group!r}")
    return tuple(orbit for orbit in all_unipotent_orbits() if orbit.group == normalized)


def get_unipotent_orbit(group: str, name: str) -> UnipotentOrbit:
    normalized = group.upper()
    for orbit in unipotent_orbits_for_group(normalized):
        if orbit.name == name:
            return orbit
    raise KeyError(f"No unipotent orbit {normalized}:{name}")


def special_unipotent_orbits(group: str | None = None) -> tuple[UnipotentOrbit, ...]:
    source = all_unipotent_orbits() if group is None else unipotent_orbits_for_group(group)
    return tuple(orbit for orbit in source if orbit.special)


def dual_unipotent_orbit(orbit: UnipotentOrbit) -> UnipotentOrbit:
    return get_unipotent_orbit(orbit.group, orbit.dual)


def unipotent_orbit_summary() -> dict[str, Any]:
    return _payload()["summary"]


def orbit_dimension_range(group: str) -> tuple[int, int]:
    orbits = unipotent_orbits_for_group(group)
    return min(orbit.dimension for orbit in orbits), max(orbit.dimension for orbit in orbits)


def closure_landing_candidates(
    group: str,
    *,
    special_only: bool = True,
    min_dimension: int | None = None,
    max_dimension: int | None = None,
) -> tuple[UnipotentOrbit, ...]:
    """Return orbit candidates for a formal closure/landing assignment.

    `special_only=True` is the conservative default because special orbits are
    the natural first class to test against Springer/Lusztig-style transport
    language. Dimension bounds let callers tie a finite CMPLX sheet to a
    compatible orbit window without claiming more structure than the table
    provides.
    """
    rows = special_unipotent_orbits(group) if special_only else unipotent_orbits_for_group(group)
    if min_dimension is not None:
        rows = tuple(row for row in rows if row.dimension >= min_dimension)
    if max_dimension is not None:
        rows = tuple(row for row in rows if row.dimension <= max_dimension)
    return rows


def verify_unipotent_orbit_tables() -> dict[str, Any]:
    errors: list[str] = []
    summary = unipotent_orbit_summary()
    records = all_unipotent_orbits()
    if not records:
        errors.append("no records loaded")
    by_id = {(orbit.group, orbit.name): orbit for orbit in records}
    if len(by_id) != len(records):
        errors.append("duplicate group/name orbit records")
    for group in EXCEPTIONAL_GROUPS:
        rows = unipotent_orbits_for_group(group)
        if len(rows) != summary["groups"][group]["orbit_count"]:
            errors.append(f"{group} summary count mismatch")
        for orbit in rows:
            if (orbit.group, orbit.dual) not in by_id:
                errors.append(f"{orbit.orbit_id} dual target missing: {orbit.dual}")
            if len(orbit.diagram) != len(rows[0].diagram):
                errors.append(f"{orbit.orbit_id} weighted diagram length mismatch")
    return {
        "status": "pass" if not errors else "fail",
        "record_count": len(records),
        "groups": summary["groups"],
        "errors": errors,
    }
