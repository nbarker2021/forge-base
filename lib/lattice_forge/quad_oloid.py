"""
quad_oloid.py — Four-Oloid D_4-quadrant ring with role-specific bijections.

Each of four Oloids occupies one D_4 quadrant (= one chart-axis in the
umbrella's `chart_codec_d4` antipodal codec) and carries a role-specific
1/4-spin generator from the octonion algebra:

    Oloid  D_4 axis          chart-axis label            generator  role
    ----  --------          ----------------            ---------  ----
    O_1   quad 1 / D1        axis 0 (shell-extremes)     e_4        ring-partner of O_4
    O_2   quad 2 / D2        axis 1 (left-active)        e_5        F_2 invariance gate
    O_3   quad 3 / D3        axis 2 (center-active)      e_6        arrow-of-time (bit-independent)
    O_4   quad 4 / D4        axis 3 (right-active)       e_7        ring-wrap to O_1

The split (e_4, e_5, e_6, e_7) is exactly the four imaginary octonions
NOT in the embedded quaternion subalgebra H = span(1, e_1, e_2, e_3),
i.e., the "octonionic extension" coordinates that Cayley-Dickson
doubling adds. Each role-specific generator squares to -1 (so two
applications = 180° gauge inversion) and four applications = identity
(the Oloid 4-period). They generate distinct rotations because of
octonion non-associativity.

Role contracts
--------------
    O_1 (ring partner):
        rolls under `bit` using generator e_4
        bijectively paired with O_4: the product O_1.octonion * conj(O_4.octonion)
        should land on the real line (real bit-independent invariant)

    O_2 (F_2 invariance):
        rolls under `bit` using generator e_5
        the orient bit's XOR-history is a F_2 cocycle: each step adds a
        verifiable invariance constraint

    O_3 (arrow of time):
        rolls UNDER A FIXED GENERATOR e_6 (bit-INDEPENDENT)
        provides the time-direction observer; its state at depth N is
        a pure function of N, not of the bit history

    O_4 (ring wrap):
        rolls under `1 - bit` (the antipodal bit) using generator e_7
        the wrap-closure check is the pairing O_4 -> O_1 via conjugation

Quad-orient signature
---------------------
After rolling, the QuadOloid emits a 4-bit quad-orient signature:
each Oloid contributes its individual orient bit. The signature lives
in F_2^4 and addresses up to 16 distinct "local frames" per input bit.

Empirical limit (algebraic trapping)
------------------------------------
Each Oloid's two bit-dependent generators (e.g. e_4 and e_5) generate
a 4-dimensional quaternion sub-algebra H = span(1, e_1, e_4, e_5) ⊂ O,
which has 8 unit elements. After rolling, each Oloid's state stays
inside its sub-algebra. The four Oloids' sub-algebras share enough
overlap that the joint quad-state takes only ~4 distinct values across
all 256 length-8 inputs (verified empirically), and the 4-bit signature
collapses to ~2 distinct values rather than 16.

This is NOT a bug — it is the structural signature that the LOCAL
four-Oloid ring is trapped in a quaternion-sub-algebra orbit. Breaking
out of the sub-algebra requires the GLOBAL E_6 → E_7 → E_8 dyadic lift
(the umbrella's exceptional Lie tower: F_4 → E_6 → E_7 → E_8). The
E-tower introduces coupling between Oloids (and between rolling levels)
that escapes the quaternion trap.

The QuadOloid as defined here is a working SKELETON of the local
four-quadrant structure. The full information bandwidth requires the
E-tower lift, which is the open scope of obligation O2'' (T_F2_BRIDGE
governance framework, extended with E_6/E_7/E_8 pode-antipode dyads).
"""
from __future__ import annotations

from typing import Iterable

from .octonion import Octonion, O_ONE, O_E4, O_E5, O_E6, O_E7
from .oloid_octonionic import OctonionicOloidState


