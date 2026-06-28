"""
SplatForge.weyl_address — preallocates every possible (L,C,R) chart state
an address, combining two real, already-proven pieces (none of them
modified):

  lattice_forge.f4_action.s3_permutation_matrices()   the actual S3 Weyl
                                                        group lookup table:
                                                        6 named 3x3
                                                        permutation
                                                        matrices acting on
                                                        the trace-2
                                                        idempotent basis.
                                                        CQE-paper-010's
                                                        proven n=3 exact
                                                        closure
                                                        (verify_n3_su3_closure_exact,
                                                        decompose_8x8_via_block_action_exact)
                                                        shows trace-1
                                                        closes as an
                                                        IDENTICAL Weyl
                                                        element, so the
                                                        same 6 matrices are
                                                        reused for trace-1's
                                                        basis here too,
                                                        just under its own
                                                        index order.
  SplatForge.gluon_blob.qcd_color_axis                 the proven
                                                        D4/QCD-isomorphic
                                                        3-coloring already
                                                        built this session.

"Every tile in any compiled Crystal Zoo lattice gets an address" reduces
to "every one of the 8 possible chart states gets an address", because
every tile's relevant boundary state IS one of those 8
(SplatForge.gluon_blob.lattice_neighbor_state's whole range) — addressing
the 8 states once, at import time, addresses every tile of every crystal.
The 2 vacua (trace 0 and 3) have no Weyl freedom (S3 fixes them); their
address is the identity element, trivially, not invented.
"""
from __future__ import annotations

from typing import Dict, Tuple

from lattice_forge.f4_action import S3_PERMUTATION_NAMES, s3_permutation_matrices

from .gluon_blob import qcd_color_axis

LCRState = Tuple[int, int, int]

# (1,1,0)=C-, (1,0,1)=C0, (0,1,1)=C+ — f4_action.py's own trace-2 idempotent order.
TRACE2_ORDER: Tuple[LCRState, ...] = ((1, 1, 0), (1, 0, 1), (0, 1, 1))
# (0,0,1)=e3, (0,1,0)=e2, (1,0,0)=e1 — f4_action.py's own trace-1 order.
TRACE1_ORDER: Tuple[LCRState, ...] = ((0, 0, 1), (0, 1, 0), (1, 0, 0))
VACUA: Tuple[LCRState, ...] = ((0, 0, 0), (1, 1, 1))

_S3_MATRICES = s3_permutation_matrices()


def _canonical_weyl_element(target_index: int) -> str:
    """The first (canonical) S3 element, in S3_PERMUTATION_NAMES order,
    whose real permutation matrix maps basis index 0 to `target_index`.
    (The stabilizer of index 0 has order 2, so two elements always map to
    the same target — this picks one deterministically rather than
    reporting an ambiguous pair.)"""
    for name in S3_PERMUTATION_NAMES:
        if _S3_MATRICES[name][target_index][0] == 1.0:
            return name
    raise RuntimeError(f"no Weyl element maps index 0 -> {target_index}; should be impossible")


def weyl_address(state: LCRState) -> Dict[str, object]:
    """One complete address for any of the 8 chart states: its trace
    stratum, the canonical Weyl (S3) element reaching it from that
    stratum's base representative, and the proven QCD color axis."""
    if state in VACUA:
        return {
            "state": state,
            "trace": sum(state),
            "stratum_index": None,
            "weyl_element": "e",
            "qcd_color_axis": qcd_color_axis(state),
            "is_vacuum": True,
        }
    if state in TRACE2_ORDER:
        order, trace = TRACE2_ORDER, 2
    elif state in TRACE1_ORDER:
        order, trace = TRACE1_ORDER, 1
    else:
        raise ValueError(f"not a valid (L,C,R) chart state: {state!r}")
    index = order.index(state)
    return {
        "state": state,
        "trace": trace,
        "stratum_index": index,
        "weyl_element": _canonical_weyl_element(index),
        "qcd_color_axis": qcd_color_axis(state),
        "is_vacuum": False,
    }


def preallocate_all_addresses() -> Dict[LCRState, Dict[str, object]]:
    """Every one of the 8 possible chart states, addressed once. "All 3D
    spaces" in this chart formalism means all 8 boundary states any tile
    in any compiled Crystal Zoo lattice can have."""
    states = [(left, center, right) for left in (0, 1) for center in (0, 1) for right in (0, 1)]
    return {s: weyl_address(s) for s in states}


# Preallocated once, at import time — the whole address table.
ADDRESS_TABLE: Dict[LCRState, Dict[str, object]] = preallocate_all_addresses()


def verify() -> Dict[str, object]:
    """Every state gets exactly one address; the 2 vacua address to the
    identity Weyl element; the 6 non-vacua split 3/3 across trace-1/
    trace-2, each getting a DISTINCT canonical Weyl element within its
    own stratum (the addressing is injective per stratum) — checked
    directly, not assumed from the construction alone."""
    addresses = ADDRESS_TABLE
    errors = []
    if len(addresses) != 8:
        errors.append(f"expected 8 states, got {len(addresses)}")
    for trace, order in ((1, TRACE1_ORDER), (2, TRACE2_ORDER)):
        elements = [addresses[s]["weyl_element"] for s in order]
        if len(set(elements)) != 3:
            errors.append(f"trace-{trace} Weyl elements not distinct: {elements}")
    for v in VACUA:
        if addresses[v]["weyl_element"] != "e":
            errors.append(f"vacuum {v} should address to 'e', got {addresses[v]['weyl_element']}")
    return {
        "states_addressed": len(addresses),
        "errors": errors,
        "status": "pass" if not errors else "fail",
    }


