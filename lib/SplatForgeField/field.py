"""SplatForgeField.field — the Spatialization Forge (deterministic crystal -> SpatialField).

This is the WP-02 spatial compiler: a CrystalForge crystal (atoms = e8_nodes)
compiles deterministically into a SpatialField (atoms with 3D positions, bonds,
clusters, Gaussian splats, selection IDs) plus two content hashes:
  - scene_graph_hash : the semantic structure (atoms + bonds), render-independent
  - splat_buffer_hash: the renderable Gaussian-splat buffer

Non-negotiable contract (the operator's §5): the SpatialField is a *reversible
projection* of the crystal, regenerable and disposable. Gaussian splats are a
rendering carrier, never the authoritative meaning store. The crystal is the
source of truth; this module only projects it.

Composes existing primitives, adds no algebra:
  - CrystalForge.crystal.get_nodes  -> the atoms (with e8_coords, snap_labels, mass)
  - PixelForge.projection.project   -> 8D E8 coords -> 3D position (with fallback)
  - SplatForge.compiler.GaussianSplatInstance -> the splat shape (reused verbatim)
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field as dc_field, asdict
from typing import Any, Dict, List, Optional, Tuple

from CrystalForge import crystal as _crystal
from SplatForge.compiler import GaussianSplatInstance, ADAPTER_ID as SPLAT_ADAPTER

FIELD_ADAPTER_ID = "SplatForgeField.field.SpatialCompiler"
FIELD_ADAPTER_VERSION = "0.1.0"


# --- the spatial projection (e8 coords -> 3D), with a deterministic fallback ---

def _project3(e8_coords: List[float]) -> Tuple[float, float, float]:
    coords = (list(e8_coords) + [0.0] * 8)[:8]
    try:
        from PixelForge.projection import project
        p = project(tuple(coords), "standard")
        return (float(p[0]), float(p[1]), float(p[2]))
    except Exception:
        # Fallback: deterministic 8D->3D linear fold (sum of disjoint pairs).
        return (coords[0] + coords[3], coords[1] + coords[4], coords[2] + coords[5])


def _jitter(seed: str) -> Tuple[float, float, float]:
    """Deterministic small offset so atoms sharing a crystal's e8_root still
    occupy distinct positions. Same seed -> same offset, always."""
    d = hashlib.sha256(seed.encode()).digest()
    return tuple(((d[i] / 255.0) - 0.5) * 0.5 for i in range(3))  # type: ignore[return-value]


def _stable_hash(obj: Any) -> str:
    body = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(body).hexdigest()


# --- the three record types (operator's §5 atom/bond shapes) -------------------

@dataclass(frozen=True)
class Atom:
    atom_id: str
    crystal_id: str
    semantic_type: str
    parent_id: str
    position: Tuple[float, float, float]
    orientation: Tuple[float, float, float, float]
    scale: Tuple[float, float, float]
    visibility_mask: int
    selection_mask: int
    validator_state: str
    residue_state: str
    receipt_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Bond:
    bond_id: str
    source_atom_id: str
    target_atom_id: str
    relation_type: str
    direction: str
    weight: float
    status: str
    evidence_class: str
    receipt_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SpatialField:
    field_id: str
    crystal_id: str
    grammar: str
    atoms: List[Atom]
    bonds: List[Bond]
    clusters: Dict[str, List[str]]
    splats: List[GaussianSplatInstance]
    scene_graph_hash: str
    splat_buffer_hash: str

    def summary(self) -> Dict[str, Any]:
        return {
            "field_id": self.field_id, "crystal_id": self.crystal_id,
            "grammar": self.grammar, "atoms": len(self.atoms),
            "bonds": len(self.bonds), "clusters": len(self.clusters),
            "splats": len(self.splats),
            "scene_graph_hash": self.scene_graph_hash,
            "splat_buffer_hash": self.splat_buffer_hash,
        }


# --- the compiler -------------------------------------------------------------

def compile_field(crystal_id: str, grammar: str = "claim_graph",
                  db_path: Optional[str] = None) -> SpatialField:
    """Deterministically compile a crystal into a SpatialField. The same
    (crystal_id, grammar) always yields the same scene_graph_hash and
    splat_buffer_hash (WP-01 exit gate).

    Grammar selects position, bond, and LOD strategy from the GRAMMAR_TABLE
    (grammar.py). Unknown grammar names raise ValueError.
    """
    from .grammar import get_grammar
    gram = get_grammar(grammar)

    nodes = sorted(_crystal.get_nodes(crystal_id, db_path), key=lambda n: n.node_id)

    atoms: List[Atom] = []
    splats: List[GaussianSplatInstance] = []
    clusters: Dict[str, List[str]] = {}

    for i, n in enumerate(nodes):
        pos = gram.position_fn(nodes, i)
        validator_state = "validated" if n.importance >= 0.5 else "candidate"
        residue_state = "residue" if (n.mass <= 0.0) else "clean"
        scale = gram.lod_fn(n)

        atom = Atom(
            atom_id=n.node_id, crystal_id=crystal_id,
            semantic_type=n.content_type, parent_id=crystal_id,
            position=pos, orientation=(0.0, 0.0, 0.0, 1.0),
            scale=(scale, scale, scale),
            visibility_mask=1, selection_mask=0,
            validator_state=validator_state, residue_state=residue_state,
            receipt_hash="",
        )
        atoms.append(atom)

        # color from the first label's hash (cosmetic, deterministic, not a claim)
        lbl = (n.snap_labels or ["atom"])[0]
        ch = hashlib.sha256(lbl.encode()).digest()
        rgb = (ch[0] / 255.0, ch[1] / 255.0, ch[2] / 255.0)
        splats.append(GaussianSplatInstance(
            splat_id=f"splat:{n.node_id}", source_class="DD", source_asset_id=crystal_id,
            mean_position=pos, covariance_or_scale=(scale, scale, scale),
            opacity=round(min(1.0, 0.3 + n.importance), 6), appearance_coefficients=rgb,
            tile_instance_id=n.node_id, vignette_state_id="field.v0",
            observer_window_id="observer.default",
        ))
        for lbl in (n.snap_labels or []):
            clusters.setdefault(lbl, []).append(n.node_id)

    # Grammar-specific bonds.
    raw_bonds = gram.bond_fn(atoms, nodes, clusters)
    bonds: List[Bond] = [
        Bond(
            bond_id=f"bond:{grammar}:{a}->{b}", source_atom_id=a, target_atom_id=b,
            relation_type=rel, direction=direction,
            weight=1.0, status="active", evidence_class="derived", receipt_hash="",
        )
        for a, b, rel, direction in raw_bonds
    ]

    scene_graph_hash = _stable_hash({
        "crystal_id": crystal_id, "grammar": grammar,
        "atoms": [a.to_dict() for a in atoms],
        "bonds": [b.to_dict() for b in bonds],
    })
    splat_buffer_hash = _stable_hash([s.to_dict() for s in splats])
    field_id = f"field:{crystal_id}:{scene_graph_hash[:12]}"

    return SpatialField(
        field_id=field_id, crystal_id=crystal_id, grammar=grammar,
        atoms=atoms, bonds=bonds, clusters=clusters, splats=splats,
        scene_graph_hash=scene_graph_hash, splat_buffer_hash=splat_buffer_hash,
    )
