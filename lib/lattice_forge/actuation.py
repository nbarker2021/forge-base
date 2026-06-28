"""
actuation.py — Explicit actuation functions on rolling states.

The umbrella's bijection-forcing principle (load-bearing): every read of
N must be paired with an antipodal read of -N. The two reads differ by
the SPECTRAL ACTUATION applied to the state:

    Reading N   → applies the +1 spectrality actuation (identity)
    Reading -N  → applies the -1 spectrality actuation (spectral negation)

The -1 actuation is multiplication of the state's algebraic element by
-1. Geometrically this is the 180° rotation that exchanges the two
sheets of the bijective companion. Two -1 actuations compose to the
identity: applying the antipodal twice returns to the original state.

Spectrality
-----------
Each state carries an explicit spectrality bit s ∈ {0, 1}:
    s = 0  →  +1 actuation (state used as-is)
    s = 1  →  -1 actuation (state negated)

When two states are joined (paired_read or composed roll), their joint
spectrality is s_1 XOR s_2 (the F_2 sum), and the joint actuation is
the product of their individual actuations.

This module provides:
    * `Actuation` — a first-class actuation element {+1, -1}
    * `apply_actuation(state, actuation)` — generic application across
      OctonionicOloidState, KinematicOloidState, QuadOloid
    * `paired_actuation_read` — read N with +1 actuation, read -N with -1,
      return both states + joint signature
"""
from __future__ import annotations

import math
from typing import Any

from .octonion import Octonion, O_ONE
from .oloid_octonionic import OctonionicOloidState
from .oloid_kinematic import KinematicOloidState
from .quad_oloid import QuadOloid


# ---------------------------------------------------------------------------
# Actuation primitive
# ---------------------------------------------------------------------------

class Actuation:
    """A first-class spectral actuation {+1, -1} acting on rolling states.

    Construct with sign ∈ {+1, -1}. Two actuations compose by multiplying
    their signs; the F_2 spectrality bit is (1 - sign) // 2.
    """

    __slots__ = ("sign",)

    POSITIVE: "Actuation"
    NEGATIVE: "Actuation"

    def __init__(self, sign: int):
        if sign not in (1, -1):
            raise ValueError(f"actuation sign must be ±1, got {sign}")
        self.sign = sign

    @property
    def spectrality(self) -> int:
        """The F_2 spectrality bit: 0 for +1 actuation, 1 for -1."""
        return (1 - self.sign) // 2

    def compose(self, other: "Actuation") -> "Actuation":
        """Composition: signs multiply, F_2 spectralities XOR."""
        return Actuation(self.sign * other.sign)

    def __repr__(self) -> str:
        return f"Actuation({'+1' if self.sign == 1 else '-1'})"

    def __eq__(self, other) -> bool:
        return isinstance(other, Actuation) and self.sign == other.sign

    def __hash__(self) -> int:
        return hash(self.sign)


Actuation.POSITIVE = Actuation(+1)
Actuation.NEGATIVE = Actuation(-1)


def actuation_for_query(N: int) -> Actuation:
    """Convention: positive depth N uses +1 actuation, negative -N uses -1.
    For the bijective read this is applied to both N and -N as paired
    actuations differing by sign."""
    return Actuation.POSITIVE if N > 0 else Actuation.NEGATIVE


# ---------------------------------------------------------------------------
# Apply actuation to specific state types
# ---------------------------------------------------------------------------

def actuate_octonionic(
    state: OctonionicOloidState, actuation: Actuation
) -> OctonionicOloidState:
    """Apply spectral actuation to an octonionic Oloid state.

    +1 actuation: identity
    -1 actuation: octonion multiplied by -1 (state.octonion * -1)
    """
    if actuation.sign == 1:
        return state
    return OctonionicOloidState(state.octonion * (-1.0))


def actuate_kinematic(
    state: KinematicOloidState, actuation: Actuation
) -> KinematicOloidState:
    """Apply spectral actuation to a kinematic Oloid state.

    +1 actuation: identity
    -1 actuation: θ += π (180° rotation), parity unchanged
    """
    if actuation.sign == 1:
        return state
    return KinematicOloidState(
        theta=(state.theta + math.pi) % (2 * math.pi),
        parity=state.parity,
    )


def actuate_quad(quad: QuadOloid, actuation: Actuation) -> QuadOloid:
    """Apply spectral actuation to all four Oloids in a QuadOloid."""
    if actuation.sign == 1:
        return quad
    return QuadOloid(
        o1=actuate_octonionic(quad.o1, actuation),
        o2=actuate_octonionic(quad.o2, actuation),
        o3=actuate_octonionic(quad.o3, actuation),
        o4=actuate_octonionic(quad.o4, actuation),
    )


# ---------------------------------------------------------------------------
# Paired actuation read
# ---------------------------------------------------------------------------

