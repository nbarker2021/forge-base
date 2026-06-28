"""
rule30_decomposition.py — Self-contained implementation of the Rule 30 =
Rule 90 (+) correction decomposition from PAPER.md.

This module is dependency-free (Python standard library only) and
contains:

    * Truth-table linearization identity (Theorem 2.1)
    * Lucas closed-form for Rule 90 (Theorem 3.1)
    * Rule 30 center via decomposition (Theorem 4.1)
    * Correction-tape chart projection (Theorem 5.1, Corollary 5.2)
    * Direct Rule 30 / Rule 90 simulation (reference implementations)

Used by `scripts/reproduce_paper.py` and `tests/test_paper_claims.py`.
"""
from __future__ import annotations

from typing import Iterable


# ---------------------------------------------------------------------------
# Truth-table primitives
# ---------------------------------------------------------------------------

def rule30(L: int, C: int, R: int) -> int:
    """Rule 30: L XOR (C OR R)."""
    return L ^ (C | R)


def rule90(L: int, C: int, R: int) -> int:
    """Rule 90: L XOR R (no C term)."""
    return L ^ R


def correction(L: int, C: int, R: int) -> int:
    """The correction term: Rule 30 minus Rule 90 over GF(2) equals
    C AND NOT R."""
    return C & (1 - R)


def linearization_identity_holds() -> bool:
    """Theorem 2.1: verify Rule_30 = Rule_90 XOR (C AND NOT R) on all
    eight inputs."""
    for L in (0, 1):
        for C in (0, 1):
            for R in (0, 1):
                if rule30(L, C, R) != rule90(L, C, R) ^ correction(L, C, R):
                    return False
    return True


# ---------------------------------------------------------------------------
# Lucas closed-form for Rule 90 from single-cell seed (Theorem 3.1)
# ---------------------------------------------------------------------------

