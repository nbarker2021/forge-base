"""
F4/SU3 action on the J3O trace-2 stratum (stdlib stub for
``lattice_forge.f4_action``).

The three trace-2 idempotents {E_11+E_22, E_11+E_33, E_22+E_33}
form a basis for the rank-1 3-fundamental representation of
SU(3) embedded in F4. The S3 Weyl group of SU(3) acts on these
by permuting diagonal indices; the 6 elements of S3 give 6
permutation matrices on the 3-fundamental.

This module exposes the 6 S3 permutation matrices and the
closed-form 8x8 Rule 30 transition matrix (marginalized over
wider-context cells LL, RR), both of which are prime diff points
against the upstream lattice_forge.
"""

from __future__ import annotations

from typing import Dict, List, Tuple


# Six S3 permutations on diagonal indices (1, 2, 3), in canonical
# order: identity, (12), (13), (23), (123), (132).
S3_PERMUTATION_NAMES: Tuple[str, ...] = (
    "id", "(12)", "(13)", "(23)", "(123)", "(132)",
)
S3_PERMUTATIONS: Tuple[Tuple[int, int, int], ...] = (
    (1, 2, 3),
    (2, 1, 3),
    (3, 2, 1),
    (1, 3, 2),
    (2, 3, 1),
    (3, 1, 2),
)


def _trace2_permutation_matrix(perm: Tuple[int, int, int]) -> List[List[float]]:
    """3x3 permutation matrix acting on (C-, C0, C+) idempotents.

    C- = E_11+E_22 = (1,1,0), C0 = E_11+E_33 = (1,0,1),
    C+ = E_22+E_33 = (0,1,1).

    For a permutation of (1,2,3), the idempotent (i,j) maps to
    (perm[i-1], perm[j-1]).
    """
    if sorted(perm) != [1, 2, 3]:
        raise ValueError(f"perm must be a permutation of (1,2,3), got {perm}")
    idempotent_index = {(1, 2): 0, (1, 3): 1, (2, 3): 2}
    matrix = [[0.0] * 3 for _ in range(3)]
    for source_pair, source_idx in idempotent_index.items():
        i, j = source_pair
        new_i, new_j = perm[i - 1], perm[j - 1]
        canonical = tuple(sorted([new_i, new_j]))
        target_idx = idempotent_index[canonical]
        matrix[target_idx][source_idx] = 1.0
    return matrix


def s3_permutation_matrices() -> Dict[str, List[List[float]]]:
    """Return all 6 S3 permutation matrices on the 3-fundamental."""
    return {
        name: _trace2_permutation_matrix(perm)
        for name, perm in zip(S3_PERMUTATION_NAMES, S3_PERMUTATIONS)
    }


def _rule30_bit(L: int, C: int, R: int) -> int:
    """Rule 30: bit = L XOR (C OR R)."""
    return L ^ (C | R)


def closed_form_rule30_8x8_transition() -> Dict[str, object]:
    """Build the closed-form 8x8 transition matrix for Rule 30's
    center cell triple (L, C, R) under uniform marginalization of
    the wider context cells (LL, RR).

    For a chart state (L, C, R) at depth t, the next state at
    depth t+1 has components:

      L' = Rule30(LL, L, C)
      C' = Rule30(L, C, R)
      R' = Rule30(C, R, RR)

    Marginalizing uniformly over (LL, RR) in {0,1}^2 gives the
    transition probabilities.
    """
    states: List[Tuple[int, int, int]] = []
    for L in range(2):
        for C in range(2):
            for R in range(2):
                states.append((L, C, R))

    matrix: Dict[Tuple[int, int, int], Dict[Tuple[int, int, int], float]] = {}
    for src in states:
        L, C, R = src
        row: Dict[Tuple[int, int, int], float] = {dst: 0.0 for dst in states}
        for LL in range(2):
            for RR in range(2):
                L_next = _rule30_bit(LL, L, C)
                C_next = _rule30_bit(L, C, R)
                R_next = _rule30_bit(C, R, RR)
                row[(L_next, C_next, R_next)] += 1.0
        # Normalize
        n = sum(row.values())
        if n > 0:
            for k in row:
                row[k] /= n
        matrix[src] = row

    # Convert to list-of-lists
    matrix_list: List[List[float]] = []
    for src in states:
        row = [matrix[src][dst] for dst in states]
        matrix_list.append(row)

    return {
        "states": states,
        "matrix": matrix_list,
        "state_count": len(states),
        "source": "stdlib",
    }


def closed_form_shell2_3x3() -> Dict[str, object]:
    """Build the 3x3 SU(3) closed-form on the trace-2 stratum.

    The three trace-2 idempotents {E_11+E_22, E_11+E_33, E_22+E_33}
    span the rank-1 3-fundamental of SU(3) embedded in F4. The
    closed-form 3x3 is the *average* of the 6 S3 Weyl permutation
    matrices acting on this basis — the uniform F4 density on
    the Weyl orbit.

    This is doubly-stochastic by construction (each S3
    permutation is doubly-stochastic, the average is too).
    """
    shell2_states: List[Tuple[int, int, int]] = [(1, 1, 0), (1, 0, 1), (0, 1, 1)]
    # Average the 6 S3 permutation matrices on the 3-fundamental
    matrix_3x3: List[List[float]] = [[0.0] * 3 for _ in range(3)]
    for name in S3_PERMUTATION_NAMES:
        m = s3_permutation_matrices()[name]
        for i in range(3):
            for j in range(3):
                matrix_3x3[i][j] += m[i][j]
    n = len(S3_PERMUTATION_NAMES)
    for i in range(3):
        for j in range(3):
            matrix_3x3[i][j] /= n
    return {
        "states": shell2_states,
        "matrix": matrix_3x3,
        "source": "stdlib",
    }


def verify_n3_su3_closure() -> Dict[str, object]:
    """Verify the shell-2 3x3 transition matrix is doubly-stochastic
    and matches a S3 group ring element.

    Doubly-stochastic: row sums = column sums = 1.
    """
    cf = closed_form_shell2_3x3()
    matrix = cf["matrix"]  # type: ignore[index]
    n = len(matrix)
    failures: List[str] = []
    # Row sums
    for i, row in enumerate(matrix):
        s = sum(row)
        if abs(s - 1.0) > 1e-9:
            failures.append(f"row {i} sum != 1: {s}")
    # Column sums
    for j in range(n):
        s = sum(matrix[i][j] for i in range(n))
        if abs(s - 1.0) > 1e-9:
            failures.append(f"col {j} sum != 1: {s}")
    # Symmetry
    for i in range(n):
        for j in range(n):
            if abs(matrix[i][j] - matrix[j][i]) > 1e-9:
                failures.append(f"matrix not symmetric: [{i}][{j}]={matrix[i][j]}, [{j}][{i}]={matrix[j][i]}")
    return {
        "status": "pass" if not failures else "fail",
        "checked": ["row_sum_1", "col_sum_1", "symmetric"],
        "failures": failures,
        "matrix": matrix,
    }


__all__ = [
    "S3_PERMUTATION_NAMES",
    "S3_PERMUTATIONS",
    "s3_permutation_matrices",
    "closed_form_rule30_8x8_transition",
    "closed_form_shell2_3x3",
    "verify_n3_su3_closure",
]
