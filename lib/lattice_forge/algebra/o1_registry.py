"""O(1) lookups: inlined classical facts (ported from Sage/SymPy/LiE tables).

Policy (project-wide):
  - If a quantity is O(1) in established libs → store here as a constant or
    tiny formula; do NOT call CAS at runtime in proof-lab / Docker hot path.
  - If a quantity requires enumeration (|W(E8)| elements, all Niemeier glue
    cosets, etc.) → custom batched code in ``backwalk`` / seed build, not a dep.

Sources: Bourbaki / Carter (Weyl orders); standard root counts; CMPLX chart
substrate is native (8-state cube), not imported from an external Lie package.
"""
from __future__ import annotations

from typing import Final

# --- Chart substrate (CMPLX native; already O(1) via substrate_map.route) ---

CHART_STATE_COUNT: Final[int] = 8
CHART_ROUTE_TABLE_SIZE: Final[int] = CHART_STATE_COUNT * CHART_STATE_COUNT  # 64

# --- Niemeier / 24D terminals (seed catalog) ---

NIEMEIER_TERMINAL_COUNT: Final[int] = 24

# --- Root counts (O(1) closed forms for ADE components in Niemeier labels) ---

def root_count_ade(family: str, rank: int) -> int:
    """Number of roots in a finite ADE root system (classical formula)."""
    fam = family.upper()
    if fam == "A":
        return rank * (rank + 1)
    if fam == "D":
        return 2 * rank * (rank - 1)
    if fam == "E" and rank == 6:
        return 72
    if fam == "E" and rank == 7:
        return 126
    if fam == "E" and rank == 8:
        return 240
    raise ValueError(f"unsupported ADE root count: {family}{rank}")


E8_ROOT_COUNT: Final[int] = 240
G2_ROOT_COUNT: Final[int] = 12
F4_ROOT_COUNT: Final[int] = 48

# --- Weyl group orders (O(1); ported from SymPy liealgebras / Sage WeylGroup.order) ---

WEYL_ORDER: Final[dict[str, int]] = {
    "A1": 2,
    "A2": 6,
    "D4": 192,
    "G2": 12,
    "F4": 1152,
    "E6": 51840,
    "E7": 2903040,
    "E8": 696_729_600,
}

E8_WEYL_ORDER: Final[int] = WEYL_ORDER["E8"]


def weyl_order(label: str) -> int:
    """O(1) |W| for supported seed labels (e.g. ``E8``, ``D4``, ``A2``)."""
    key = label.upper().replace(" ", "")
    if key in WEYL_ORDER:
        return WEYL_ORDER[key]
    # A_n: (n+1)!
    if key.startswith("A") and key[1:].isdigit():
        n = int(key[1:])
        out = 1
        for k in range(2, n + 2):
            out *= k
        return out
    # D_n: 2^(n-1) * n!
    if key.startswith("D") and key[1:].isdigit():
        n = int(key[1:])
        out = 1
        for k in range(2, n + 1):
            out *= k
        return out << (n - 1)
    raise KeyError(f"no O(1) Weyl order for {label!r}")


def chart_route_is_o1() -> bool:
    """Chart Weyl routing is 8×8 precomputed table — constant time per query."""
    return True
