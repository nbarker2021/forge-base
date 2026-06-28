"""E8Forge — exact E8 lattice membership, roots, and closure receipts.

Distilled from CMPLXUNI (profile repo) into the forge ring.
Paper binding: CQE-paper-08 (Lattice Closure). E8 is the even unimodular
closure frame in 8 dimensions: 240 roots of norm^2 = 2 (112 integer
(+-1, +-1, 0^6) plus 128 half-integer (+-1/2)^8 with an even number of
minus signs), Weyl group order 696,729,600 = 4! * 6! * 8!.

All arithmetic is exact: points are carried in DOUBLED coordinates
(u = 2v, integers), so membership is

    u all even or all odd,  and  sum(u) == 0 (mod 4)

with norm^2(v) = norm^2(u) / 4. No floats, no numpy.

Adjudicated divergences from the source repo:
  1. lfai/cona_e8.constructionA_E8_check is a self-declared surrogate whose
     conditions are provably wrong as E8 membership: its mod-8 constraint
     rejects ALL 112 integer roots (sum x^2 = 2), and its integer-only API
     cannot represent the 128 half-integer roots. E8Forge replaces it with
     exact membership; the surrogate's misclassification is verified here
     as a check, not silently discarded.
  2. src/cmplx/lattice/e8.py carries the real structure but is numpy-bound
     and trusts its own generation; E8Forge is stdlib-exact and verifies
     counts, closure, and minimality finitely.
  3. lfai/ledger_merkle.py hash-chain logic is sound but hardcodes a POSIX
     data path; ledger receipts remain ChromaForge territory.

Stdlib only.
"""
from __future__ import annotations

import itertools
from typing import Any, Iterable, Optional

WEYL_ORDER = 696_729_600


def is_e8_doubled(u: tuple[int, ...]) -> bool:
    """Exact E8 membership in doubled coordinates (u = 2v)."""
    if len(u) != 8:
        return False
    parities = {x & 1 for x in u}
    if len(parities) != 1:
        return False
    return sum(u) % 4 == 0


def norm2_doubled(u: tuple[int, ...]) -> int:
    """4 * norm^2(v) for u = 2v. A point is a root iff this equals 8."""
    return sum(x * x for x in u)


def inner_doubled(u: tuple[int, ...], w: tuple[int, ...]) -> int:
    """4 * <v, v'> for doubled coordinates."""
    return sum(a * b for a, b in zip(u, w))


def roots() -> list[tuple[int, ...]]:
    """All 240 E8 roots in doubled coordinates (norm2_doubled == 8).

    112 integer roots: (+-2, +-2, 0^6) over all position pairs and signs.
    128 half-integer roots: (+-1)^8 with an even number of minus signs.
    """
    out: list[tuple[int, ...]] = []
    for i, j in itertools.combinations(range(8), 2):
        for si, sj in itertools.product((2, -2), repeat=2):
            u = [0] * 8
            u[i], u[j] = si, sj
            out.append(tuple(u))
    for signs in itertools.product((1, -1), repeat=8):
        if signs.count(-1) % 2 == 0:
            out.append(signs)
    return out


def simple_roots(root_list: Optional[list[tuple[int, ...]]] = None
                 ) -> list[tuple[int, ...]]:
    """Derive a simple system algorithmically: positive roots under a
    generic integer functional; simple = positive and not a sum of two
    positives. Convention-free and exact."""
    rs = root_list if root_list is not None else roots()
    weights = (64, 32, 16, 8, 4, 2, 1, 97)  # generic: no root maps to 0
    def f(u: tuple[int, ...]) -> int:
        return sum(w * x for w, x in zip(weights, u))
    positives = [u for u in rs if f(u) > 0]
    pos_set = set(positives)
    simples = []
    for u in positives:
        if not any(
            tuple(u[k] - p[k] for k in range(8)) in pos_set for p in positives
            if p != u
        ):
            simples.append(u)
    return simples


def cartan_matrix(simples: list[tuple[int, ...]]) -> list[list[int]]:
    """A_ij = 2<ai, aj>/<aj, aj>; for norm^2 = 2 roots this is <ai, aj>."""
    return [[(2 * inner_doubled(a, b)) // norm2_doubled(b)
             for b in simples] for a in simples]


def det_int(m: list[list[int]]) -> int:
    """Exact integer determinant via fraction-free Gaussian elimination."""
    from fractions import Fraction
    n = len(m)
    a = [[Fraction(x) for x in row] for row in m]
    det = Fraction(1)
    for col in range(n):
        pivot = next((r for r in range(col, n) if a[r][col] != 0), None)
        if pivot is None:
            return 0
        if pivot != col:
            a[col], a[pivot] = a[pivot], a[col]
            det = -det
        det *= a[col][col]
        inv = a[col][col]
        for r in range(col + 1, n):
            factor = a[r][col] / inv
            for c in range(col, n):
                a[r][c] -= factor * a[col][c]
    assert det.denominator == 1
    return int(det)


