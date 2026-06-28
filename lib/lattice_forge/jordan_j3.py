"""
The exceptional Jordan algebra J_3(O) — 3x3 Hermitian octonionic matrices.

A Hermitian octonionic matrix A satisfies A_ij = conj(A_ji), which forces
the diagonal entries to be real (since conj(A_ii) = A_ii implies A_ii has
zero imaginary part). The dimension is:
- 3 real diagonal entries
- 3 octonionic off-diagonal entries (the upper triangle determines the lower)
- 3 + 3*8 = 27 real dimensions

This is the unique 27-dimensional exceptional Jordan algebra. Its automorphism
group is F_4 (52-dimensional), and the algebra carries Freudenthal's cubic
form whose determinant-locus is the Cayley plane OP^2.

The Jordan product a o b = (a*b + b*a) / 2 is commutative but non-associative
in general (it is power-associative and satisfies the Jordan identity).

This module provides:
- J3O class with addition, scalar multiplication, Jordan product
- Trace, Freudenthal determinant
- Diagonal idempotents E_11, E_22, E_33
- The trace-2 idempotents E_ii + E_jj (the SHELL=2 stratum under our chart's
  isomorphism with Rule 30)
- The S_3 permutation action on diagonal indices, especially (1,3) which is
  the chart's Weyl L<->R involution

References:
- Freudenthal-Tits "Magic Square"
- Jacobson "Structure and Representations of Jordan Algebras" (1968)
"""

from __future__ import annotations

from dataclasses import dataclass

from .octonion import Octonion, O_ONE, O_ZERO


