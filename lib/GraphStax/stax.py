"""
GraphStax Stax — Sheet-on-graph data model and resolution engine.

Core operation: bit_to_c(ribbon_id, bit_pos, L, C, R, level)
  "Turn any single bit on any single ribbon into a C on ITS sheet size."

A Stax item IS a bit treated as the center (C) of a local (L,C,R) context
at a specific sheet resolution (MDHG level). Every Stax has:

  - A ribbon identity  (which ribbon it lives on)
  - A bit position     (where on that ribbon)
  - A sheet level      (which MDHG resolution scale, 0=grain .. 8=universe)
  - A local state      (L,C,R) at that position in the sheet context
  - The T_EMISSION result (the output bit the C-gluon produces)
  - Classification     (symmetric / correction / chiral)
  - AGRM position      (24D, derived from ribbon + bit_pos + level + state)
  - A graph ID         (used for AGRM registration and graph adjacency)

StaxGraph holds all Stax items registered for a session, keyed by graph_id.
Adjacency is maintained as a dict of {source_graph_id: [target_graph_id, ...]}.

The "sheet" metaphor: at level k, the C-gluon is the center of a 2^(k+1)-bit
window. A grain sheet (level 0) covers 2 bits; a universe sheet (level 8)
covers 512 bits. The C-gluon IS the oloid at that scale — same geometry,
different resolution.
"""
import hashlib
import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from GraphStax.rule30 import (
    _ALL_STATES, _T_EMISSION_TABLE, _GLUON_TABLE,
    _VOA_WEIGHT_TABLE, _VOA_SECTOR_TABLE, _STATE_CLASS_TABLE,
    _STATE_PROB_TABLE, _ANNEAL_TABLE, _HAMMING_TO_CENTROID,
    CORRECTION_FIRING_STATES, CHIRAL_DOUBLET, TRUE_VACUA, LIE_CONJUGATES,
    _MDHG_LEVELS, _SHEET_SIZE_TABLE, t_emission, profile, sheet_size,
)

# ─── Lookup tables (import-time, read-only) ────────────────────────────────────

PHI: float = (1.0 + math.sqrt(5.0)) / 2.0
COUPLING: float = math.log(PHI) / 16.0   # κ ≈ 0.030076

# 24D basis projections for Stax AGRM positioning:
# Dimensions 0-7:   encoded from (ribbon_id_hash, bit_pos, level)
# Dimensions 8-15:  local state features + T_EMISSION result
# Dimensions 16-23: VOA / anneal / probability profile
_STAX_POSITION_SCALE: float = 1.0 / (2.0 ** 9)   # normalize to [-1, 1] range


# ─── Stax dataclass ───────────────────────────────────────────────────────────

@dataclass
class Stax:
    """A single bit resolved as a C-gluon on its sheet at a given resolution level."""

    # Identity
    graph_id: str                       # unique ID in the graph
    ribbon_id: str                      # which ribbon this bit lives on
    bit_pos: int                        # position on the ribbon (0-indexed)
    level: int                          # MDHG sheet resolution (0=grain .. 8=universe)

    # Local context
    local_state: Tuple[int, int, int]   # (L, C, R) at this position

    # Derived (all from lookup tables — no computation at use time)
    emission_bit: int   = 0             # T_EMISSION output
    emission_path: str  = ""            # "centroid_inversion" | "boundary_parity"
    gluon: int          = 0             # C (always = local_state[1])
    voa_weight: int     = 0             # 0=vacuum, 5=excited
    voa_sector: str     = ""            # "Vacuum" | "Excited"
    state_class: str    = ""            # "symmetric" | "correction" | "chiral"
    correction_fires: bool = False
    is_chiral: bool     = False
    is_vacuum: bool     = False
    is_lie_conj: bool   = False
    hamming_to_c: int   = 0
    anneal_steps: int   = 0
    anneal_final: Tuple[int,int,int] = (0, 0, 0)
    approx_prob: float  = 0.0

    # Sheet geometry
    sheet_width: int    = 2             # 2^(level+1) bits in the sheet at this level
    sheet_start: int    = 0             # first bit index in this sheet window
    sheet_offset: int   = 0            # bit_pos relative to sheet center

    # AGRM spatial position (24D) — precomputed from identity + state
    agrm_position: List[float] = field(default_factory=lambda: [0.0] * 24)
    resonance: str = ""                 # SHA256-derived resonance signature

    # Graph
    ts: float = field(default_factory=time.time)

    # Optional user metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