def paired_actuation_read_octonionic(
    N: int,
    enumeration_bit_fn,
    history_bits: list[int] | None = None,
) -> dict[str, Any]:
    """Read N from the substrate via paired ±1 actuations.

    Step 1: read enumeration → b at N, ¬b at -N (precondition antipode)
    Step 2: build TWO octonion-Oloid traces in parallel:
              positive_state: starts from O_ONE under +1 actuation,
                              rolls history_bits ending with b
              negative_state: starts from O_ONE under -1 actuation
                              (= -O_ONE = O_ONE.actuate(NEGATIVE)),
                              rolls history_bits ending with ¬b
    Step 3: return both states + their joint spectral signature.

    The joint spectral signature is the F_2 sum of:
        sign(positive_state.octonion.components[0])
      ⊕ sign(negative_state.octonion.components[0])
    This is the load-bearing F_2 invariant: it should equal 1 under
    correct bijection (since positive and negative traces have opposite
    real-part signs after a paired roll).
    """
    from .oloid_octonionic import roll_octonion

    b = enumeration_bit_fn(N)
    b_at_minus_N = 1 - b
    if history_bits is None:
        history_bits_pos = [b]
        history_bits_neg = [b_at_minus_N]
    else:
        history_bits_pos = list(history_bits) + [b]
        history_bits_neg = [1 - x for x in history_bits] + [b_at_minus_N]

    # Start from the same root and apply opposite actuations
    initial_pos = actuate_octonionic(OctonionicOloidState(O_ONE), Actuation.POSITIVE)
    initial_neg = actuate_octonionic(OctonionicOloidState(O_ONE), Actuation.NEGATIVE)

    positive_state = roll_octonion(history_bits_pos, initial=initial_pos)
    negative_state = roll_octonion(history_bits_neg, initial=initial_neg)

    # The substantive F_2 signature uses the orient bit (parity of dominant
    # octonion-basis index), which carries non-trivial path information
    # because octonion multiplication is non-associative. Real-part signs
    # would be trivial here because octonion rolls produce pure-imaginary
    # results.
    pos_orient = positive_state.orient_bit()
    neg_orient = negative_state.orient_bit()
    pos_dom_idx = positive_state.dominant_basis_index()
    neg_dom_idx = negative_state.dominant_basis_index()
    joint_signature = pos_orient ^ neg_orient

    return {
        "N": N,
        "bit_at_N": b,
        "bit_at_minus_N": b_at_minus_N,
        "positive_state": positive_state,
        "negative_state": negative_state,
        "positive_orient_bit": pos_orient,
        "negative_orient_bit": neg_orient,
        "positive_dominant_index": pos_dom_idx,
        "negative_dominant_index": neg_dom_idx,
        "joint_spectral_signature": joint_signature,
        # Bijective expectation: joint should be 1 (the +1 and -1
        # actuated traces are antipodal images, so their orient bits
        # should disagree at every step where the bijection holds).
        "bijection_consistent": joint_signature == 1,
    }


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_actuation_module() -> dict[str, Any]:
    """Battery of correctness checks for the actuation primitives."""
    results: dict[str, Any] = {}

    # 1. POSITIVE * POSITIVE = POSITIVE
    p_p = Actuation.POSITIVE.compose(Actuation.POSITIVE)
    results["pos_pos_is_pos"] = (p_p == Actuation.POSITIVE)

    # 2. NEGATIVE * NEGATIVE = POSITIVE
    n_n = Actuation.NEGATIVE.compose(Actuation.NEGATIVE)
    results["neg_neg_is_pos"] = (n_n == Actuation.POSITIVE)

    # 3. POSITIVE * NEGATIVE = NEGATIVE
    p_n = Actuation.POSITIVE.compose(Actuation.NEGATIVE)
    results["pos_neg_is_neg"] = (p_n == Actuation.NEGATIVE)

    # 4. spectrality of NEGATIVE = 1
    results["negative_spectrality_is_1"] = (Actuation.NEGATIVE.spectrality == 1)
    results["positive_spectrality_is_0"] = (Actuation.POSITIVE.spectrality == 0)

    # 5. Octonionic +1 actuation is identity
    s = OctonionicOloidState(O_ONE)
    s_actuated = actuate_octonionic(s, Actuation.POSITIVE)
    results["octonionic_positive_is_identity"] = (
        s_actuated.octonion.components == s.octonion.components
    )

    # 6. Octonionic -1 actuation negates components
    s_neg = actuate_octonionic(s, Actuation.NEGATIVE)
    results["octonionic_negative_negates"] = (
        s_neg.octonion.components[0] == -1.0
        and all(c == 0.0 for c in s_neg.octonion.components[1:])
    )

    # 7. Octonionic actuation involutive: -1 then -1 returns to original
    s_back = actuate_octonionic(s_neg, Actuation.NEGATIVE)
    results["octonionic_negative_is_involution"] = (
        s_back.octonion.components == s.octonion.components
    )

    # 8. Kinematic +1 is identity
    k = KinematicOloidState()
    k_actuated = actuate_kinematic(k, Actuation.POSITIVE)
    results["kinematic_positive_is_identity"] = (
        k_actuated.theta == k.theta and k_actuated.parity == k.parity
    )

    # 9. Kinematic -1 advances θ by π
    k_neg = actuate_kinematic(k, Actuation.NEGATIVE)
    results["kinematic_negative_advances_pi"] = abs(k_neg.theta - math.pi) < 1e-12

    # 10. Kinematic -1 is involutive
    k_back = actuate_kinematic(k_neg, Actuation.NEGATIVE)
    results["kinematic_negative_is_involution"] = abs(k_back.theta) < 1e-12

    # 11. Paired actuation read against a known Rule 30 input
    from .block_tower import rule30_center_column
    bits = rule30_center_column(64)
    def enum(n):
        return bits[n - 1]
    # Test at N=1, 5, 17, 33, 64
    consistent_count = 0
    for N in (1, 5, 17, 33, 64):
        r = paired_actuation_read_octonionic(N, enum)
        if r["bijection_consistent"]:
            consistent_count += 1
    results["paired_read_consistency_5_samples"] = consistent_count
    results["paired_read_consistency_rate"] = consistent_count / 5

    all_pass = all(
        v if isinstance(v, bool) else True
        for v in results.values()
    )
    results["status"] = "pass" if all_pass else "fail"
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(verify_actuation_module(), indent=2, default=str))
