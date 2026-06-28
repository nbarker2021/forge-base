"""
PixelForge RGB — RGB pixel ordering IS the LCR chart.

The identification (no new mathematics — the substrate applied):

    (R, G, B)  =  (L, C, R)
    R = L = fermionic read wire
    G = C = THE GLUON — the center channel, invariant under R<->B swap
            (exactly as C is invariant under the LR-podal reversal)
    B = R = bosonic write wire

An 8-bit pixel decomposes into 8 BIT-PLANES, each plane one chart state:
plane i of pixel (r, g, b) is ((r>>i)&1, (g>>i)&1, (b>>i)&1). Eight planes =
the 8-slot ribbon: A PIXEL IS A RIBBON. T_EMISSION read across the planes
yields the pixel's emission byte (its shadow); the correction-firing count
across planes is its carry density. Color blending is chart-state mixing —
the gluon channel blends independently of the L/R swap class.

Stdlib only. All per-state work is table lookup.
"""
from typing import Dict, List, Tuple

BITS = 8

# T_EMISSION lookup over the 8 chart states: bit = NOT(L) if C else L^R
_EMIT: Dict[Tuple[int, int, int], int] = {
    (L, C, R): (1 - L) if C else (L ^ R)
    for L in (0, 1) for C in (0, 1) for R in (0, 1)
}
# correction firing (the frustrated bond): C=1 and R=0
_CARRY: Dict[Tuple[int, int, int], int] = {
    (L, C, R): 1 if (C == 1 and R == 0) else 0
    for L in (0, 1) for C in (0, 1) for R in (0, 1)
}


def pixel_planes(r: int, g: int, b: int) -> List[Tuple[int, int, int]]:
    """Decompose one RGB pixel into its 8 chart states (MSB first).
    plane[i] = (L, C, R) at bit 7-i. A pixel IS a ribbon of 8 windows."""
    return [((r >> i) & 1, (g >> i) & 1, (b >> i) & 1)
            for i in range(BITS - 1, -1, -1)]


def planes_pixel(planes: List[Tuple[int, int, int]]) -> Tuple[int, int, int]:
    """Inverse: 8 chart states (MSB first) -> the RGB pixel. Lossless."""
    r = g = b = 0
    for L, C, R in planes:
        r = (r << 1) | (L & 1)
        g = (g << 1) | (C & 1)
        b = (b << 1) | (R & 1)
    return (r, g, b)


def pixel_gluon(r: int, g: int, b: int) -> int:
    """The pixel's gluon byte = the G channel. Invariant under R<->B swap,
    exactly as Gamma(s) = C is invariant under the LR-podal reversal."""
    return g


def pixel_emission(r: int, g: int, b: int) -> int:
    """T_EMISSION read across the 8 planes -> the pixel's shadow byte."""
    out = 0
    for s in pixel_planes(r, g, b):
        out = (out << 1) | _EMIT[s]
    return out


def pixel_carry(r: int, g: int, b: int) -> int:
    """Correction-firing count across planes (0..8): the pixel's carry density.
    High carry = deep in an active rollout; low = near equilibrium color."""
    return sum(_CARRY[s] for s in pixel_planes(r, g, b))


def blend_rgb(a: Tuple[int, int, int], b: Tuple[int, int, int],
              t: float) -> Tuple[int, int, int]:
    """Color blending — the picture-making primitive. Linear in each wire;
    the gluon channel blends independently of the L/R pair."""
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return (int(round(a[0] + (b[0] - a[0]) * t)),
            int(round(a[1] + (b[1] - a[1]) * t)),
            int(round(a[2] + (b[2] - a[2]) * t)))
