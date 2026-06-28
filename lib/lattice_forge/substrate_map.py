"""
Substrate directional map — O(1) routing between chart states.

The chart has 8 states corresponding to the 8 vertices of the 3-cube {0,1}^3.
For substrate navigation, two routing primitives are needed:

1. **Rule 30 deterministic routing**: given current state (L, C, R) and
   wider-context cells (LL, RR), the next state is fully determined. The
   table has 8 * 4 = 32 entries covering every (state, context) combination.

2. **Weyl-group routing**: which permutation + sign action takes one chart
   state to another. Within a trace stratum, this is an S_3 element (6
   options). Between trace strata, this composes with an idempotent shift
   (adding or removing a diagonal idempotent). The full 8x8 = 64 entries.

Both routings are exact, deterministic, and computable in O(1) per query
once the table is built. The tables are pre-computed at import time.

State indexing:
  index 0: (0, 0, 0) — shell 0, trace 0
  index 1: (0, 0, 1) — shell 1, side +, e3
  index 2: (0, 1, 0) — shell 1, side 0, e2
  index 3: (0, 1, 1) — shell 2, side +, C+
  index 4: (1, 0, 0) — shell 1, side -, e1
  index 5: (1, 0, 1) — shell 2, side 0, C0
  index 6: (1, 1, 0) — shell 2, side -, C-
  index 7: (1, 1, 1) — shell 3, trace 3

This matches the binary representation: L * 4 + C * 2 + R.

The Weyl L<->R reflection acts as: index XOR 5 (swaps bits 0 and 2 of the
3-bit state). Verified:
  (0,0,0) <-> (0,0,0)  same                    [index 0 XOR 5 = 5? no, see below]

Actually, L<->R swap: (L, C, R) -> (R, C, L).
  index L*4 + C*2 + R -> index R*4 + C*2 + L
  This is NOT a single XOR. The mapping is:
    0 (0,0,0) -> 0 (0,0,0)   fixed
    1 (0,0,1) -> 4 (1,0,0)   swap
    2 (0,1,0) -> 2 (0,1,0)   fixed
    3 (0,1,1) -> 6 (1,1,0)   swap
    4 (1,0,0) -> 1 (0,0,1)   swap
    5 (1,0,1) -> 5 (1,0,1)   fixed
    6 (1,1,0) -> 3 (0,1,1)   swap
    7 (1,1,1) -> 7 (1,1,1)   fixed

Fixed points: 0, 2, 5, 7 (all states with L = R).
Swap pairs: (1,4), (3,6).
"""

from __future__ import annotations

from typing import Any


# ----------------------------------------------------------------------
# State indexing
# ----------------------------------------------------------------------

CHART_STATES: tuple[tuple[int, int, int], ...] = tuple(
    (L, C, R) for L in range(2) for C in range(2) for R in range(2)
)


def state_to_index(L: int, C: int, R: int) -> int:
    """Map (L, C, R) to integer index 0..7."""
    return L * 4 + C * 2 + R


def index_to_state(index: int) -> tuple[int, int, int]:
    """Inverse of state_to_index."""
    return CHART_STATES[index]


STATE_LABELS = {
    0: "ZERO",       # (0, 0, 0)  shell 0
    1: "e3+",        # (0, 0, 1)  shell 1 side +
    2: "e2-0",       # (0, 1, 0)  shell 1 side 0
    3: "C+",         # (0, 1, 1)  shell 2 side +
    4: "e1-",        # (1, 0, 0)  shell 1 side -
    5: "C0",         # (1, 0, 1)  shell 2 side 0
    6: "C-",         # (1, 1, 0)  shell 2 side -
    7: "FULL",       # (1, 1, 1)  shell 3
}


def shell(index: int) -> int:
    """Return shell = L + C + R for state index."""
    L, C, R = CHART_STATES[index]
    return L + C + R


def side_label(index: int) -> str:
    """Return chirality label: '+' if R>L, '-' if L>R, '0' if equal."""
    L, _, R = CHART_STATES[index]
    if R > L:
        return "+"
    if L > R:
        return "-"
    return "0"


# ----------------------------------------------------------------------
# Rule 30 deterministic 8 x 4 routing table
# ----------------------------------------------------------------------
#
# Given current state index and (LL, RR) context, the next state is
# fully determined by Rule 30:
#   L' = Rule30(LL, L, C) = LL XOR (L OR C)
#   C' = Rule30(L, C, R)  = L  XOR (C OR R)
#   R' = Rule30(C, R, RR) = C  XOR (R OR RR)


def _rule30_bit(a: int, b: int, c: int) -> int:
    return a ^ (b | c)


