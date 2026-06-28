"""
oloid_kinematic.py — Empirical kinematic harness for the WP-OLOID-01 companion.

The Oloid (Schatz, 1933; Dirnböck & Stachel, 1997) is the convex hull of
two unit circles whose planes are perpendicular and whose centers are
separated by exactly the radius. It is the unique smooth convex body
that rolls without slipping on a plane while sweeping out its entire
surface in one full motion period.

This module simulates the Oloid's rolling kinematics numerically and
compares the resulting (sheet, phase, parity) sequence against the
discrete algebraic quad_oloid model. The trigger WP-OLOID-01 requires
"quad_oloid + full kinematic roll proof key in run_all_proofs". This
harness provides the kinematic proof key.

Kinematic model
---------------
We parametrize the rolling motion by an angle θ ∈ [0, 2π). The full
unroll has period 2π and the contact-circle alternates four times,
giving a natural 4-period quarter-rotation structure:

    θ ∈ [0,      π/2):    phase 0, sheet 0 (circle A in contact)
    θ ∈ [π/2,    π):      phase 1, sheet 1 (circle B in contact)
    θ ∈ [π,     3π/2):    phase 2, sheet 0 (circle A in contact)
    θ ∈ [3π/2,  2π):      phase 3, sheet 1 (circle B in contact)

At each quarter-boundary, the rolling kinematics swap which circle is
the support — the antipodal circle has rotated exactly 90° from its
prior orientation. This matches the algebraic identity e_4^4 = +1
(four rolls return to identity) and e_4^2 = -1 (two rolls = 180°
gauge inversion) from `oloid_octonionic`.

Correspondence test
-------------------
For a bit stream `b_0, b_1, ..., b_{N-1}`, we:

    1. Step the kinematic Oloid by Δθ = π/2 per bit, with `bit` controlling
       a phase advance vs phase reversal (binary direction).
    2. Step the algebraic quad_oloid by the same bit stream.
    3. At each step, compare the (sheet, phase) of the kinematic model
       to the (sheet, phase) inferred from the algebraic state.

If they agree at every step, the algebraic 4-period structure is
empirically faithful to the kinematic 4-period. If they diverge, we
report at which step and by how much (the "kinematic-discrete gap" the
prior Move 1 work measured at 33.6% defect floor).

Honesty discipline
------------------
The harness reports `BOUNDED_EXEC` honesty with explicit step count
and correspondence rate.
- Correspondence rate > 0.99 at N ≥ 256 steps would trigger WP-OLOID-01
  promotion to PROVEN_AT_TESTED_DEPTH.
- Correspondence rate ≤ 0.55 means the algebraic model is not faithful
  to the kinematic at this discretization.
- The discrete model can only ever match the kinematic at the
  4-period level; finer-grained kinematic features (like the Dirnböck-
  Stachel contact curve's exact shape) are not captured by quad_oloid.
"""
from __future__ import annotations

import math
from typing import Any, Iterable

from .quad_oloid import QuadOloid, roll_quad


# ---------------------------------------------------------------------------
# Continuous Oloid rolling parameters
# ---------------------------------------------------------------------------

# Quarter-period boundaries: one rolling step = one quarter-period (π/2)
QUARTER_PERIOD: float = math.pi / 2

# The Oloid's two circles labelled A and B
CIRCLE_A: str = "A"
CIRCLE_B: str = "B"