def surrogate_check(v8: Iterable[int]) -> bool:
    """The CMPLXUNI lfai surrogate, reproduced verbatim for adjudication:
    legal iff sum even, sum of squares even, sum of squares % 8 == 0."""
    v = list(v8)
    return (sum(v) % 2 == 0
            and sum(x * x for x in v) % 2 == 0
            and sum(x * x for x in v) % 8 == 0)


# ─── Finite verifier (paper-bound claims, CQE-paper-08) ─────────────────────

def verify() -> dict[str, Any]:
    """Run the 10 finite checks that bind E8Forge to CQE-paper-08."""
    checks: dict[str, bool] = {}
    rs = roots()
    rset = set(rs)

    # 1. Exactly 240 roots: 112 integer + 128 half-integer, no duplicates
    integer_roots = [u for u in rs if all(x % 2 == 0 for x in u)]
    half_roots = [u for u in rs if all(x % 2 == 1 for x in u)]
    checks["root_count_240_split_112_128"] = (
        len(rs) == 240 == len(rset)
        and len(integer_roots) == 112
        and len(half_roots) == 128
    )

    # 2. Every root is an E8 point of norm^2 = 2
    checks["all_roots_member_and_norm2_2"] = all(
        is_e8_doubled(u) and norm2_doubled(u) == 8 for u in rs
    )

    # 3. Half-integer roots have an even number of minus signs (2^7 = 128)
    checks["half_roots_even_minus_signs"] = all(
        u.count(-1) % 2 == 0 for u in half_roots
    )

    # 4. Weyl order closed forms: 696729600 = 4!*6!*8! = 2^14 * 3^5 * 5^2 * 7
    import math
    checks["weyl_order_factorizations"] = (
        WEYL_ORDER == math.factorial(4) * math.factorial(6) * math.factorial(8)
        == 2 ** 14 * 3 ** 5 * 5 ** 2 * 7
    )

    # 5. Root inner products lie in {-2,-1,0,1,2}; -2 exactly at antipodes
    ok5 = True
    for u in rs:
        for w in rs:
            ip4 = inner_doubled(u, w)          # 4 * <v, w>
            ok5 &= ip4 % 4 == 0 or ip4 % 2 == 0  # exact: ip4 in {-8,-4,0,4,8}
            ok5 &= ip4 in (-8, -4, 0, 4, 8)
            if ip4 == -8:
                ok5 &= w == tuple(-x for x in u)
    checks["inner_products_bounded_antipodal_minus2"] = ok5

    # 6. Lattice closure: the sum of any two roots is an E8 point (240^2)
    checks["closed_under_root_addition"] = all(
        is_e8_doubled(tuple(a + b for a, b in zip(u, w)))
        for u in rs for w in rs
    )

    # 7. Evenness: norm^2 of every root pair sum is even (in {0,2,4,6,8})
    sums_norms = {norm2_doubled(tuple(a + b for a, b in zip(u, w))) // 4
                  for u in rs for w in rs}
    checks["even_lattice_pair_sums"] = (
        sums_norms <= {0, 2, 4, 6, 8} and all(n % 2 == 0 for n in sums_norms)
    )

    # 8. Minimal norm is 2: no E8 point with norm^2 = 1 (exhaustive over
    #    doubled vectors of norm 4: the 16 vectors +-2 e_i, all rejected;
    #    all-odd vectors have norm2_doubled >= 8)
    candidates = []
    for i in range(8):
        for s in (2, -2):
            u = [0] * 8
            u[i] = s
            candidates.append(tuple(u))
    checks["minimum_norm2_is_2"] = (
        all(not is_e8_doubled(u) for u in candidates)
        and min(norm2_doubled(u) for u in half_roots) == 8
    )

    # 9. A simple system of 8 roots exists with Cartan diagonal 2,
    #    off-diagonal in {0,-1}, determinant 1, one degree-3 node
    simples = simple_roots(rs)
    cm = cartan_matrix(simples)
    degs = [sum(1 for j in range(len(simples)) if i != j and cm[i][j] == -1)
            for i in range(len(simples))]
    checks["simple_system_cartan_e8"] = (
        len(simples) == 8
        and all(cm[i][i] == 2 for i in range(8))
        and all(cm[i][j] in (0, -1) for i in range(8) for j in range(8) if i != j)
        and det_int(cm) == 1
        and sorted(degs) == [1, 1, 1, 2, 2, 2, 2, 3]
    )

    # 10. Surrogate adjudication: the CMPLXUNI cona_e8 surrogate rejects
    #     every one of the 112 integer roots (true E8 members), so it is
    #     not E8 membership
    int_roots_v = [tuple(x // 2 for x in u) for u in integer_roots]
    checks["cmplxuni_surrogate_rejects_all_112_integer_roots"] = all(
        not surrogate_check(v) and is_e8_doubled(tuple(2 * x for x in v))
        for v in int_roots_v
    )

    return {
        "forge": "E8Forge",
        "paper": "CQE-paper-08",
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2))