def lucas_bit(d: int, x: int) -> int:
    """Rule 90 cell at depth d, offset x from the seed: 1 iff (d+x) is
    even and k = (d+x)/2 satisfies (k & d) == k by Lucas's theorem.

    Computable in O(log d) bit operations.
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
# Direct (reference) simulators
# ---------------------------------------------------------------------------

def _direct_step(row: list[int], local: callable) -> list[int]:
    """One step of any local rule on a finite row with implicit-zero
    boundary."""
    w = len(row)
    new = [0] * w
    prev_l = 0
    for i in range(w):
        c = row[i]
        r = row[i + 1] if i + 1 < w else 0
        new[i] = local(prev_l, c, r)
        prev_l = c
    return new


def rule30_full_grid(depth: int) -> tuple[list[list[int]], int]:
    """Run Rule 30 from a single-cell seed. Returns (grid, center_index)
    where grid[t] is the row at depth t, depth = 0..depth."""
    width = 2 * depth + 3
    center = width // 2
    row = [0] * width
    row[center] = 1
    grid = [list(row)]
    for _ in range(depth):
        row = _direct_step(row, rule30)
        grid.append(list(row))
    return grid, center


def rule90_full_grid(depth: int) -> tuple[list[list[int]], int]:
    """Reference Rule 90 simulator from single-cell seed."""
    width = 2 * depth + 3
    center = width // 2
    row = [0] * width
    row[center] = 1
    grid = [list(row)]
    for _ in range(depth):
        row = _direct_step(row, rule90)
        grid.append(list(row))
    return grid, center


def rule30_center_column(depth: int) -> list[int]:
    """Center bit at depths 1..depth from the single-cell seed."""
    grid, center = rule30_full_grid(depth)
    return [grid[t][center] for t in range(1, depth + 1)]


# ---------------------------------------------------------------------------
# Theorem 4.1: Rule 30 center via decomposition
# ---------------------------------------------------------------------------

def rule30_center_via_decomposition(N: int) -> dict:
    """Compute r30(N, 0) via the decomposition

        r30(N, 0) = L_N(0) XOR XOR_{(t,x)} L_{N-1-t}(-x) * corr(t, x)

    Returns the decomposed bit, the direct bit, and diagnostic counts.
    """
    if N < 1:
        raise ValueError("N must be >= 1")
    grid, center = rule30_full_grid(N)
    width = len(grid[0])

    base = lucas_bit(N, 0)
    acc = base
    contributing = 0
    lucas_nonzero_cells = 0

    for t in range(N):
        # Only iterate the past light cone of (N, 0): |x| <= min(t+1, N-1-t)
        x_lo = max(-(t + 1), -(N - 1 - t))
        x_hi = min(t + 1, N - 1 - t)
        for x_off in range(x_lo, x_hi + 1):
            idx = center + x_off
            if 0 <= idx < width - 1:
                g = lucas_bit(N - 1 - t, -x_off)
                if g:
                    lucas_nonzero_cells += 1
                    c_val = grid[t][idx] & (1 - grid[t][idx + 1])
                    if c_val:
                        acc ^= 1
                        contributing += 1

    direct = grid[N][center]
    return {
        "N": N,
        "decomposed_bit": acc,
        "direct_bit": direct,
        "match": acc == direct,
        "base_lucas_bit": base,
        "lucas_nonzero_cells": lucas_nonzero_cells,
        "contributing_cells": contributing,
    }


# ---------------------------------------------------------------------------
# Theorem 5.1, Corollary 5.2: correction chart-projection
# ---------------------------------------------------------------------------

CHART_STATES = tuple(
    (a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)
)

CORRECTION_FIRING_CHART_STATES = frozenset({(0, 1, 0), (1, 1, 0)})


def correction_from_chart(state: tuple[int, int, int]) -> int:
    """corr at center = C AND NOT R, expressed via chart-state membership.

    Theorem 5.1 / Corollary 5.2: the firing set is exactly
    {(0,1,0), (1,1,0)}.
    """
    return 1 if state in CORRECTION_FIRING_CHART_STATES else 0


def correction_firing_set_matches_truth_table() -> bool:
    """Verify the chart-projection theorem: corr(L,C,R) = 1 iff
    (L,C,R) in {(0,1,0), (1,1,0)}."""
    for s in CHART_STATES:
        if correction(*s) != correction_from_chart(s):
            return False
    return True


# ---------------------------------------------------------------------------
# Module-level verification surface
# ---------------------------------------------------------------------------

def verify_all_theorems(decomposition_depths: Iterable[int] = None) -> dict:
    """Run every theorem-level check and return a structured result."""
    if decomposition_depths is None:
        decomposition_depths = [1, 2, 3, 5, 8, 16, 32, 64, 128, 256, 512, 1024]

    # Theorem 2.1
    t21 = linearization_identity_holds()

    # Theorem 3.1 — Lucas vs direct Rule 90 at depth 64, all positions
    t31 = True
    d = 64
    grid90, c90 = rule90_full_grid(d)
    for x in range(-d, d + 1):
        if grid90[d][c90 + x] != lucas_bit(d, x):
            t31 = False
            break

    # Theorems 5.1 and 5.2 (corollary)
    t51 = correction_firing_set_matches_truth_table()

    # Theorem 4.1 across the depth grid
    t41_results = []
    t41 = True
    for N in decomposition_depths:
        r = rule30_center_via_decomposition(N)
        t41_results.append(r)
        if not r["match"]:
            t41 = False

    return {
        "status": "pass" if (t21 and t31 and t41 and t51) else "fail",
        "theorem_2_1_linearization_identity": t21,
        "theorem_3_1_lucas_closed_form": t31,
        "theorem_4_1_decomposition": t41,
        "theorem_5_1_correction_chart_projection": t51,
        "decomposition_depths_tested": list(decomposition_depths),
        "decomposition_results": t41_results,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify_all_theorems(), indent=2))
