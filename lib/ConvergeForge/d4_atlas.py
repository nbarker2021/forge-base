"""ConvergeForge.d4_atlas — the 8-chart dihedral atlas, proven bijective.

Closes the ConvergeForge open obligation (chart8 D4 atlas bijectivity) left
by the triality-annealing promotion. Distilled from product_converge
(src/state/chart8.py) and CMPLX-TMN-main board atlases.

Paper binding: CQE-paper-03 (D4 / J3 triality surface) — the same paper that
hosts the S3 triality annealing. The 8 chart views are the dihedral group D4
(order 8 = 2*4): four rotations r^0..r^3 and four mirror-rotations s, sr,
sr^2, sr^3. Every view is a bijection of the square's four corners, so
applying a view and then its inverse returns the original state exactly
(the source's stated invariant view(view_inverse(state)) == state).

Stdlib only. The group is generated and checked exhaustively from the two
generators r (rotation) and s (reflection); nothing is asserted by name.
"""
from __future__ import annotations

from typing import Any

# Corners of the square, labeled 0..3 clockwise.
CORNERS = (0, 1, 2, 3)

# Generators as permutations: perm[i] = image of corner i.
ROT = (1, 2, 3, 0)        # r: 90-degree rotation
REFLECT = (0, 3, 2, 1)    # s: reflection fixing corners 0 and 2

VIEW_NAMES = (
    "rotate_0", "rotate_90", "rotate_180", "rotate_270",
    "mirror_rotate_0", "mirror_rotate_90", "mirror_rotate_180", "mirror_rotate_270",
)


def compose(p: tuple[int, ...], q: tuple[int, ...]) -> tuple[int, ...]:
    """(p . q)(i) = p(q(i)) — apply q first, then p."""
    return tuple(p[q[i]] for i in CORNERS)


def inverse(p: tuple[int, ...]) -> tuple[int, ...]:
    inv = [0] * len(p)
    for i, pi in enumerate(p):
        inv[pi] = i
    return tuple(inv)


def identity() -> tuple[int, ...]:
    return CORNERS


def d4_elements() -> list[tuple[int, ...]]:
    """The 8 dihedral views: r^k and s.r^k for k = 0..3, in atlas order."""
    rots = [identity()]
    for _ in range(3):
        rots.append(compose(ROT, rots[-1]))
    mirrors = [compose(REFLECT, r) for r in rots]
    return rots + mirrors


def apply_view(view: tuple[int, ...], state: tuple[Any, ...]) -> tuple[Any, ...]:
    """Re-address a 4-slot state through a view: out[i] = state[view(i)]."""
    return tuple(state[view[i]] for i in CORNERS)


# ─── Finite verifier (paper-bound claims, CQE-paper-03) ─────────────────────

def verify() -> dict[str, Any]:
    """Run the 10 finite checks binding the D4 atlas to CQE-paper-03."""
    checks: dict[str, bool] = {}
    views = d4_elements()
    vset = set(views)

    # 1. Exactly 8 distinct views (|D4| = 8 = 2*4)
    checks["eight_distinct_views"] = len(views) == 8 == len(vset)

    # 2. Every view is a bijection of the 4 corners (a permutation)
    checks["every_view_is_bijection"] = all(
        sorted(v) == list(CORNERS) for v in views
    )

    # 3. Closure: composing any two views yields a view (8x8 table)
    checks["group_closed_under_composition"] = all(
        compose(a, b) in vset for a in views for b in views
    )

    # 4. Identity is present and acts as a unit
    e = identity()
    checks["identity_present_and_unit"] = (
        e in vset and all(compose(e, v) == v == compose(v, e) for v in views)
    )

    # 5. Every view has an inverse inside the group, and
    #    view(view_inverse(state)) == state exactly (the source invariant)
    state = ("A", "B", "C", "D")
    ok5 = True
    for v in views:
        vi = inverse(v)
        ok5 &= vi in vset
        ok5 &= apply_view(v, apply_view(vi, state)) == state
    checks["inverses_present_and_roundtrip_identity"] = ok5

    # 6. The four rotations form a cyclic subgroup of order 4
    rots = views[:4]
    checks["rotations_cyclic_order_4"] = (
        compose(ROT, compose(ROT, compose(ROT, ROT))) == e
        and len(set(rots)) == 4
        and all(compose(a, b) in set(rots) for a in rots for b in rots)
    )

    # 7. The four mirrors are involutions (order 2)
    mirrors = views[4:]
    checks["mirrors_are_involutions"] = all(compose(m, m) == e for m in mirrors)

    # 8. D4 is non-abelian: rotation and reflection do not commute
    checks["non_abelian"] = compose(ROT, REFLECT) != compose(REFLECT, ROT)

    # 9. Information preservation: the 8 views of a 4-distinct-symbol state
    #    are all permutations of the same multiset (no symbol lost or gained)
    imgs = [apply_view(v, state) for v in views]
    checks["views_preserve_information"] = all(
        sorted(img) == sorted(state) for img in imgs
    )

    # 10. The atlas exposes exactly 8 named views matching the group order
    checks["named_views_match_group"] = len(VIEW_NAMES) == len(views) == 8

    return {
        "forge": "ConvergeForge",
        "module": "d4_atlas",
        "paper": "CQE-paper-03",
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2))
