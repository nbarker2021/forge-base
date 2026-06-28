"""
Core primitives for Universality exploration.

THE FUNDAMENTAL CONSTRUCTION — Single-Tape Bijective Encoding
==============================================================
The negative spin state does not require a second physical tape.
It is already present in the forward tape via the shell=2 bijection:

  Shell=2 states:  (1,1,0), (1,0,1), (0,1,1)
                       ↑         ↑        ↑
                   side=+1   side=0   side=-1
                   (LC bond) (center) (CR bond)

The bijection is the side-flip:
  (1,1,0)  ←→  (0,1,1)    [+1 chirality ↔ -1 chirality]
  (1,0,1)  is the fixed point (center bar null, side=0)

So the three shell=2 states ARE the complete SU(2) doublet:
  (1,1,0) = positive spin state (+1)
  (0,1,1) = negative spin state (-1)
  (1,0,1) = center bar / null / singlet (0)

The transition matrix on these three states, built from the single
forward tape, already encodes both spin states and their coupling.
No second page is needed — the bijection IS the negative state encoding.

The n=3 S3 closure test asks: does the 3-step transition matrix on this
SU(2) triplet close as an element of the S3 group ring?
If yes, the sequence has the full J3(O) Weyl coherence.
"""
from __future__ import annotations

from fractions import Fraction

from .f4_action import decompose_3x3_in_s3_group_ring_exact


# ─────────────────────────────────────────────────────────────────────────────
# Primitive chart operations
# ─────────────────────────────────────────────────────────────────────────────

# The three shell=2 states, ordered as: +spin, null, -spin
SHELL2_STATES = [(1,1,0), (1,0,1), (0,1,1)]
SHELL2_IDX    = {s: i for i, s in enumerate(SHELL2_STATES)}

def chart_state(L, C, R):
    return (int(L), int(C), int(R))

def shell(L, C, R):
    return int(L) + int(C) + int(R)

def side(L, C, R):
    L, C, R = int(L), int(C), int(R)
    return 1 if R > L else (-1 if L > R else 0)

def readout(L, C, R):
    """Open-channel law: bit=1 iff NOT_L AND (C OR R) OR L AND NOT_C AND NOT_R."""
    L, C, R = int(L), int(C), int(R)
    return int((not L and (C or R)) or (L and not C and not R))

def sequence_to_triples(seq):
    """Convert a binary sequence to overlapping (L,C,R) triples."""
    return [chart_state(seq[i-1], seq[i], seq[i+1]) for i in range(1, len(seq) - 1)]


# ─────────────────────────────────────────────────────────────────────────────
# Transition matrix on the shell=2 SU(2) triplet
# ─────────────────────────────────────────────────────────────────────────────

def compute_empirical_n_step(triples, n_steps=3):
    """
    Build the empirical n-step transition matrix on the shell=2 stratum.

    The three shell=2 states are the SU(2) triplet:
      idx 0: (1,1,0) = +spin
      idx 1: (1,0,1) = null / center bar
      idx 2: (0,1,1) = -spin

    The bijection (1,1,0) ↔ (0,1,1) is the negative-state encoding.
    This matrix already contains both spin states — no second tape needed.
    """
    counts = [[0]*3 for _ in range(3)]
    for i in range(len(triples) - n_steps):
        src = triples[i]
        dst = triples[i + n_steps]
        if src in SHELL2_IDX and dst in SHELL2_IDX:
            counts[SHELL2_IDX[src]][SHELL2_IDX[dst]] += 1

    matrix = [[Fraction(0)]*3 for _ in range(3)]
    for i in range(3):
        row_sum = sum(counts[i])
        if row_sum > 0:
            for j in range(3):
                matrix[i][j] = Fraction(counts[i][j], row_sum)
    return matrix

def test_s3_closure(matrix):
    """Test if a 3x3 Fraction matrix is an exact S3 group ring element."""
    return decompose_3x3_in_s3_group_ring_exact(matrix)


# ─────────────────────────────────────────────────────────────────────────────
# Bijection symmetry check
# ─────────────────────────────────────────────────────────────────────────────

def check_bijection_symmetry(triples):
    """
    Check whether the forward tape's shell=2 stratum is symmetric under
    the side-flip bijection: count(+spin) vs count(-spin).
    Perfect symmetry means the negative state is fully encoded in the forward tape.
    """
    pos = sum(1 for t in triples if t == (1,1,0))
    neg = sum(1 for t in triples if t == (0,1,1))
    null = sum(1 for t in triples if t == (1,0,1))
    total = pos + neg + null
    if total == 0:
        return {"pos": 0, "neg": 0, "null": 0, "symmetry_defect": 0.0}
    return {
        "pos": pos,
        "neg": neg,
        "null": null,
        "pos_frac": pos / total,
        "neg_frac": neg / total,
        "null_frac": null / total,
        "symmetry_defect": abs(pos - neg) / total,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Full pipeline
# ─────────────────────────────────────────────────────────────────────────────

def probe(seq, label="", n_steps=3, verbose=True):
    """
    Full pipeline: binary sequence → triples → shell=2 SU(2) triplet →
    n-step transition matrix → S3 closure test.

    The shell=2 stratum already encodes both spin states via the bijection.
    """
    triples = sequence_to_triples(seq)
    n = len(triples)

    # Statistics
    shells   = [shell(*t) for t in triples]
    readouts = [readout(*t) for t in triples]
    density  = sum(readouts) / n if n > 0 else 0
    shell_counts = {0:0, 1:0, 2:0, 3:0}
    for s in shells: shell_counts[s] += 1

    # Bijection symmetry
    bij = check_bijection_symmetry(triples)

    # Transition matrix and closure
    mat  = compute_empirical_n_step(triples, n_steps=n_steps)
    decomp = test_s3_closure(mat)
    res  = float(decomp["residual_squared_exact"])
    closed = res < 1e-6

    coeffs = decomp["coefficients_float"]
    dominant = max(coeffs.items(), key=lambda kv: abs(kv[1]))[0] if coeffs else "zero"

    result = {
        "label": label,
        "n_triples": n,
        "readout_density": density,
        "shell_fractions": {k: v/n for k,v in shell_counts.items()},
        "bijection_symmetry": bij,
        "residual_squared": res,
        "is_closed": closed,
        "dominant_s3_element": dominant,
        "coefficients": coeffs,
    }

    if verbose:
        sym = bij.get("symmetry_defect", 0)
        status = "CLOSED" if closed else f"open (res²={res:.2e})"
        print(f"  [{label}] n={n}, density={density:.4f}, "
              f"sym_defect={sym:.4f}, bij_null={bij.get('null_frac',0):.3f} → {status}")

    return result
