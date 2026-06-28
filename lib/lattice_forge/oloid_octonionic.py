"""
oloid_octonionic.py — Octonion-grounded Oloid rolling, where the rolling
operations are ACTUAL octonion right-multiplications rather than integer
phase counters.

The replacement of assumption with assertion
--------------------------------------------
In `oloid_rolling.py` and `oloid_dual_path.py`, the rolling state is
tracked as integers (sheet, phase, parity). Those integers are the
*shadow* projections of operations that live natively in the octonion
algebra O:

    "1/4 spin in octonion space"  =  right-multiplication by e_4

This generator satisfies:
    e_4 * e_4 = -1          (two applications = 180° gauge inversion)
    e_4^4 = +1              (four applications = identity)

which is exactly the Oloid's 4-period rolling structure. By carrying an
actual `Octonion` in each rolling state and performing the rolls as
right-multiplications, we replace the shadow with the algebra itself.

What this module provides
-------------------------
    * `OctonionicOloidState` — rolling state carrying an actual `Octonion`
    * `roll(bit)` — right-multiplication by `e_4` (bit=0) or `e_5` (bit=1)
    * `gauge_inverted_initial()` — `O_ONE * (-1)`, the explicit 180° flip
    * `orient_bit(state)` — derived from the *non-trivial octonion
      projection* `parity(argmax_i |state.components[i]|)`, which gives
      information beyond `not bit`

The non-trivial orient bit comes from the fact that octonion
multiplication is non-associative: the result of rolling a bit-sequence
depends on the order, and the "dominant component" of the resulting
octonion encodes a path-history feature that pure parity counting misses.
"""
from __future__ import annotations

from typing import Iterable

from .octonion import (
    Octonion,
    O_ONE,
    O_E1, O_E2, O_E3, O_E4, O_E5, O_E6, O_E7,
)


# ---------------------------------------------------------------------------
# Generator selection
# ---------------------------------------------------------------------------

# The 1/4-spin generator for bit=0: e_4. Squares to -1 (180° = gauge
# inversion). Four applications return to identity (the Oloid period).
GENERATOR_BIT0: Octonion = O_E4

# The 1/4-spin generator for bit=1: e_5. Same period structure (e_5^2 = -1,
# e_5^4 = +1), but distinct from e_4 — gives bit-dependent path divergence.
GENERATOR_BIT1: Octonion = O_E5

# Octonions are non-associative: x * (y * z) != (x * y) * z in general.
# This is why the "orient bit" derived from the octonion path carries
# information beyond bit parity.


# ---------------------------------------------------------------------------
# Octonion-grounded Oloid state
# ---------------------------------------------------------------------------

class OctonionicOloidState:
    """Oloid rolling state carrying an actual `Octonion` value.

    The `roll(bit)` operation is right-multiplication by `e_4` or `e_5`
    depending on the bit. The 180° gauge inversion is multiplication by
    `-1` (which equals `e_4 * e_4`).
    """

    __slots__ = ("octonion",)

    def __init__(self, octonion: Octonion | None = None):
        self.octonion = octonion if octonion is not None else O_ONE

    @classmethod
    def initial(cls) -> "OctonionicOloidState":
        """Default initial state: O_ONE (the real unit octonion)."""
        return cls(O_ONE)

    @classmethod
    def gauge_inverted(cls) -> "OctonionicOloidState":
        """180° gauge inversion: multiply O_ONE by -1.

        Equivalently: apply two 1/4-spin rotations via e_4 * e_4 = -1.
        This is the FIRST encoded action of the read-then-verify flow.
        """
        return cls(O_ONE * (-1.0))

    def roll(self, bit: int) -> "OctonionicOloidState":
        """One 1/4-spin step driven by `bit`. Right-multiplication by
        `e_4` (bit=0) or `e_5` (bit=1)."""
        if bit == 0:
            return OctonionicOloidState(self.octonion * GENERATOR_BIT0)
        elif bit == 1:
            return OctonionicOloidState(self.octonion * GENERATOR_BIT1)
        else:
            raise ValueError(f"bit must be 0 or 1, got {bit}")

    def head_bit(self) -> int:
        """The "head" bit of the dyad: sign of the e_0 component.
        Returns 1 if components[0] >= 0, else 0.

        Note: this does NOT predict Rule 30 — the head bit is a property
        of the octonion state, not a substitute for the enumeration read.
        """
        return 1 if self.octonion.components[0] >= 0 else 0

    def orient_bit(self) -> int:
        """The orienting bit: parity of the index of the dominant
        (largest |component|) octonion basis element.

        This is the 1/4-spin error-correcting bit the user describes:
        it carries genuine information about the *path history* through
        the octonion algebra, not just the cumulative bit parity.
        """
        comps = self.octonion.components
        max_idx = max(range(8), key=lambda i: abs(comps[i]))
        return max_idx & 1

    def dominant_basis_index(self) -> int:
        """Index of the dominant basis element (0..7)."""
        comps = self.octonion.components
        return max(range(8), key=lambda i: abs(comps[i]))

    def as_dict(self) -> dict:
        return {
            "components": list(self.octonion.components),
            "dominant_index": self.dominant_basis_index(),
            "orient_bit": self.orient_bit(),
            "head_bit": self.head_bit(),
        }


# ---------------------------------------------------------------------------
# Rolling operations
# ---------------------------------------------------------------------------

