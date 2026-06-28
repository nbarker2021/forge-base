"""SplatForgeField.grammar — multi-grammar spatial compiler table (WP-02 finish).

Each grammar is a named SpatialGrammar that determines:

  * How crystal atoms are placed in 3D space (position_fn).
  * What bonds are drawn between atoms (bond_fn).
  * How atom scale / LOD is derived (lod_fn).

Four built-in grammars:

  claim_graph     (default) — E8 projection; co-label chains.
                  The "proof graph" view: atoms cluster by shared label
                  in the E8 root space they were committed to.

  molecule        — 3D hex-grid packing; "bond"-labelled connections.
                  Atoms are packed in a compact sphere grid; only pairs
                  that share a "bond" snap-label are bonded. Scale is
                  uniform (all atoms the same size).

  engineering_part — Radial tree layout; parent→child arcs.
                  The first atom (lowest node_id) is the root at origin;
                  subsequent atoms are placed on concentric shells by
                  their creation order. Bonds trace the shell sequence.

  rule30_strip    — 1D horizontal strip; sequential neighbor bonds.
                  Atoms are laid out in creation order along the x-axis;
                  y-position is driven by importance (high importance ->
                  positive y). Neighboring atoms are bonded in sequence.
                  Matches the Rule-30 row-reading convention.

Adding a grammar: define a SpatialGrammar and register it in GRAMMAR_TABLE.
The grammar is looked up in compile_field; unknown names raise ValueError.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

# PositionFn(nodes, index) -> (x, y, z) world position for the i-th node.
PositionFn = Callable[[List[Any], int], Tuple[float, float, float]]

# BondFn(atoms, nodes, clusters) -> list of (a_id, b_id, relation, direction)
BondFn = Callable[
    [List[Any], List[Any], Dict[str, List[str]]],
    List[Tuple[str, str, str, str]],
]

# LodFn(node) -> scale float
LodFn = Callable[[Any], float]


@dataclass(frozen=True)
class SpatialGrammar:
    name: str
    description: str
    position_fn: PositionFn
    bond_fn: BondFn
    lod_fn: LodFn


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _jitter(seed: str) -> Tuple[float, float, float]:
    d = hashlib.sha256(seed.encode()).digest()
    return tuple(((d[i] / 255.0) - 0.5) * 0.5 for i in range(3))  # type: ignore[return-value]


def _importance_lod(node: Any) -> float:
    return max(0.02, round(getattr(node, "importance", 0.5) * 0.2, 6))


def _uniform_lod(node: Any) -> float:
    return 0.1


# ---------------------------------------------------------------------------
# claim_graph grammar
# ---------------------------------------------------------------------------

def _cg_position(nodes: List[Any], i: int) -> Tuple[float, float, float]:
    """E8 projection into 3D (same as the v0.1 default)."""
    n = nodes[i]
    coords = (list(n.e8_coords) + [0.0] * 8)[:8]
    try:
        from PixelForge.projection import project
        p = project(tuple(coords), "standard")
        base = (float(p[0]), float(p[1]), float(p[2]))
    except Exception:
        base = (coords[0] + coords[3], coords[1] + coords[4], coords[2] + coords[5])
    jx, jy, jz = _jitter(n.node_id)
    return (round(base[0] + jx, 6), round(base[1] + jy, 6), round(base[2] + jz, 6))


def _cg_bonds(atoms: List[Any], nodes: List[Any],
              clusters: Dict[str, List[str]]) -> List[Tuple[str, str, str, str]]:
    """Co-label chains: atoms sharing a snap_label are chained in sorted order."""
    result = []
    for lbl in sorted(clusters):
        members = sorted(clusters[lbl])
        for a, b in zip(members, members[1:]):
            result.append((a, b, f"co_label:{lbl}", "undirected"))
    return result


CLAIM_GRAPH = SpatialGrammar(
    name="claim_graph",
    description="E8 projection + co-label chains (proof-graph view)",
    position_fn=_cg_position,
    bond_fn=_cg_bonds,
    lod_fn=_importance_lod,
)


# ---------------------------------------------------------------------------
# molecule grammar
# ---------------------------------------------------------------------------

def _mol_position(nodes: List[Any], i: int) -> Tuple[float, float, float]:
    """Compact 3D hex-grid packing: atoms fill a sphere layer by layer."""
    if i == 0:
        return (0.0, 0.0, 0.0)
    # Place on concentric hex shells (layer = 1,2,3,...).
    # Each layer l has 6*l atoms on a ring at radius l*0.25.
    layer = 1
    capacity = 0
    while capacity + 6 * layer < i:
        capacity += 6 * layer
        layer += 1
    slot = i - capacity
    angle = (2 * math.pi * slot) / (6 * layer)
    r = layer * 0.25
    z_offset = (layer % 3 - 1) * 0.15  # slight z-spread by layer
    jx, jy, jz = _jitter(nodes[i].node_id)
    return (
        round(r * math.cos(angle) + jx * 0.05, 6),
        round(r * math.sin(angle) + jy * 0.05, 6),
        round(z_offset + jz * 0.05, 6),
    )


def _mol_bonds(atoms: List[Any], nodes: List[Any],
               clusters: Dict[str, List[str]]) -> List[Tuple[str, str, str, str]]:
    """Bond atoms that share a 'bond' snap-label (valence-bond model)."""
    bond_members = sorted(clusters.get("bond", []))
    result = []
    for a, b in zip(bond_members, bond_members[1:]):
        result.append((a, b, "valence", "undirected"))
    # Also bond atoms sharing 'ring' label (cyclic bonds).
    ring = sorted(clusters.get("ring", []))
    if len(ring) >= 2:
        for a, b in zip(ring, ring[1:]):
            result.append((a, b, "ring_bond", "undirected"))
        result.append((ring[-1], ring[0], "ring_bond", "undirected"))  # close ring
    return result


MOLECULE = SpatialGrammar(
    name="molecule",
    description="3D hex-grid packing + valence bonds (chemistry/molecule view)",
    position_fn=_mol_position,
    bond_fn=_mol_bonds,
    lod_fn=_uniform_lod,
)


# ---------------------------------------------------------------------------
# engineering_part grammar
# ---------------------------------------------------------------------------

def _eng_position(nodes: List[Any], i: int) -> Tuple[float, float, float]:
    """Radial tree: root at origin, shells at radius 0.3*depth."""
    if i == 0:
        return (0.0, 0.0, 0.0)
    # Place on concentric rings at depth = ceil(log2(i+1)).
    depth = math.ceil(math.log2(i + 1))
    # How many nodes have been placed at this depth?
    start = 2 ** (depth - 1) - 1  # 0-indexed first slot at this depth
    slot = i - start
    total_at_depth = 2 ** (depth - 1)
    angle = (2 * math.pi * slot) / total_at_depth
    r = depth * 0.3
    jx, jy, jz = _jitter(nodes[i].node_id)
    return (
        round(r * math.cos(angle) + jx * 0.03, 6),
        round(r * math.sin(angle) + jy * 0.03, 6),
        round(depth * 0.05 + jz * 0.02, 6),
    )


def _eng_bonds(atoms: List[Any], nodes: List[Any],
               clusters: Dict[str, List[str]]) -> List[Tuple[str, str, str, str]]:
    """Parent→child arcs: each atom i bonds to atom i//2 (binary tree parent)."""
    atom_ids = [a.atom_id for a in atoms]
    result = []
    for i in range(1, len(atom_ids)):
        parent_idx = (i - 1) // 2
        result.append((atom_ids[parent_idx], atom_ids[i], "component_of", "directed"))
    return result


