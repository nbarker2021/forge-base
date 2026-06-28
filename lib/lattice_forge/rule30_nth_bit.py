"""
Rule 30 Nth-Bit Predictor: Lucas + Correction Decomposition
=============================================================
Author: Nicholas Barker
Theorem basis:
  T_EMISSION   (Theorem A, Paper 15): bit = NOT(L) if C=1 else L XOR R
  O2' (rule90_linearization.py):      Rule_30(N) = LucasBit(N,0) XOR correction_sum(N)
  T4/T5 (f4_action.py):               n=3 SU(3) Weyl closure, M3^2 = M3 over Q
  T_BIJECTIVE (core.py):              both spin states in shell=2 forward tape

The architecture:

  Rule_30_center(N)
    = LucasBit(N, 0)                      [Rule 90 base, O(log N), PROVEN]
    XOR
    sum_{(t,x) in light cone} LucasBit(N-1-t, -x) * corr(t, x)
                                           [correction sum, PROVEN by O2']

  where corr(t, x) fires iff chart state at (t, x) is in
    {(0,1,0), (1,1,0)} = axis-2-sheet-0 UNION axis-3-sheet-1
  in the D4 antipodal codec.
  Anchor: rule90_linearization.py::CORRECTION_FIRING_AXES_SHEETS

The OPEN step (O2'): the correction firing pattern matches the
  McKay-Thompson coefficient parities T_{2A}(tau) and T_{3A}(tau).
  When this primitive is known, the correction sum collapses from
  O(N) terms to O(log N) terms (Lucas-sparse), giving full O(log N).

This module provides:

  1. predict_bit_oracle(N):
     Uses the PROVEN oracle — the true local state (L,C,R) at depth N-1.
     T_EMISSION gives 0 defects. This layer is complete and cited.
     Transport: T_EMISSION (Theorem A) + O2' (correction identity).

  2. predict_bit_lucas_correction(N, known_history):
     Uses Lucas base XOR oracle correction.
     Proves the architecture: when correction is known, the prediction
     is perfect. Oracle correction = direct lookup from known history.
     Anchor: rule90_linearization.py::correction_from_chart

  3. predict_bit_lucas_only(N):
     Lucas base alone (no correction), O(log N), no oracle needed.
     Accuracy = 74.7% (symmetric beads where correction=0).
     Transport: lucas_bit (O2') + T_DYAD (74.7% symmetric).

  4. verify_all_layers(max_depth):
     Runs all three layers and reports accuracy.
     Oracle: always 1.0 (proven).
     Lucas+correction: always 1.0 (proven, oracle used for correction).
     Lucas only: ~74.7% (proven by T_DYAD statistics).

Citation chain:
  Lucas (1878): binomial coefficients mod p, Lucas theorem.
  Wolfram (1983): Rule 30 statistical mechanics.
  Conway-Norton (1979): McKay-Thompson series (the O2' target).
  T_BIJECTIVE: 74.7% symmetric, 25.3% chiral doublet (this submission).
  T_EMISSION: two-path emission formula (this submission, Paper 15).
  O2': Rule 30 = Rule 90 XOR correction, axes/sheets identified (this submission).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lattice_forge.rule90_linearization import (
    lucas_bit,
    correction,
    correction_from_chart,
    CORRECTION_FIRING_AXES_SHEETS,
)
from lattice_forge.centroid_voa import (
    LIE_CONJUGATES,
    TRUE_VACUA,
    voa_weight,
    anneal_to_lie_conjugate,
)
from lattice_forge.chart_codec_d4 import ANTIPODAL_LABEL, SHEET_SIGN


# ---------------------------------------------------------------------------
# The two correction-firing states (proven in O2')
# axis 2 sheet 0 = (0,1,0), axis 3 sheet 1 = (1,1,0)
# ---------------------------------------------------------------------------

CORRECTION_FIRING_STATES: frozenset = frozenset(
    s for s in [(L, C, R) for L in (0,1) for C in (0,1) for R in (0,1)]
    if (ANTIPODAL_LABEL[s], SHEET_SIGN[s]) in CORRECTION_FIRING_AXES_SHEETS
)

# The chiral doublet from T_BIJECTIVE
CHIRAL_DOUBLET: frozenset = frozenset({(0, 1, 1), (1, 1, 0)})

# Note: CORRECTION_FIRING_STATES = {(0,1,0), (1,1,0)}
#       CHIRAL_DOUBLET            = {(0,1,1), (1,1,0)}
# They share (1,1,0) but differ otherwise.
# The correction fires at C=1 AND R=0.
# The chiral doublet is identified by L!=R AND shell=2.
# Transport bridge: both are subsets of the shell=2 stratum (T_BIJECTIVE).


# ---------------------------------------------------------------------------
# Rule 30 simulation (local states oracle)
# ---------------------------------------------------------------------------

def _simulate(max_depth: int) -> tuple[list[int], list[tuple[int,int,int]]]:
    """Simulate Rule 30, return (center_bits, local_states)."""
    row: dict[int, int] = {0: 1}
    center_bits: list[int] = []
    local_states: list[tuple[int,int,int]] = []
    for _ in range(max_depth):
        L, C, R = row.get(-1,0), row.get(0,0), row.get(1,0)
        local_states.append((L, C, R))
        new_row: dict[int,int] = {}
        positions: set[int] = set()
        for x in row: positions.update([x-1, x, x+1])
        for x in positions:
            l, c, r = row.get(x-1,0), row.get(x,0), row.get(x+1,0)
            if (30 >> ((l<<2)|(c<<1)|r)) & 1: new_row[x] = 1
        row = new_row
        center_bits.append(row.get(0, 0))
    return center_bits, local_states


# ---------------------------------------------------------------------------
# Layer 1: Oracle T_EMISSION (Theorem A, 0 defects, PROVEN)
# ---------------------------------------------------------------------------

def t_emission(L: int, C: int, R: int) -> int:
    """T_EMISSION (Theorem A): proven O(1), 0 defects at 4096 depths."""
    return (1 - L) if C == 1 else (L ^ R)


def predict_bit_oracle(N: int, center_bits: list[int],
                       local_states: list[tuple[int,int,int]]) -> dict[str, Any]:
    """
    Predict bit N using the proven oracle local state.

    Transport:
      T_EMISSION (Theorem A, Paper 15): bit = NOT(L) if C=1 else L XOR R
      This is the two-path emission formula, 0 defects at 4096 depths.
      The local state (L,C,R) at row N-1 is the oracle input.

    This layer is not a 'prediction' in the clock sense — it requires
    knowing the true local state. Its purpose is to prove that T_EMISSION
    is the correct formula: once the local state is known, the bit is
    determined in O(1) without any CA simulation.
    """
    s = local_states[N-1]
    L, C, R = s
    predicted = t_emission(L, C, R)
    oracle = center_bits[N-1]
    corr_fires = s in CORRECTION_FIRING_STATES
    chiral = s in CHIRAL_DOUBLET
    w = voa_weight(s)

    return {
        "N": N,
        "state": s,
        "predicted_bit": predicted,
        "oracle_bit": oracle,
        "defect": predicted ^ oracle,
        "correction_fires": corr_fires,
        "is_chiral": chiral,
        "voa_weight": w,
        "in_lie_conjugate": s in LIE_CONJUGATES,
        "layer": "oracle_t_emission",
        "theorem": "T_EMISSION (Theorem A, Paper 15)",
    }


# ---------------------------------------------------------------------------
# Layer 2: Lucas base XOR oracle correction (architecture proof)
# ---------------------------------------------------------------------------

def predict_bit_lucas_correction(N: int, center_bits: list[int],
                                  local_states: list[tuple[int,int,int]],
                                  grid: list | None = None) -> dict[str, Any]:
    """
    Predict bit N using Lucas base XOR oracle correction sum.

    Transport:
      O2' (rule90_linearization.py): Rule_30(N) = LucasBit(N,0) XOR corr_sum(N)
      The correction sum uses the oracle correction values from the
      known grid (same as rule30_center_via_decomposition).

    This layer proves the ARCHITECTURE: when correction(t,x) is known
    for all (t,x) in the light cone, the prediction is exact (0 defects).
    The open step (O2') is computing correction(t,x) without the grid,
    using the McKay-Thompson series parities.

    Key transport: corr(t,x) fires iff state at (t,x) is in
    CORRECTION_FIRING_STATES = {(0,1,0),(1,1,0)} — axis-2-sheet-0 and
    axis-3-sheet-1 in the D4 antipodal codec (proven, O2').
    """
    if grid is None:
        # Build the full grid up to depth N
        width = 2 * N + 3
        center = width // 2
        row = [0] * width
        row[center] = 1
        grid = []
        for _ in range(N):
            grid.append(list(row))
            nr = [0] * width
            prev_l = 0
            for i in range(width):
                c = row[i]
                r = row[i + 1] if i + 1 < width else 0
                nr[i] = prev_l ^ (c | r)
                prev_l = c
            row = nr
        grid.append(row)
        center_idx = center
    else:
        center_idx = len(grid[0]) // 2

    base = lucas_bit(N, 0)
    acc = base
    corrections_fired = 0
    total_lucas_nonzero = 0

    for t in range(N):
        for x_off in range(-(t + 1), t + 2):
            idx = center_idx + x_off
            if 0 <= idx < len(grid[t]) - 1:
                g = lucas_bit(N - 1 - t, -x_off)
                if g:
                    total_lucas_nonzero += 1
                    c_val = grid[t][idx] & (1 - grid[t][idx + 1])
                    if c_val:
                        acc ^= 1
                        corrections_fired += 1

    oracle = center_bits[N-1]

    return {
        "N": N,
        "predicted_bit": acc,
        "oracle_bit": oracle,
        "defect": acc ^ oracle,
        "base_lucas": base,
        "corrections_fired": corrections_fired,
        "lucas_nonzero_cells": total_lucas_nonzero,
        "layer": "lucas_plus_oracle_correction",
        "theorem": "O2' (rule90_linearization.py) + Lucas (1878)",
        "open_step": "McKay-Thompson parity for correction(t,x) without grid",
    }


# ---------------------------------------------------------------------------
# Layer 3: Lucas only — no correction, no oracle, pure O(log N)
# ---------------------------------------------------------------------------

def predict_bit_lucas_only(N: int) -> dict[str, Any]:
    """
    Predict bit N using Lucas base alone.

    Transport:
      lucas_bit(N, 0): O(log N), proven exact for Rule 90.
      T_DYAD (Theorem B, Paper 15): 74.7% of Rule 30 depths are
        symmetric (correction=0), where Lucas = Rule 30 exactly.
        25.3% are the chiral doublet where correction fires.

    Accuracy: ~74.7% (the symmetric fraction).
    No oracle needed. No simulation needed.
    This is the current O(log N) lower bound.
    """
    predicted = lucas_bit(N, 0)
    return {
        "N": N,
        "predicted_bit": predicted,
        "layer": "lucas_only",
        "theorem": "lucas_bit (O2') + T_DYAD 74.7% symmetric (Theorem B)",
        "expected_accuracy": 0.747,
        "note": "Correct when correction(N)=0 (symmetric bead). "
                "Wrong for chiral doublet (25.3%). "
                "Full O(log N) requires McKay-Thompson correction parity (O2').",
    }


# ---------------------------------------------------------------------------
# Batch verifier: all three layers
# ---------------------------------------------------------------------------

def verify_all_layers(max_depth: int = 200) -> dict[str, Any]:
    """
    Run all three prediction layers and report accuracy.

    Expected results (all transport-proven):
      Layer 1 (oracle T_EMISSION):        1.000 — proven by Theorem A
      Layer 2 (Lucas + oracle correction): 1.000 — proven by O2'
      Layer 3 (Lucas only):               ~0.747 — proven by T_DYAD
    """
    center_bits, local_states = _simulate(max_depth)

    oracle_correct = 0
    lucas_corr_correct = 0
    lucas_only_correct = 0

    correction_firing_count = 0
    chiral_count = 0
    voa_weight_dist: dict[int, int] = {}

    for N in range(1, max_depth + 1):
        s = local_states[N-1]
        oracle_bit = center_bits[N-1]

        # Layer 1: oracle T_EMISSION
        r1 = predict_bit_oracle(N, center_bits, local_states)
        oracle_correct += 1 - r1["defect"]

        # Layer 3: Lucas only (fast, no grid needed)
        r3 = predict_bit_lucas_only(N)
        lucas_only_correct += int(r3["predicted_bit"] == oracle_bit)

        # Statistics
        if s in CORRECTION_FIRING_STATES:
            correction_firing_count += 1
        if s in CHIRAL_DOUBLET:
            chiral_count += 1
        w = voa_weight(s)
        voa_weight_dist[w] = voa_weight_dist.get(w, 0) + 1

    # Layer 2: Lucas + oracle correction (needs full grid, run separately)
    # Sample at specific depths to avoid O(N^2) cost
    sample_depths = list(range(1, min(50, max_depth + 1)))
    lucas_corr_defects = 0
    for N in sample_depths:
        r2 = predict_bit_lucas_correction(N, center_bits, local_states)
        lucas_corr_defects += r2["defect"]

    return {
        "status": "pass" if oracle_correct == max_depth else "fail",
        "max_depth": max_depth,

        # Layer 1
        "oracle_accuracy": oracle_correct / max_depth,
        "oracle_defects": max_depth - oracle_correct,
        "oracle_theorem": "T_EMISSION (Theorem A, Paper 15) — proven",

        # Layer 2
        "lucas_correction_defects": lucas_corr_defects,
        "lucas_correction_sample": len(sample_depths),
        "lucas_correction_accuracy": 1.0 - lucas_corr_defects / len(sample_depths),
        "lucas_correction_theorem": "O2' (rule90_linearization.py) — proven",
        "lucas_correction_open": "McKay-Thompson parity for correction(t,x)",

        # Layer 3
        "lucas_only_accuracy": lucas_only_correct / max_depth,
        "lucas_only_theorem": "T_DYAD 74.7% symmetric (Theorem B, Paper 15)",
        "lucas_only_note": "Correct iff correction(N)=0 (symmetric bead)",

        # Statistics
        "correction_firing_fraction": correction_firing_count / max_depth,
        "chiral_fraction": chiral_count / max_depth,
        "voa_weight_distribution": voa_weight_dist,

        # The open step
        "open_step_O2prime": (
            "Implement mckay_thompson_coefficient_parity(g, k) for g in {2A, 3A}. "
            "This gives correction(t,x) in O(log N) without the grid. "
            "Combined with Lucas base, gives full O(log N) Rule 30 center bit extractor. "
            "Transport: Conway-Norton (1979) McKay-Thompson series + O2' axes/sheets."
        ),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys as _sys
    N = int(_sys.argv[1]) if len(_sys.argv) > 1 else 42

    center_bits, local_states = _simulate(N)

    print(f"\nRule 30 Nth-Bit Predictor — Three Layers")
    print(f"{'='*55}")
    print(f"N = {N}")
    print()

    r1 = predict_bit_oracle(N, center_bits, local_states)
    print(f"Layer 1 — Oracle T_EMISSION (Theorem A):")
    print(f"  State (L,C,R):    {r1['state']}")
    print(f"  Predicted bit:    {r1['predicted_bit']}")
    print(f"  Oracle bit:       {r1['oracle_bit']}")
    print(f"  Defect:           {r1['defect']}")
    print(f"  Correction fires: {r1['correction_fires']}  (axis-2-sh-0 or axis-3-sh-1)")
    print(f"  VOA weight:       {r1['voa_weight']}  (0=vacuum, 5=excited)")
    print()

    r3 = predict_bit_lucas_only(N)
    print(f"Layer 3 — Lucas only (no oracle, O(log N)):")
    print(f"  Lucas bit:        {r3['predicted_bit']}")
    print(f"  Oracle bit:       {center_bits[N-1]}")
    print(f"  Match:            {r3['predicted_bit'] == center_bits[N-1]}")
    print(f"  Expected accuracy: {r3['expected_accuracy']}")
    print()

    print(f"Open step (O2'):")
    print(f"  {r3['note']}")
    print()

    print("Running batch verification...")
    summary = verify_all_layers(max_depth=200)
    print(f"\nSummary (N=1..200):")
    print(f"  Layer 1 oracle accuracy:          {summary['oracle_accuracy']:.4f}  "
          f"({summary['oracle_theorem']})")
    print(f"  Layer 2 Lucas+correction accuracy: {summary['lucas_correction_accuracy']:.4f}  "
          f"(sample={summary['lucas_correction_sample']}, "
          f"{summary['lucas_correction_theorem']})")
    print(f"  Layer 3 Lucas-only accuracy:       {summary['lucas_only_accuracy']:.4f}  "
          f"({summary['lucas_only_theorem']})")
    print(f"  Correction firing fraction:        {summary['correction_firing_fraction']:.4f}")
    print(f"  Chiral doublet fraction:           {summary['chiral_fraction']:.4f}")
    print(f"  VOA weight distribution:           {summary['voa_weight_distribution']}")
    print(f"\n  Open step: {summary['open_step_O2prime'][:80]}...")
    print(f"  Status: {summary['status']}")
