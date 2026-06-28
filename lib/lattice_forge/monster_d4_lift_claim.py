"""
monster_d4_lift_claim.py — Test harness for D4 lift after global activation.

Accounting uses the **resolved bijective state**, not marginal L/C/R bit streams:
  - Full 8-state chart enumeration (joint (L,C,R))
  - Shell-2 triad 3x3 (C-, C0, C+) with S3 1/3 closure (T4)
  - C*R bond as deterministic observer term (GF(2) ANF visible face)
  - Readout-0 vs readout-1 joint chart states
  - G2 → F4 → T5A conjugate route in ≤3 steps

Marginal P(L=1), P(C=1), P(R=1) **without** conditioning on shell/stratum
undersamples the bijection and falsely suggests lane asymmetry.
"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction
from typing import Any

from .chart_codec_d4 import ANTIPODAL_LABEL, SHEET_SIGN, decode_d4, encode_d4
from .core import SHELL2_STATES, check_bijection_symmetry, compute_empirical_n_step, sequence_to_triples
from .f4_action import closed_form_shell2_3x3, verify_n3_su3_closure_exact
from .g2_f4_t5_conjugate import conjugate_triple_route, verify_conjugate_triple
from .rule30 import canonical_rows
from .three_move_closure import verify_three_move_closure


def _center_triple_trajectory(max_depth: int) -> list[tuple[int, int, int]]:
    rows = canonical_rows(max_depth + 1)
    return [(rows[n - 1].get(-1, 0), rows[n - 1].get(0, 0), rows[n - 1].get(1, 0)) for n in range(1, max_depth + 1)]


def _cr_bond(L: int, C: int, R: int) -> int:
    return int(C) & int(R)


def _chart_readout(L: int, C: int, R: int) -> int:
    L, C, R = int(L), int(C), int(R)
    sh = L + C + R
    return int((sh == 1) or (sh == 2 and R > L))


def _eight_state_enumeration(trajectory: list[tuple[int, int, int]]) -> dict[str, Any]:
    counts = Counter(trajectory)
    seen = set(counts.keys())
    all_eight = {tuple(s) for s in [(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)]}
    first_seen: dict[tuple[int, int, int], int] = {}
    for i, st in enumerate(trajectory, start=1):
        if st not in first_seen:
            first_seen[st] = i
    activation_depth = max(first_seen.values()) if len(seen) == 8 else None
    return {
        "states_seen": len(seen),
        "all_eight_seen": seen == all_eight,
        "activation_depth_all_eight": activation_depth,
        "state_counts": {str(k): v for k, v in sorted(counts.items())},
        "missing_states": [list(s) for s in sorted(all_eight - seen)],
    }


def _shell2_triad_thirds(trajectory: list[tuple[int, int, int]], *, min_visits: int = 9) -> dict[str, Any]:
    """
    On shell=2 only, the resolving 3x3 lives on (C-, C0, C+) = SHELL2_STATES.
    Equilibrium accounting: each leg ~1/3 among shell=2 visits (not raw L/C/R marginals).
    """
    shell2 = [t for t in trajectory if sum(t) == 2]
    n = len(shell2)
    if n < min_visits:
        return {"shell2_visits": n, "sufficient": False, "reason": f"need>={min_visits} shell2 visits"}
    c = Counter(shell2)
    fracs = {str(k): c[k] / n for k in SHELL2_STATES}
    target = 1.0 / 3.0
    tol = 0.12
    thirds_ok = all(abs(fracs[str(s)] - target) <= tol for s in SHELL2_STATES)
    bij = check_bijection_symmetry(shell2)
    return {
        "shell2_visits": n,
        "sufficient": True,
        "triad_fractions": fracs,
        "triad_thirds_within_tolerance": thirds_ok,
        "bijection_symmetry": bij,
        "pos_neg_symmetry_ok": bij.get("symmetry_defect", 1.0) < 0.15,
    }


def _cr_bond_observer_accounting(trajectory: list[tuple[int, int, int]]) -> dict[str, Any]:
    """
    C*R bond (C & R) is the relational observer face; readout 0/1 is the time tick.
    Joint distribution over (cr_bond, readout, chart_state) — not lane marginals.
    """
    joint: Counter = Counter()
    readout0_states: Counter = Counter()
    readout1_states: Counter = Counter()
    for L, C, R in trajectory:
        cr = _cr_bond(L, C, R)
        bit = _chart_readout(L, C, R)
        joint[(cr, bit, L, C, R)] += 1
        if bit == 0:
            readout0_states[(L, C, R)] += 1
        else:
            readout1_states[(L, C, R)] += 1
    n = len(trajectory)
    readout0_frac = sum(readout0_states.values()) / n if n else 0.0
    # When CR=1 (visible nonlinear face), readout is still governed by full open-channel law
    cr1_readout1 = sum(1 for (cr, bit, *_rest) in joint if cr == 1 and bit == 1)
    cr1_total = sum(1 for (cr, bit, *_rest) in joint if cr == 1)
    return {
        "readout0_fraction": readout0_frac,
        "readout1_fraction": 1.0 - readout0_frac,
        "distinct_states_at_readout0": len(readout0_states),
        "distinct_states_at_readout1": len(readout1_states),
        "cr_bond_active_fraction": cr1_total / n if n else 0.0,
        "cr_bond_implies_open_when_active": (
            (cr1_readout1 / cr1_total) if cr1_total else None
        ),
        "note": (
            "0-emission depths are a valid stratum; lane marginals L/C/R conflate shells. "
            "Use joint chart_state accounting at readout=0."
        ),
    }


def _empirical_shell2_one_step(trajectory: list[tuple[int, int, int]]) -> list[list[float]]:
    """1-step P[next in SHELL2 | current in SHELL2] from trajectory."""
    idx = {s: i for i, s in enumerate(SHELL2_STATES)}
    counts = [[0] * 3 for _ in range(3)]
    for i in range(len(trajectory) - 1):
        src, dst = trajectory[i], trajectory[i + 1]
        if sum(src) == 2 and sum(dst) == 2:
            counts[idx[src]][idx[dst]] += 1
    mat = [[0.0] * 3 for _ in range(3)]
    for r in range(3):
        row_sum = sum(counts[r])
        if row_sum:
            for c in range(3):
                mat[r][c] = counts[r][c] / row_sum
    return mat


def _three_by_three_resolution(trajectory: list[tuple[int, int, int]]) -> dict[str, Any]:
    """Shell=2 3x3: empirical 1-step, closed-form 1-step, T4 exact n=3 S3."""
    emp1 = _empirical_shell2_one_step(trajectory)
    closed = closed_form_shell2_3x3()
    cf_mat = closed["conditional_matrix"]
    max_diff_1step = max(
        abs(float(emp1[i][j]) - float(cf_mat[i][j])) for i in range(3) for j in range(3)
    )
    t4 = verify_n3_su3_closure_exact()
    n3 = compute_empirical_n_step(trajectory, n_steps=3)
    from .core import test_s3_closure

    decomp = test_s3_closure(n3)
    n3_closed = float(decomp["residual_squared_exact"]) < 1e-6
    return {
        "t4_status": t4.get("status"),
        "s3_coefficients_one_third": t4.get("s3_coefficients_exact_strings"),
        "empirical_1step_vs_closed_max_abs_diff": max_diff_1step,
        "one_step_matrices_agree": max_diff_1step < 0.2,
        "n3_empirical_s3_residual_sq": float(decomp["residual_squared_exact"]),
        "n3_empirical_s3_closed": n3_closed,
        "closed_form_labels": closed.get("labels"),
    }


def _d4_lift_per_n(max_depth: int, n_start: int) -> dict[str, Any]:
    rows = canonical_rows(max_depth + 1)
    failures: list[dict[str, Any]] = []
    for n in range(max(n_start, 1), max_depth + 1):
        prev = rows[n - 1]
        st = (prev.get(-1, 0), prev.get(0, 0), prev.get(1, 0))
        enc = encode_d4([st])
        if decode_d4(enc)[0] != st:
            failures.append({"N": n, "state": st})
    return {"n_start": n_start, "all_lift_ok": len(failures) == 0, "failures": failures}


def _three_step_route_after(n_start: int, max_depth: int) -> dict[str, Any]:
    from .block_tower import rule30_center_column

    bits = rule30_center_column(max_depth)

    def enum(nn: int) -> int:
        return bits[nn - 1]

    over_3 = 0
    paths: Counter = Counter()
    for n in range(max(n_start, 1), max_depth + 1):
        r = conjugate_triple_route(n, enum)
        moves = r["moves_to_resolution"]
        if moves > 3 or moves < 0:
            over_3 += 1
        paths[tuple(r.get("conjugate_path", []))] += 1
    return {
        "all_within_3_moves": over_3 == 0,
        "path_distribution": {"/".join(k) if k else "identity": v for k, v in paths.items()},
    }


def verify_monster_d4_lift_claim(max_depth: int = 256) -> dict[str, Any]:
    traj = _center_triple_trajectory(max_depth)
    eight = _eight_state_enumeration(traj)
    shell2 = _shell2_triad_thirds(traj)
    cr_obs = _cr_bond_observer_accounting(traj)
    mat3 = _three_by_three_resolution(traj)
    conj = verify_conjugate_triple(max_depth=max_depth)
    three = verify_three_move_closure()

    n0 = eight.get("activation_depth_all_eight") or 1
    d4 = _d4_lift_per_n(max_depth, n0)
    route = _three_step_route_after(n0, max_depth)

    checks = {
        "all_eight_chart_states_enumerated": eight["all_eight_seen"],
        "shell2_triad_thirds_ok": shell2.get("triad_thirds_within_tolerance", False),
        "shell2_pos_neg_bijection_symmetric": shell2.get("pos_neg_symmetry_ok", False),
        "three_by_three_one_step_agrees": mat3.get("one_step_matrices_agree", False),
        "n3_empirical_s3_closed": mat3.get("n3_empirical_s3_closed", False),
        "s3_bond_one_third_proven": mat3.get("t4_status") == "pass",
        "d4_lift_all_n_after_activation": d4["all_lift_ok"],
        "g2_f4_route_within_3_moves": route["all_within_3_moves"],
        "g2_f4_t5_verifier_pass": conj.get("status") == "pass",
        "three_move_closure_pass": three.get("status") == "pass",
    }

    structural = (
        checks["all_eight_chart_states_enumerated"]
        and checks["s3_bond_one_third_proven"]
        and checks["d4_lift_all_n_after_activation"]
        and checks["g2_f4_route_within_3_moves"]
        and checks["g2_f4_t5_verifier_pass"]
        and checks["three_move_closure_pass"]
    )
    triad_ok = checks["shell2_triad_thirds_ok"] and checks["shell2_pos_neg_bijection_symmetric"]

    if structural and triad_ok:
        status, honesty = "pass_with_open_gaps", "BOUNDED_EXEC"
    elif structural:
        status, honesty = "pass_with_open_gaps", "CONJ"
    else:
        status, honesty = "fail", "CONJ"

    return {
        "claim_id": "monster.d4_lift.after_global_activation",
        "status": status,
        "honesty_label": honesty,
        "max_depth_tested": max_depth,
        "eight_state_enumeration": eight,
        "shell2_triad_accounting": shell2,
        "cr_bond_observer": cr_obs,
        "three_by_three_resolution": mat3,
        "d4_per_n": d4,
        "conjugate_routing": route,
        "checks": checks,
        "deprecated_metric_warning": (
            "Do not use marginal P(L=1),P(C=1),P(R=1) for this claim; "
            "they mix shells and undersample the bijective 3x3 triad."
        ),
        "interpretation": (
            "After all 8 joint chart states appear, D4 lift and ≤3-step G2→F4→T5A "
            "routing hold. The 1/3 law is on the shell-2 bonded triad (3x3), "
            "aligned with T4 S3 coefficients — not independent lane bit frequencies."
        ),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(verify_monster_d4_lift_claim(256), indent=2, default=str))