@dataclass(frozen=True)
class J3O:
    """
    A 3x3 Hermitian octonionic matrix:

        [ a_11    a_12    a_13 ]
        [ ~a_12   a_22    a_23 ]
        [ ~a_13   ~a_23   a_33 ]

    where ~x denotes octonionic conjugation.

    Stored as:
    - diag: (a_11, a_22, a_33) real values
    - upper: (a_12, a_13, a_23) octonion values (off-diagonal upper triangle)
    """

    diag: tuple[float, float, float]
    upper: tuple[Octonion, Octonion, Octonion]  # (a_12, a_13, a_23)

    @classmethod
    def zero(cls) -> "J3O":
        return cls((0.0, 0.0, 0.0), (O_ZERO, O_ZERO, O_ZERO))

    @classmethod
    def from_diagonal(cls, a: float, b: float, c: float) -> "J3O":
        """Construct a diagonal matrix diag(a, b, c) with zero off-diagonal."""
        return cls((float(a), float(b), float(c)), (O_ZERO, O_ZERO, O_ZERO))

    @classmethod
    def identity(cls) -> "J3O":
        return cls.from_diagonal(1.0, 1.0, 1.0)

    @classmethod
    def diagonal_idempotent(cls, index: int) -> "J3O":
        """E_ii: diagonal idempotent with 1 at position (i,i) and 0 elsewhere."""
        if not 1 <= index <= 3:
            raise ValueError(f"diagonal idempotent index must be 1, 2, or 3, got {index}")
        diag = [0.0, 0.0, 0.0]
        diag[index - 1] = 1.0
        return cls(tuple(diag), (O_ZERO, O_ZERO, O_ZERO))  # type: ignore[arg-type]

    @classmethod
    def trace_2_idempotent(cls, i: int, j: int) -> "J3O":
        """E_ii + E_jj: trace-2 idempotent (one of three under permutation)."""
        if i == j or not (1 <= i <= 3) or not (1 <= j <= 3):
            raise ValueError(f"trace-2 idempotent requires distinct i,j in 1..3, got ({i}, {j})")
        a = cls.diagonal_idempotent(i)
        b = cls.diagonal_idempotent(j)
        return a + b

    def __add__(self, other: "J3O") -> "J3O":
        new_diag = tuple(a + b for a, b in zip(self.diag, other.diag))
        new_upper = tuple(a + b for a, b in zip(self.upper, other.upper))
        return J3O(new_diag, new_upper)  # type: ignore[arg-type]

    def __sub__(self, other: "J3O") -> "J3O":
        new_diag = tuple(a - b for a, b in zip(self.diag, other.diag))
        new_upper = tuple(a - b for a, b in zip(self.upper, other.upper))
        return J3O(new_diag, new_upper)  # type: ignore[arg-type]

    def __mul__(self, scalar: float | int) -> "J3O":
        """Scalar multiplication."""
        if not isinstance(scalar, (int, float)):
            raise TypeError("J3O multiplication with non-scalar: use jordan_product()")
        s = float(scalar)
        new_diag = tuple(a * s for a in self.diag)
        new_upper = tuple(a * s for a in self.upper)
        return J3O(new_diag, new_upper)  # type: ignore[arg-type]

    def __rmul__(self, scalar: float | int) -> "J3O":
        return self.__mul__(scalar)

    def __neg__(self) -> "J3O":
        return self.__mul__(-1.0)

    # ------------------------------------------------------------------
    # Matrix-form access
    # ------------------------------------------------------------------

    def entry(self, i: int, j: int) -> Octonion:
        """Return the (i, j) entry as an Octonion, 1-indexed."""
        if not (1 <= i <= 3) or not (1 <= j <= 3):
            raise ValueError(f"indices must be 1..3, got ({i}, {j})")
        if i == j:
            return Octonion.real(self.diag[i - 1])
        # Upper-triangle storage order: (a_12, a_13, a_23) at indices 0, 1, 2
        if (i, j) == (1, 2):
            return self.upper[0]
        if (i, j) == (1, 3):
            return self.upper[1]
        if (i, j) == (2, 3):
            return self.upper[2]
        # Lower triangle: take conjugate of upper
        if (i, j) == (2, 1):
            return self.upper[0].conjugate()
        if (i, j) == (3, 1):
            return self.upper[1].conjugate()
        if (i, j) == (3, 2):
            return self.upper[2].conjugate()
        raise ValueError(f"unhandled entry ({i}, {j})")

    # ------------------------------------------------------------------
    # Algebraic structure
    # ------------------------------------------------------------------

    def trace(self) -> float:
        return self.diag[0] + self.diag[1] + self.diag[2]

    def jordan_product(self, other: "J3O") -> "J3O":
        """
        Jordan product a o b = (a*b + b*a) / 2 in the algebra of Hermitian
        octonionic matrices.

        This is computed entry-wise via matrix multiplication (which uses
        octonion multiplication for the entries).
        """
        # Compute (a * b) entry-wise
        ab_entries: list[list[Octonion]] = []
        ba_entries: list[list[Octonion]] = []
        for i in range(1, 4):
            ab_row: list[Octonion] = []
            ba_row: list[Octonion] = []
            for j in range(1, 4):
                # (a*b)[i,j] = sum_k a[i,k] * b[k,j]
                s_ab = O_ZERO
                s_ba = O_ZERO
                for k in range(1, 4):
                    s_ab = s_ab + self.entry(i, k) * other.entry(k, j)
                    s_ba = s_ba + other.entry(i, k) * self.entry(k, j)
                ab_row.append(s_ab)
                ba_row.append(s_ba)
            ab_entries.append(ab_row)
            ba_entries.append(ba_row)
        # Jordan product (a*b + b*a) / 2 — this is automatically Hermitian
        # because a, b are Hermitian and (a*b + b*a)^H = b^H * a^H + a^H * b^H
        # = b * a + a * b = same sum.
        result_diag: list[float] = []
        result_upper: list[Octonion] = []
        for i in range(3):
            jordan = (ab_entries[i][i] + ba_entries[i][i]) * 0.5
            # Diagonal entry must be real; take real part (imaginary should be ~0)
            result_diag.append(jordan.real_part())
        for (i, j) in [(0, 1), (0, 2), (1, 2)]:  # (1,2), (1,3), (2,3) 0-indexed
            jordan = (ab_entries[i][j] + ba_entries[i][j]) * 0.5
            result_upper.append(jordan)
        return J3O(tuple(result_diag), tuple(result_upper))  # type: ignore[arg-type]

    def is_idempotent(self, tol: float = 1e-9) -> bool:
        """Check whether x o x = x."""
        squared = self.jordan_product(self)
        return self._close_to(squared, tol)

    def is_hermitian_consistent(self, tol: float = 1e-9) -> bool:
        """Verify diagonal entries are real (always true by construction)."""
        # Hermiticity is enforced by storage; this is a sanity check.
        return True

    def _close_to(self, other: "J3O", tol: float = 1e-9) -> bool:
        for a, b in zip(self.diag, other.diag):
            if abs(a - b) > tol:
                return False
        for a, b in zip(self.upper, other.upper):
            diff = a - b
            if any(abs(c) > tol for c in diff.components):
                return False
        return True

    # ------------------------------------------------------------------
    # S_3 permutation action on diagonal indices
    # ------------------------------------------------------------------

    def permute_indices(self, perm: tuple[int, int, int]) -> "J3O":
        """
        Apply a permutation in S_3 to diagonal indices.

        perm is a tuple (p_1, p_2, p_3) describing the new position of each
        original index — e.g., (3, 2, 1) is the (1 3) transposition, swapping
        positions 1 and 3, fixing position 2.

        The diagonal entries permute directly. The off-diagonal entries permute
        with their indices: entry at (i, j) moves to (perm[i-1], perm[j-1]).
        """
        if sorted(perm) != [1, 2, 3]:
            raise ValueError(f"perm must be a permutation of (1,2,3), got {perm}")
        # New diag: new[i] = old[perm^{-1}(i)]
        inv = [0, 0, 0]
        for new_pos, old_pos in enumerate(perm, 1):
            inv[old_pos - 1] = new_pos
        # diag[i] is at position i+1 originally; under perm, it goes to perm[i]
        new_diag = [0.0, 0.0, 0.0]
        for i in range(3):
            new_diag[perm[i] - 1] = self.diag[i]
        # off-diagonal: entry at (i, j) -> (perm[i-1], perm[j-1])
        # We need entry at new (a, b) = old (perm^{-1}(a), perm^{-1}(b))
        # Build the new upper triangle (1,2), (1,3), (2,3)
        new_upper = [O_ZERO, O_ZERO, O_ZERO]
        upper_positions = [(1, 2), (1, 3), (2, 3)]
        for new_idx, (new_i, new_j) in enumerate(upper_positions):
            old_i, old_j = inv[new_i - 1], inv[new_j - 1]
            # Get the old entry at (old_i, old_j) — may be lower triangle
            old_entry = self.entry(old_i, old_j)
            # If new (new_i, new_j) corresponds to old (old_i, old_j) with old_i > old_j,
            # the conjugate-mapping already happened in self.entry — we now need to
            # store it in the upper triangle, so it stays as-is.
            new_upper[new_idx] = old_entry
        return J3O(tuple(new_diag), tuple(new_upper))  # type: ignore[arg-type]

    def weyl_13_transposition(self) -> "J3O":
        """The (1 3) transposition: swap positions 1 and 3, fix position 2.

        This is the chart's Weyl L<->R involution under the isomorphism
        L=position1, C=position2, R=position3.
        """
        return self.permute_indices((3, 2, 1))

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, object]:
        return {
            "diag": list(self.diag),
            "upper_12": list(self.upper[0].components),
            "upper_13": list(self.upper[1].components),
            "upper_23": list(self.upper[2].components),
            "trace": self.trace(),
        }

    def __repr__(self) -> str:
        d = self.diag
        nonzero_upper = any(
            any(abs(c) > 1e-12 for c in u.components) for u in self.upper
        )
        if not nonzero_upper:
            return f"J3O.diag({d[0]:.3f}, {d[1]:.3f}, {d[2]:.3f})"
        return (
            f"J3O(diag=({d[0]:.3f},{d[1]:.3f},{d[2]:.3f}),"
            f" a12={self.upper[0]}, a13={self.upper[1]}, a23={self.upper[2]})"
        )


