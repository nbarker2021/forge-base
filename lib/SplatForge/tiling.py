"""
SplatForge.tiling — standard unit-cell tile-site generation for the nine
Crystal Zoo families (ecology/registries/crystal_zoo.csv).

Adapted (shape only, not imported) from the legacy g/CMPLX tiling_engine.py
OctantTile pattern (row/col/layer position + adjacency) per
production/_meta/NAMING-LAW.md: lineage code may not be imported under its
old name without a CQE-/Forge wrapper. That module tiled RAG text content;
this module tiles crystal lattices, so only the position-record *shape*
carries over, reimplemented here.

The lattice geometry (basis vectors + site bases below) is standard
solid-state-physics unit-cell construction (the usual nine Bravais/crystal
prototypes). It is declared geometry, independent of Crystal Zoo's own
"registered, open_external_validation" status (CRYSTAL_ZOO.md) — building a
correct unit cell for "FCC" does not itself close that external-validation
gap.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

_SQRT3_2 = math.sqrt(3.0) / 2.0
_HCP_C = math.sqrt(8.0 / 3.0)


@dataclass(frozen=True)
class TileFamilyAsset:
    """Mirrors ecology/schemas/tile_family_asset.schema.json."""

    tile_family_id: str
    name: str
    dimensionality: int
    basis_vectors: Tuple[Tuple[float, float, float], ...]
    site_basis: Tuple[Tuple[str, Tuple[float, float, float]], ...]
    coordination_number: int
    crystal_id: str
    nearest_neighbor_distance: float = 0.0
    orientation_chirality: Optional[str] = None
    matching_rules: Optional[str] = None
    substitution_grammar: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "tile_family_id": self.tile_family_id,
            "name": self.name,
            "dimensionality": self.dimensionality,
            "basis_vectors": [list(v) for v in self.basis_vectors],
            "site_basis": [
                {"label": label, "fractional_coords": list(coords)}
                for label, coords in self.site_basis
            ],
            "coordination_number": self.coordination_number,
            "nearest_neighbor_distance": self.nearest_neighbor_distance,
            "orientation_chirality": self.orientation_chirality,
            "matching_rules": self.matching_rules,
            "substitution_grammar": self.substitution_grammar,
            "provenance": {
                "crystal_id": self.crystal_id,
                "source": "ecology/registries/crystal_zoo.csv",
            },
        }


@dataclass(frozen=True)
class TileInstance:
    """Mirrors ecology/schemas/tile_instance.schema.json."""

    tile_instance_id: str
    tile_family_id: str
    cell_index: Tuple[int, int, int]
    site_label: str
    position: Tuple[float, float, float]

    def to_dict(self) -> Dict:
        return {
            "tile_instance_id": self.tile_instance_id,
            "tile_family_id": self.tile_family_id,
            "cell_index": list(self.cell_index),
            "site_label": self.site_label,
            "position": list(self.position),
            "lineage": self.tile_family_id,
            "lcr_signature": None,
            "correction_state": None,
            "energy_residual": None,
            "receipt_id": None,
        }


def _basis(*vecs: Sequence[float]) -> Tuple[Tuple[float, float, float], ...]:
    return tuple(tuple(float(x) for x in v) + (0.0,) * (3 - len(v)) for v in vecs)


# crystal_id (ecology/registries/crystal_zoo.csv) -> standard unit-cell definition.
# Lattice constant a = 1.0 throughout; nearest_neighbor_distance is measured
# from the generated geometry below, not hand-copied from a textbook table,
# so the schema field can never silently drift from what the generator
# actually produces.
_FAMILY_DEFS: Dict[str, Dict] = {
    "CZ-SQUARE": dict(
        tile_family_id="SquareTile", name="Square lattice", dimensionality=2,
        basis_vectors=_basis((1.0, 0.0), (0.0, 1.0)),
        site_basis=(("A", (0.0, 0.0, 0.0)),),
        coordination_number=4,
    ),
    "CZ-HEX": dict(
        tile_family_id="HexagonTile", name="Hexagonal lattice", dimensionality=2,
        basis_vectors=_basis((1.0, 0.0), (0.5, _SQRT3_2)),
        site_basis=(("A", (0.0, 0.0, 0.0)),),
        coordination_number=6,
    ),
    "CZ-FCC": dict(
        tile_family_id="FCCTile", name="Face-centered cubic", dimensionality=3,
        basis_vectors=_basis((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        site_basis=(
            ("A", (0.0, 0.0, 0.0)), ("A", (0.5, 0.5, 0.0)),
            ("A", (0.5, 0.0, 0.5)), ("A", (0.0, 0.5, 0.5)),
        ),
        coordination_number=12,
    ),
    "CZ-BCC": dict(
        tile_family_id="BCCTile", name="Body-centered cubic", dimensionality=3,
        basis_vectors=_basis((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        site_basis=(("A", (0.0, 0.0, 0.0)), ("A", (0.5, 0.5, 0.5))),
        coordination_number=8,
    ),
    "CZ-HCP": dict(
        tile_family_id="HCPTile", name="Hexagonal close packed", dimensionality=3,
        basis_vectors=_basis((1.0, 0.0, 0.0), (0.5, _SQRT3_2, 0.0), (0.0, 0.0, _HCP_C)),
        site_basis=(("A", (0.0, 0.0, 0.0)), ("A", (1.0 / 3.0, 1.0 / 3.0, 0.5))),
        coordination_number=12,
    ),
    "CZ-DIAMOND": dict(
        tile_family_id="DiamondTile", name="Diamond cubic", dimensionality=3,
        basis_vectors=_basis((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        site_basis=(
            ("A", (0.0, 0.0, 0.0)), ("A", (0.5, 0.5, 0.0)),
            ("A", (0.5, 0.0, 0.5)), ("A", (0.0, 0.5, 0.5)),
            ("B", (0.25, 0.25, 0.25)), ("B", (0.75, 0.75, 0.25)),
            ("B", (0.75, 0.25, 0.75)), ("B", (0.25, 0.75, 0.75)),
        ),
        coordination_number=4,
    ),
    "CZ-GRAPHENE": dict(
        tile_family_id="GrapheneTile", name="Graphene", dimensionality=2,
        basis_vectors=_basis((1.0, 0.0), (0.5, _SQRT3_2)),
        site_basis=(("A", (0.0, 0.0, 0.0)), ("B", (1.0 / 3.0, 1.0 / 3.0, 0.0))),
        coordination_number=3,
    ),
    "CZ-KAGOME": dict(
        tile_family_id="KagomeTile", name="Kagome lattice", dimensionality=2,
        basis_vectors=_basis((1.0, 0.0), (0.5, _SQRT3_2)),
        site_basis=(
            ("A", (0.5, 0.0, 0.0)), ("B", (0.0, 0.5, 0.0)), ("C", (0.5, 0.5, 0.0)),
        ),
        coordination_number=4,
    ),
    "CZ-PYROCHLORE": dict(
        tile_family_id="PyrochloreTile", name="Pyrochlore lattice", dimensionality=3,
        basis_vectors=_basis((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        # Standard simplified construction: corner-sharing tetrahedra centered
        # on the 4 FCC sites, each split into 4 corners by a small tetrahedral
        # offset. A declared geometric prototype, not a refined-structure claim
        # for any specific compound in crystal_zoo.csv's material_examples column.
        site_basis=tuple(
            (f"T{ci}{di}", ((cx + dx) % 1.0, (cy + dy) % 1.0, (cz + dz) % 1.0))
            for ci, (cx, cy, cz) in enumerate(
                [(0.0, 0.0, 0.0), (0.0, 0.5, 0.5), (0.5, 0.0, 0.5), (0.5, 0.5, 0.0)]
            )
            for di, (dx, dy, dz) in enumerate(
                [(0.125, 0.125, 0.125), (0.125, -0.125, -0.125),
                 (-0.125, 0.125, -0.125), (-0.125, -0.125, 0.125)]
            )
        ),
        coordination_number=6,
    ),
}

CRYSTAL_IDS: Tuple[str, ...] = tuple(_FAMILY_DEFS.keys())


def _cartesian(basis_vectors: Sequence[Sequence[float]], frac: Sequence[float]) -> Tuple[float, float, float]:
    p = np.zeros(3)
    for coeff, vec in zip(frac, basis_vectors):
        p += coeff * np.array(vec)
    return (float(p[0]), float(p[1]), float(p[2]))


def _measure_nearest_neighbor(d: Dict) -> float:
    """Self-checking nn distance: generate a 3x3(x3) block of cells around an
    interior site and take the minimum pairwise distance from the site
    nearest the block centroid, instead of hand-typing a textbook constant
    that could silently drift from the geometry defined above."""
    is_3d = d["dimensionality"] == 3
    rng = (-1, 0, 1)
    z_rng = rng if is_3d else (0,)
    pts: List[np.ndarray] = []
    for ix in rng:
        for iy in rng:
            for iz in z_rng:
                cell_frac = (ix, iy, iz) if is_3d else (ix, iy)
                origin = np.array(_cartesian(d["basis_vectors"], cell_frac))
                for _, frac in d["site_basis"]:
                    site = np.array(_cartesian(d["basis_vectors"], frac))
                    pts.append(origin + site)
    arr = np.array(pts)
    centroid = arr.mean(axis=0)
    ref = arr[int(np.argmin(np.linalg.norm(arr - centroid, axis=1)))]
    dists = np.linalg.norm(arr - ref, axis=1)
    nonzero = dists[dists > 1e-9]
    return round(float(nonzero.min()), 6)


def build_tile_family_asset(crystal_id: str) -> TileFamilyAsset:
    if crystal_id not in _FAMILY_DEFS:
        raise KeyError(f"unknown crystal_id {crystal_id!r}; known: {CRYSTAL_IDS}")
    d = _FAMILY_DEFS[crystal_id]
    return TileFamilyAsset(
        tile_family_id=d["tile_family_id"],
        name=d["name"],
        dimensionality=d["dimensionality"],
        basis_vectors=d["basis_vectors"],
        site_basis=d["site_basis"],
        coordination_number=d["coordination_number"],
        crystal_id=crystal_id,
        nearest_neighbor_distance=_measure_nearest_neighbor(d),
    )


def generate_tile_instances(
    crystal_id: str, extent: Tuple[int, int, int] = (2, 2, 2)
) -> List[TileInstance]:
    """Deterministic TileInstance generation: extent[i] unit cells along each
    basis direction (extent[2] is ignored for 2D families)."""
    family = build_tile_family_asset(crystal_id)
    d = _FAMILY_DEFS[crystal_id]
    is_3d = d["dimensionality"] == 3
    nz = extent[2] if is_3d else 1

    out: List[TileInstance] = []
    for ix in range(extent[0]):
        for iy in range(extent[1]):
            for iz in range(nz):
                cell_frac = (ix, iy, iz) if is_3d else (ix, iy)
                origin = _cartesian(d["basis_vectors"], cell_frac)
                for label, frac in d["site_basis"]:
                    site = _cartesian(d["basis_vectors"], frac)
                    pos = (origin[0] + site[0], origin[1] + site[1], origin[2] + site[2])
                    out.append(TileInstance(
                        tile_instance_id=f"{family.tile_family_id}:{ix}.{iy}.{iz}:{label}",
                        tile_family_id=family.tile_family_id,
                        cell_index=(ix, iy, iz),
                        site_label=label,
                        position=pos,
                    ))
    return out
