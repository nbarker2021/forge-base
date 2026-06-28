"""
f2_majorana.py — F_2 quadratic-form / Majorana-parity primitives.

This module provides the binary-deterministic edge-glue apparatus that
makes T_BRIDGE governance portable: given two cell-trajectory windows
(or two block addresses, or two D_4-codec sub-sequences), the F_2
quadratic form attached to each window admits a canonical Arf invariant
in F_2 = {0, 1}, and two windows can be glued losslessly along their
shared boundary iff their Arf invariants match. This is the discrete
companion to the SL(2,Z) modular companion: where the modular partner
provides the analytic gluing, the F_2 Arf invariant provides the
binary-deterministic gluing.

Background
----------
The chart trajectory of Rule 30 evolves on F_2 = GF(2). Each cell value
is a F_2 element; the row is a vector in F_2^W. Rule 30's transition
function is the GF(2) polynomial L + C + R + C·R (= L ⊕ C ⊕ R ⊕ CR),
which decomposes into a linear part L + C + R and the bilinear obstruction
C·R. The bilinear obstruction is, by definition, a F_2 quadratic form.

Majorana operators γ_i = γ_i† with {γ_i, γ_j} = 2δ_ij generate a
Clifford algebra Cl(n, 0) whose Z_2 grading by Majorana-parity is the
same F_2 structure: the parity of the number of Majorana operators in a
monomial. Spin chains / topological superconductors realize this Z_2
grading physically as fermion-parity superselection. For Rule 30 chart
work, the relevant abstraction is:

    Q : F_2^n → F_2,
        Q(v) = v^T A v   (with A upper triangular)

with associated bilinear form B(v, w) = Q(v + w) + Q(v) + Q(w) (over F_2).

Theorem (Arf, 1941; standard). Two non-degenerate F_2 quadratic forms on
F_2^n with the same bilinear form are equivalent under F_2-linear
isometry iff their Arf invariants agree. The Arf invariant of Q is

    Arf(Q) = Σ_{i=1}^{g} Q(e_i) · Q(f_i)   (mod 2)

for any symplectic basis (e_1, ..., e_g, f_1, ..., f_g) of F_2^{2g}
with respect to B.

Rule 30 correction tape: the bilinear obstruction C·R has Arf invariant
0 (computed in this module's verification).
"""
from __future__ import annotations

from typing import Iterable


# ---------------------------------------------------------------------------
# F_2 quadratic forms
# ---------------------------------------------------------------------------

class F2Quadratic:
    """A quadratic form Q: F_2^n -> F_2 represented by an upper-triangular
    coefficient matrix `A` of size n × n with entries in {0, 1}.

    The form is Q(v) = sum_{i <= j} A[i][j] * v_i * v_j  over F_2.

    The associated bilinear form B(v, w) = Q(v+w) + Q(v) + Q(w) has matrix
    A + A^T (with diagonal forced to zero), i.e. the strictly off-diagonal
    symmetric part.
    """

    def __init__(self, A: list[list[int]]):
        n = len(A)
        if any(len(row) != n for row in A):
            raise ValueError("A must be square")
        # Force upper-triangular by absorbing lower into upper and clearing.
        upper: list[list[int]] = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i <= j:
                    upper[i][j] = (A[i][j] + (A[j][i] if i != j else 0)) & 1
        self.n = n
        self.A = upper

    def evaluate(self, v: list[int]) -> int:
        """Q(v) over F_2."""
        if len(v) != self.n:
            raise ValueError("v dimension mismatch")
        s = 0
        for i in range(self.n):
            if not v[i]:
                continue
            for j in range(i, self.n):
                if self.A[i][j] and v[j]:
                    s ^= 1
        return s

    def bilinear(self, v: list[int], w: list[int]) -> int:
        """B(v, w) = Q(v+w) - Q(v) - Q(w) over F_2."""
        if len(v) != self.n or len(w) != self.n:
            raise ValueError("dimension mismatch")
        s = 0
        for i in range(self.n):
            for j in range(self.n):
                if i != j and self.A[min(i, j)][max(i, j)]:
                    if v[i] and w[j]:
                        s ^= 1
        return s

    def radical(self) -> list[list[int]]:
        """Vectors v with B(v, _) = 0, returned as a list of basis vectors."""
        # B matrix: for i < j, B[i][j] = B[j][i] = A[i][j]
        n = self.n
        B = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                B[i][j] = self.A[i][j]
                B[j][i] = self.A[i][j]
        # Null space over F_2
        return _null_space_f2(B)

    def is_non_degenerate(self) -> bool:
        return len(self.radical()) == 0

    def arf_invariant(self) -> int:
        """Arf invariant of Q, computed by reducing to a symplectic basis.

        Definition: for a non-degenerate F_2 quadratic form on F_2^{2g},
        Arf(Q) = sum Q(e_i) · Q(f_i) over a symplectic basis. The choice
        of symplectic basis does not affect the result (mod 2).

        If Q is degenerate, we compute Arf on the quotient by the radical.
        """
        rad = self.radical()
        if not rad:
            return _arf_via_symplectic(self.A, self.n)
        # Quotient by radical: find vectors complementary to radical.
        # Pick a basis of F_2^n / radical, restrict Q to it.
        comp_basis = _complement_basis_f2(rad, self.n)
        m = len(comp_basis)
        if m == 0:
            return 0
        # Build the restricted A matrix on the complement basis.
        A_restricted = [[0] * m for _ in range(m)]
        for i in range(m):
            for j in range(i, m):
                v_ij = _xor_vectors(comp_basis[i], comp_basis[j]) if i != j else comp_basis[i]
                if i == j:
                    A_restricted[i][i] = self.evaluate(comp_basis[i])
                else:
                    q_sum = self.evaluate(v_ij)
                    q_i = self.evaluate(comp_basis[i])
                    q_j = self.evaluate(comp_basis[j])
                    A_restricted[i][j] = (q_sum ^ q_i ^ q_j) & 1
        return _arf_via_symplectic(A_restricted, m)


