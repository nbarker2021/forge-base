"""
empirical.py — Empirical measurements for Sections 6 and 8 of PAPER.md.

Provides:
    * `lucas_sparsity_at(N)` — counts for Result 6.1
    * `chart_conditional_entropy(N)` — Result 8.1
    * `center_density(N)` — Result 8.2
    * `chart_periodicity_scan(N, shifts)` — Result 8.3

Dependency-free.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Any

from .rule30_decomposition import lucas_bit, rule30_full_grid
from .fast_rule30 import fast_rule30, fast_rule30_chart


# ---------------------------------------------------------------------------
# Result 6.1 — Lucas-sparsity at depth N
# ---------------------------------------------------------------------------

def lucas_sparsity_at(N: int) -> dict[str, Any]:
    """Count light-cone cells, Lucas-nonzero cells, correction-nonzero
    cells, and contributing cells (both nonzero) at depth N."""
    grid, center = rule30_full_grid(N)
    width = len(grid[0])

    total_cone = 0
    g_nonzero = 0
    corr_nonzero = 0
    both = 0

    for t in range(N):
        x_lo = max(-(t + 1), -(N - 1 - t))
        x_hi = min(t + 1, N - 1 - t)
        for x_off in range(x_lo, x_hi + 1):
            idx = center + x_off
            if 0 <= idx < width - 1:
                total_cone += 1
                g = lucas_bit(N - 1 - t, -x_off)
                if g:
                    g_nonzero += 1
                c_val = grid[t][idx] & (1 - grid[t][idx + 1])
                if c_val:
                    corr_nonzero += 1
                if g and c_val:
                    both += 1

    return {
        "N": N,
        "total_light_cone_cells": total_cone,
        "lucas_nonzero_cells": g_nonzero,
        "correction_nonzero_cells": corr_nonzero,
        "contributing_cells": both,
        "lucas_density": g_nonzero / total_cone if total_cone else 0.0,
        "correction_density": corr_nonzero / total_cone if total_cone else 0.0,
        "reduction_factor_vs_cone": (
            total_cone / both if both else float("inf")
        ),
    }


# ---------------------------------------------------------------------------
# Result 8.1 — chart conditional entropy
# ---------------------------------------------------------------------------

def _shannon_bits(counts) -> float:
    t = sum(counts.values())
    if t == 0:
        return 0.0
    return -sum(
        (c / t) * math.log2(c / t)
        for c in counts.values() if c > 0
    )


def chart_conditional_entropy(N: int, order_max: int = 2) -> dict[str, Any]:
    """Marginal and conditional entropies of the joint 8-state chart
    trajectory at depths 1..N. Encodes each chart as integer
    L*4 + C*2 + R in [0, 8).
    """
    chart_ints = [L * 4 + C * 2 + R for (L, C, R) in fast_rule30_chart(N)]

    results = {}
    prev_h = 0.0
    for n in range(1, order_max + 1):
        if len(chart_ints) < n:
            break
        grams = Counter(
            tuple(chart_ints[i : i + n]) for i in range(len(chart_ints) - n + 1)
        )
        h_n = _shannon_bits(grams)
        h_cond = h_n - prev_h
        results[f"H_{n}_gram"] = h_n
        results[f"H_cond_order_{n - 1}"] = h_cond
        prev_h = h_n

    return {
        "N": N,
        "chart_length": len(chart_ints),
        **results,
    }


# ---------------------------------------------------------------------------
# Result 8.2 — center density
# ---------------------------------------------------------------------------

def center_density(N: int) -> dict[str, Any]:
    bits = list(fast_rule30(N))
    ones = sum(bits)
    n = len(bits)
    return {
        "N": N,
        "center_bits_counted": n,
        "ones": ones,
        "density_of_1": ones / n if n else 0.0,
        "deviation_from_half": (ones / n - 0.5) if n else 0.0,
    }


# ---------------------------------------------------------------------------
# Result 8.3 — periodicity scan on the chart trajectory
# ---------------------------------------------------------------------------

def chart_periodicity_scan(N: int, shifts: list[int]) -> dict[str, Any]:
    """For each shift s, compute the autocorrelation of the joint chart
    encoding at lag s (fraction of (i, i+s) pairs with equal chart values).

    Also confirms no exact period of length p exists for p in `shifts`.
    """
    chart_ints = [L * 4 + C * 2 + R for (L, C, R) in fast_rule30_chart(N)]
    n = len(chart_ints)
    autocorr = {}
    any_period = False
    for s in shifts:
        if s >= n:
            continue
        matches = sum(
            1 for i in range(n - s) if chart_ints[i] == chart_ints[i + s]
        )
        autocorr[s] = matches / (n - s)
        # exact period check on a prefix
        if all(
            chart_ints[i] == chart_ints[i % s]
            for i in range(min(n, 8 * s))
        ):
            any_period = True
    return {
        "N": N,
        "chart_length": n,
        "shifts_tested": list(shifts),
        "autocorrelation": autocorr,
        "any_exact_period_found": any_period,
        "iid_baseline_8_state": 1 / 8,
    }