class KinematicOloidState:
    """Continuous rolling state of an Oloid parametrized by angle θ.

    θ ∈ [0, 2π) cycles through four quarter-periods, alternating which
    circle is the support and accumulating the rolling-direction parity.
    """

    __slots__ = ("theta", "parity")

    def __init__(self, theta: float = 0.0, parity: int = 0):
        # Wrap to [0, 2π)
        self.theta = theta % (2 * math.pi)
        self.parity = parity & 1

    def quarter_index(self) -> int:
        """Which of the 4 quarter-periods (0, 1, 2, 3) is currently active."""
        return int(self.theta // QUARTER_PERIOD) % 4

    def sheet(self) -> int:
        """Which circle (0=A, 1=B) is currently in contact with the plane.
        Circles alternate every quarter-period."""
        return self.quarter_index() & 1

    def phase(self) -> int:
        """The phase ∈ {0, 1, 2, 3} = the quarter index."""
        return self.quarter_index()

    def as_tuple(self) -> tuple[int, int, int]:
        return (self.sheet(), self.phase(), self.parity)

    def roll(self, bit: int) -> "KinematicOloidState":
        """Advance one quarter-period. `bit` controls rolling direction:
        bit=0 advances θ by +π/2; bit=1 advances by -π/2 (rolls backward).
        The parity tracks the XOR of all consumed bits (= the cumulative
        rolling-direction-reversal count mod 2).
        """
        if bit not in (0, 1):
            raise ValueError(f"bit must be 0 or 1, got {bit}")
        delta = QUARTER_PERIOD if bit == 0 else -QUARTER_PERIOD
        return KinematicOloidState(
            theta=(self.theta + delta) % (2 * math.pi),
            parity=(self.parity ^ bit) & 1,
        )


# ---------------------------------------------------------------------------
# Kinematic rolling driver
# ---------------------------------------------------------------------------

def roll_kinematic(
    bits: Iterable[int],
    initial: KinematicOloidState | None = None,
) -> KinematicOloidState:
    state = initial or KinematicOloidState(theta=0.0, parity=0)
    for b in bits:
        state = state.roll(b)
    return state


def roll_kinematic_trace(
    bits: Iterable[int],
    initial: KinematicOloidState | None = None,
) -> list[KinematicOloidState]:
    state = initial or KinematicOloidState(theta=0.0, parity=0)
    trace = [state]
    for b in bits:
        state = state.roll(b)
        trace.append(state)
    return trace


# ---------------------------------------------------------------------------
# Algebraic-vs-kinematic correspondence
# ---------------------------------------------------------------------------

# Map a quad_oloid state to a (sheet, phase) tuple by inspecting its
# four oloid sub-states. The "quad-state sheet" is defined as the parity
# of the count of Oloids whose dominant octonion-component index is ≥ 4
# (the octonionic-extension hemisphere). The "quad-state phase" is
# inferred from the cumulative quarter-rotations driven so far.

def quad_oloid_inferred_sheet_phase(
    q: QuadOloid,
    step: int,
    *,
    gauge_offset_phase: int = 0,
    gauge_offset_sheet: int = 0,
) -> tuple[int, int]:
    """Infer (sheet, phase) from the algebraic QuadOloid state at step `step`.

    Sheet: parity of count of Oloids with dominant octonion index ≥ 4,
           XORed with `gauge_offset_sheet`.
    Phase: (step + gauge_offset_phase) mod 4.

    The gauge offsets are NON-OPTIONAL when testing in the gauge-inverted
    bijective frame. Without them the algebraic and kinematic frames are
    offset by 2 in phase (= 180° = π) and differ in sheet by the
    extension-hemisphere flip from multiplying by -1.
    """
    dominant_indices = [
        q.o1.dominant_basis_index(),
        q.o2.dominant_basis_index(),
        q.o3.dominant_basis_index(),
        q.o4.dominant_basis_index(),
    ]
    extension_count = sum(1 for i in dominant_indices if i >= 4)
    sheet = (extension_count ^ gauge_offset_sheet) & 1
    phase = (step + gauge_offset_phase) & 3
    return (sheet, phase)


def gauge_inverted_kinematic_initial() -> KinematicOloidState:
    """The kinematic 180° gauge inversion: start at θ = π instead of 0.
    This is the FIRST encoded action that forces the full state bijection
    before any measurement (paralleling `gauge_inverted_initial()` in the
    octonion-grounded Oloid).
    """
    return KinematicOloidState(theta=math.pi, parity=0)


def gauge_inverted_quad_initial() -> QuadOloid:
    """The algebraic 180° gauge inversion: each Oloid is reflected through
    its octonionic-extension hemisphere (sheet flipped, phase advanced by 2).

    By the convention in `oloid_octonionic.gauge_inverted()`, this is
    multiplication of each Oloid's octonion state by e_4^2 = -1.
    """
    from .oloid_octonionic import OctonionicOloidState
    from .octonion import O_ONE
    return QuadOloid(
        o1=OctonionicOloidState(O_ONE * (-1.0)),
        o2=OctonionicOloidState(O_ONE * (-1.0)),
        o3=OctonionicOloidState(O_ONE * (-1.0)),
        o4=OctonionicOloidState(O_ONE * (-1.0)),
    )


def correspondence_test(
    bits: list[int],
    *,
    force_bijection: bool = True,
) -> dict[str, Any]:
    """Step both models through `bits` and compare (sheet, phase) at each step.

    The umbrella's load-bearing rule: any 1-sided test of an unproven
    state will hit a 50% Bernoulli trap because the bijective companion
    isn't being measured. We force the bijection by starting BOTH models
    from their gauge-inverted initial states.

    Args:
        bits: the bit stream to roll through
        force_bijection: if True (default), start from gauge-inverted state

    Returns:
        per-step (kinematic, algebraic) pairs
        total matches / total steps
        first-divergence step (or None)
        whether bijection-forcing was applied
    """
    if force_bijection:
        quad = gauge_inverted_quad_initial()
        kin = gauge_inverted_kinematic_initial()
        # Gauge-inverted kinematic starts at θ=π → phase=2, sheet=0.
        # Gauge-inverted algebraic has all Oloids multiplied by -1 →
        # dominant indices all stay in [0,7] but the extension-hemisphere
        # parity inherits the -1 sign-flip's count parity.
        gauge_phase_offset = 2
        gauge_sheet_offset = 0
    else:
        quad = QuadOloid()
        kin = KinematicOloidState()
        gauge_phase_offset = 0
        gauge_sheet_offset = 0

    matches = 0
    total = 0
    first_divergence_step: int | None = None
    sheet_matches = 0
    phase_matches = 0

    for step_idx, b in enumerate(bits):
        quad = quad.roll(b)
        kin = kin.roll(b)

        kin_sheet, kin_phase, _ = kin.as_tuple()
        alg_sheet, alg_phase = quad_oloid_inferred_sheet_phase(
            quad,
            step_idx + 1,
            gauge_offset_phase=gauge_phase_offset,
            gauge_offset_sheet=gauge_sheet_offset,
        )

        total += 1
        match_sheet = (kin_sheet == alg_sheet)
        match_phase = (kin_phase == alg_phase)
        if match_sheet:
            sheet_matches += 1
        if match_phase:
            phase_matches += 1
        if match_sheet and match_phase:
            matches += 1
        elif first_divergence_step is None:
            first_divergence_step = step_idx + 1

    return {
        "total_steps": total,
        "joint_match_count": matches,
        "joint_match_rate": matches / total if total else 0.0,
        "sheet_match_count": sheet_matches,
        "sheet_match_rate": sheet_matches / total if total else 0.0,
        "phase_match_count": phase_matches,
        "phase_match_rate": phase_matches / total if total else 0.0,
        "first_divergence_step": first_divergence_step,
    }


# ---------------------------------------------------------------------------
# Structural identities (kinematic)
# ---------------------------------------------------------------------------

def verify_four_period_returns_to_origin() -> bool:
    """Four bit=0 rolls advance θ by 4 × π/2 = 2π, returning to θ=0."""
    state = KinematicOloidState()
    for _ in range(4):
        state = state.roll(0)
    return abs(state.theta) < 1e-12 and state.parity == 0


def verify_two_period_is_pi_phase_advance() -> bool:
    """Two bit=0 rolls advance θ by π = 180° gauge inversion."""
    state = KinematicOloidState()
    state = state.roll(0).roll(0)
    return abs(state.theta - math.pi) < 1e-12


def verify_bit_complement_inverts_rotation() -> bool:
    """Rolling [1, 1, 1, 1] (= four backward quarter-turns) returns to origin."""
    state = KinematicOloidState()
    for _ in range(4):
        state = state.roll(1)
    return abs(state.theta) < 1e-12 and state.parity == 0


def verify_alternating_bits_zero_net() -> bool:
    """Rolling [0, 1, 0, 1] gives net θ = 0 and parity = 0."""
    state = roll_kinematic([0, 1, 0, 1])
    return abs(state.theta) < 1e-12 and state.parity == 0


# ---------------------------------------------------------------------------
# Top-level verifier
# ---------------------------------------------------------------------------

def verify_oloid_kinematic(
    bit_streams: list[list[int]] | None = None,
) -> dict[str, Any]:
    """Run kinematic structural checks + algebraic-correspondence test.

    Reports BOUNDED_EXEC honesty with explicit step count and rates.
    """
    if bit_streams is None:
        # Default: test all 8-bit sequences (256 streams × 8 steps = 2048 cells)
        bit_streams = [
            [(n >> i) & 1 for i in range(8)] for n in range(256)
        ]

    # Structural kinematic identities
    structural_pass = (
        verify_four_period_returns_to_origin()
        and verify_two_period_is_pi_phase_advance()
        and verify_bit_complement_inverts_rotation()
        and verify_alternating_bits_zero_net()
    )

    # Correspondence sweep
    total_steps = 0
    total_joint_match = 0
    total_sheet_match = 0
    total_phase_match = 0
    divergence_steps: list[int] = []

    for stream in bit_streams:
        r = correspondence_test(stream)
        total_steps += r["total_steps"]
        total_joint_match += r["joint_match_count"]
        total_sheet_match += r["sheet_match_count"]
        total_phase_match += r["phase_match_count"]
        if r["first_divergence_step"] is not None:
            divergence_steps.append(r["first_divergence_step"])

    joint_rate = total_joint_match / total_steps if total_steps else 0.0
    sheet_rate = total_sheet_match / total_steps if total_steps else 0.0
    phase_rate = total_phase_match / total_steps if total_steps else 0.0

    # Honesty determination based on joint rate
    if joint_rate > 0.99:
        honesty = "PROVEN_AT_TESTED_DEPTH"
    elif joint_rate > 0.7:
        honesty = "BOUNDED_EXEC_STRONG"
    elif joint_rate > 0.55:
        honesty = "BOUNDED_EXEC_WEAK"
    else:
        honesty = "BOUNDED_EXEC_PARTIAL"

    return {
        "status": "pass" if structural_pass else "fail",
        "honesty": honesty,
        "structural_identities_pass": structural_pass,
        "kinematic_checks": {
            "four_period_returns_to_origin": verify_four_period_returns_to_origin(),
            "two_period_is_pi_phase_advance": verify_two_period_is_pi_phase_advance(),
            "bit_complement_inverts_rotation": verify_bit_complement_inverts_rotation(),
            "alternating_bits_zero_net": verify_alternating_bits_zero_net(),
        },
        "correspondence_total_steps": total_steps,
        "joint_match_rate": joint_rate,
        "sheet_match_rate": sheet_rate,
        "phase_match_rate": phase_rate,
        "streams_with_divergence": len(divergence_steps),
        "mean_divergence_step": (
            sum(divergence_steps) / len(divergence_steps) if divergence_steps else None
        ),
        "trigger_status": (
            "WP-OLOID-01-PROMOTABLE"
            if honesty == "PROVEN_AT_TESTED_DEPTH"
            else "WP-OLOID-01-DEFERRED"
        ),
        "notes": (
            "The kinematic model implements rolling by quarter-period steps "
            "(θ += ±π/2 per bit). Phase match rate measures how often the "
            "algebraic 'step mod 4' agrees with the kinematic quarter-index. "
            "Sheet match rate measures how often the algebraic "
            "extension-hemisphere parity agrees with the kinematic "
            "contact-circle index. Joint rate is the conjunction."
        ),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify_oloid_kinematic(), indent=2, default=str))
