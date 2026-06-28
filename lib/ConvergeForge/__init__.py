"""ConvergeForge — S3 transposition annealing with a tight 3-swap bound.

Distilled from product_converge (historical_pastworks) into the forge ring.
Paper binding: CQE-paper-03 (D4/J3 triality surface). S3 is the triality
group: the three transpositions permute the (L, C, R) lanes, and annealing
drives any 3-bit state into the Lie-conjugate basin (L = R) in at most
3 swaps under the fixed sequence (LR, LC, CR).

Adjudicated corrections to the source product:
  1. The product docstring claimed (1,1,0) requires exactly 3 swaps. It
     requires 2. The tight 3-swap states are (0,1,1) and (1,0,0); the bound
     itself (max 3) is correct and verified exhaustively here.
  2. The gRPC/REST/consensus/cluster layers stay product-side; the forge
     carries only the proven annealing core.

Stdlib only.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional

ALL_STATES: list[tuple[int, int, int]] = [
    (L, C, R) for L in (0, 1) for C in (0, 1) for R in (0, 1)
]

# The Lie-conjugate basin: states with L = R (fixed points of triality mirror)
LIE_CONJUGATES = frozenset(s for s in ALL_STATES if s[0] == s[2])

# Circle classification of the conjugate basin
CIRCLE_F = frozenset({(0, 1, 0), (1, 1, 1)})
CIRCLE_P = frozenset({(0, 0, 0), (1, 0, 1)})

# Tight states: the only states needing the full 3 swaps under (LR, LC, CR)
TIGHT_STATES = frozenset({(0, 1, 1), (1, 0, 0)})


def swap_lr(s: tuple[int, int, int]) -> tuple[int, int, int]:
    return (s[2], s[1], s[0])


def swap_lc(s: tuple[int, int, int]) -> tuple[int, int, int]:
    return (s[1], s[0], s[2])


def swap_cr(s: tuple[int, int, int]) -> tuple[int, int, int]:
    return (s[0], s[2], s[1])


SWAPS: dict[str, Callable[[tuple[int, int, int]], tuple[int, int, int]]] = {
    "swap_lr": swap_lr,
    "swap_lc": swap_lc,
    "swap_cr": swap_cr,
}

DEFAULT_SEQUENCE: tuple[str, ...] = ("swap_lr", "swap_lc", "swap_cr")


@dataclass(frozen=True)
class AnnealingResult:
    """Full deterministic trace of one annealing run."""
    start: tuple[int, int, int]
    final: tuple[int, int, int]
    steps: int
    swaps_applied: tuple[str, ...]
    trajectory: tuple[tuple[int, int, int], ...]
    converged: bool

    @property
    def trace_hash(self) -> str:
        payload = f"{self.start}:{self.swaps_applied}:{self.final}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": list(self.start),
            "final": list(self.final),
            "steps": self.steps,
            "swaps_applied": list(self.swaps_applied),
            "trajectory": [list(t) for t in self.trajectory],
            "converged": self.converged,
            "trace_hash": self.trace_hash,
        }


def anneal(state: tuple[int, int, int],
           sequence: Optional[Iterable[str]] = None) -> AnnealingResult:
    """Drive a state into the Lie-conjugate basin, at most 3 swaps.

    Applies the fixed sequence in order, stopping as soon as the state is
    conjugate. Deterministic: same input, same trace.
    """
    seq = tuple(sequence or DEFAULT_SEQUENCE)
    current = state
    trajectory = [state]
    applied: list[str] = []
    for name in seq[:3]:
        if current in LIE_CONJUGATES:
            break
        current = SWAPS[name](current)
        trajectory.append(current)
        applied.append(name)
    return AnnealingResult(
        start=state,
        final=current,
        steps=len(applied),
        swaps_applied=tuple(applied),
        trajectory=tuple(trajectory),
        converged=current in LIE_CONJUGATES,
    )


def classify_state(state: tuple[int, int, int]) -> dict[str, Any]:
    L, C, R = state
    conj = state in LIE_CONJUGATES
    return {
        "state": list(state),
        "lie_conjugate": conj,
        "circle": ("F" if state in CIRCLE_F else "P") if conj else None,
        "correction_fires": C == 1 and R == 0,
        "geometry_level": 0 if conj else 1,
        "rule30_emitted_bit": L ^ (C | R),
    }


@dataclass(frozen=True)
class ConvergenceBound:
    """The proof object: exhaustively verified convergence guarantee."""
    group_name: str = "S3"
    state_space_size: int = 8
    max_swaps: int = 3
    tight_states: tuple = tuple(sorted(TIGHT_STATES))
    proof_reference: str = "exhaustive enumeration over {0,1}^3 under (LR, LC, CR)"

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_name": self.group_name,
            "state_space_size": self.state_space_size,
            "max_swaps": self.max_swaps,
            "tight_states": [list(s) for s in self.tight_states],
            "proof_reference": self.proof_reference,
        }


def schedule_triple(loads: tuple[float, float, float],
                    threshold: float) -> dict[str, Any]:
    """Map a 3-node load triple to a reassignment plan via annealing.

    Encodes each load as a bit (above/below threshold), anneals the triple
    into the conjugate basin, and reports the swap plan. Each swap names a
    pair of lanes whose tasks exchange; at most 3 reassignments.
    """
    state = tuple(1 if x > threshold else 0 for x in loads)
    result = anneal(state)  # type: ignore[arg-type]
    return {
        "input_loads": list(loads),
        "encoded_state": list(result.start),
        "reassignments": list(result.swaps_applied),
        "final_state": list(result.final),
        "balanced": result.converged,
        "bound": ConvergenceBound().to_dict(),
    }


# ─── Finite verifier (paper-bound claims, CQE-paper-03) ─────────────────────

def _perm_of(name: str) -> tuple[int, int, int]:
    """The position permutation each swap realizes."""
    return {"swap_lr": (2, 1, 0), "swap_lc": (1, 0, 2), "swap_cr": (0, 2, 1)}[name]


def _compose(p: tuple[int, int, int], q: tuple[int, int, int]) -> tuple[int, int, int]:
    return (q[p[0]], q[p[1]], q[p[2]])


def verify() -> dict[str, Any]:
    """Run the 10 finite checks that bind ConvergeForge to CQE-paper-03."""
    checks: dict[str, bool] = {}

    # 1. The conjugate basin is exactly the four L=R states
    checks["lie_conjugates_are_the_4_lr_equal_states"] = (
        LIE_CONJUGATES == {(0, 0, 0), (0, 1, 0), (1, 0, 1), (1, 1, 1)}
    )

    # 2. Each swap is an involution on all 8 states
    checks["swaps_are_involutions"] = all(
        SWAPS[n](SWAPS[n](s)) == s for n in SWAPS for s in ALL_STATES
    )

    # 3. The three transpositions generate all of S3 (order 6)
    gens = [_perm_of(n) for n in SWAPS]
    group = {(0, 1, 2)}
    frontier = list(group)
    while frontier:
        p = frontier.pop()
        for g in gens:
            q = _compose(p, g)
            if q not in group:
                group.add(q)
                frontier.append(q)
    checks["transpositions_generate_s3_order_6"] = len(group) == 6

    # 4. Every state converges within 3 swaps (exhaustive)
    results = {s: anneal(s) for s in ALL_STATES}
    checks["all_8_states_converge_within_3"] = all(
        r.converged and r.steps <= 3 for r in results.values()
    )

    # 5. The bound is tight and the tight states are (0,1,1) and (1,0,0)
    #    (corrects the source docstring, which named (1,1,0))
    three_step = {s for s, r in results.items() if r.steps == 3}
    checks["tight_bound_is_3_at_011_and_100"] = (
        max(r.steps for r in results.values()) == 3
        and three_step == set(TIGHT_STATES)
    )

    # 6. Conjugate states anneal in zero steps, unchanged
    checks["conjugates_anneal_in_zero_steps"] = all(
        results[s].steps == 0 and results[s].final == s for s in LIE_CONJUGATES
    )

    # 7. Annealing is idempotent: f(f(x)) = f(x)
    checks["annealing_idempotent"] = all(
        anneal(r.final).final == r.final and anneal(r.final).steps == 0
        for r in results.values()
    )

    # 8. Trajectory replay: recorded swaps reproduce the final state, one
    #    transposition per step
    ok8 = True
    for s, r in results.items():
        cur = s
        for i, name in enumerate(r.swaps_applied):
            nxt = SWAPS[name](cur)
            ok8 &= nxt == r.trajectory[i + 1]
            cur = nxt
        ok8 &= cur == r.final
    checks["trajectory_replay_deterministic"] = ok8

    # 9. Circle classes F and P partition the conjugate basin disjointly
    checks["circle_partition_of_conjugates"] = (
        CIRCLE_F | CIRCLE_P == LIE_CONJUGATES and not (CIRCLE_F & CIRCLE_P)
    )

    # 10. Scheduler mapping: an unbalanced load triple balances in <= 3
    #     reassignments; a balanced one needs none
    plan_hot = schedule_triple((90.0, 95.0, 10.0), threshold=50.0)
    plan_ok = schedule_triple((10.0, 90.0, 10.0), threshold=50.0)
    checks["scheduler_balances_within_3_reassignments"] = (
        plan_hot["balanced"] and len(plan_hot["reassignments"]) <= 3
        and plan_ok["balanced"] and len(plan_ok["reassignments"]) == 0
    )

    return {
        "forge": "ConvergeForge",
        "paper": "CQE-paper-03",
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2))