# ---------------------------------------------------------------------------
# Linear-algebra helpers over F_2
# ---------------------------------------------------------------------------

def _null_space_f2(M: list[list[int]]) -> list[list[int]]:
    """Return a basis of {v in F_2^n : Mv = 0} for an n×n matrix M."""
    n = len(M)
    if n == 0:
        return []
    # Copy for row reduction
    A = [row[:] for row in M]
    pivot_col = [-1] * n
    row = 0
    for col in range(n):
        # Find pivot
        pivot_row = -1
        for r in range(row, n):
            if A[r][col]:
                pivot_row = r
                break
        if pivot_row == -1:
            continue
        A[row], A[pivot_row] = A[pivot_row], A[row]
        pivot_col[row] = col
        # Eliminate
        for r in range(n):
            if r != row and A[r][col]:
                A[r] = [(A[r][c] ^ A[row][c]) for c in range(n)]
        row += 1
    # Build null space: free variables are columns not in pivot_col
    pivot_set = set(c for c in pivot_col if c >= 0)
    free_cols = [c for c in range(n) if c not in pivot_set]
    null_basis = []
    for fc in free_cols:
        v = [0] * n
        v[fc] = 1
        # Back-substitute: for each pivot row, set v at pivot_col to expression in free vars
        for r in range(n):
            pc = pivot_col[r]
            if pc < 0:
                continue
            # A[r][fc] is the coefficient of free var fc in the equation for v[pc]
            v[pc] = A[r][fc]
        null_basis.append(v)
    return null_basis


def _complement_basis_f2(subspace: list[list[int]], n: int) -> list[list[int]]:
    """Return vectors completing `subspace` to a basis of F_2^n."""
    basis = [row[:] for row in subspace]
    for i in range(n):
        e_i = [0] * n
        e_i[i] = 1
        # Check if e_i is in span of `basis`
        if _in_span_f2(e_i, basis):
            continue
        basis.append(e_i)
    return basis[len(subspace):]


def _in_span_f2(v: list[int], basis: list[list[int]]) -> bool:
    """Is v in the F_2 span of `basis`?"""
    n = len(v)
    M = [row[:] for row in basis] + [v[:]]
    # Augmented row-reduce; v is in span iff its row reduces to zero.
    rows = [r[:] for r in M]
    r_idx = 0
    for c in range(n):
        pr = -1
        for r in range(r_idx, len(rows) - 1):
            if rows[r][c]:
                pr = r
                break
        if pr == -1:
            continue
        rows[r_idx], rows[pr] = rows[pr], rows[r_idx]
        for r in range(len(rows)):
            if r != r_idx and rows[r][c]:
                rows[r] = [(rows[r][cc] ^ rows[r_idx][cc]) for cc in range(n)]
        r_idx += 1
        if r_idx >= len(rows) - 1:
            break
    return all(b == 0 for b in rows[-1])


def _xor_vectors(a: list[int], b: list[int]) -> list[int]:
    return [(x ^ y) for x, y in zip(a, b)]


