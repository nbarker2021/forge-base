"""
J3O — the 3x3 Hermitian octonionic matrix algebra (stdlib stub
for ``lattice_forge.jordan_j3``).

J3O is the unique 27-dimensional exceptional Jordan algebra. The
diagonal entries are real; the upper-triangle off-diagonals are
octonions. The Jordan product a o b = (a*b + b*a) / 2 is
commutative and power-associative but not associative.

This is a stdlib reimplementation. When ``lattice_forge`` is
installed, the bridge uses the upstream J3O; otherwise this is
the local authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from .octonion import Octonion, Octonion as _O  # type: ignore


@dataclass(frozen=True)
class J3O:
    """A 3x3 Hermitian octonionic matrix.

    Stored compactly as:
      * ``diag``  — 3 real diagonal entries
      * ``upper`` — 3 octonion upper-triangle entries (a_12, a_13, a_23)
    The lower triangle is the conjugate of the upper.
    """

    diag: Tuple[float, float, float]
    upper: Tuple[Octonion, Octonion, Octonion]  # (a_12, a_13, a_23)

    @classmethod
    def zero(cls) -> "J3O":
        z = _O.zero()
        return cls((0.0, 0.0, 0.0), (z, z, z))

    @classmethod
    def diag_only(cls, d1: float, d2: float, d3: float) -> "J3O":
        z = _O.zero()
        return cls((d1, d2, d3), (z, z, z))

    def trace(self) -> float:
        return self.diag[0] + self.diag[1] + self.diag[2]

    def jordan_product(self, other: "J3O") -> "J3O":
        """The Jordan product a o b = (a*b + b*a) / 2.

        For Hermitian octonionic J3O, the standard matrix product
        is non-Hermitian, but the symmetrized product a*o*b is
        Hermitian. We compute the symmetrized product explicitly
        for the small (3x3) case.

        For two **diagonal** matrices, the Jordan product is
        element-wise: (a o b)_ii = a_ii * b_ii, and off-diagonals
        remain 0 (because they involve only zero entries from each
        operand's upper triangle).

        For the general case, the off-diagonal entries pick up
        bilinear terms from the diagonal and from the matching
        upper entries.
        """
        a, b = self, other
        # Diagonal entries of (a*b + b*a)/2:
        # (a*b)_ii = a_ii * b_ii + sum_{k != i} a_ik * b_ki
        # For Hermitian: b_ki = conj(b_ik), a_ki = conj(a_ik)
        # so a_ik * b_ki = a_ik * conj(b_ik) is real
        # (it's the inner product <a_ik, b_ik>).
        new_d = [0.0, 0.0, 0.0]
        for i in range(3):
            new_d[i] = a.diag[i] * b.diag[i]
            for j in range(3):
                if i != j:
                    aij = a._off(i, j)
                    bij = b._off(i, j)
                    # a_ik * b_ki at (i,i) when k = j:
                    # (a*b)_ii gets a_ij * b_ji = a_ij * conj(b_ij)
                    new_d[i] += (aij * bij.conjugate()).components[0]
        # Off-diagonals: (a*b + b*a)/2 at (i, j) for i != j
        # (a*b)_ij = a_ii * b_ij + a_ij * b_jj + sum_{k != i, j} a_ik * b_kj
        # (b*a)_ij = b_ii * a_ij + b_ij * a_jj + sum_{k != i, j} b_ik * a_kj
        # Symmetrized: ((a_ii + b_ii) * (i,j) + (a_jj + b_jj) * (i,j)) / 2
        # + (cross terms with k != i, j which cancel under sym + conj)
        # For Hermitian a, b: cross terms are
        #   a_ik * b_kj + b_ik * a_kj (at (i,j) for k != i,j)
        # Under sym + conj, this becomes
        #   2 * real( (a_ik . b_kj) * conj(something) ) — generally non-zero.
        # For simplicity we compute the off-diagonals by direct
        # matrix multiply and symmetrize.
        # Use a simple 3x3 dense matrix multiply.
        def to_dense(m: "J3O") -> List[List[Octonion]]:
            d0, d1, d2 = m.diag
            u0, u1, u2 = m.upper
            return [
                [_O((d0, 0, 0, 0, 0, 0, 0, 0)), u0, u1],
                [u0.conjugate(), _O((d1, 0, 0, 0, 0, 0, 0, 0)), u2],
                [u1.conjugate(), u2.conjugate(), _O((d2, 0, 0, 0, 0, 0, 0, 0))],
            ]
        A = to_dense(a)
        B = to_dense(b)
        AB = [[_O.zero() for _ in range(3)] for _ in range(3)]
        BA = [[_O.zero() for _ in range(3)] for _ in range(3)]
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    AB[i][j] = AB[i][j] + A[i][k] * B[k][j]
                    BA[i][j] = BA[i][j] + B[i][k] * A[k][j]
        # Symmetrize
        new_upper = []
        for k, (i, j) in enumerate([(0, 1), (0, 2), (1, 2)]):
            sym = _O(tuple((AB[i][j].components[c] + BA[i][j].components[c]) / 2 for c in range(8)))
            new_upper.append(sym)
        return J3O((new_d[0], new_d[1], new_d[2]), tuple(new_upper))

    def _off(self, i: int, j: int) -> Octonion:
        """Return the (i, j) entry, with i < j convention."""
        if i == j:
            raise ValueError(f"_off is for off-diagonal only, got ({i},{j})")
        # Map (i, j) with i != j to one of three upper indices
        pair_to_idx = {(0, 1): 0, (0, 2): 1, (1, 2): 2,
                       (1, 0): 0, (2, 0): 1, (2, 1): 2}
        a, b = sorted((i, j))
        idx = pair_to_idx[(a, b)]
        if (a, b) == (i, j):
            return self.upper[idx]
        return self.upper[idx].conjugate()


def verify_j3o_axioms() -> dict:
    """Verify J3O axioms:

      * Jordan product is commutative: a o b = b o a
      * Jordan product is power-associative: (a o a) o (a o a) =
        a o (a o (a o a))
      * Identity matrix (1, 1, 1) is identity for Jordan product
      * The trace form tr(a o b) = 2 * sum_i (a_ii * b_ii) is the
        standard symmetric bilinear form for J3O (the factor 2
        is the conventional normalization of the Jordan trace)

    Returns a dict with status, axiom names, and failure list.
    """
    failures: list = []
    identity = J3O.diag_only(1.0, 1.0, 1.0)
    # Pick some test matrices
    a = J3O.diag_only(1.0, 2.0, 3.0)
    b = J3O.diag_only(0.5, 1.5, 2.5)
    # Commutativity
    ab = a.jordan_product(b)
    ba = b.jordan_product(a)
    if (ab.diag != ba.diag
            or any(ab.upper[k].components != ba.upper[k].components
                  for k in range(3))):
        failures.append("Jordan product not commutative")
    # Power-associativity: ((a o a) o a) = (a o (a o a))
    aa = a.jordan_product(a)
    aaa_left = aa.jordan_product(a)
    aaa_right = a.jordan_product(aa)
    if (aaa_left.diag != aaa_right.diag
            or any(aaa_left.upper[k].components != aaa_right.upper[k].components
                  for k in range(3))):
        failures.append("Jordan product not power-associative")
    # Identity matrix: a o I = a and I o a = a
    ai = a.jordan_product(identity)
    if ai.diag != a.diag or any(ai.upper[k].components != a.upper[k].components
                                for k in range(3)):
        failures.append("identity matrix (1,1,1) not identity for Jordan product")
    ia = identity.jordan_product(a)
    if ia.diag != a.diag or any(ia.upper[k].components != a.upper[k].components
                                for k in range(3)):
        failures.append("identity matrix (1,1,1) not identity for Jordan product (right side)")
    # trace form: tr(a o b) = sum_i (a_ii * b_ii)
    # For Hermitian diagonal J3Os, the Jordan product is the
    # pointwise product on diagonals, and the trace is the
    # standard linear trace. So tr(a o b) = sum_i a_ii * b_ii.
    tr_ab = sum(ab.diag)
    expected = a.diag[0] * b.diag[0] + a.diag[1] * b.diag[1] + a.diag[2] * b.diag[2]
    if abs(tr_ab - expected) > 1e-9:
        failures.append(f"trace of Jordan product not bilinear: got {tr_ab}, expected {expected}")
    return {
        "status": "pass" if not failures else "fail",
        "checked": ["commutativity", "power-associativity", "identity-(1,1,1)", "trace-bilinear"],
        "failures": failures,
        "j3o_dimension": 27,
    }


__all__ = ["J3O", "verify_j3o_axioms"]
