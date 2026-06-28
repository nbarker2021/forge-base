"""
GraphStax — Graph-based identity and tabular lookup engine for ChromaBlend Studio.

Architecture:
  GraphStaxEngine = the wired composite. One instance per context.
  Module-level `engine` singleton for single-context use.

Component layers:
  rule30.py  — Lookup tables: T_EMISSION, Rule30, VOA sectors, state probabilities
  agrm.py    — AGRM router: GR-spiral sweep, zone density, cached routing
  stax.py    — Stax dataclass + StaxGraph: bit-to-C resolution + graph adjacency

Core operation:
  "Turn any single bit on any single ribbon into a C on ITS sheet size."

  GraphStaxEngine.resolve_bit(ribbon_id, bit_pos, L, C, R, level) → Stax
    1. Constructs the local (L,C,R) context for that bit at that level
    2. Applies T_EMISSION via lookup table (O(1), no simulation)
    3. Registers the Stax node in the graph AND the AGRM router
    4. Returns the full Stax with sheet geometry, VOA classification, 24D position

  GraphStaxEngine.route(from_id, to_id) → StaxRoute
    Routes between two Stax nodes via GR-spiral AGRM traversal.

Invariant: every resolved bit has a unique, deterministic identity:
  graph_id = "{ribbon_id}:{bit_pos}:{level}"
  The graph IS the lookup table — no two bits share an identity.

Integration with ChromaForge:
  GraphStaxEngine is designed to be composed INTO ChromaForgeEngine.
  The SNAP stratifier can use `resolve_bit` as a label_fn to seed the
  taxonomy with C-gluon identities at every resolution level.
"""
import math
from typing import Any, Callable, Dict, List, Optional, Tuple

# ─── Re-export all public lookup tables from rule30 ──────────────────────────
from GraphStax.rule30 import (
    _ALL_STATES, _RULE30_TABLE, _T_EMISSION_TABLE, _GLUON_TABLE,
    _VOA_WEIGHT_TABLE, _VOA_SECTOR_TABLE, _STATE_CLASS_TABLE, _STATE_PROB_TABLE,
    _ANNEAL_TABLE, _HAMMING_TO_CENTROID, _STATE_PROFILE,
    TRUE_VACUA, LIE_CONJUGATES, CORRECTION_FIRING_STATES, CHIRAL_DOUBLET,
    SYMMETRIC_STATES, SYMMETRIC_FRACTION, CHIRAL_FRACTION,
    _MDHG_LEVELS, _SHEET_SIZE_TABLE, _SHEET_LEVEL_INDEX,
    t_emission, profile, classify, sheet_size, level_of,
)

# ─── Re-export AGRM types ────────────────────────────────────────────────────
from GraphStax.agrm import (
    AGRMRouter, StaxNode, StaxRoute, SweepResult, ZoneDensity,
    PHI, COUPLING,
)

# ─── Re-export Stax types ────────────────────────────────────────────────────
from GraphStax.stax import (
    Stax, StaxGraph, make_stax,
)

# ─── Re-export PermForge (superperm scheduler + C-enumeration normal form) ────
from GraphStax.permforge import (
    SuperPermScheduler, superperm, coverage_check, coverage_checksum,
    enumeration_request, c_normal_form,
    action_graph_compression, dimensional_split,
    SUPERPERM_N4, SUPERPERM_N5, N5_OCTAD, N5_OCTAD_LAYOUT,
    N5_REVERSAL_ORBIT, N5_REVERSAL_FIXED, N5_REVERSAL_PAIRS,
    N4_PERM_COUNT, N5_PERM_COUNT,
)

# ─── Mathematical constants ───────────────────────────────────────────────────
# PHI and COUPLING already re-exported from agrm.py


# ─── GraphStaxEngine — the wired composite ───────────────────────────────────