def _arf_via_symplectic(A: list[list[int]], n: int) -> int:
    """Compute Arf invariant by finding a symplectic basis under B."""
    if n == 0:
        return 0
    # Build bilinear B (off-diagonal symmetric part of A + A^T)
    B = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            B[i][j] = A[i][j]
            B[j][i] = A[i][j]
    # Q values for each basis vector e_k
    Q_e = [A[k][k] for k in range(n)]

    # Greedy: pair up pivots in B to form symplectic basis pairs.
    used = [False] * n
    arf = 0
    for i in range(n):
        if used[i]:
            continue
        # Find j > i with B[i][j] = 1
        partner = -1
        for j in range(i + 1, n):
            if not used[j] and B[i][j]:
                partner = j
                break
        if partner == -1:
            # i is in the radical; skip
            used[i] = True
            continue
        # Contribute Q(e_i) * Q(f_j)
        arf ^= Q_e[i] * Q_e[partner]
        used[i] = True
        used[partner] = True
    return arf & 1


# ---------------------------------------------------------------------------
# Rule 30 specific: the correction's quadratic form
# ---------------------------------------------------------------------------

def rule30_correction_quadratic() -> F2Quadratic:
    """The Rule 30 correction term C ∧ ¬R = C + CR is a quadratic form
    on F_2^3 with coordinates (L, C, R).

    Coefficient matrix (upper triangular) on basis (L, C, R):
        A[1][1] = 1   (C term)
        A[1][2] = 1   (CR term)
    """
    A = [
        [0, 0, 0],
        [0, 1, 1],
        [0, 0, 0],
    ]
    return F2Quadratic(A)


def rule30_correction_arf() -> int:
    """Arf invariant of the Rule 30 correction quadratic form."""
    return rule30_correction_quadratic().arf_invariant()


# ---------------------------------------------------------------------------
# Edge gluing: Majorana-parity preservation
# ---------------------------------------------------------------------------

def can_glue_edges(q_left: F2Quadratic, q_right: F2Quadratic) -> dict:
    """Two trajectory edges (each carrying its own F_2 quadratic form) can
    be glued losslessly along their shared boundary iff their Arf
    invariants match. This is the discrete Arf-gluing criterion.

    Returns a dict with the comparison result and both Arf invariants.
    """
    a_left = q_left.arf_invariant()
    a_right = q_right.arf_invariant()
    return {
        "left_arf": a_left,
        "right_arf": a_right,
        "can_glue": a_left == a_right,
        "rationale": (
            "Two non-degenerate F_2 quadratic forms on a shared boundary "
            "admit a F_2-linear isometry connecting them iff their Arf "
            "invariants agree (Arf 1941)."
        ),
    }


# ---------------------------------------------------------------------------
# Module-level verification
# ---------------------------------------------------------------------------

def verify_f2_majorana() -> dict:
    """Run a battery of correctness checks against known identities."""
    results: dict = {}

    # 1. Trivial form Q = 0 has Arf = 0
    q_zero = F2Quadratic([[0, 0], [0, 0]])
    results["q_zero_arf"] = q_zero.arf_invariant()

    # 2. The standard rank-2 hyperbolic form Q(x,y) = xy has Arf = 0
    q_hyp = F2Quadratic([[0, 1], [0, 0]])
    results["q_hyperbolic_arf"] = q_hyp.arf_invariant()

    # 3. The standard rank-2 elliptic form Q(x,y) = xy + x^2 + y^2 has Arf = 1
    q_ell = F2Quadratic([[1, 1], [0, 1]])
    results["q_elliptic_arf"] = q_ell.arf_invariant()

    # 4. Rule 30 correction
    results["rule30_correction_arf"] = rule30_correction_arf()

    # 5. Glueability: two trivial forms can glue; trivial + elliptic cannot.
    g1 = can_glue_edges(q_zero, q_hyp)
    g2 = can_glue_edges(q_zero, q_ell)
    results["zero_vs_hyperbolic_can_glue"] = g1["can_glue"]
    results["zero_vs_elliptic_can_glue"] = g2["can_glue"]

    # Status: known values check out
    expected = {
        "q_zero_arf": 0,
        "q_hyperbolic_arf": 0,
        "q_elliptic_arf": 1,
        "rule30_correction_arf": 0,  # CR is hyperbolic; no quadratic
        "zero_vs_hyperbolic_can_glue": True,
        "zero_vs_elliptic_can_glue": False,
    }
    passed = all(results[k] == v for k, v in expected.items())
    results["status"] = "pass" if passed else "fail"
    results["expected"] = expected
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(verify_f2_majorana(), indent=2))
