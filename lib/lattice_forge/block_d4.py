"""
block_d4.py — Regime B substrate: D4 root system as 4-axis decomposition
for 2D Rule 30 patches.

This module provides the algebraic skeleton for *patch-level* compression
of the 2D Rule 30 light cone (the strip of cells whose interaction can
influence the center column over a page_size window). It does NOT and
cannot provide compression of the center column considered in isolation —
that signal is empirically full-entropy (see `block_tower.py`).

Algebra:
  D4 root system: 24 roots in R^4, all permutations of (+/-1, +/-1, 0, 0).
  Sub-blocks d1..d4 partition the 64 hypercube states by which coordinate
  pair carries the active D4 root direction.

Scope (Regime B):
  * The 4-axis decomposition is the natural symmetry group on the 2D
    patches Rule 30 produces; nested-triangle self-similarity lives in
    this group.
  * Three of the four sub-blocks (d1, d2, d3) correspond to the trace-2
    idempotents of J_3(O), which by T_BRIDGE are the chart's zero-weight
    space; the fourth (d4) carries the trace-1 / trace-3 residue.

Building the actual patch codec (assigning a Rule 30 light-cone patch to
a D4 equivalence class, then storing a per-class canonical representative)
is the engineering scope of Open Obligation O1. The structures here are
the *algebraic foundation* for that codec; they are not by themselves a
sub-O(N) extractor.

For ribbon-level (1D center column) I/O, use `block_tower.py` and
`rule30_block_extractor.py` (Regime A).
"""
from __future__ import annotations
from fractions import Fraction
from typing import NamedTuple


# ---------------------------------------------------------------------------
# D4 root system (24 roots in R^4)
# ---------------------------------------------------------------------------

def d4_roots() -> list[tuple[int, int, int, int]]:
    """Return all 24 roots of the D4 root system.

    D4 roots are all (±1, ±1, 0, 0) permutations — 4 choose 2 positions
    times 4 sign combinations = 6 * 4 = 24 roots.
    """
    roots = []
    coords = [0, 1, 2, 3]
    for i in range(4):
        for j in range(i + 1, 4):
            for si in [1, -1]:
                for sj in [1, -1]:
                    v = [0, 0, 0, 0]
                    v[i] = si
                    v[j] = sj
                    roots.append(tuple(v))
    return roots


# ---------------------------------------------------------------------------
# The 4 sub-blocks of the 64-cell D4 block
# ---------------------------------------------------------------------------

# Each sub-block corresponds to one of the 4 coordinate axes of D4.
# Sub-block d_k contains the 16 states where the k-th coordinate pair
# is the "active" pair (the two non-zero entries of the D4 root).

def subblock_states(axis: int) -> list[tuple[int, ...]]:
    """Return the 16 states in sub-block d_{axis+1}.

    The 4 sub-blocks partition the 64 states of {0,1}^6 by which
    pair of coordinates is active. We use a 6-bit encoding:
    bits 0-1: axis 0 pair, bits 2-3: axis 1 pair, bits 4-5: axis 2 pair.

    For the D4 block, we use the natural 4-bit encoding {0,1}^4 = 16 states
    per sub-block, with the sub-block index (0-3) selecting which D4 axis
    is the "primary" axis.
    """
    states = []
    for i in range(16):
        # 4-bit state within the sub-block
        bits = tuple((i >> b) & 1 for b in range(4))
        # Tag with sub-block index
        states.append((axis,) + bits)
    return states


def all_subblocks() -> dict[str, list[tuple[int, ...]]]:
    """Return all 4 sub-blocks as a dict."""
    return {
        f"d{k+1}": subblock_states(k)
        for k in range(4)
    }


# ---------------------------------------------------------------------------
# D4 edges (connections between sub-blocks)
# ---------------------------------------------------------------------------

def d4_edges() -> list[tuple[tuple[int, ...], tuple[int, ...], tuple[int, int, int, int]]]:
    """Return the D4 root edges between sub-block states.

    Each edge connects two states in adjacent sub-blocks, labeled by
    the D4 root that connects them.
    """
    roots = d4_roots()
    edges = []
    blocks = all_subblocks()
    all_states = []
    for states in blocks.values():
        all_states.extend(states)

    # For each root, find the pair of states it connects
    # A root (r0, r1, r2, r3) connects state s to state s + root (mod 2)
    for root in roots:
        for state in all_states:
            axis = state[0]
            bits = state[1:]
            # Apply root as a bit-flip on the 4-bit state
            # Root coordinates map to bit positions 0-3
            new_bits = tuple((bits[i] + abs(root[i])) % 2 for i in range(4))
            # New axis: determined by which root direction is active
            # The root's non-zero entries determine the new sub-block
            nonzero = [i for i in range(4) if root[i] != 0]
            if len(nonzero) == 2:
                new_axis = nonzero[0]  # primary axis of the root
                new_state = (new_axis,) + new_bits
                if new_state != state:
                    edges.append((state, new_state, root))

    return edges


