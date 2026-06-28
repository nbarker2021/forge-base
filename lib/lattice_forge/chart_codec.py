"""
chart_codec.py — Regime C compression: encode/decode the Rule 30 chart's
shell=2 sub-trajectory as a word in S_3, the Weyl group of SU(3) ⊂ F_4.

Theoretical foundation:
    T3      : chart (L,C,R) ↔ J_3(O) diagonal idempotent diag(L,C,R)
    T_BRIDGE: the diagonal subalgebra IS the zero-weight space of F_4's
              26-dim fundamental representation; the Weyl group preserves it
    T4      : the n=3 conditional shell=2 transition matrix is the exact
              uniform Weyl average M_3 = (1/3)(T_(1,2) + T_(1,3) + T_(2,3))

For the shell=2 stratum {(1,1,0), (1,0,1), (0,1,1)} ↔
{e_11+e_22, e_11+e_33, e_22+e_33} ⊂ J_3(O), any two distinct states
differ by exactly one S_3 transposition that swaps the two diagonal
positions of unequal value. Self-loops encode as the identity 'e'.

Encoding: starting chart state + sequence of S_3 elements.
Decoding: apply each S_3 element as a coordinate permutation of (L,C,R).
Round-trip is exact and lossless on the shell=2 sub-trajectory.

Per-step entropy: log_2(4) = 2 bits (e plus 3 transpositions on shell=2).
Per-step entropy of raw chart state: log_2(3) = ~1.585 bits.
The codec is symbolic, not Huffman-optimal; the win is that each step is
a *named group element* that composes via the proven M_3 algebra.
"""
from __future__ import annotations

from typing import Any

from .rule30 import canonical_rows


# ---------------------------------------------------------------------------
# Shell=2 stratum and S_3 actions
# ---------------------------------------------------------------------------

SHELL2_STATES: tuple[tuple[int, int, int], ...] = (
    (1, 1, 0),
    (1, 0, 1),
    (0, 1, 1),
)

# S_3 elements as 1-indexed permutations of (1, 2, 3) acting on (L, C, R)
S3: dict[str, tuple[int, int, int]] = {
    "e":       (1, 2, 3),
    "(1 2)":   (2, 1, 3),
    "(1 3)":   (3, 2, 1),
    "(2 3)":   (1, 3, 2),
    "(1 2 3)": (2, 3, 1),
    "(1 3 2)": (3, 1, 2),
}


def apply_s3(perm_name: str, state: tuple[int, int, int]) -> tuple[int, int, int]:
    """Apply an S_3 element to a chart state.

    The permutation perm = (p_1, p_2, p_3) sends position i to position p_i.
    For a state v = (v_1, v_2, v_3) the result has v'_i = v_{p_i}.
    """
    p = S3[perm_name]
    return (state[p[0] - 1], state[p[1] - 1], state[p[2] - 1])


def shell2_transition_element(
    src: tuple[int, int, int],
    dst: tuple[int, int, int],
) -> str:
    """Return the unique S_3 element mapping src → dst on the shell=2 stratum.

    Any two distinct shell=2 states differ in exactly two positions (the
    position whose value flipped from 1→0 and the one that flipped 0→1).
    The transposition swapping those two positions sends src to dst.
    """
    if src not in SHELL2_STATES or dst not in SHELL2_STATES:
        raise ValueError(f"non-shell=2 state: src={src} dst={dst}")
    if src == dst:
        return "e"
    diff = [i for i in range(3) if src[i] != dst[i]]
    if len(diff) != 2:
        raise ValueError(
            f"shell=2 states differ in {len(diff)} positions, expected 2"
        )
    i, j = diff[0] + 1, diff[1] + 1
    return f"({i} {j})"


# ---------------------------------------------------------------------------
# Chart trajectory extraction
# ---------------------------------------------------------------------------

def rule30_chart_trajectory(max_depth: int) -> list[tuple[int, int, int]]:
    """Return the (L,C,R) chart state at each depth 0..max_depth from the
    single-cell seed.

    depth=0 is the seed: (0,1,0).
    """
    rows = canonical_rows(max_depth)
    return [(row.get(-1, 0), row.get(0, 0), row.get(1, 0)) for row in rows]


def shell2_subtrajectory(
    trajectory: list[tuple[int, int, int]],
) -> list[tuple[int, tuple[int, int, int]]]:
    """Return (depth, state) pairs from the trajectory where state ∈ shell=2."""
    return [(d, s) for d, s in enumerate(trajectory) if s in SHELL2_STATES]


# ---------------------------------------------------------------------------
# Codec
# ---------------------------------------------------------------------------

def encode(shell2_traj: list[tuple[int, tuple[int, int, int]]]) -> dict[str, Any]:
    """Encode a shell=2 sub-trajectory as (start_state, word).

    The word is the sequence of S_3 elements mapping each shell=2 state to
    the next. Depths are recorded so that decoded states can be re-aligned
    to the original chart timeline.
    """
    if not shell2_traj:
        return {"start_depth": None, "start_state": None, "word": [], "depths": []}
    depths = [d for d, _ in shell2_traj]
    states = [s for _, s in shell2_traj]
    word = [
        shell2_transition_element(states[i], states[i + 1])
        for i in range(len(states) - 1)
    ]
    return {
        "start_depth": depths[0],
        "start_state": states[0],
        "word": word,
        "depths": depths,
        "length": len(states),
    }


def decode(encoded: dict[str, Any]) -> list[tuple[int, tuple[int, int, int]]]:
    """Reconstruct the shell=2 (depth, state) sequence from an encoded form."""
    if encoded["start_state"] is None:
        return []
    state = encoded["start_state"]
    out = [(encoded["depths"][0], state)]
    for k, g in enumerate(encoded["word"]):
        state = apply_s3(g, state)
        out.append((encoded["depths"][k + 1], state))
    return out


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_chart_codec(max_depth: int = 4096) -> dict[str, Any]:
    """Encode/decode the Rule 30 shell=2 sub-trajectory and confirm
    round-trip equality at every step up to max_depth."""
    traj = rule30_chart_trajectory(max_depth)
    shell2 = shell2_subtrajectory(traj)
    encoded = encode(shell2)
    decoded = decode(encoded)

    mismatches = []
    for (d_a, s_a), (d_b, s_b) in zip(shell2, decoded):
        if (d_a, s_a) != (d_b, s_b):
            mismatches.append({"expected": (d_a, s_a), "got": (d_b, s_b)})

    word = encoded["word"]
    counts = {name: word.count(name) for name in S3.keys()}

    return {
        "status": "pass" if not mismatches and len(shell2) == len(decoded) else "fail",
        "max_depth": max_depth,
        "trajectory_length": len(traj),
        "shell2_length": len(shell2),
        "shell2_fraction": len(shell2) / len(traj) if traj else 0.0,
        "word_length": len(word),
        "round_trip_mismatches": len(mismatches),
        "first_mismatch": mismatches[0] if mismatches else None,
        "element_counts": counts,
        "identity_self_loops": counts.get("e", 0),
        "non_identity_steps": sum(v for k, v in counts.items() if k != "e"),
        "bits_per_shell2_step_raw": 1.585,  # log2(3) lower bound on shell=2 state
        "bits_per_step_codec": 2.0,         # log2(4) e + 3 transpositions
    }


if __name__ == "__main__":
    import json
    result = verify_chart_codec(max_depth=4096)
    print(json.dumps(result, indent=2))