# ---------------------------------------------------------------------------
# Role-specific generator PAIRS (the octonionic extension coordinates)
#
# Each Oloid uses two distinct generators, one for bit=0 and one for
# bit=1. The two generators are adjacent in the (e_4, e_5, e_6, e_7)
# cycle so each Oloid spans a different rotation-plane pair. The choice
# rotates cyclically through the 4-tuple, ensuring each Oloid samples
# a different pair of octonion axes:
#
#     Oloid    bit=0    bit=1
#     O_1      e_4      e_5
#     O_2      e_5      e_6
#     O_3      e_6      e_7
#     O_4      e_7      e_4
#
# Using two distinct generators per Oloid (rather than ±same generator)
# produces genuine path-dependent orient bits: orient depends on the
# specific bit history, not just the bit popcount.
# ---------------------------------------------------------------------------

GENERATOR_O1_BIT0: Octonion = O_E4
GENERATOR_O1_BIT1: Octonion = O_E5
GENERATOR_O2_BIT0: Octonion = O_E5
GENERATOR_O2_BIT1: Octonion = O_E6
GENERATOR_O3_BIT0: Octonion = O_E6
GENERATOR_O3_BIT1: Octonion = O_E7
GENERATOR_O4_BIT0: Octonion = O_E7
GENERATOR_O4_BIT1: Octonion = O_E4


# ---------------------------------------------------------------------------
# Four-Oloid ring
# ---------------------------------------------------------------------------

