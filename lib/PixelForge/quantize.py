"""
PixelForge Quantize — float RGBA -> uint8 Picture conversion with the
rounding residual retained rather than discarded.

This module's design was redirected mid-build by a measurement, which is
recorded here rather than smoothed over.

The original idea (suggested as a fix for this exact float32->uint8 step):
reuse the D4 root system (CQECMPLX-Formal-Suite/lib/src/lattice_forge/
block_d4.py d4_roots(): the 24 roots of D4, every (+/-1,+/-1,0,0)
permutation in R^4) to round each RGBA 4-vector onto the nearest point of
the D4 checkerboard lattice {x in Z^4 : sum(x) even}, on the textbook claim
that D4 is a better 4D vector quantizer than rounding each channel
independently.

quantize_d4() below implements that lattice-snap exactly. Measuring it
(20000 random RGBA samples) against plain per-channel rounding showed D4
snapping is WORSE: MSE ~0.43 vs ~0.33 for plain rounding. The textbook
"D4 beats Z^4" result holds at equal *point density* (equal bit-rate); D4
at unit spacing is the index-2 sum-even sublattice of Z^4, i.e. literally
half the points of Z^4 at that spacing, so snapping to it without also
exploiting the freed parity bit downstream (entropy-coding it, which this
renderer does not do) just throws away precision. quantize_d4() is kept,
correctly labeled, for whoever does add that downstream coding; it is not
used by the default path.

What IS used by default, and is genuinely correct, is the other half of
the original suggestion: ConvergeForge.d4_atlas's proven CQE-paper-19
result ("observation = D4 face selection": the atlas's center view is
selected as the observed face; the other 7 views are retained as
obligations, not discarded — the selection is lossless because nothing is
thrown away). Applied here: plain per-channel rounding is the *selected*
uint8 value; what rounding discarded is *retained* as a residual obligation
the caller folds into its frame receipt — the same "failures are data"
Event-Law pattern PixelForge.frame.FrameStream already uses for
parity/entropy violations. This does not make float32->uint8 conversion
lossless (it inherently is not); it makes the loss accounted for instead
of silent.
"""
from __future__ import annotations

from typing import Dict, Sequence, Tuple


def quantize_scalar_pixel(rgba_0_1: Sequence[float]) -> Tuple[Tuple[int, int, int], Tuple[float, float, float, float]]:
    """Float RGBA in 0..1 -> (clamped uint8 RGB, per-channel rounding
    residual in 0..255 units). The default conversion: plain independent
    rounding (the precision-correct choice, see module docstring), with the
    residual returned instead of discarded — fold it into a ResidualLedger."""
    scaled = [max(0.0, min(1.0, v)) * 255.0 for v in rgba_0_1]
    rounded = [round(v) for v in scaled]
    residual = tuple(round(v - r, 6) for v, r in zip(scaled, rounded))
    r, g, b = (max(0, min(255, v)) for v in rounded[:3])
    return (r, g, b), residual  # type: ignore[return-value]


def quantize_d4(values: Sequence[float]) -> Tuple[Tuple[int, int, int, int], Tuple[float, float, float, float]]:
    """Round one 4-vector onto the nearest point of the D4 checkerboard
    lattice {x in Z^4 : sum(x) even}. NOT used by quantize_scalar_pixel /
    the default render path — see module docstring: at unit spacing this
    has *higher* mean-squared error than independent rounding, because D4
    is a sparser sublattice of Z^4. Kept for a future caller that entropy-
    codes the freed parity bit, where the lattice's real advantage lives."""
    if len(values) != 4:
        raise ValueError("quantize_d4 operates on 4-vectors (RGBA)")
    rounded = [round(v) for v in values]
    errors = [v - r for v, r in zip(values, rounded)]
    if sum(rounded) % 2 != 0:
        worst = max(range(4), key=lambda i: abs(errors[i]))
        rounded[worst] += 1 if errors[worst] > 0 else -1
        errors[worst] = values[worst] - rounded[worst]
    return tuple(rounded), tuple(round(e, 6) for e in errors)  # type: ignore[return-value]


class ResidualLedger:
    """Accumulates quantization residuals across a frame instead of
    discarding them per-pixel — the bounded, frame-level form of
    CQE-paper-19's 'retain the unselected as an obligation' policy (a
    per-pixel ledger would be exact but unbounded; this keeps the same
    honesty at a frame-level grain: nothing is silently thrown away, the
    accounting is just summarized)."""

    def __init__(self, method: str = "scalar_round") -> None:
        self.method = method
        self._count = 0
        self._sum_abs = 0.0
        self._sum_sq = 0.0
        self._max_abs = 0.0

    def add(self, residual: Sequence[float]) -> None:
        for e in residual:
            ae = abs(e)
            self._sum_abs += ae
            self._sum_sq += e * e
            self._max_abs = max(self._max_abs, ae)
            self._count += 1

    def stats(self) -> Dict[str, float]:
        if self._count == 0:
            return {"method": self.method, "samples": 0, "mean_abs": 0.0,
                    "rms": 0.0, "max_abs": 0.0}
        return {
            "method": self.method,
            "samples": self._count,
            "mean_abs": round(self._sum_abs / self._count, 6),
            "rms": round((self._sum_sq / self._count) ** 0.5, 6),
            "max_abs": round(self._max_abs, 6),
        }
