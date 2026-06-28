from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from fractions import Fraction
from itertools import combinations, product
import re
from typing import Iterable

from .exact import F, Matrix, Vector, identity_matrix, mat, norm2, reflect, vec


@dataclass(frozen=True)
class RootSystemData:
    name: str
    rank: int
    gram: Matrix
    roots: tuple[Vector, ...]
    basis: tuple[Vector, ...]
    notes: str = ""


def closure_from_simple_roots(name: str, gram: Matrix) -> RootSystemData:
    """Generate a finite root system by Weyl-reflecting simple roots.

    Vectors are stored in simple-root coefficient coordinates. The Gram form
    supplies the exact bilinear form. This gives compact exact coordinates in
    the intrinsic rank rather than an arbitrary Euclidean over-embedding.
    """
    n = len(gram)
    basis = tuple(vec(1 if i == j else 0 for j in range(n)) for i in range(n))
    roots: set[Vector] = set(basis)
    roots.update(tuple(tuple(-x for x in r) for r in basis))
    q: deque[Vector] = deque(roots)
    while q:
        v = q.popleft()
        for alpha in basis:
            w = reflect(v, alpha, gram)
            if w not in roots:
                roots.add(w)
                q.append(w)
    ordered = tuple(sorted(roots, key=lambda x: (norm2(x, gram), tuple(x))))
    return RootSystemData(name=name, rank=n, gram=gram, roots=ordered, basis=basis)


def cartan_from_edges(rank: int, edges: Iterable[tuple[int, int]]) -> Matrix:
    rows = [[Fraction(2 if i == j else 0) for j in range(rank)] for i in range(rank)]
    for i, j in edges:
        rows[i][j] = rows[j][i] = Fraction(-1)
    return tuple(tuple(row) for row in rows)


def cartan_A(n: int) -> Matrix:
    if n < 1:
        raise ValueError("A_n requires n>=1")
    return cartan_from_edges(n, [(i, i + 1) for i in range(n - 1)])


def cartan_D(n: int) -> Matrix:
    if n < 4:
        raise ValueError("D_n requires n>=4")
    # Chain 0-1-...-(n-3), then branch from n-3 to n-2 and n-1.
    edges = [(i, i + 1) for i in range(n - 3)]
    edges.extend([(n - 3, n - 2), (n - 3, n - 1)])
    return cartan_from_edges(n, edges)


@lru_cache(maxsize=None)
def root_system_A(n: int) -> RootSystemData:
    # A_n in intrinsic simple-root coordinates. Positive roots are contiguous
    # sums alpha_i+...+alpha_j; negatives are included explicitly.
    gram = cartan_A(n)
    roots: set[Vector] = set()
    for i in range(n):
        v = [Fraction(0)] * n
        for j in range(i, n):
            v[j] = Fraction(1)
            roots.add(tuple(v))
            roots.add(tuple(-x for x in v))
    basis = tuple(vec(1 if i == j else 0 for j in range(n)) for i in range(n))
    return RootSystemData(name=f"A{n}", rank=n, gram=gram, roots=tuple(sorted(roots, key=lambda x: (norm2(x, gram), tuple(x)))), basis=basis)


@lru_cache(maxsize=None)
def root_system_D(n: int) -> RootSystemData:
    # D_n as roots ±e_i±e_j in exact Euclidean coordinates.
    roots: set[Vector] = set()
    for i, j in combinations(range(n), 2):
        for si, sj in product([1, -1], repeat=2):
            v = [Fraction(0)] * n
            v[i] = Fraction(si)
            v[j] = Fraction(sj)
            roots.add(tuple(v))
    basis: list[Vector] = []
    for i in range(n - 1):
        v = [Fraction(0)] * n
        v[i] = Fraction(1)
        v[i + 1] = Fraction(-1)
        basis.append(tuple(v))
    v = [Fraction(0)] * n
    v[n - 2] = Fraction(1)
    v[n - 1] = Fraction(1)
    basis.append(tuple(v))
    gram = identity_matrix(n)
    return RootSystemData(name=f"D{n}", rank=n, gram=gram, roots=tuple(sorted(roots, key=lambda x: (norm2(x, gram), tuple(x)))), basis=tuple(basis))


@lru_cache(maxsize=None)
def root_system_G2() -> RootSystemData:
    # Simple-root coordinates. alpha_1 short, alpha_2 long.
    # Gram [[2,-3],[-3,6]] gives Cartan entries -3 and -1.
    return closure_from_simple_roots("G2", mat([[2, -3], [-3, 6]]))