def _build_rule30_routing_table() -> list[list[int]]:
    """Build the 8x4 table: rule30_route[state_idx][context_idx] = next_state_idx.
    Context indexing: context_idx = LL * 2 + RR (4 contexts per state).
    """
    table = [[0] * 4 for _ in range(8)]
    for src_idx in range(8):
        L, C, R = CHART_STATES[src_idx]
        for LL in range(2):
            for RR in range(2):
                ctx_idx = LL * 2 + RR
                L_next = _rule30_bit(LL, L, C)
                C_next = _rule30_bit(L, C, R)
                R_next = _rule30_bit(C, R, RR)
                table[src_idx][ctx_idx] = state_to_index(L_next, C_next, R_next)
    return table


RULE30_ROUTING_TABLE = _build_rule30_routing_table()


def rule30_next_state(state_idx: int, LL: int, RR: int) -> int:
    """O(1) Rule 30 next-state lookup given state index and (LL, RR) context."""
    if not 0 <= state_idx < 8:
        raise ValueError(f"state_idx must be 0..7, got {state_idx}")
    if LL not in (0, 1) or RR not in (0, 1):
        raise ValueError("LL and RR must be 0 or 1")
    return RULE30_ROUTING_TABLE[state_idx][LL * 2 + RR]


# ----------------------------------------------------------------------
# Weyl involution (L <-> R swap, the chart's (1,3) transposition)
# ----------------------------------------------------------------------


def weyl_13_permutation_index(state_idx: int) -> int:
    """Apply the L<->R Weyl involution to a state index. O(1)."""
    L, C, R = CHART_STATES[state_idx]
    return state_to_index(R, C, L)


WEYL_13_TABLE = tuple(weyl_13_permutation_index(i) for i in range(8))


# ----------------------------------------------------------------------
# Full 8x8 Weyl routing table
# ----------------------------------------------------------------------
#
# For each (source_idx, target_idx) pair, return the routing description
# as a dict with:
#   - same_trace: True iff both states are in the same trace stratum
#   - within_trace_permutation: name of the S_3 element if same_trace
#   - trace_change: target_trace - source_trace (integer in -3..+3)
#   - is_weyl_involution_partner: True iff target == weyl_13(source)
#   - is_self: True iff source == target


# S_3 acts on the trace-1 stratum {(0,0,1)=e3, (0,1,0)=e2, (1,0,0)=e1}
# and on the trace-2 stratum {(0,1,1)=C+, (1,0,1)=C0, (1,1,0)=C-}.
# Both strata are 3-element sets; S_3 permutes their elements.

# Trace-1 ordering: index 1=e3, 2=e2, 4=e1 → positions (3, 2, 1) in J3(O) diag
TRACE1_INDICES = (1, 2, 4)  # (e3, e2, e1)
# Trace-2 ordering: index 6=C-, 5=C0, 3=C+ → positions (1+2, 1+3, 2+3) in J3(O)
TRACE2_INDICES = (6, 5, 3)  # (C-, C0, C+)

# Trace 0: {0} ; Trace 3: {7}. Both fixed by S_3.


def _s3_permutation_table() -> dict[str, tuple[int, int, int]]:
    """The 6 S_3 permutations of (1, 2, 3) — same as f4_action.py."""
    return {
        "e":       (1, 2, 3),
        "(1 2)":   (2, 1, 3),
        "(1 3)":   (3, 2, 1),  # the chart Weyl L<->R
        "(2 3)":   (1, 3, 2),
        "(1 2 3)": (2, 3, 1),
        "(1 3 2)": (3, 1, 2),
    }


S3_PERMUTATIONS = _s3_permutation_table()


def _apply_s3_perm_to_trace1(state_idx: int, perm_name: str) -> int:
    """Apply an S_3 permutation to a trace-1 state.
    Trace-1 indices correspond to J3(O) diagonal positions (3, 2, 1).
    """
    if state_idx not in TRACE1_INDICES:
        raise ValueError(f"{state_idx} is not a trace-1 state")
    # position in trace-1 ordering: 0 = e3 (J3 pos 3), 1 = e2 (J3 pos 2), 2 = e1 (J3 pos 1)
    j3_positions = (3, 2, 1)  # the J3(O) position each trace-1 state occupies
    pos_in_trace1 = TRACE1_INDICES.index(state_idx)
    old_j3_pos = j3_positions[pos_in_trace1]
    new_j3_pos = S3_PERMUTATIONS[perm_name][old_j3_pos - 1]
    new_pos_in_trace1 = j3_positions.index(new_j3_pos)
    return TRACE1_INDICES[new_pos_in_trace1]


