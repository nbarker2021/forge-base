from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
import json
from typing import Iterable, Sequence

Number = int | Fraction
Vector = tuple[Fraction, ...]
Matrix = tuple[tuple[Fraction, ...], ...]


def F(x: Number | str) -> Fraction:
    """Parse an exact rational."""
    if isinstance(x, Fraction):
        return x
    return Fraction(x)


def vec(xs: Iterable[Number | str]) -> Vector:
    return tuple(F(x) for x in xs)


def mat(rows: Iterable[Iterable[Number | str]]) -> Matrix:
    return tuple(tuple(F(x) for x in row) for row in rows)


def add(a: Vector, b: Vector) -> Vector:
    return tuple(x + y for x, y in zip(a, b, strict=True))


def sub(a: Vector, b: Vector) -> Vector:
    return tuple(x - y for x, y in zip(a, b, strict=True))


def scale(c: Number | str, a: Vector) -> Vector:
    c = F(c)
    return tuple(c * x for x in a)


def dot(a: Vector, b: Vector, gram: Matrix | None = None) -> Fraction:
    if gram is None:
        return sum(x * y for x, y in zip(a, b, strict=True))
    total = Fraction(0)
    n = len(a)
    for i in range(n):
        for j in range(n):
            total += a[i] * gram[i][j] * b[j]
    return total


def norm2(a: Vector, gram: Matrix | None = None) -> Fraction:
    return dot(a, a, gram)


def reflect(v: Vector, root: Vector, gram: Matrix) -> Vector:
    """Reflect v across the hyperplane perpendicular to root."""
    denom = norm2(root, gram)
    if denom == 0:
        raise ValueError("zero root")
    coeff = Fraction(2) * dot(v, root, gram) / denom
    return sub(v, scale(coeff, root))


def canonical_vector(v: Vector) -> str:
    return json.dumps([str(x) for x in v], separators=(",", ":"))


def canonical_matrix(m: Matrix) -> str:
    return json.dumps([[str(x) for x in row] for row in m], separators=(",", ":"))


def stable_hash(*parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


def vector_json(v: Vector) -> str:
    return json.dumps([str(x) for x in v])


def matrix_json(m: Matrix) -> str:
    return json.dumps([[str(x) for x in row] for row in m])


def parse_vector_json(s: str) -> Vector:
    return vec(json.loads(s))


def parse_matrix_json(s: str) -> Matrix:
    return mat(json.loads(s))


def identity_matrix(n: int) -> Matrix:
    return tuple(tuple(Fraction(1 if i == j else 0) for j in range(n)) for i in range(n))


def determinant(m: Matrix) -> Fraction:
    """Exact determinant by fraction-preserving Gaussian elimination."""
    n = len(m)
    if n == 0:
        return Fraction(1)
    a = [[Fraction(x) for x in row] for row in m]
    det = Fraction(1)
    sign = 1
    for i in range(n):
        pivot = None
        for r in range(i, n):
            if a[r][i] != 0:
                pivot = r
                break
        if pivot is None:
            return Fraction(0)
        if pivot != i:
            a[i], a[pivot] = a[pivot], a[i]
            sign *= -1
        piv = a[i][i]
        det *= piv
        for r in range(i + 1, n):
            if a[r][i] == 0:
                continue
            factor = a[r][i] / piv
            for c in range(i, n):
                a[r][c] -= factor * a[i][c]
    return det * sign


def fraction_json(x: Fraction) -> str:
    return str(x)