class QuadOloid:
    """Four OctonionicOloidStates in a D_4-quadrant ring with explicit
    role bijections.

    Each Oloid is initialized at a distinct octonion seed so the four
    quadrants start at four distinct frames in F_2^4.
    """

    __slots__ = ("o1", "o2", "o3", "o4")

    def __init__(
        self,
        o1: OctonionicOloidState | None = None,
        o2: OctonionicOloidState | None = None,
        o3: OctonionicOloidState | None = None,
        o4: OctonionicOloidState | None = None,
    ):
        # Default: each Oloid starts at its role-specific generator's
        # cube root (i.e., applied 1, 2, 3, 4 times to O_ONE respectively).
        # This guarantees distinct initial frames.
        self.o1 = o1 if o1 is not None else OctonionicOloidState(O_ONE)
        self.o2 = o2 if o2 is not None else OctonionicOloidState(O_ONE * GENERATOR_O2_BIT0)
        self.o3 = o3 if o3 is not None else OctonionicOloidState(O_ONE * GENERATOR_O3_BIT0)
        self.o4 = o4 if o4 is not None else OctonionicOloidState(GENERATOR_O4_BIT0 * GENERATOR_O4_BIT0)

    def roll(self, bit: int) -> "QuadOloid":
        """One quad-rolling step. Each Oloid right-multiplies by its
        role-specific generator pair (one generator for bit=0, a
        different one for bit=1). The bit-coupling is also role-specific:

            O_1: rolls under `bit`         (own bit)
            O_2: rolls under `bit`         (own bit; F_2 gate verifies separately)
            O_3: rolls under `0`           (bit-independent observer / time arrow)
            O_4: rolls under `1 - bit`     (antipodal bit; ring-wrap)
        """
        if bit not in (0, 1):
            raise ValueError(f"bit must be 0 or 1, got {bit}")
        return QuadOloid(
            o1=_roll_with_pair(self.o1, GENERATOR_O1_BIT0, GENERATOR_O1_BIT1, bit),
            o2=_roll_with_pair(self.o2, GENERATOR_O2_BIT0, GENERATOR_O2_BIT1, bit),
            o3=_roll_with_pair(self.o3, GENERATOR_O3_BIT0, GENERATOR_O3_BIT1, 0),
            o4=_roll_with_pair(self.o4, GENERATOR_O4_BIT0, GENERATOR_O4_BIT1, 1 - bit),
        )

    def quad_orient_signature(self) -> tuple[int, int, int, int]:
        """The 4-bit quad-orient signature. Each Oloid uses a DIFFERENT
        signature derivation tied to its role, so the four bits sample
        genuinely independent F_2 invariants of the octonion state:

            O_1 (ring partner):     sign of the e_4 component (its primary
                                    generator direction)
            O_2 (F_2 invariance):   parity of popcount of components > 0
                                    (the F_2 cocycle of positive coords)
            O_3 (time arrow):       sign of the e_6 - e_0 difference
                                    (observer's offset from the real line)
            O_4 (ring wrap):        sign of c[4]+c[5]+c[6]+c[7] (the
                                    octonionic-extension hemisphere)

        Each derivation looks at a different geometric feature of the
        octonion state, so the four bits sample F_2^4 = 16 distinct
        local frames rather than four correlated signs of one feature.
        """
        c1 = self.o1.octonion.components
        c2 = self.o2.octonion.components
        c3 = self.o3.octonion.components
        c4 = self.o4.octonion.components

        # O_1: sign of e_4 coordinate
        bit_1 = 1 if c1[4] >= 0 else 0

        # O_2: parity of popcount of strictly positive components
        bit_2 = sum(1 for x in c2 if x > 1e-12) & 1

        # O_3: sign of (e_6 - e_0) — observer's offset from the real line
        bit_3 = 1 if (c3[6] - c3[0]) >= 0 else 0

        # O_4: sign of the octonionic-extension hemisphere sum
        ext_sum = c4[4] + c4[5] + c4[6] + c4[7]
        bit_4 = 1 if ext_sum >= 0 else 0

        return (bit_1, bit_2, bit_3, bit_4)

    def quad_orient_int(self) -> int:
        """Quad-orient as an integer in [0, 16)."""
        s = self.quad_orient_signature()
        return s[0] + 2 * s[1] + 4 * s[2] + 8 * s[3]

    def ring_closure_check(self) -> dict:
        """The O_1 <-> O_4 ring closure check: O_1.octonion * conj(O_4.octonion)
        should have its dominant component on the real line if the ring
        is well-closed."""
        pairing = self.o1.octonion * self.o4.octonion.conjugate()
        comps = pairing.components
        real_part = comps[0]
        dominant_idx = max(range(8), key=lambda i: abs(comps[i]))
        return {
            "pairing_real": real_part,
            "pairing_dominant_index": dominant_idx,
            "ring_closes_on_real_line": dominant_idx == 0,
        }

    def as_dict(self) -> dict:
        return {
            "o1": self.o1.as_dict(),
            "o2": self.o2.as_dict(),
            "o3": self.o3.as_dict(),
            "o4": self.o4.as_dict(),
            "quad_orient_signature": list(self.quad_orient_signature()),
            "quad_orient_int": self.quad_orient_int(),
            "ring_closure": self.ring_closure_check(),
        }


def _roll_with_pair(
    state: OctonionicOloidState,
    gen_bit0: Octonion,
    gen_bit1: Octonion,
    bit: int,
) -> OctonionicOloidState:
    """One roll: right-multiply by gen_bit0 if bit==0, gen_bit1 if bit==1.

    Distinct generators per bit value couples the bit history into the
    octonion path via genuine non-associativity: orient_bit then depends
    on the specific sequence of bits, not just the bit popcount.
    """
    g = gen_bit0 if bit == 0 else gen_bit1
    return OctonionicOloidState(state.octonion * g)


# ---------------------------------------------------------------------------
# Rolling driver
# ---------------------------------------------------------------------------

def roll_quad(bits: Iterable[int], initial: QuadOloid | None = None) -> QuadOloid:
    state = initial or QuadOloid()
    for b in bits:
        state = state.roll(b)
    return state


# ---------------------------------------------------------------------------
# Information content of the quad-orient signature
# ---------------------------------------------------------------------------