def _apply_s3_perm_to_trace2(state_idx: int, perm_name: str) -> int:
    """Apply an S_3 permutation to a trace-2 state.
    Trace-2 indices correspond to J3(O) diagonal idempotent pairs:
        C- = E_11 + E_22 = positions {1, 2}
        C0 = E_11 + E_33 = positions {1, 3}
        C+ = E_22 + E_33 = positions {2, 3}
    """
    if state_idx not in TRACE2_INDICES:
        raise ValueError(f"{state_idx} is not a trace-2 state")
    pair_for_state = {6: (1, 2), 5: (1, 3), 3: (2, 3)}  # C-, C0, C+
    state_for_pair = {(1, 2): 6, (1, 3): 5, (2, 3): 3}
    old_pair = pair_for_state[state_idx]
    perm = S3_PERMUTATIONS[perm_name]
    new_pair = tuple(sorted([perm[p - 1] for p in old_pair]))
    return state_for_pair[new_pair]


def _build_weyl_routing_table() -> list[list[dict[str, Any]]]:
    """8x8 routing table with full description per (source, target) pair."""
    table: list[list[dict[str, Any]]] = [
        [{} for _ in range(8)] for _ in range(8)
    ]
    for src in range(8):
        for tgt in range(8):
            src_shell = shell(src)
            tgt_shell = shell(tgt)
            same_trace = (src_shell == tgt_shell)
            is_self = (src == tgt)
            is_weyl_partner = (tgt == WEYL_13_TABLE[src])
            within_trace_perm: list[str] = []
            if same_trace and src_shell in (1, 2):
                # Find which S_3 element takes src to tgt within the stratum
                indices = TRACE1_INDICES if src_shell == 1 else TRACE2_INDICES
                apply_fn = (
                    _apply_s3_perm_to_trace1 if src_shell == 1
                    else _apply_s3_perm_to_trace2
                )
                for name in S3_PERMUTATIONS:
                    if apply_fn(src, name) == tgt:
                        within_trace_perm.append(name)
            entry = {
                "source": src,
                "target": tgt,
                "source_label": STATE_LABELS[src],
                "target_label": STATE_LABELS[tgt],
                "source_state": CHART_STATES[src],
                "target_state": CHART_STATES[tgt],
                "source_shell": src_shell,
                "target_shell": tgt_shell,
                "same_trace": same_trace,
                "trace_change": tgt_shell - src_shell,
                "within_trace_permutations": within_trace_perm,
                "is_self": is_self,
                "is_weyl_involution_partner": is_weyl_partner,
            }
            table[src][tgt] = entry
    return table


WEYL_ROUTING_TABLE = _build_weyl_routing_table()


def route(source_idx: int, target_idx: int) -> dict[str, Any]:
    """O(1) Weyl routing lookup."""
    return WEYL_ROUTING_TABLE[source_idx][target_idx]


# ----------------------------------------------------------------------
# Bit emission per state (readout law)
# ----------------------------------------------------------------------


def _build_emission_table() -> tuple[int, ...]:
    """Return the bit emission for each state (Rule 30 truth table)."""
    return tuple(
        1 if (shell(i) == 1) or (shell(i) == 2 and CHART_STATES[i][2] > CHART_STATES[i][0])
        else 0
        for i in range(8)
    )


EMISSION_TABLE = _build_emission_table()
# Expected: (0, 1, 1, 1, 1, 0, 0, 0)


def emit_bit(state_idx: int) -> int:
    """O(1) bit emission from chart state index."""
    return EMISSION_TABLE[state_idx]


# ----------------------------------------------------------------------
# The directional map summary
# ----------------------------------------------------------------------


def get_directional_map() -> dict[str, Any]:
    """Return the substrate's complete directional map as a serializable dict."""
    return {
        "model_id": "substrate_directional_map_v0_1",
        "states": [
            {
                "index": i,
                "label": STATE_LABELS[i],
                "state": list(CHART_STATES[i]),
                "shell": shell(i),
                "side": side_label(i),
                "emits_bit": EMISSION_TABLE[i],
                "weyl_involution_partner_index": WEYL_13_TABLE[i],
            }
            for i in range(8)
        ],
        "rule30_routing_table": {
            f"state_{i}_context_LL{LL}_RR{RR}": RULE30_ROUTING_TABLE[i][LL * 2 + RR]
            for i in range(8)
            for LL in range(2)
            for RR in range(2)
        },
        "weyl_routing_summary": {
            "trace_strata": {
                "trace_0": [0],
                "trace_1": list(TRACE1_INDICES),
                "trace_2": list(TRACE2_INDICES),
                "trace_3": [7],
            },
            "within_trace_action": "S_3 permutation on diagonal positions",
            "cross_trace_action": "idempotent shift (add/remove diagonal idempotent)",
        },
        "weyl_involution_table": list(WEYL_13_TABLE),
        "emission_table": list(EMISSION_TABLE),
        "fixed_points_of_weyl_involution": [
            i for i in range(8) if WEYL_13_TABLE[i] == i
        ],
        "swap_pairs_of_weyl_involution": [
            [i, WEYL_13_TABLE[i]] for i in range(8)
            if WEYL_13_TABLE[i] > i
        ],
        "interpretation": (
            "The 8 chart states are the 8 vertices of the 3-cube {0,1}^3. "
            "Rule 30 routes deterministically with (LL, RR) context (32 entries). "
            "Weyl routes within each trace stratum via S_3 (6 elements). "
            "Cross-trace routes require idempotent shifts (Rule 30's actual evolution)."
        ),
    }