# ---------------------------------------------------------------------------
# The 64-cell D4 transition block
# ---------------------------------------------------------------------------

class D4Block(NamedTuple):
    """The 64-cell D4 base block.

    Attributes:
        states: list of 64 states, each a (axis, b0, b1, b2, b3) tuple
        subblocks: dict mapping 'd1'..'d4' to their 16 states
        edges: list of (state_a, state_b, root) triples
        transition: dict mapping state -> list of reachable states via D4 roots
    """
    states: list[tuple[int, ...]]
    subblocks: dict[str, list[tuple[int, ...]]]
    edges: list[tuple[tuple[int, ...], tuple[int, ...], tuple[int, int, int, int]]]
    transition: dict[tuple[int, ...], list[tuple[int, ...]]]


def build_d4_block() -> D4Block:
    """Build the 64-cell D4 base block."""
    subblocks = all_subblocks()
    states = []
    for sb in subblocks.values():
        states.extend(sb)

    edges = d4_edges()

    transition: dict[tuple[int, ...], list[tuple[int, ...]]] = {s: [] for s in states}
    for src, tgt, _root in edges:
        if src in transition:
            transition[src].append(tgt)

    return D4Block(
        states=states,
        subblocks=subblocks,
        edges=edges,
        transition=transition,
    )


# ---------------------------------------------------------------------------
# Rule 30 chart embedding into D4 block
# ---------------------------------------------------------------------------

# The Rule 30 chart has 8 states: (L, C, R) for L,C,R in {0,1}.
# The shell=2 stratum has 3 states: (1,1,0), (1,0,1), (0,1,1).
# These 3 states embed into the D4 block as the 3 trace-2 idempotents
# of J3(O), which correspond to the 3 non-zero weight spaces of the
# A2 subalgebra of F4.

SHELL2_STATES = [(1, 1, 0), (1, 0, 1), (0, 1, 1)]

# The embedding maps each shell=2 state to a D4 sub-block state.
# The 3 shell=2 states map to the 3 non-zero roots of the A2 subalgebra,
# which live in sub-blocks d1, d2, d3 of the D4 block.

CHART_TO_D4 = {
    (1, 1, 0): (0, 1, 1, 0, 0),  # d1: axis=0, bits=(1,1,0,0)
    (1, 0, 1): (1, 1, 0, 1, 0),  # d2: axis=1, bits=(1,0,1,0)
    (0, 1, 1): (2, 0, 1, 1, 0),  # d3: axis=2, bits=(0,1,1,0)
}

D4_TO_CHART = {v: k for k, v in CHART_TO_D4.items()}


def chart_state_to_d4(lcr: tuple[int, int, int]) -> tuple[int, ...]:
    """Map a Rule 30 chart state (L,C,R) to its D4 block state."""
    return CHART_TO_D4.get(lcr, (3, lcr[0], lcr[1], lcr[2], 0))  # d4 for non-shell2


def d4_state_to_chart(d4_state: tuple[int, ...]) -> tuple[int, int, int] | None:
    """Map a D4 block state back to a Rule 30 chart state, or None."""
    return D4_TO_CHART.get(d4_state)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_d4_block() -> dict:
    """Verify the D4 block structure."""
    block = build_d4_block()
    errors = []

    # Check state count
    if len(block.states) != 64:
        errors.append(f"Expected 64 states, got {len(block.states)}")

    # Check sub-block sizes
    for name, sb in block.subblocks.items():
        if len(sb) != 16:
            errors.append(f"Sub-block {name} has {len(sb)} states, expected 16")

    # Check root count
    roots = d4_roots()
    if len(roots) != 24:
        errors.append(f"Expected 24 D4 roots, got {len(roots)}")

    # Check that chart embedding is consistent
    for lcr, d4 in CHART_TO_D4.items():
        recovered = d4_state_to_chart(d4)
        if recovered != lcr:
            errors.append(f"Chart embedding inconsistent for {lcr}: got {recovered}")

    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "state_count": len(block.states),
        "root_count": len(roots),
        "edge_count": len(block.edges),
        "subblock_sizes": {k: len(v) for k, v in block.subblocks.items()},
    }


if __name__ == "__main__":
    import json
    result = verify_d4_block()
    print(json.dumps(result, indent=2))