class GraphStaxEngine:
    """
    Wired engine: AGRM router + StaxGraph + Rule30 lookup tables.

    Usage:
        engine = GraphStaxEngine()

        # Resolve any bit as a C-gluon on its sheet:
        stax = engine.resolve_bit("ribbon_A", bit_pos=42, L=0, C=1, R=0, level=2)
        print(stax.emission_bit, stax.state_class)   # 1, "correction"

        # Auto-wire a ribbon then route:
        engine.wire_ribbon("ribbon_A")
        route = engine.route("ribbon_A:40:2", "ribbon_A:44:2")

        # Query all correction-firing nodes (the 25.3% chiral set):
        corrections = engine.graph.correction_nodes()
    """

    def __init__(self, dimensions: int = 24):
        self.dimensions = dimensions
        self.graph  = StaxGraph()
        self.router = AGRMRouter(dimensions=dimensions)
        # Supervisor cursor: schedules enumeration requests over n=4 blocks.
        # The cursor produces C — Γ(s) = π_C(enum(r_i, W)).
        self.scheduler = SuperPermScheduler(n=4)

    # ── Core resolution ──────────────────────────────────────────────────────

    def resolve_bit(
        self,
        ribbon_id: str,
        bit_pos: int,
        L: int,
        C: int,
        R: int,
        level: int = 0,
        metadata: Dict[str, Any] = None,
        _reclassify: bool = True,
    ) -> Stax:
        """
        Turn any single bit on any ribbon into a C on its sheet size.

        Given (ribbon_id, bit_pos) and the local (L, C, R) context at that
        position, resolves the Stax item: applies T_EMISSION, classifies the
        state, computes the 24D AGRM position, registers in the graph.

        Returns the Stax immediately from lookup tables — O(1) per bit.
        (_reclassify=False is used internally for bulk ribbon resolution.)
        """
        # Build or retrieve from graph
        existing = self.graph.resolve(ribbon_id, bit_pos, level)
        if existing is not None:
            return existing

        stax = make_stax(ribbon_id, bit_pos, (L, C, R), level, metadata)
        self.graph.add(stax)

        # Register in AGRM router
        self.router.register(
            node_id   = stax.graph_id,
            position  = stax.agrm_position,
            resonance = stax.resonance,
            metadata  = {"ribbon": ribbon_id, "bit_pos": bit_pos,
                         "level": level, "state": (L, C, R)},
            reclassify = _reclassify,
        )
        return stax

    def resolve_ribbon(
        self,
        ribbon_id: str,
        bits: List[int],
        level: int = 0,
        metadata: Dict[str, Any] = None,
    ) -> List[Stax]:
        """
        Resolve an entire ribbon of bits at a given sheet level.

        bits[i] is the value of bit at position i. The local (L,C,R) context
        for position i is (bits[i-1], bits[i], bits[i+1]) with boundary=0.

        Returns the list of Stax nodes (one per bit position) in order.
        """
        results = []
        n = len(bits)
        for i, c_bit in enumerate(bits):
            L = bits[i - 1] if i > 0 else 0
            R = bits[i + 1] if i < n - 1 else 0
            # Bulk path: defer AGRM reclassification to one batch call below
            stax = self.resolve_bit(ribbon_id, i, L, c_bit, R, level, metadata,
                                    _reclassify=False)
            results.append(stax)

        # One reclassification + adjacency wiring after all nodes registered
        self.router.reclassify()
        self.graph.wire_ribbon_adjacency(ribbon_id)
        return results

    def resolve_multilevel(
        self,
        ribbon_id: str,
        bits: List[int],
        levels: Optional[List[int]] = None,
    ) -> Dict[int, List[Stax]]:
        """
        Resolve a ribbon at multiple MDHG resolution levels simultaneously.

        "local at resolution R = global at resolution R-1"
        Produces a vertical stack of Stax graphs, one per level. Vertical
        adjacency edges are wired between same-position nodes across levels.

        Returns {level: [stax_at_position_0, stax_at_position_1, ...]}
        """
        if levels is None:
            levels = list(range(9))    # all MDHG levels by default
        result: Dict[int, List[Stax]] = {}
        for lv in levels:
            result[lv] = self.resolve_ribbon(ribbon_id, bits, level=lv)

        # Wire vertical (level) adjacency for each bit position
        for pos in range(len(bits)):
            self.graph.wire_level_adjacency(ribbon_id, pos)

        return result

    def enumerate_ribbon(
        self,
        ribbon_id: str,
        bits: List[int],
        level: int = 0,
    ) -> Dict[str, Any]:
        """
        Resolve a ribbon under superpermutation supervision.

        The C of each bit is produced by an enumeration request from the n=4
        supervisor cursor — Γ(s) = π_C(enum(r_i, W)). Bits are processed in
        blocks of 4; within each block the cursor string dictates the read
        order, so every one of the 24 possible orderings of the block's slots
        fires exactly once (full coverage, maximally compressed).

        First request for a position creates its Stax (the enumeration act);
        repeat requests are pure lookups — f(f(x)) = f(x) at the identity layer.
        """
        n = len(bits)
        requests = 0
        creations = 0
        resolved: Dict[str, Stax] = {}

        for block_start in range(0, n, 4):
            block = bits[block_start:block_start + 4]
            if len(block) < 4:
                block = block + [0] * (4 - len(block))    # boundary padding
            for cursor, slot in enumerate(superperm(4)):
                requests += 1
                pos = block_start + (int(slot) - 1)
                if pos >= n:
                    continue
                gid = f"{ribbon_id}:{pos}:{level}"
                if gid not in resolved and self.graph.get(gid) is None:
                    creations += 1
                L = bits[pos - 1] if pos > 0 else 0
                R = bits[pos + 1] if pos < n - 1 else 0
                stax = self.resolve_bit(ribbon_id, pos, L, bits[pos], R, level,
                                        _reclassify=False)
                resolved[gid] = stax

        self.router.reclassify()
        self.graph.wire_ribbon_adjacency(ribbon_id)

        return {
            "ribbon_id":     ribbon_id,
            "bits":          n,
            "level":         level,
            "requests":      requests,         # cursor enumeration acts fired
            "creations":     creations,        # first-fire C productions
            "idempotent_hits": requests - creations - sum(
                1 for b in range(0, n, 4)
                for c in superperm(4)
                if b + int(c) - 1 >= n
            ),
            "normal_form":   "Γ(s) = π_C(enum(r_i, W))",
            "stax":          list(resolved.values()),
        }

    # ── Routing ──────────────────────────────────────────────────────────────

    def route(self, from_id: str, to_id: str, max_hops: int = 5) -> Optional[StaxRoute]:
        """Route between two Stax nodes via AGRM GR-spiral traversal."""
        return self.router.route(from_id, to_id, max_hops)

    def route_by_resonance(
        self,
        from_id: str,
        target_resonance: str,
        threshold: float = 0.7,
        max_results: int = 3,
    ) -> List[Tuple[str, StaxRoute]]:
        """Find and route to nodes with matching resonance signature."""
        return self.router.query_resonance(from_id, target_resonance,
                                           threshold, max_results)

    def nearest(self, ribbon_id: str, bit_pos: int, level: int,
                n: int = 5) -> List[Tuple[StaxNode, float]]:
        """Find n nearest AGRM nodes to a given Stax position."""
        gid = f"{ribbon_id}:{bit_pos}:{level}"
        node = self.router.get_node(gid)
        if node is None:
            return []
        return self.router.find_nearest(node.position, n)

    def sweep(self, from_id: str,
              predicate: Optional[Callable[[StaxNode], bool]] = None) -> SweepResult:
        """GR sweep from a registered Stax node."""
        return self.router.sweep_from(from_id, predicate)

    # ── Lookup queries ───────────────────────────────────────────────────────

    def state_profile(self, state: Tuple[int,int,int]) -> Dict:
        """Full lookup-table profile for a local (L,C,R) state."""
        return profile(state)

    def all_profiles(self) -> Dict[Tuple[int,int,int], Dict]:
        """All 8 state profiles (read-only)."""
        return dict(_STATE_PROFILE)

    def correction_nodes(self) -> List[Stax]:
        """All registered Stax nodes where Rule30 correction fires (25.3%)."""
        return self.graph.correction_nodes()

    def vacuum_nodes(self) -> List[Stax]:
        """All registered Stax nodes at TRUE_VACUA states (L=C=R)."""
        return self.graph.vacuum_nodes()

    # ── Convenience wiring ───────────────────────────────────────────────────

    def wire_ribbon(self, ribbon_id: str) -> int:
        """Wire horizontal adjacency for all resolved nodes on a ribbon."""
        return self.graph.wire_ribbon_adjacency(ribbon_id)

    # ── Status ───────────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        return {
            "graph":       self.graph.stats(),
            "router":      self.router.stats(),
            "scheduler":   self.scheduler.status(),
            "dimensions":  self.dimensions,
            "rule30_states": len(_ALL_STATES),
            "vacua":       len(TRUE_VACUA),
            "lie_conjugates": len(LIE_CONJUGATES),
            "correction_firing": len(CORRECTION_FIRING_STATES),
            "symmetric_fraction": SYMMETRIC_FRACTION,
            "chiral_fraction":    CHIRAL_FRACTION,
            "mdhg_levels": list(_MDHG_LEVELS),
            "sheet_sizes": dict(_SHEET_SIZE_TABLE),
        }


