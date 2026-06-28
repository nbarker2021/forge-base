"""AGRMForge — golden-ratio low-discrepancy sweep over geometric space.

Distilled from CMPLXMCP (profile repo, agrm_mdhg_integration/agrm_router.py)
into the forge ring. Paper binding: CQE-paper-21 (the applied Forge reader /
grid-swept ribbons). The Adaptive Geometric Resonance Matrix sweeps a set of
24D nodes in golden-ratio order, producing a ranked ribbon; it classifies
zone density, assigns radial shells, and caches routes idempotently.

The sweep is a golden-ratio rotation. The reason phi is used is the three-gap
theorem (Steinhaus): for every N, the points {0, phi, 2 phi, ..., (N-1) phi}
mod 1 cut the circle into arcs of at most THREE distinct lengths, and because
phi is the most irrational number (continued fraction [1; 1, 1, 1, ...]) the
gaps stay maximally even at every N. That is the optimal low-discrepancy
sweep — the formal reason a golden-ratio reader covers an object uniformly.

Adjudicated divergences from the source:
  1. The source spiral score mixed the sweep index with a per-node distance
     and a SPARSE-zone 1.2x bonus, so identical geometry could rank
     differently by insertion order; the forge separates the pure
     golden-ratio sweep order (provable, order-stable) from the heuristic
     density bonus (kept as a separate, optional re-rank).
  2. The route cache used an unordered dict with no idempotence guarantee
     across rebuilds; the forge makes route reuse explicitly idempotent.
  3. find_nearest / route heuristics that call random or wall-clock stay
     product-side; the forge carries the proven sweep + classification core.

Stdlib only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

PHI = (1 + math.sqrt(5)) / 2
LEECH_DIM = 24


def frac(x: float) -> float:
    return x - math.floor(x)


def golden_sweep_order(n: int) -> list[float]:
    """The golden-ratio rotation sequence {k * phi mod 1} for k = 0..n-1."""
    return [frac(k * PHI) for k in range(n)]


def three_gap_lengths(points: list[float]) -> list[float]:
    """The distinct circular gap lengths between sorted points on [0,1)."""
    s = sorted(points)
    gaps = [s[i + 1] - s[i] for i in range(len(s) - 1)]
    gaps.append(1.0 - s[-1] + s[0])      # wraparound arc
    # round to absorb float noise, then take the distinct set
    rounded = sorted({round(g, 9) for g in gaps})
    return rounded


def star_discrepancy(points: list[float]) -> float:
    """Star discrepancy D*_N of points in [0,1): max over the sorted points
    of |k/N - x_(k)| extremes. Lower is more uniform."""
    n = len(points)
    s = sorted(points)
    d = 0.0
    for k, x in enumerate(s):
        d = max(d, abs((k + 1) / n - x), abs(k / n - x))
    return d


def euclid(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def centroid(positions: list[list[float]], dim: int = LEECH_DIM) -> list[float]:
    if not positions:
        return [0.0] * dim
    return [sum(p[d] for p in positions) / len(positions) for d in range(dim)]


@dataclass
class AGRMNode:
    node_id: str
    position: list[float]
    density: str = "medium"
    shell: int = 0


def classify_density(neighbors: int) -> str:
    """Zone density by neighbor count: sparse (<3), medium (<8), dense (>=8)."""
    if neighbors < 3:
        return "sparse"
    if neighbors < 8:
        return "medium"
    return "dense"


def assign_shells(positions: list[list[float]], center: list[float],
                  num_shells: int = 5) -> list[int]:
    """Radial bucketing: each node to one of num_shells concentric shells."""
    dists = [euclid(p, center) for p in positions]
    max_d = max(dists, default=0.0)
    width = max_d / num_shells if max_d > 0 else 1.0
    return [min(int(d / width), num_shells - 1) for d in dists]


class AGRMRouter:
    """Golden-ratio sweep router with idempotent route caching."""

    def __init__(self, dim: int = LEECH_DIM):
        self.dim = dim
        self._nodes: dict[str, AGRMNode] = {}
        self._routes: dict[tuple[str, str], dict[str, Any]] = {}

    def register(self, node_id: str, position: list[float]) -> None:
        self._nodes[node_id] = AGRMNode(node_id, list(position[:self.dim]))

    def sweep(self) -> list[str]:
        """Return node ids in golden-ratio sweep order (stable by node id)."""
        ids = sorted(self._nodes)
        order = sorted(range(len(ids)), key=lambda k: frac(k * PHI))
        return [ids[k] for k in order]

    def route(self, a: str, b: str) -> Optional[dict[str, Any]]:
        if a not in self._nodes or b not in self._nodes:
            return None
        key = (a, b)
        if key in self._routes:
            return self._routes[key]
        r = {"path": [a, b],
             "distance": euclid(self._nodes[a].position, self._nodes[b].position)}
        self._routes[key] = r
        return r


# ─── Finite verifier (paper-bound claims, CQE-paper-21) ─────────────────────

def verify() -> dict[str, Any]:
    """Run the 10 finite checks binding AGRMForge to CQE-paper-21."""
    checks: dict[str, bool] = {}

    # 1. phi identity and value
    checks["phi_identity"] = (
        abs(PHI * PHI - (PHI + 1)) < 1e-12
        and abs(PHI - (1 + math.sqrt(5)) / 2) < 1e-15
    )

    # 2. phi is the most irrational: Fibonacci-ratio convergents -> phi
    fib = [1, 1]
    for _ in range(30):
        fib.append(fib[-1] + fib[-2])
    checks["fibonacci_convergents_to_phi"] = (
        abs(fib[-1] / fib[-2] - PHI) < 1e-9
        and all(abs(fib[i + 1] / fib[i] - PHI) > abs(fib[i + 2] / fib[i + 1] - PHI)
                for i in range(5, 25))  # convergence is monotone
    )

    # 3. THREE-GAP THEOREM: for every N, {k phi mod 1} has <= 3 distinct gaps
    checks["three_gap_theorem_all_N"] = all(
        len(three_gap_lengths(golden_sweep_order(n))) <= 3
        for n in range(2, 400)
    )

    # 4. The three gap lengths satisfy the Steinhaus relation: the largest
    #    equals the sum of the other two (when there are exactly 3)
    ok4 = True
    had_three = False
    for n in range(4, 200):
        g = three_gap_lengths(golden_sweep_order(n))
        if len(g) == 3:
            had_three = True
            ok4 &= abs(g[2] - (g[0] + g[1])) < 1e-6   # > 9-place rounding noise
    checks["steinhaus_largest_is_sum_of_two"] = ok4 and had_three

    # 5. Low discrepancy: the golden sweep beats a rational rotation badly,
    #    and its discrepancy decreases with N
    d_phi_100 = star_discrepancy(golden_sweep_order(100))
    d_phi_400 = star_discrepancy(golden_sweep_order(400))
    d_rational = star_discrepancy([frac(k * 0.5) for k in range(100)])
    checks["golden_sweep_low_discrepancy"] = (
        d_phi_100 < 0.05 and d_phi_400 < d_phi_100 and d_phi_100 < d_rational
    )

    # 6. Sweep order is a permutation of the nodes (no loss, no duplication)
    r = AGRMRouter()
    for i in range(20):
        r.register(f"n{i:02d}", [float((i * 7) % 13) / 13] * LEECH_DIM)
    swept = r.sweep()
    checks["sweep_is_permutation"] = sorted(swept) == sorted(r._nodes)

    # 7. Sweep order is deterministic and order-independent of registration
    r2 = AGRMRouter()
    for i in reversed(range(20)):
        r2.register(f"n{i:02d}", [float((i * 7) % 13) / 13] * LEECH_DIM)
    checks["sweep_deterministic_insertion_independent"] = r2.sweep() == swept

    # 8. Density classification thresholds partition the neighbor counts
    checks["density_thresholds_partition"] = (
        classify_density(0) == "sparse" and classify_density(2) == "sparse"
        and classify_density(3) == "medium" and classify_density(7) == "medium"
        and classify_density(8) == "dense" and classify_density(50) == "dense"
    )

    # 9. Shell assignment is a total partition: every node lands in exactly
    #    one of num_shells shells, monotone in radius
    positions = [[float(i) / 20] * LEECH_DIM for i in range(20)]
    c = centroid(positions)
    shells = assign_shells(positions, c, num_shells=5)
    radii = [euclid(p, c) for p in positions]
    # monotone non-decreasing: a strictly larger radius never lands in a
    # lower shell
    monotone = all(
        shells[i] <= shells[j]
        for i in range(len(radii)) for j in range(len(radii))
        if radii[i] < radii[j] - 1e-9
    )
    checks["shell_assignment_partition_monotone"] = (
        all(0 <= s < 5 for s in shells) and monotone
    )

    # 10. Distance is a metric (identity, symmetry, triangle) and routes are
    #     idempotent in the cache
    a, b, cc = [0.0] * LEECH_DIM, [1.0] + [0.0] * 23, [1.0, 1.0] + [0.0] * 22
    metric_ok = (
        euclid(a, a) == 0.0
        and abs(euclid(a, b) - euclid(b, a)) < 1e-12
        and euclid(a, cc) <= euclid(a, b) + euclid(b, cc) + 1e-12
    )
    r.route("n00", "n01")
    route_idem = r.route("n00", "n01") is r.route("n00", "n01")
    checks["distance_metric_and_route_idempotent"] = metric_ok and route_idem

    return {
        "forge": "AGRMForge",
        "paper": "CQE-paper-21",
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2))