def roll_octonion(
    bits: Iterable[int],
    initial: OctonionicOloidState | None = None,
) -> OctonionicOloidState:
    """Apply `bits` as successive 1/4-spin steps."""
    state = initial or OctonionicOloidState.initial()
    for b in bits:
        state = state.roll(b)
    return state


def roll_octonion_trace(
    bits: Iterable[int],
    initial: OctonionicOloidState | None = None,
) -> list[OctonionicOloidState]:
    """Full octonion-state history along the rolling."""
    state = initial or OctonionicOloidState.initial()
    trace = [state]
    for b in bits:
        state = state.roll(b)
        trace.append(state)
    return trace


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_octonionic_oloid() -> dict:
    """Battery of correctness checks for the octonion-grounded Oloid."""
    results: dict = {}

    # 1. e_4 * e_4 = -1 (the 180° gauge inversion identity)
    e4_sq = O_E4 * O_E4
    results["e4_squared_is_minus_one"] = (
        abs(e4_sq.components[0] - (-1.0)) < 1e-12
        and all(abs(c) < 1e-12 for c in e4_sq.components[1:])
    )

    # 2. e_4^4 = +1 (the 4-period rolling identity)
    e4_4 = e4_sq * e4_sq
    results["e4_fourth_is_one"] = (
        abs(e4_4.components[0] - 1.0) < 1e-12
        and all(abs(c) < 1e-12 for c in e4_4.components[1:])
    )

    # 3. Gauge inversion = state * (-1) = state * e_4 * e_4
    initial = OctonionicOloidState.initial()
    gauge = OctonionicOloidState.gauge_inverted()
    via_e4_squared = initial.roll(0).roll(0)  # roll twice with bit=0
    results["gauge_inversion_equals_double_roll_bit0"] = (
        abs(gauge.octonion.components[0] - via_e4_squared.octonion.components[0]) < 1e-12
    )

    # 4. Four rolls with bit=0 return to initial
    s = OctonionicOloidState.initial()
    for _ in range(4):
        s = s.roll(0)
    diffs = [abs(a - b) for a, b in zip(s.octonion.components, initial.octonion.components)]
    results["four_rolls_bit0_return_to_initial"] = max(diffs) < 1e-12

    # 5. Non-associativity: (1 * e_4) * e_5 vs 1 * (e_4 * e_5)
    a = (O_ONE * O_E4) * O_E5
    b = O_ONE * (O_E4 * O_E5)
    # These should be EQUAL because O_ONE is the identity (so it factors out)
    diffs = [abs(x - y) for x, y in zip(a.components, b.components)]
    results["associative_when_one_is_identity"] = max(diffs) < 1e-12

    # 6. Genuine non-associativity: (e_1 * e_2) * e_4 vs e_1 * (e_2 * e_4)
    a = (O_E1 * O_E2) * O_E4
    b = O_E1 * (O_E2 * O_E4)
    diffs = [abs(x - y) for x, y in zip(a.components, b.components)]
    results["non_associative_imaginary_units"] = max(diffs) > 1e-9

    # 7. Orient bit for a known bit sequence is deterministic
    s = roll_octonion([1, 0, 1, 1, 0])
    results["orient_after_known_input"] = s.orient_bit()
    results["dominant_after_known_input"] = s.dominant_basis_index()

    expected_pass = (
        results["e4_squared_is_minus_one"]
        and results["e4_fourth_is_one"]
        and results["gauge_inversion_equals_double_roll_bit0"]
        and results["four_rolls_bit0_return_to_initial"]
        and results["associative_when_one_is_identity"]
        and results["non_associative_imaginary_units"]
    )
    results["status"] = "pass" if expected_pass else "fail"
    return results


# ---------------------------------------------------------------------------
# Compare orient bit against trivial (NOT bit) behaviour at a depth range
# ---------------------------------------------------------------------------

def orient_bit_information_content(
    bit_sequences: list[list[int]],
) -> dict:
    """For a collection of bit sequences, compute:
      * how often the orient bit equals (NOT last_bit) — the trivial baseline
      * the marginal distribution of orient bits
      * the joint (last_bit, orient_bit) distribution

    If orient_bit always = NOT last_bit, the orient bit carries no
    information beyond the bit. If the joint distribution is non-trivial,
    the orient bit is a genuine independent F_2 invariant.
    """
    from collections import Counter
    counts = Counter()
    for seq in bit_sequences:
        if not seq:
            continue
        state = roll_octonion(seq)
        last_bit = seq[-1]
        orient = state.orient_bit()
        counts[(last_bit, orient)] += 1
    total = sum(counts.values())
    equals_not_bit = (
        counts.get((0, 1), 0) + counts.get((1, 0), 0)
    )
    return {
        "sample_count": total,
        "joint_distribution": {
            f"last_bit={k[0]},orient={k[1]}": v for k, v in counts.items()
        },
        "orient_equals_not_bit_count": equals_not_bit,
        "trivial_baseline_rate": equals_not_bit / total if total else 0.0,
        "orient_marginal_density": (
            (counts.get((0, 1), 0) + counts.get((1, 1), 0)) / total
            if total else 0.0
        ),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify_octonionic_oloid(), indent=2, default=str))
    # Run the orient-bit information probe on a sample
    sequences = [
        [(n >> i) & 1 for i in range(8)] for n in range(256)
    ]
    print("Orient-bit information content over all 8-bit sequences:")
    print(json.dumps(orient_bit_information_content(sequences), indent=2, default=str))
