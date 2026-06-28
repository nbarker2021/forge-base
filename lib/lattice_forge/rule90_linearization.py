"""
rule90_linearization.py — The Rule 30 = Rule 90 ⊕ correction decomposition.

Algebraic facts (over GF(2)):
    Rule_30(L, C, R) = L ⊕ (C ∨ R) = L ⊕ C ⊕ R ⊕ (C·R)
    Rule_90(L, C, R) = L ⊕ R                         (no C term, no nonlinear)
    Rule_30 − Rule_90 = C ⊕ (C·R) = C ∧ ¬R

So at the truth-table level:
    Rule_30(L, C, R) = Rule_90(L, R) ⊕ (C ∧ ¬R)

Rule 90 from the single-cell seed has a closed-form solution by Lucas's
theorem on binomial coefficients mod 2:

    Rule_90_cell(d, x) = 1  iff  (d + x) is even  and  k = (d+x)/2
                                  satisfies (k AND d) == k   [no bit borrow]

This makes Rule 90 O(log d) computable — a single bit-AND. The Sierpinski
triangle is Pascal's triangle mod 2, exactly.

The Rule 30 center bit at depth N can therefore be decomposed:

    Rule_30_center(N) = LucasBit(N, 0)
                       ⊕ XOR over (t < N, x in light cone) of
                            LucasBit(N − 1 − t, −x) · corr(t, x)

where corr(t, x) = r30(t, x) AND NOT r30(t, x+1) — the GF(2) correction
that distinguishes Rule 30 from Rule 90 at each cell.

The crucial bridge to the umbrella's existing chart algebra: corr(t, x)
is nonzero precisely when the chart state at (t, x) is in
    {(0, 1, 0), (1, 1, 0)}
which is exactly
    (axis 2, sheet 0) ∪ (axis 3, sheet 1)
in the D_4 antipodal codec from `chart_codec_d4.py`. The correction tape
is thus a single-bit projection of the umbrella's D_4 chart state.

Open computational question (Wolfram Problem 3 in this framing):
    Do the contributing (t, x) pairs cluster into D_4-Weyl-octonionic
    orbits whose XOR-sums collapse to a polylog count of surviving
    orbits? If so, O(log N) extraction follows.
"""
from __future__ import annotations

from typing import Any

from .chart_codec_d4 import ANTIPODAL_LABEL, SHEET_SIGN


# ---------------------------------------------------------------------------
# Linearization identity at the truth-table level
# ---------------------------------------------------------------------------

def correction(L: int, C: int, R: int) -> int:
    """The GF(2) correction: Rule_30 − Rule_90 = C AND NOT R."""
    return C & (1 - R)


def linearization_identity_holds() -> bool:
    """Rule_30(L,C,R) = Rule_90(L,R) XOR correction(L,C,R)?"""
    for L in (0, 1):
        for C in (0, 1):
            for R in (0, 1):
                r30 = L ^ (C | R)
                r90 = L ^ R
                if r30 != r90 ^ correction(L, C, R):
                    return False
    return True


# ---------------------------------------------------------------------------
# Lucas closed-form for Rule 90 from a single-cell seed
# ---------------------------------------------------------------------------

def lucas_bit(d: int, x: int) -> int:
    """Rule_90_cell(d, x) from the single-cell seed at the origin.

    Closed-form via Lucas: returns 1 iff (d+x) is even and
    k = (d+x)/2 satisfies (k AND d) == k (k is a bit-subset of d).
    """
    if d < 0:
        return 0
    s = d + x
    if s & 1:
        return 0
    k = s >> 1
    if k < 0 or k > d:
        return 0
    return 1 if (k & d) == k else 0


# ---------------------------------------------------------------------------
# D_4-codec projection of the correction tape
# ---------------------------------------------------------------------------

# The correction tape at the center column is nonzero iff the chart state is
# in {(0, 1, 0), (1, 1, 0)} — i.e. (axis 2, sheet 0) OR (axis 3, sheet 1).
CORRECTION_FIRING_AXES_SHEETS: frozenset = frozenset({(2, 0), (3, 1)})