def make_stax(
    ribbon_id: str,
    bit_pos: int,
    local_state: Tuple[int, int, int],
    level: int = 0,
    metadata: Dict[str, Any] = None,
) -> Stax:
    """
    Core factory: resolve any bit into a C-gluon Stax on its sheet.

    Given a (ribbon_id, bit_pos, L, C, R, level), returns a Stax where:
      - C = local_state[1] acts as the local gluon at sheet resolution `level`
      - All fields are populated from lookup tables (no simulation)
      - AGRM 24D position is derived analytically
    """
    L, C, R = local_state
    # ── T_EMISSION lookup ──────────────────────────────────────────────────────
    em_bit, em_path = _T_EMISSION_TABLE[local_state]
    p = profile(local_state)

    # ── Sheet geometry ─────────────────────────────────────────────────────────
    sw = _SHEET_SIZE_TABLE.get(level, 2 ** (level + 1))
    half = sw // 2
    # The C-gluon at position bit_pos is the center of a window of width sw.
    # The sheet starts at bit_pos - half + 1 (C is the center cell).
    sheet_start = max(0, bit_pos - half + 1)
    sheet_offset = bit_pos - (sheet_start + half - 1)

    # ── AGRM 24D position ──────────────────────────────────────────────────────
    # Encode (ribbon, bit_pos, level, state) into 24D space.
    # Dimensions 0-7:  hash-based ribbon coordinates + bit_pos + level
    ribbon_hash = int(hashlib.sha256(ribbon_id.encode()).hexdigest()[:16], 16)
    pos: List[float] = [0.0] * 24
    for i in range(8):
        pos[i] = ((ribbon_hash >> (i * 8)) & 0xFF) / 255.0
    pos[0] += bit_pos * _STAX_POSITION_SCALE
    pos[1] += level * 0.1
    # Dimensions 8-15:  local state + emission features
    pos[8]  = float(L)
    pos[9]  = float(C)
    pos[10] = float(R)
    pos[11] = float(em_bit)
    pos[12] = float(p["correction_fires"])
    pos[13] = float(p["is_chiral"])
    pos[14] = float(p["is_vacuum"])
    pos[15] = float(p["is_lie_conjugate"])
    # Dimensions 16-23: VOA / anneal / probability
    pos[16] = p["voa_weight"] / 5.0
    pos[17] = p["anneal_steps"] / 3.0
    pos[18] = p["hamming_to_c"] / 2.0
    pos[19] = p["approx_prob"] * 8.0        # scale back to ~1.0 range
    pos[20] = level / 8.0
    pos[21] = (bit_pos % sw) / max(sw, 1)
    pos[22] = float(C) * math.cos(bit_pos * COUPLING)
    pos[23] = float(C) * math.sin(level * COUPLING)

    # ── Resonance signature ────────────────────────────────────────────────────
    resonance = hashlib.sha256(
        f"{ribbon_id}:{bit_pos}:{level}:{local_state}".encode()
    ).hexdigest()[:16]

    # ── Graph ID ───────────────────────────────────────────────────────────────
    graph_id = f"{ribbon_id}:{bit_pos}:{level}"

    return Stax(
        graph_id      = graph_id,
        ribbon_id     = ribbon_id,
        bit_pos       = bit_pos,
        level         = level,
        local_state   = local_state,
        emission_bit  = em_bit,
        emission_path = em_path,
        gluon         = C,
        voa_weight    = p["voa_weight"],
        voa_sector    = p["voa_sector"],
        state_class   = p["state_class"],
        correction_fires = p["correction_fires"],
        is_chiral     = p["is_chiral"],
        is_vacuum     = p["is_vacuum"],
        is_lie_conj   = p["is_lie_conjugate"],
        hamming_to_c  = p["hamming_to_c"],
        anneal_steps  = p["anneal_steps"],
        anneal_final  = p["anneal_final"],
        approx_prob   = p["approx_prob"],
        sheet_width   = sw,
        sheet_start   = sheet_start,
        sheet_offset  = sheet_offset,
        agrm_position = pos,
        resonance     = resonance,
        metadata      = metadata or {},
    )


# ─── StaxGraph ────────────────────────────────────────────────────────────────