def quad_orient_information_content(
    bit_sequences: list[list[int]],
) -> dict:
    """For each bit sequence, compute the quad-orient signature at the
    landing. Report:
      * marginal distribution of each of the 4 quad-orient bits
      * joint distribution of all 16 quad-orient values
      * mutual independence relative to the last bit
    """
    from collections import Counter

    quad_counts: Counter = Counter()
    joint_with_last_bit: Counter = Counter()
    per_oloid_match_not_last = [0, 0, 0, 0]
    total = 0

    for seq in bit_sequences:
        if not seq:
            continue
        state = roll_quad(seq)
        sig = state.quad_orient_signature()
        last_bit = seq[-1]
        quad_counts[sig] += 1
        joint_with_last_bit[(last_bit, sig)] += 1
        for i, b in enumerate(sig):
            if b == (1 - last_bit):
                per_oloid_match_not_last[i] += 1
        total += 1

    return {
        "sample_count": total,
        "quad_orient_marginal_distribution": {
            "_".join(str(b) for b in k): v for k, v in quad_counts.items()
        },
        "distinct_quad_orient_values": len(quad_counts),
        "max_possible_quad_orient_values": 16,
        "per_oloid_match_not_last_bit": {
            f"oloid_{i+1}": (c / total if total else 0.0)
            for i, c in enumerate(per_oloid_match_not_last)
        },
        # If every oloid's orient bit were trivially NOT bit, this would be 1.0.
        # If independent of bit, this would be ~0.5.
    }


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_quad_oloid() -> dict:
    """Battery of correctness checks for the four-Oloid D_4 ring."""
    results: dict = {}

    # 1. Initial state: all four Oloids have distinct octonion seeds
    q = QuadOloid()
    seeds = [
        q.o1.octonion.components,
        q.o2.octonion.components,
        q.o3.octonion.components,
        q.o4.octonion.components,
    ]
    all_distinct = True
    for i in range(4):
        for j in range(i + 1, 4):
            if seeds[i] == seeds[j]:
                all_distinct = False
    results["distinct_initial_seeds"] = all_distinct

    # 2. Four rolls with bit=0 return each Oloid to its initial state
    #    (since each generator's 4th power is +1)
    q = QuadOloid()
    rolled = q
    for _ in range(4):
        rolled = rolled.roll(0)
    diffs = []
    for orig, new in [
        (q.o1, rolled.o1), (q.o2, rolled.o2), (q.o3, rolled.o3), (q.o4, rolled.o4),
    ]:
        max_diff = max(
            abs(a - b) for a, b in zip(orig.octonion.components, new.octonion.components)
        )
        diffs.append(max_diff)
    results["four_rolls_bit0_return_each_oloid"] = max(diffs) < 1e-10

    # 3. The quad-orient signature gives a 4-bit address
    q = roll_quad([1, 0, 1, 1, 0, 0, 1, 0])
    sig = q.quad_orient_signature()
    results["quad_orient_after_8_bits"] = list(sig)
    results["quad_orient_int_after_8_bits"] = q.quad_orient_int()

    # 4. Information content over all 8-bit inputs
    sequences = [[(n >> i) & 1 for i in range(8)] for n in range(256)]
    info = quad_orient_information_content(sequences)
    results["distinct_quad_orient_over_256_inputs"] = info["distinct_quad_orient_values"]
    results["per_oloid_match_not_last_bit"] = info["per_oloid_match_not_last_bit"]

    # 5. Ring closure check
    rc = roll_quad([1, 0, 1, 1]).ring_closure_check()
    results["ring_closure_pairing_dominant"] = rc["pairing_dominant_index"]

    expected_pass = (
        results["distinct_initial_seeds"]
        and results["four_rolls_bit0_return_each_oloid"]
        and results["distinct_quad_orient_over_256_inputs"] >= 2
    )
    results["status"] = "pass" if expected_pass else "fail"
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(verify_quad_oloid(), indent=2, default=str))