# --- Color ladder: every one of the 8 states gets its own distinguishable
# color, not just the 3 trace-2 (shell-2) states. ---------------------------
#
# Real QCD has 3 colors AND 3 anticolors (an antiquark carries the
# complementary charge that cancels its quark's color back to "colorless").
# Standard color theory's RGB/CMY relationship is the exact same complement
# structure: Cyan=complement of Red, Magenta=complement of Green,
# Yellow=complement of Blue (each color/anticolor pair sums to white, i.e.
# to "colorless" in the additive sense). PRIMARY_COLORS below keeps
# gluon_blob's original, already-rendered trace-2 hues exactly as they
# were (muted, not pure RGB) rather than swapping in pure (255,0,0) etc.,
# so this slice changes the 5 states that were genuinely all one gray and
# nothing else; ANTICOLORS is the exact 255-minus-each-channel complement
# of those same muted hues, so they read as muted cyan/magenta/yellow, not
# textbook-pure ones -- the complement *identity* (each pair sums to
# (255,255,255)) is what's proven-by-construction here, not a claim about
# the specific shade. CQE-paper-010's own proof
# (decompose_8x8_via_block_action_exact) already showed trace-1 closes
# under the IDENTICAL Weyl element as trace-2 -- the same group action, one
# stratum down. Pairing trace-1's stratum_index to trace-2's stratum_index
# (both TRACE1_ORDER and TRACE2_ORDER are fixed lists, so "index i of one"
# to "index i of the other" is a deterministic ordinal convention) and
# assigning trace-1 the RGB-complement of trace-2's color at that same
# index is therefore principled, not arbitrary: it reuses a proven
# structural correspondence (same Weyl element) plus a proven color-theory
# identity (complement), composed for the first time here. What is NOT
# proven: that ordinal index i of TRACE1_ORDER is "the" physically correct
# partner of ordinal index i of TRACE2_ORDER -- no theorem ties the two
# lists' element-by-element order together beyond each list's own fixed
# definition. Named here, same as the canonical-Weyl-element pick above.
#
# The 2 vacua get the achromatic extremes, using the same additive-RGB
# logic already used for the chromatic states: trace 0 = (0,0,0), nothing
# is "on" -> black; trace 3 = (1,1,1), everything is "on" -> white. Black
# and white are themselves a complementary pair (sum to white), so all 4
# trace strata follow one consistent rule: a state's color is the additive
# RGB reading of which axis/axes are "lit", and trace-1's reading is
# inverted (anticolor) relative to trace-2's at the same ordinal position.

# The exact original trace-2 base hues from gluon_blob's first version of
# this palette -- kept unchanged here on purpose, so adding color to the
# other 5 states doesn't also silently change the 3 states that were
# already correctly colored (a visual regression nobody asked for).
PRIMARY_COLORS: Dict[int, Tuple[int, int, int]] = {
    0: (200, 60, 60),
    1: (60, 200, 60),
    2: (60, 60, 200),
}
ANTICOLORS: Dict[int, Tuple[int, int, int]] = {
    axis: tuple(255 - c for c in rgb) for axis, rgb in PRIMARY_COLORS.items()  # type: ignore[misc]
}
VACUUM_COLORS: Dict[LCRState, Tuple[int, int, int]] = {
    (0, 0, 0): (0, 0, 0),
    (1, 1, 1): (255, 255, 255),
}


def full_spectrum_color(state: LCRState) -> Tuple[int, int, int]:
    """Every one of the 8 states gets its own color: trace-2 -> RGB
    primary (the proven QCD color-charge axis), trace-1 -> the exact RGB
    complement at the same ordinal stratum index (the antiquark/anticolor
    reading), vacua -> black/white (the additive "nothing lit"/"everything
    lit" extremes). Replaces the previous behaviour where all 5 non-shell2
    states (3 trace-1 + 2 vacua) collapsed into one identical neutral gray
    -- this is strictly more expressive, not a different palette choice."""
    addr = weyl_address(state)
    if addr["is_vacuum"]:
        return VACUUM_COLORS[state]
    if addr["trace"] == 2:
        return PRIMARY_COLORS[addr["stratum_index"]]
    return ANTICOLORS[addr["stratum_index"]]


def verify_color_ladder() -> Dict[str, object]:
    """Every state gets a distinct color (8 distinct RGB triples for 8
    states -- checked directly, not assumed), and every trace-2/trace-1
    pair at the same ordinal stratum index is an exact RGB complement
    (each channel sums to 255) -- a numeric identity, not a description."""
    colors = {state: full_spectrum_color(state) for state in ADDRESS_TABLE}
    errors = []
    if len(set(colors.values())) != 8:
        errors.append(f"expected 8 distinct colors, got {len(set(colors.values()))}: {colors}")
    for i in range(3):
        c2 = colors[TRACE2_ORDER[i]]
        c1 = colors[TRACE1_ORDER[i]]
        summed = tuple(a + b for a, b in zip(c1, c2))
        if summed != (255, 255, 255):
            errors.append(f"stratum {i}: {c1} + {c2} = {summed}, expected (255,255,255)")
    vac_sum = tuple(a + b for a, b in zip(VACUUM_COLORS[(0, 0, 0)], VACUUM_COLORS[(1, 1, 1)]))
    if vac_sum != (255, 255, 255):
        errors.append(f"vacua not complementary: {vac_sum}")
    return {"colors": colors, "errors": errors, "status": "pass" if not errors else "fail"}
