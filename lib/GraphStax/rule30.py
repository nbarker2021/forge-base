"""
GraphStax Rule30 — Tabular lookup layer for Rule 30 / T_EMISSION / VOA state tables.

All tables are computed once at import time and are read-only after that.
No simulation at use time — every operation is a dict lookup.

Foundation theorems (from lattice_forge PROOF papers):
  T_EMISSION (Theorem A, Paper 15):   bit = NOT(L) if C=1 else L^R  — proven 0 defects
  T_DYAD    (Theorem B, Paper 15):    74.7% symmetric, 25.3% chiral doublet
  Gluon Invariance (Theorem 0):       Γ(s) = C — invariant under LR transposition
  VOA sector decomposition:           True vacua weight=0, excited weight=5 (6 states)
  Hamming-centroid universality:      All 8 states close to Lie conjugate in ≤3 steps

These are the "probabilities in local states" and "algebra for Weyl transformations"
referenced by the framework. Everything that would otherwise require simulation is
pre-computed here so TarPit / GraphStax can dispatch by table lookup only.
"""
import math
from typing import Dict, FrozenSet, Tuple

# ─── All 8 local states (canonical order) ─────────────────────────────────────

_ALL_STATES: Tuple[Tuple[int,int,int], ...] = tuple(
    (L, C, R) for L in (0, 1) for C in (0, 1) for R in (0, 1)
)
# Order: (0,0,0) (0,0,1) (0,1,0) (0,1,1) (1,0,0) (1,0,1) (1,1,0) (1,1,1)


# ─── Rule 30 output table ─────────────────────────────────────────────────────
# Rule number 30 = 0b00011110
# bit_index = (L<<2)|(C<<1)|R; output = (30 >> bit_index) & 1
# Proven equal to T_EMISSION for all 8 states (that IS the proof of T_EMISSION).

_RULE30_TABLE: Dict[Tuple[int,int,int], int] = {
    s: (30 >> ((s[0] << 2) | (s[1] << 1) | s[2])) & 1
    for s in _ALL_STATES
}
# {(0,0,0):0, (0,0,1):1, (0,1,0):1, (0,1,1):1,
#  (1,0,0):1, (1,0,1):0, (1,1,0):0, (1,1,1):0}


# ─── T_EMISSION lookup table (Theorem A) ──────────────────────────────────────
# bit = NOT(L) if C=1 (centroid_inversion path)
# bit = L XOR R if C=0 (boundary_parity path)
# Matches _RULE30_TABLE exactly for all 8 states — this is what T_EMISSION proves.

_T_EMISSION_TABLE: Dict[Tuple[int,int,int], Tuple[int, str]] = {
    (L, C, R): (
        (1 - L, "centroid_inversion") if C else (L ^ R, "boundary_parity")
    )
    for L, C, R in _ALL_STATES
}


def t_emission(state: Tuple[int,int,int]) -> Tuple[int, str]:
    """T_EMISSION O(1) lookup. Returns (bit, path). Proven 0 defects at 4096 depths."""
    return _T_EMISSION_TABLE[state]


# ─── Gluon — C is invariant under LR transposition ────────────────────────────
# Γ(s) = C for all 8 states. Pre-computed for lookup.

_GLUON_TABLE: Dict[Tuple[int,int,int], int] = {s: s[1] for s in _ALL_STATES}


# ─── VOA state tables (centroid_voa.py provenance) ────────────────────────────

# True vacua: L=C=R. Weight=0. Both settings simultaneously at attractor.
TRUE_VACUA: FrozenSet[Tuple[int,int,int]] = frozenset({(0, 0, 0), (1, 1, 1)})

# Lie conjugates: L=R (C-centroid attractor plane).
# The 4 attractors for the C-setting transposition orbit.
LIE_CONJUGATES: FrozenSet[Tuple[int,int,int]] = frozenset({
    (0, 0, 0), (0, 1, 0), (1, 0, 1), (1, 1, 1)
})

# VOA sector:
#   - Vacuum sector (weight=0):  TRUE_VACUA = {(0,0,0), (1,1,1)}
#   - Excited sector (weight=5): all 6 non-vacuum states
# Seed partition function: Z(q) = 2q^0 + 6q^5
_VOA_WEIGHT_TABLE: Dict[Tuple[int,int,int], int] = {
    s: 0 if s in TRUE_VACUA else 5
    for s in _ALL_STATES
}

_VOA_SECTOR_TABLE: Dict[Tuple[int,int,int], str] = {
    s: "Vacuum" if s in TRUE_VACUA else "Excited"
    for s in _ALL_STATES
}


# ─── State classification (T_DYAD + O2' correction firing) ───────────────────
# CORRECTION_FIRING_STATES: states where the Rule30 = Rule90 XOR correction
# fires. Proven: correction fires iff state ∈ {(0,1,0), (1,1,0)}.
# Axis-2-sheet-0 and axis-3-sheet-1 in the D4 antipodal codec.

CORRECTION_FIRING_STATES: FrozenSet[Tuple[int,int,int]] = frozenset({(0, 1, 0), (1, 1, 0)})

# CHIRAL_DOUBLET: L≠R states at C=1. T_BIJECTIVE identifies these as the
# 25.3% chiral fraction. {(0,1,1), (1,1,0)}.
CHIRAL_DOUBLET: FrozenSet[Tuple[int,int,int]] = frozenset({(0, 1, 1), (1, 1, 0)})

# Symmetric states: correction=0 (74.7% of Rule 30 center-column steps)
SYMMETRIC_STATES: FrozenSet[Tuple[int,int,int]] = frozenset(
    s for s in _ALL_STATES if s not in CORRECTION_FIRING_STATES
)