# ─── Module-level singleton ────────────────────────────────────────────────────

engine = GraphStaxEngine()


# ─── Module-level convenience forwarding ──────────────────────────────────────

def resolve_bit(ribbon_id: str, bit_pos: int, L: int, C: int, R: int,
                level: int = 0, **kwargs) -> Stax:
    return engine.resolve_bit(ribbon_id, bit_pos, L, C, R, level, **kwargs)

def resolve_ribbon(ribbon_id: str, bits: List[int],
                   level: int = 0, **kwargs) -> List[Stax]:
    return engine.resolve_ribbon(ribbon_id, bits, level, **kwargs)

def status() -> Dict:
    return engine.status()


# ─── Version ──────────────────────────────────────────────────────────────────

__version__ = "0.2.0"

__all__ = [
    # Engine
    "GraphStaxEngine", "engine",
    # PermForge — superperm scheduler + C-enumeration normal form
    "SuperPermScheduler", "superperm", "coverage_check", "coverage_checksum",
    "enumeration_request", "c_normal_form",
    "action_graph_compression", "dimensional_split",
    "SUPERPERM_N4", "SUPERPERM_N5", "N5_OCTAD", "N5_OCTAD_LAYOUT",
    "N5_REVERSAL_ORBIT", "N5_REVERSAL_FIXED", "N5_REVERSAL_PAIRS",
    # Core types
    "Stax", "StaxGraph", "StaxNode", "StaxRoute", "SweepResult", "ZoneDensity",
    # Factories
    "make_stax",
    # Rule30 lookup tables
    "_RULE30_TABLE", "_T_EMISSION_TABLE", "_GLUON_TABLE",
    "_VOA_WEIGHT_TABLE", "_STATE_CLASS_TABLE", "_STATE_PROB_TABLE",
    "_STATE_PROFILE", "_ANNEAL_TABLE", "_SHEET_SIZE_TABLE",
    # Named sets
    "TRUE_VACUA", "LIE_CONJUGATES", "CORRECTION_FIRING_STATES",
    "CHIRAL_DOUBLET", "SYMMETRIC_STATES",
    # Constants
    "PHI", "COUPLING", "SYMMETRIC_FRACTION", "CHIRAL_FRACTION",
    "_MDHG_LEVELS", "_SHEET_LEVEL_INDEX",
    # Pure functions
    "t_emission", "profile", "classify", "sheet_size", "level_of",
    # Convenience
    "resolve_bit", "resolve_ribbon", "status",
    # Router
    "AGRMRouter",
]
