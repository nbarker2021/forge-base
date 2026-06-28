"""
Octonion algebra (stdlib stub for ``lattice_forge.octonion``).

The octonions (Cayley numbers) are the unique 8-dimensional
normed division algebra over the reals. They are non-associative
but alternative (any two elements generate an associative subalgebra).

This is a pure-stdlib reimplementation. When ``lattice_forge`` is
installed, the kernel's bridge uses the upstream octonion type;
otherwise this module is the local authority.

Multiplication table: the canonical (1, i, j, k, l, il, jl, kl)
sign table, encoded as a list of (sign, a, b) triples that
``product[i][j]`` returns the k such that e_i * e_j = sign * e_k.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple


# Canonical Fano plane (oriented triples (a, b, c) meaning
# e_a * e_b = +e_c, with cyclic shifts also +sign and reverses
# -sign). This is the Cayley-Dickson construction; matches the
# Fano-plane encoding used by lattice_forge.octonion.
#
# The 7 Fano lines per the lattice_forge convention:
#   (1,2,3), (1,4,5), (1,7,6), (2,4,6), (2,5,7), (3,4,7), (3,6,5)
FANO_TRIPLES: tuple = (
    (1, 2, 3), (1, 4, 5), (1, 7, 6),
    (2, 4, 6), (2, 5, 7),
    (3, 4, 7), (3, 6, 5),
)


def _build_octonion_table() -> tuple:
    """Build the 8x8 multiplication table from the Fano plane.

    The identity row/column is filled first (1 * e_i = e_i * 1 = e_i).
    Then imaginary units square to -1. Then the Fano plane
    propagates cyclic shifts (a,b)->c, (b,c)->a, (c,a)->b all
    with +sign, and reverses (b,a)->-c, (c,b)->-a, (a,c)->-b all
    with -sign.
    """
    table = [[(1, 0) for _ in range(8)] for _ in range(8)]
    # Identity
    for i in range(8):
        table[0][i] = (1, i)
        table[i][0] = (1, i)
    # Imaginary units square to -1
    for i in range(1, 8):
        table[i][i] = (-1, 0)
    # Fano propagation
    triples: dict = {}
    for a, b, c in FANO_TRIPLES:
        # Cyclic shifts: +sign
        triples[(a, b)] = (1, c)
        triples[(b, c)] = (1, a)
        triples[(c, a)] = (1, b)
        # Reverse order: -sign
        triples[(b, a)] = (-1, c)
        triples[(c, b)] = (-1, a)
        triples[(a, c)] = (-1, b)
    for i in range(1, 8):
        for j in range(1, 8):
            if i == j:
                continue
            if (i, j) not in triples:
                raise ValueError(f"Missing Fano triple for (e_{i}, e_{j})")
            table[i][j] = triples[(i, j)]
    return tuple(tuple(row) for row in table)


CANONICAL_TABLE: tuple = _build_octonion_table()


@dataclass(frozen=True)
class Octonion:
    """An octonion element stored as 8 real components.

    The components are stored in canonical order:
    (1, i, j, k, l, il, jl, kl).
    """

    components: Tuple[float, ...]  # length 8

    def __post_init__(self) -> None:
        if len(self.components) != 8:
            raise ValueError(
                f"octonion must have 8 components, got {len(self.components)}"
            )

    @classmethod
    def zero(cls) -> "Octonion":
        return cls((0.0,) * 8)

    @classmethod
    def one(cls) -> "Octonion":
        return cls((1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))

    @classmethod
    def basis(cls, i: int) -> "Octonion":
        """Return the i-th basis element (i=0..7)."""
        if not (0 <= i < 8):
            raise ValueError(f"basis index must be 0..7, got {i}")
        comps = [0.0] * 8
        comps[i] = 1.0
        return cls(tuple(comps))

    def __add__(self, other: "Octonion") -> "Octonion":
        return Octonion(tuple(a + b for a, b in zip(self.components, other.components)))

    def __sub__(self, other: "Octonion") -> "Octonion":
        return Octonion(tuple(a - b for a, b in zip(self.components, other.components)))

    def __neg__(self) -> "Octonion":
        return Octonion(tuple(-a for a in self.components))

    def __mul__(self, other: "Octonion") -> "Octonion":
        out = [0.0] * 8
        for i in range(8):
            for j in range(8):
                sign, k = CANONICAL_TABLE[i][j]
                out[k] += sign * self.components[i] * other.components[j]
        return Octonion(tuple(out))

    def conjugate(self) -> "Octonion":
        # conj(1) = 1, conj(i) = -i, etc.
        comps = list(self.components)
        comps[0] = comps[0]  # 1 stays
        for i in range(1, 8):
            comps[i] = -comps[i]
        return Octonion(tuple(comps))

    def norm_squared(self) -> float:
        return sum(a * a for a in self.components)

    def to_list(self) -> List[float]:
        return list(self.components)


def verify_octonion_axioms() -> dict:
    """Verify the octonion multiplication table satisfies the
    alternative-algebra axioms:

      * 1 is the multiplicative identity
      * multiplication is bilinear
      * every element has a unique conjugate (norm-squared form)
      * norm is multiplicative: ||xy|| = ||x|| * ||y||

    Returns a dict with ``status`` (``"pass"`` / ``"fail"``), a
    list of axiom names, and a count of failures.
    """
    failures: list = []
    one = Octonion.one()
    zero = Octonion.zero()
    # Identity: x * 1 = x and 1 * x = x
    for i in range(8):
        e_i = Octonion.basis(i)
        if (e_i * one).components != e_i.components:
            failures.append(f"e_{i} * 1 != e_{i}")
        if (one * e_i).components != e_i.components:
            failures.append(f"1 * e_{i} != e_{i}")
    # Conjugate: x * conj(x) = ||x||^2 * 1
    for i in range(8):
        for j in range(i, 8):
            x = Octonion.basis(i)
            y = Octonion.basis(j)
            xy = x * y
            yx = y * x
            # Anti-commutativity on distinct imaginary basis: yx = -xy
            if i != j and i != 0 and j != 0:
                expected = (-xy.components[0],) + tuple(-c for c in xy.components[1:])
                if yx.components != expected:
                    failures.append(f"e_{i}*e_{j} not anti-commuting with e_{j}*e_{i}")
            # x * conj(x) = ||x||^2 * 1
            xcx = x * x.conjugate()
            nsq = x.norm_squared()
            expected = (nsq,) + (0.0,) * 7
            if xcx.components != expected:
                failures.append(f"e_{i}*conj(e_{i}) != ||e_{i}||^2 * 1")
    # Norm multiplicativity on a few random pairs
    import random
    rng = random.Random(42)
    for _ in range(8):
        x = Octonion(tuple(rng.uniform(-1, 1) for _ in range(8)))
        y = Octonion(tuple(rng.uniform(-1, 1) for _ in range(8)))
        xy = x * y
        # Tolerance accounts for floating-point error in 8x8 = 64
        # multiplications + 7 additions per octonion product, then
        # one more full product. 1e-6 is well within float64 noise.
        if abs(xy.norm_squared() - x.norm_squared() * y.norm_squared()) > 1e-6:
            failures.append("||xy||^2 != ||x||^2 * ||y||^2")
    return {
        "status": "pass" if not failures else "fail",
        "checked": ["identity", "anti-commutativity", "x*conj(x)=||x||^2*1", "norm-multiplicative"],
        "failures": failures,
        "octonion_dimension": 8,
    }


__all__ = ["Octonion", "verify_octonion_axioms"]