ENGINEERING_PART = SpatialGrammar(
    name="engineering_part",
    description="Radial tree + parent→child arcs (BOM/assembly view)",
    position_fn=_eng_position,
    bond_fn=_eng_bonds,
    lod_fn=_importance_lod,
)


# ---------------------------------------------------------------------------
# rule30_strip grammar
# ---------------------------------------------------------------------------

def _r30_position(nodes: List[Any], i: int) -> Tuple[float, float, float]:
    """1D strip: atoms in creation order along x; importance drives y."""
    n = nodes[i]
    x = round((i - len(nodes) / 2.0) * 0.2, 6)
    y = round((getattr(n, "importance", 0.5) - 0.5) * 0.6, 6)
    # z encodes mass (0 for empty, positive for heavy atoms)
    z = round(min(getattr(n, "mass", 0.0) * 0.3, 1.0), 6)
    return (x, y, z)


def _r30_bonds(atoms: List[Any], nodes: List[Any],
               clusters: Dict[str, List[str]]) -> List[Tuple[str, str, str, str]]:
    """Sequential neighbor bonds: each atom bonds to the next in strip order."""
    atom_ids = [a.atom_id for a in atoms]
    return [
        (atom_ids[i], atom_ids[i + 1], "strip_neighbor", "directed")
        for i in range(len(atom_ids) - 1)
    ]


RULE30_STRIP = SpatialGrammar(
    name="rule30_strip",
    description="1D horizontal strip + sequential bonds (Rule-30 row view)",
    position_fn=_r30_position,
    bond_fn=_r30_bonds,
    lod_fn=_importance_lod,
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

GRAMMAR_TABLE: Dict[str, SpatialGrammar] = {
    "claim_graph": CLAIM_GRAPH,
    "molecule": MOLECULE,
    "engineering_part": ENGINEERING_PART,
    "rule30_strip": RULE30_STRIP,
}

GRAMMAR_NAMES = tuple(GRAMMAR_TABLE)


def get_grammar(name: str) -> SpatialGrammar:
    """Look up a grammar by name. Raises ValueError for unknown names."""
    try:
        return GRAMMAR_TABLE[name]
    except KeyError:
        known = ", ".join(f"'{k}'" for k in GRAMMAR_TABLE)
        raise ValueError(
            f"unknown grammar {name!r}; known grammars: {known}"
        ) from None


__all__ = [
    "SpatialGrammar", "get_grammar", "GRAMMAR_TABLE", "GRAMMAR_NAMES",
    "CLAIM_GRAPH", "MOLECULE", "ENGINEERING_PART", "RULE30_STRIP",
]