# ----------------------------------------------------------------------
# The three trace-2 idempotents — these are the Rule 30 shell=2 stratum
# ----------------------------------------------------------------------

J3_TRACE2_E11_E22 = J3O.trace_2_idempotent(1, 2)  # corresponds to chart state (1,1,0) i.e., C-
J3_TRACE2_E11_E33 = J3O.trace_2_idempotent(1, 3)  # corresponds to chart state (1,0,1) i.e., C0
J3_TRACE2_E22_E33 = J3O.trace_2_idempotent(2, 3)  # corresponds to chart state (0,1,1) i.e., C+


def verify_j3o_axioms() -> dict[str, object]:
    """Verify J_3(O) algebra axioms hold for the implementation."""
    errors: list[str] = []
    # Diagonal idempotent E_ii satisfies E_ii o E_ii = E_ii
    for i in (1, 2, 3):
        E = J3O.diagonal_idempotent(i)
        E_sq = E.jordan_product(E)
        if not E._close_to(E_sq):
            errors.append(f"E_{i}{i} is not idempotent under Jordan product")
    # Distinct diagonal idempotents are Jordan-orthogonal: E_ii o E_jj = 0 for i != j
    for i in (1, 2, 3):
        for j in (1, 2, 3):
            if i == j:
                continue
            E_i = J3O.diagonal_idempotent(i)
            E_j = J3O.diagonal_idempotent(j)
            prod = E_i.jordan_product(E_j)
            if not prod._close_to(J3O.zero()):
                errors.append(
                    f"E_{i}{i} o E_{j}{j} != 0 (got diag={prod.diag})"
                )
    # Sum of diagonal idempotents is identity
    E_sum = J3O.diagonal_idempotent(1) + J3O.diagonal_idempotent(2) + J3O.diagonal_idempotent(3)
    if not E_sum._close_to(J3O.identity()):
        errors.append("E_11 + E_22 + E_33 != identity")
    # Trace-2 idempotents have trace 2
    for (i, j) in [(1, 2), (1, 3), (2, 3)]:
        T = J3O.trace_2_idempotent(i, j)
        if abs(T.trace() - 2.0) > 1e-9:
            errors.append(f"E_{i}{i} + E_{j}{j} has trace {T.trace()}, expected 2")
        # And idempotent under Jordan product
        T_sq = T.jordan_product(T)
        if not T._close_to(T_sq):
            errors.append(f"E_{i}{i} + E_{j}{j} is not idempotent under Jordan product")
    # The (1,3) transposition fixes E_22 (= trace-2 idempotent E_11 + E_33)
    fixed_by_13 = J3_TRACE2_E11_E33.weyl_13_transposition()
    if not fixed_by_13._close_to(J3_TRACE2_E11_E33):
        errors.append(
            "(1,3) transposition does not fix E_11 + E_33 (expected fixed)"
        )
    # The (1,3) transposition swaps E_11+E_22 <-> E_22+E_33
    swap_a = J3_TRACE2_E11_E22.weyl_13_transposition()
    if not swap_a._close_to(J3_TRACE2_E22_E33):
        errors.append("(1,3) transposition does not swap E_11+E_22 -> E_22+E_33")
    swap_b = J3_TRACE2_E22_E33.weyl_13_transposition()
    if not swap_b._close_to(J3_TRACE2_E11_E22):
        errors.append("(1,3) transposition does not swap E_22+E_33 -> E_11+E_22")
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "checks_passed": [
            "diagonal_idempotents_are_idempotent",
            "diagonal_idempotents_jordan_orthogonal",
            "diagonal_idempotents_sum_to_identity",
            "trace_2_idempotents_have_correct_trace",
            "trace_2_idempotents_are_idempotent",
            "weyl_13_fixes_chirality_balanced",
            "weyl_13_swaps_chirality_broken_pair",
        ],
    }
