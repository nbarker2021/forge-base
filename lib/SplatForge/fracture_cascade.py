"""
SplatForge.fracture_cascade — a rendered discontinuity (tear/shear/pinch
between adjacent splats) treated as the start of a fracture cascade,
closed by this corpus's own proven Hamming-centroid annealing
(lattice_forge/centroid_voa.py), not smoothed away.

The 7-fold substitution at a tear site is the 7 non-identity sequences of
the 3 real transpositions centroid_voa.py already defines (swap_LR,
swap_LC, swap_CR) — single application of each (3), every pair (3), and
all three (1) = 7. This module composes those three real functions in the
7 documented sequences; none of the transposition logic is new.

Honesty note, checked directly rather than assumed: CQE-PAPER-010's own
"TrialityState"/"triality_project" code block (cited there as "from
lattice_forge/forge.py and lattice_forge/f4_action.py") does not literally
exist in either real file — neither defines those names. What IS real and
used here instead: centroid_voa.py's three actual transposition functions
and its machine-verified <=3-step closure bound
(verify_hamming_centroid_universality), plus an empirical check (not an
assumption) of which of the 7 paths actually close to a Lie conjugate for
each of the 8 states — confirmed: every state has at least one such path,
but it is NOT always the same path (the full 3-step LR->LC->CR composition
closes for exactly 4 of the 8 states, not all 8 — checked, not assumed).

"Void" path(s) = the substitution(s) that land on a Lie conjugate (a true
fixed point of the chart, L=R) — the slot(s) where the cascade is
guaranteed to terminate. "Glue" paths = the remaining substitutions: valid
correction transformations of the tear site that have not yet reached a
fixed point.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from lattice_forge.centroid_voa import LIE_CONJUGATES, swap_CR, swap_LC, swap_LR

LCRState = Tuple[int, int, int]

_OPS = {"LR": swap_LR, "LC": swap_LC, "CR": swap_CR}

SEVEN_PATHS: Tuple[Tuple[str, ...], ...] = (
    ("LR",), ("LC",), ("CR",),
    ("LR", "LC"), ("LR", "CR"), ("LC", "CR"),
    ("LR", "LC", "CR"),
)


def apply_path(state: LCRState, path: Tuple[str, ...]) -> LCRState:
    """Apply a sequence of the 3 real transpositions in order."""
    for op_name in path:
        state = _OPS[op_name](state)
    return state


def fracture_cascade(state: LCRState) -> Dict[str, Any]:
    """The 7 substitution children of a tear-site state, each tagged
    void (lands on a Lie conjugate — a guaranteed closure slot) or glue
    (does not, yet). Every one of the 8 possible chart states has at
    least one void child — checked across all 8, not assumed for this
    one call."""
    children: List[Dict[str, Any]] = []
    for path in SEVEN_PATHS:
        result = apply_path(state, path)
        children.append({
            "path": path,
            "state": result,
            "is_void": result in LIE_CONJUGATES,
        })
    void_indices = [i for i, c in enumerate(children) if c["is_void"]]
    glue_indices = [i for i in range(7) if i not in void_indices]
    return {
        "source_state": state,
        "children": children,
        "void_indices": void_indices,
        "glue_indices": glue_indices,
        "has_void_slot": len(void_indices) > 0,
    }


def verify_every_state_has_a_void_slot() -> Dict[str, Any]:
    """All 8 chart states have at least one of the 7 substitution paths
    landing on a Lie conjugate — the claim under test, checked
    exhaustively rather than asserted."""
    states = [(l, c, r) for l in (0, 1) for c in (0, 1) for r in (0, 1)]
    per_state = {}
    all_have_void = True
    for s in states:
        cascade = fracture_cascade(s)
        per_state[str(s)] = {
            "void_path_count": len(cascade["void_indices"]),
            "void_paths": [SEVEN_PATHS[i] for i in cascade["void_indices"]],
        }
        all_have_void = all_have_void and cascade["has_void_slot"]
    return {
        "states_checked": len(states),
        "all_states_have_a_void_slot": all_have_void,
        "per_state": per_state,
        "status": "pass" if all_have_void else "fail",
    }


def detect_tear(radii_a: Tuple[float, float, float], radii_b: Tuple[float, float, float],
                 threshold: float = 0.2) -> bool:
    """Two adjacent splats' shape radii (SplatForge.gluon_blob.
    lucas_correction_radii) are a 'tear' site when their relative
    difference on any axis exceeds `threshold` — a real, measurable
    discontinuity in the rendered surface, not a metaphor."""
    for a, b in zip(radii_a, radii_b):
        denom = max(abs(a), abs(b), 1e-9)
        if abs(a - b) / denom > threshold:
            return True
    return False


def repaired_state(state: LCRState) -> LCRState:
    """The single state a tear at `state` repairs to. close_tear's void
    slots can number more than one (e.g. the 2 vacua have all 7 paths
    void), but every void slot for a given source state lands on the
    *same* closes_to state — verified across all 8 states by
    verify_repaired_state_is_well_defined, not assumed here. Returns the
    first void slot's closes_to, which is therefore the only possible
    answer, not an arbitrary pick among several."""
    record = close_tear(state)
    return record["void_slots"][0]["closes_to"]


def verify_repaired_state_is_well_defined() -> Dict[str, Any]:
    """The fact repaired_state relies on, checked exhaustively: for every
    one of the 8 chart states, every void slot agrees on closes_to."""
    states = [(l, c, r) for l in (0, 1) for c in (0, 1) for r in (0, 1)]
    mismatches = []
    for s in states:
        record = close_tear(s)
        targets = {slot["closes_to"] for slot in record["void_slots"]}
        if len(targets) != 1:
            mismatches.append({"state": s, "targets": sorted(targets)})
    return {
        "states_checked": len(states),
        "mismatches": mismatches,
        "status": "pass" if not mismatches else "fail",
    }


def close_tear(state: LCRState) -> Dict[str, Any]:
    """The full tear-closing record for one boundary state: its fracture
    cascade, which slot(s) are void (guaranteed closure), and which are
    glue (the remaining repair routes). This is descriptive evidence
    (what the proven algebra says about this state), not a rendering
    mutation — nothing about the splat's actual shape/color is changed
    by calling this."""
    cascade = fracture_cascade(state)
    return {
        "tear_state": state,
        "void_slots": [
            {"path": cascade["children"][i]["path"], "closes_to": cascade["children"][i]["state"]}
            for i in cascade["void_indices"]
        ],
        "glue_slots": [
            {"path": cascade["children"][i]["path"], "intermediate_state": cascade["children"][i]["state"]}
            for i in cascade["glue_indices"]
        ],
    }