@lru_cache(maxsize=None)
def root_system_F4() -> RootSystemData:
    # F4 in intrinsic simple-root coordinates with Cartan/Gram convention:
    # alpha_1-alpha_2=>alpha_3-alpha_4, where alpha_3 is short.
    return closure_from_simple_roots("F4", mat([
        [2, -1, 0, 0],
        [-1, 2, -2, 0],
        [0, -2, 4, -2],
        [0, 0, -2, 4],
    ]))


@lru_cache(maxsize=None)
def root_system_E6() -> RootSystemData:
    # E6 as a three-arm simply-laced tree with arm lengths 2,2,1.
    return closure_from_simple_roots("E6", cartan_from_edges(6, [(2, 0), (0, 1), (2, 3), (3, 4), (2, 5)]))


@lru_cache(maxsize=None)
def root_system_E7() -> RootSystemData:
    # E7 as a three-arm simply-laced tree with arm lengths 2,3,1.
    return closure_from_simple_roots("E7", cartan_from_edges(7, [(2, 0), (0, 1), (2, 3), (3, 4), (4, 6), (2, 5)]))


@lru_cache(maxsize=None)
def root_system_E8() -> RootSystemData:
    # E8 as a three-arm simply-laced tree with arm lengths 2,4,1.
    return closure_from_simple_roots("E8", cartan_from_edges(8, [(2, 0), (0, 1), (2, 3), (3, 4), (4, 6), (6, 7), (2, 5)]))


def core_root_systems() -> dict[str, RootSystemData]:
    return {
        "A1": root_system_A(1),
        "A2": root_system_A(2),
        "D4": root_system_D(4),
        "G2": root_system_G2(),
        "F4": root_system_F4(),
        "E6": root_system_E6(),
        "E7": root_system_E7(),
        "E8": root_system_E8(),
    }


@lru_cache(maxsize=None)
def component_root_system(family: str, rank: int) -> RootSystemData:
    family = family.upper()
    if family == "A":
        return root_system_A(rank)
    if family == "D":
        return root_system_D(rank)
    if family == "E" and rank == 6:
        return root_system_E6()
    if family == "E" and rank == 7:
        return root_system_E7()
    if family == "E" and rank == 8:
        return root_system_E8()
    raise ValueError(f"unsupported component root system: {family}{rank}")


def parse_root_system_label(label: str) -> list[tuple[str, int, int]]:
    """Parse labels like 'A5^4 D4', 'D10 E7^2', 'A1^24'.

    Returns (family, rank, multiplicity) triples.
    """
    label = label.strip()
    if not label or label == "rootless":
        return []
    out: list[tuple[str, int, int]] = []
    for token in label.split():
        m = re.fullmatch(r"([ADE])(\d+)(?:\^(\d+))?", token)
        if not m:
            raise ValueError(f"unsupported root-system token: {token!r} in {label!r}")
        fam, rank, mult = m.group(1), int(m.group(2)), int(m.group(3) or 1)
        out.append((fam, rank, mult))
    return out


def block_diag(mats: list[Matrix]) -> Matrix:
    size = sum(len(m) for m in mats)
    rows = [[Fraction(0) for _ in range(size)] for _ in range(size)]
    off = 0
    for m in mats:
        for i, row in enumerate(m):
            for j, val in enumerate(row):
                rows[off + i][off + j] = val
        off += len(m)
    return tuple(tuple(r) for r in rows)


def direct_sum_root_system(name: str, components: list[tuple[str, int, int]]) -> RootSystemData:
    """Direct-sum ADE components into an exact rank-sum root system.

    Only the root system/minimal root shell is generated here, not the full
    Niemeier overlattice glue. This is intentionally the rootful terminal
    template layer.
    """
    component_instances: list[RootSystemData] = []
    for fam, rank, mult in components:
        for _ in range(mult):
            component_instances.append(component_root_system(fam, rank))
    total_rank = sum(c.rank for c in component_instances)
    grams = [c.gram for c in component_instances]
    gram = block_diag(grams)
    roots: list[Vector] = []
    basis: list[Vector] = []
    off = 0
    for comp in component_instances:
        for r in comp.roots:
            v = [Fraction(0)] * total_rank
            for i, x in enumerate(r):
                v[off + i] = x
            roots.append(tuple(v))
        for b in comp.basis:
            v = [Fraction(0)] * total_rank
            for i, x in enumerate(b):
                v[off + i] = x
            basis.append(tuple(v))
        off += comp.rank
    return RootSystemData(
        name=name,
        rank=total_rank,
        gram=gram,
        roots=tuple(sorted(set(roots), key=lambda x: tuple(x))),
        basis=tuple(basis),
        notes="direct-sum root shell; glue/overlattice data stored separately",
    )