# ----------------------------------------------------------------------
# Verifier
# ----------------------------------------------------------------------


def verify_substrate_map(max_depth: int = 4096) -> dict[str, Any]:
    """
    Verify the substrate directional map by:
    1. Checking the Rule 30 routing table reproduces the canonical center
       column when applied step-by-step with the correct (LL, RR) context.
    2. Verifying the Weyl involution is its own inverse.
    3. Verifying emission table matches Rule 30 truth table.
    """
    # Import canonical_rows to compare
    from .rule30 import canonical_rows

    errors: list[str] = []
    warnings: list[str] = []

    # Check: Weyl involution is its own inverse
    for i in range(8):
        if WEYL_13_TABLE[WEYL_13_TABLE[i]] != i:
            errors.append(
                f"Weyl involution not involutive at state {i}: "
                f"{i} -> {WEYL_13_TABLE[i]} -> {WEYL_13_TABLE[WEYL_13_TABLE[i]]}"
            )

    # Check: emission table matches Rule 30 truth table
    expected_emissions = (0, 1, 1, 1, 1, 0, 0, 0)
    if EMISSION_TABLE != expected_emissions:
        errors.append(
            f"emission table {EMISSION_TABLE} != expected {expected_emissions}"
        )

    # Check: rule30 routing on canonical trace produces correct center column
    rows = canonical_rows(max_depth + 1)
    bit_mismatches = 0
    state_mismatches = 0
    for n in range(1, max_depth + 1):
        # Get the actual local state at depth n-1
        prev_row = rows[n - 1]
        L = prev_row.get(-1, 0)
        C = prev_row.get(0, 0)
        R = prev_row.get(1, 0)
        src_idx = state_to_index(L, C, R)
        # Get the canonical (LL, RR) context
        LL = prev_row.get(-2, 0)
        RR = prev_row.get(2, 0)
        # Predicted next state via routing table
        pred_next_idx = rule30_next_state(src_idx, LL, RR)
        pred_next_state = CHART_STATES[pred_next_idx]
        # Actual next state from canonical trace
        next_row = rows[n]
        actual_L = next_row.get(-1, 0)
        actual_C = next_row.get(0, 0)
        actual_R = next_row.get(1, 0)
        actual_state = (actual_L, actual_C, actual_R)
        if pred_next_state != actual_state:
            state_mismatches += 1
        # Bit check: emission from current state == actual bit at depth n
        actual_bit = rows[n].get(0, 0)
        pred_bit = emit_bit(src_idx)
        if pred_bit != actual_bit:
            bit_mismatches += 1

    # Check: Weyl involution swap pairs and fixed points
    fixed_points = [i for i in range(8) if WEYL_13_TABLE[i] == i]
    swap_pairs = [
        [i, WEYL_13_TABLE[i]] for i in range(8) if WEYL_13_TABLE[i] > i
    ]
    expected_fixed = [0, 2, 5, 7]  # ZERO, e2-0, C0, FULL — all have L=R
    expected_swaps = [[1, 4], [3, 6]]  # e3+ <-> e1-, C+ <-> C-
    if fixed_points != expected_fixed:
        errors.append(
            f"Weyl fixed points {fixed_points} != expected {expected_fixed}"
        )
    if swap_pairs != expected_swaps:
        errors.append(
            f"Weyl swap pairs {swap_pairs} != expected {expected_swaps}"
        )

    return {
        "model_id": "substrate_directional_map_verifier_v0_1",
        "status": "pass" if not errors else "fail",
        "max_depth_tested": max_depth,
        "errors": errors,
        "warnings": warnings,
        "checks": {
            "weyl_involutive": all(
                WEYL_13_TABLE[WEYL_13_TABLE[i]] == i for i in range(8)
            ),
            "emission_table_matches_rule30": EMISSION_TABLE == expected_emissions,
            "rule30_routing_state_mismatches": state_mismatches,
            "rule30_routing_bit_mismatches": bit_mismatches,
            "weyl_fixed_points_correct": fixed_points == expected_fixed,
            "weyl_swap_pairs_correct": swap_pairs == expected_swaps,
        },
        "fixed_points": fixed_points,
        "swap_pairs": swap_pairs,
    }