def correction_from_chart(state: tuple[int, int, int]) -> int:
    """corr at center = C AND NOT R, expressed via the D_4 codec."""
    key = (ANTIPODAL_LABEL[state], SHEET_SIGN[state])
    return 1 if key in CORRECTION_FIRING_AXES_SHEETS else 0


# ---------------------------------------------------------------------------
# Reconstruct Rule 30 at depth N via the decomposition
# ---------------------------------------------------------------------------

def _rule30_full_grid(depth: int) -> tuple[list[list[int]], int]:
    """Run Rule 30 from a single-cell seed for `depth` steps. Returns
    the full 2D grid rows[0..depth-1] and the center index."""
    width = 2 * depth + 3
    center = width // 2
    row = [0] * width
    row[center] = 1
    grid: list[list[int]] = []
    for _ in range(depth):
        grid.append(list(row))
        nr = [0] * width
        prev_l = 0
        for i in range(width):
            c = row[i]
            r = row[i + 1] if i + 1 < width else 0
            nr[i] = prev_l ^ (c | r)
            prev_l = c
        row = nr
    grid.append(row)  # row at depth = depth (for completeness)
    return grid, center


def rule30_center_via_decomposition(N: int) -> dict[str, Any]:
    """Compute the Rule 30 center bit at depth N via:

        center(N) = LucasBit(N, 0)
                  XOR  XOR over (t<N, x) of LucasBit(N-1-t, -x) · corr(t, x)

    Returns the bit, the base term, the number of contributing (t,x),
    and the Lucas-sparse count for diagnostic comparison.
    """
    if N < 1:
        raise ValueError("N must be >= 1")
    grid, center = _rule30_full_grid(N)
    width = len(grid[0])

    base = lucas_bit(N, 0)
    acc = base
    contributions = 0
    lucas_nonzero = 0
    for t in range(N):
        for x_off in range(-(t + 1), t + 2):
            idx = center + x_off
            if 0 <= idx < width - 1:
                g = lucas_bit(N - 1 - t, -x_off)
                if g:
                    lucas_nonzero += 1
                    c_val = grid[t][idx] & (1 - grid[t][idx + 1])
                    if c_val:
                        acc ^= 1
                        contributions += 1
    return {
        "bit": acc,
        "base_lucas": base,
        "contributing_terms": contributions,
        "lucas_nonzero_cells": lucas_nonzero,
        "direct_simulated_bit": grid[N][center],
        "match": acc == grid[N][center],
        "N": N,
    }


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_rule90_linearization(depths: list[int] | None = None) -> dict[str, Any]:
    """Verify (a) the truth-table identity, (b) Lucas vs direct Rule 90,
    (c) the Rule 30 center decomposition at a list of depths."""
    if depths is None:
        depths = [1, 2, 3, 5, 8, 16, 32, 64, 128, 256, 512, 1024]

    identity_ok = linearization_identity_holds()

    # Lucas vs direct Rule 90: full row at depth 64
    direct_match = True
    d = 64
    width = 2 * d + 3
    cidx = width // 2
    row = [0] * width
    row[cidx] = 1
    for _ in range(d):
        nr = [0] * width
        for i in range(width):
            l = row[i - 1] if i > 0 else 0
            r = row[i + 1] if i + 1 < width else 0
            nr[i] = l ^ r
        row = nr
    for x in range(-d, d + 1):
        if row[cidx + x] != lucas_bit(d, x):
            direct_match = False
            break

    # Decomposition at each requested depth
    decomp_results = []
    decomp_match = True
    for N in depths:
        r = rule30_center_via_decomposition(N)
        if not r["match"]:
            decomp_match = False
        decomp_results.append({
            "N": N,
            "bit": r["bit"],
            "match": r["match"],
            "contributing_terms": r["contributing_terms"],
            "lucas_nonzero_cells": r["lucas_nonzero_cells"],
        })

    return {
        "status": "pass" if identity_ok and direct_match and decomp_match else "fail",
        "identity_at_truth_table": identity_ok,
        "lucas_matches_direct_rule90_at_depth_64": direct_match,
        "decomposition_matches_at_all_depths": decomp_match,
        "depths_tested": depths,
        "decomposition_results": decomp_results,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify_rule90_linearization(), indent=2))
