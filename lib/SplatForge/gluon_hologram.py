"""
SplatForge.gluon_hologram — "replace bit with color-locked gluon, apply
that as 3 LCR windows, one for each diagonal position on the Jordan
chart" (the operator's direct instruction), composing three already-proven
corpus pieces, none of them modified:

  CQE-PAPER-010's T3 isomorphism: a chart state's 3 bits (L,C,R) ARE the
  3 diagonal entries of its J3(O) trace class — "diagonal position" means
  literally one of these 3 slots, not a new structure.
  MorphForge.ribbon / round_trip (Paper 21, "applied lossless ribbon
  reader"): a generic, type-agnostic, proven-lossless sliding-window
  encoder. Fed the cyclically-extended 5-element sequence (R,L,C,R,L), it
  returns exactly 3 overlapping length-3 windows — one centered at each of
  L, C, and R's original positions — and round_trip() proves the original
  sequence is always exactly recoverable from them. MorphForge.ribbon is
  generic over symbol type already; this module checks (not assumes) that
  it works unmodified when fed GluonBit objects instead of raw ints.
  PixelForge.rgb.pixel_gluon (the gluon invariant = the G channel).

GluonBit IS the literal "bit replaced by a color-locked gluon": it carries
the logical bit and a deterministically-derived color such that
`pixel_gluon(*color) & 1 == bit` exactly — the bit is recoverable from the
color alone, with no side-channel. Everything outside that one locked bit
(7 bits of G, all of R and B) is decorative, derived from a hash of the
caller's key — real, deterministic, but explicitly not claimed to carry
information beyond making each position's gluon visually distinct.
"""
from __future__ import annotations

import dataclasses
import hashlib
from typing import List, Tuple

from MorphForge import ribbon as morph_ribbon, round_trip as morph_round_trip
from PixelForge.rgb import pixel_gluon

LCRState = Tuple[int, int, int]


@dataclasses.dataclass(frozen=True)
class GluonBit:
    """A bit, color-locked. `bit` is the logical value; `color` is an RGB
    triple whose G channel's low bit IS `bit` exactly (locked_bit
    property) — the substitution target for "bit" everywhere in this
    module."""

    bit: int
    color: Tuple[int, int, int]

    def __post_init__(self) -> None:
        if self.bit not in (0, 1):
            raise ValueError("GluonBit.bit must be 0 or 1")

    @property
    def locked_bit(self) -> int:
        """Recover the bit from the color alone — the point of "locked"."""
        return pixel_gluon(*self.color) & 1


def lock_gluon(bit: int, key: str) -> GluonBit:
    """bit -> color-locked gluon. The G channel's low bit is forced to
    `bit` exactly; every other bit of R/G/B is filled deterministically
    from a hash of `key`, so each position gets a visually distinct color
    while the logical bit stays exactly recoverable."""
    if bit not in (0, 1):
        raise ValueError("lock_gluon requires bit in (0, 1)")
    digest = hashlib.sha256(f"{key}:{bit}".encode("utf-8")).digest()
    r = digest[0]
    g = (digest[1] & 0b11111110) | bit
    b = digest[2]
    return GluonBit(bit=bit, color=(r, g, b))


def jordan_diagonal_windows(state: LCRState, key: str) -> List[Tuple[GluonBit, GluonBit, GluonBit]]:
    """3 LCR windows, one centered at each J3(O) diagonal position (L, C,
    R) of `state`, every element a color-locked gluon. Built via
    MorphForge.ribbon on the cyclically-extended sequence (R,L,C,R,L) —
    MorphForge's own windowing, unmodified, applied to gluon-typed symbols
    instead of the raw ints it was demonstrated with."""
    left, center, right = state
    extended_bits = [right, left, center, right, left]
    gluons = [lock_gluon(b, key=f"{key}:{i}") for i, b in enumerate(extended_bits)]
    windows = morph_ribbon(gluons)
    if len(windows) != 3:
        raise RuntimeError(f"expected 3 windows from a 5-element ribbon, got {len(windows)}")
    return windows


def decode_jordan_diagonal_windows(windows: List[Tuple[GluonBit, GluonBit, GluonBit]]) -> LCRState:
    """Recover the original (L,C,R) exactly from the 3 windows, using
    MorphForge's own round-trip reconstruction (window[0] plus the last
    element of every subsequent window) — reading each gluon's
    `locked_bit` (from its color), not its stored `.bit` field, so the
    claim being tested is genuinely about the color, not a hidden
    side-channel."""
    rebuilt = [g.locked_bit for g in windows[0]] + [w[-1].locked_bit for w in windows[1:]]
    right, left, center = rebuilt[0], rebuilt[1], rebuilt[2]
    return (left, center, right)


def verify_lossless_round_trip(key: str = "verify") -> dict:
    """Exercise jordan_diagonal_windows/decode for all 8 possible (L,C,R)
    states and confirm exact recovery — the literal "perfect lossless
    transition" claim, checked, not asserted."""
    mismatches = []
    for left in (0, 1):
        for center in (0, 1):
            for right in (0, 1):
                state = (left, center, right)
                windows = jordan_diagonal_windows(state, key=key)
                decoded = decode_jordan_diagonal_windows(windows)
                if decoded != state:
                    mismatches.append({"state": state, "decoded": decoded})
    return {
        "states_checked": 8,
        "mismatches": mismatches,
        "status": "pass" if not mismatches else "fail",
        "morphforge_round_trip_on_gluonbits": morph_round_trip(
            [lock_gluon(b, key=f"{key}:rt:{i}") for i, b in enumerate([1, 0, 1, 1, 0])]
        ),
    }