# T_DYAD fractions (Theorem B, Paper 15)
SYMMETRIC_FRACTION: float = 0.747
CHIRAL_FRACTION: float = 0.253

_STATE_CLASS_TABLE: Dict[Tuple[int,int,int], str] = {
    s: ("correction" if s in CORRECTION_FIRING_STATES else
        "chiral" if s in CHIRAL_DOUBLET else
        "symmetric")
    for s in _ALL_STATES
}

# Approximate per-state occurrence probability in Rule 30 center column.
# Derived from T_DYAD: correction fraction = 0.253 / 2 each,
# symmetric fraction = 0.747 / 6 each (uniform within class, approximate).
_STATE_PROB_TABLE: Dict[Tuple[int,int,int], float] = {
    s: (CHIRAL_FRACTION / 2.0 if s in CORRECTION_FIRING_STATES
        else SYMMETRIC_FRACTION / 6.0)
    for s in _ALL_STATES
}


# ─── Hamming-centroid anneal table ───────────────────────────────────────────
# Anneal steps to reach Lie conjugate (L=R) plane via S3 transpositions.
# Applied in order: swap_LR, swap_LC, swap_CR.
# All states reach LIE_CONJUGATES in ≤3 steps (proven).

def _swap_LR(s: Tuple[int,int,int]) -> Tuple[int,int,int]:
    L, C, R = s; return (R, C, L)

def _swap_LC(s: Tuple[int,int,int]) -> Tuple[int,int,int]:
    L, C, R = s; return (C, L, R)

def _swap_CR(s: Tuple[int,int,int]) -> Tuple[int,int,int]:
    L, C, R = s; return (L, R, C)

_S3_OPS = (_swap_LR, _swap_LC, _swap_CR)
_S3_NAMES = ("T_LR", "T_LC", "T_CR")

def _compute_anneal(s: Tuple[int,int,int]) -> Tuple[int, Tuple[int,int,int]]:
    """Returns (steps, final_state) after annealing to Lie conjugate."""
    current = s
    for i, t in enumerate(_S3_OPS):
        if current in LIE_CONJUGATES:
            return i, current
        current = t(current)
    return len(_S3_OPS), current

_ANNEAL_TABLE: Dict[Tuple[int,int,int], Tuple[int, Tuple[int,int,int]]] = {
    s: _compute_anneal(s) for s in _ALL_STATES
}


# ─── Hamming distance to centroid ─────────────────────────────────────────────

_HAMMING_TO_CENTROID: Dict[Tuple[int,int,int], int] = {
    (L, C, R): int(L != C) + int(R != C)
    for L, C, R in _ALL_STATES
}


# ─── Combined state profile table ─────────────────────────────────────────────
# Master lookup: state → full profile dict (read-only at use time)

_STATE_PROFILE: Dict[Tuple[int,int,int], dict] = {
    s: {
        "state":             s,
        "rule30_out":        _RULE30_TABLE[s],
        "emission_bit":      _T_EMISSION_TABLE[s][0],
        "emission_path":     _T_EMISSION_TABLE[s][1],
        "gluon":             _GLUON_TABLE[s],           # = C
        "voa_weight":        _VOA_WEIGHT_TABLE[s],
        "voa_sector":        _VOA_SECTOR_TABLE[s],
        "is_vacuum":         s in TRUE_VACUA,
        "is_lie_conjugate":  s in LIE_CONJUGATES,
        "state_class":       _STATE_CLASS_TABLE[s],
        "correction_fires":  s in CORRECTION_FIRING_STATES,
        "is_chiral":         s in CHIRAL_DOUBLET,
        "hamming_to_c":      _HAMMING_TO_CENTROID[s],
        "anneal_steps":      _ANNEAL_TABLE[s][0],
        "anneal_final":      _ANNEAL_TABLE[s][1],
        "approx_prob":       _STATE_PROB_TABLE[s],
    }
    for s in _ALL_STATES
}


# ─── Sheet size table (MDHG levels) ──────────────────────────────────────────
# Each MDHG resolution level maps to a sheet width in bits.
# Sheet width doubles at each level: grain=2, dust=4, ..., universe=512.
# The C-gluon at level k is the center of a 2^(k+1)-bit window.

_MDHG_LEVELS: Tuple[str, ...] = (
    "grain", "dust", "triad", "block", "cluster",
    "domain", "region", "planet", "universe",
)
_SHEET_SIZE_TABLE: Dict[int, int] = {i: 2 ** (i + 1) for i in range(9)}
_SHEET_LEVEL_INDEX: Dict[str, int] = {name: i for i, name in enumerate(_MDHG_LEVELS)}

# The C-gluon spans exactly ONE full sheet at its resolution level.
# A grain C covers a 2-bit window; a universe C covers 512 bits.


# ─── Public API ──────────────────────────────────────────────────────────────

def profile(state: Tuple[int,int,int]) -> dict:
    """Full state profile dict from lookup table."""
    return _STATE_PROFILE[state]

def classify(state: Tuple[int,int,int]) -> str:
    """'correction', 'chiral', or 'symmetric'."""
    return _STATE_CLASS_TABLE[state]

def sheet_size(level: int) -> int:
    """Number of bits in a sheet at MDHG level 0..8."""
    return _SHEET_SIZE_TABLE.get(level, 2 ** (level + 1))

def level_of(name: str) -> int:
    """MDHG level index from name (e.g. 'grain' → 0)."""
    return _SHEET_LEVEL_INDEX.get(name, 0)