class StaxGraph:
    """
    Graph of Stax items. Nodes = Stax items; edges = adjacency relationships.

    "Every sheet on every graph is a Stax item."

    The graph IS the identity layer: given (ribbon_id, bit_pos, level) the
    graph_id deterministically resolves to exactly one Stax node. Edges encode
    which C-gluons are adjacent across ribbons, sheet levels, or bit positions.
    """

    def __init__(self):
        self._nodes: Dict[str, Stax] = {}
        self._edges: Dict[str, Set[str]] = {}
        self._ribbon_index: Dict[str, Set[str]] = {}
        self._level_index: Dict[int, Set[str]] = {}

    def add(self, stax: Stax) -> Stax:
        """Add a Stax node to the graph."""
        gid = stax.graph_id
        self._nodes[gid] = stax
        self._ribbon_index.setdefault(stax.ribbon_id, set()).add(gid)
        self._level_index.setdefault(stax.level, set()).add(gid)
        if gid not in self._edges:
            self._edges[gid] = set()
        return stax

    def connect(self, from_id: str, to_id: str) -> None:
        """Add a directed edge between two Stax nodes."""
        if from_id in self._nodes and to_id in self._nodes:
            self._edges.setdefault(from_id, set()).add(to_id)

    def connect_undirected(self, id_a: str, id_b: str) -> None:
        """Add bidirectional edge."""
        self.connect(id_a, id_b)
        self.connect(id_b, id_a)

    def resolve(self, ribbon_id: str, bit_pos: int, level: int) -> Optional[Stax]:
        """Deterministic lookup: (ribbon, bit_pos, level) → Stax node."""
        return self._nodes.get(f"{ribbon_id}:{bit_pos}:{level}")

    def get(self, graph_id: str) -> Optional[Stax]:
        return self._nodes.get(graph_id)

    def neighbors(self, graph_id: str) -> List[Stax]:
        """Direct successors of a Stax node."""
        return [self._nodes[gid] for gid in self._edges.get(graph_id, set())
                if gid in self._nodes]

    def by_ribbon(self, ribbon_id: str) -> List[Stax]:
        """All Stax nodes on a given ribbon (sorted by bit_pos, then level)."""
        ids = list(self._ribbon_index.get(ribbon_id, set()))
        nodes = [self._nodes[gid] for gid in ids if gid in self._nodes]
        return sorted(nodes, key=lambda s: (s.bit_pos, s.level))

    def by_level(self, level: int) -> List[Stax]:
        """All Stax nodes at a given MDHG resolution level."""
        ids = list(self._level_index.get(level, set()))
        return [self._nodes[gid] for gid in ids if gid in self._nodes]

    def vacuum_nodes(self) -> List[Stax]:
        """Nodes whose local state is a true vacuum (L=C=R)."""
        return [s for s in self._nodes.values() if s.is_vacuum]

    def correction_nodes(self) -> List[Stax]:
        """Nodes where Rule30 correction fires — the 25.3% chiral set."""
        return [s for s in self._nodes.values() if s.correction_fires]

    def wire_ribbon_adjacency(self, ribbon_id: str) -> int:
        """
        Auto-wire consecutive bit positions on a ribbon as adjacent at same level.
        Returns edge count added.
        """
        nodes = self.by_ribbon(ribbon_id)
        count = 0
        level_groups: Dict[int, List[Stax]] = {}
        for n in nodes:
            level_groups.setdefault(n.level, []).append(n)
        for level_nodes in level_groups.values():
            level_nodes.sort(key=lambda s: s.bit_pos)
            for i in range(len(level_nodes) - 1):
                self.connect_undirected(
                    level_nodes[i].graph_id, level_nodes[i+1].graph_id
                )
                count += 2
        return count

    def wire_level_adjacency(self, ribbon_id: str, bit_pos: int) -> int:
        """
        Wire the same (ribbon, bit_pos) across all resolution levels (vertical edges).
        This is the "local=global at resolution R-1" wiring.
        Returns edge count added.
        """
        count = 0
        level_nodes = sorted(
            [s for s in self._nodes.values()
             if s.ribbon_id == ribbon_id and s.bit_pos == bit_pos],
            key=lambda s: s.level
        )
        for i in range(len(level_nodes) - 1):
            self.connect_undirected(
                level_nodes[i].graph_id, level_nodes[i+1].graph_id
            )
            count += 2
        return count

    def stats(self) -> Dict[str, Any]:
        total_edges = sum(len(e) for e in self._edges.values())
        class_counts = {"symmetric": 0, "correction": 0, "chiral": 0}
        for s in self._nodes.values():
            class_counts[s.state_class] = class_counts.get(s.state_class, 0) + 1
        return {
            "node_count":    len(self._nodes),
            "edge_count":    total_edges,
            "ribbon_count":  len(self._ribbon_index),
            "level_count":   len(self._level_index),
            "class_dist":    class_counts,
            "vacuum_count":  sum(1 for s in self._nodes.values() if s.is_vacuum),
        }

    @property
    def node_count(self) -> int:
        return len(self._nodes)
