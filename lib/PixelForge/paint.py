"""
PixelForge Paint — color is the tools applied as a paint-by-numbers machine.

The machine has exactly two parts:

  NUMBERING  any system tool that assigns each cell a small integer.
             The substrate already numbers everything: chart-state index
             (0-7), carry count (0-8), anneal steps (0-3), VOA weight
             (0/5), digital root (0-9), emission bits... Tools number;
             they never color.

  PALETTE    a lookup table number -> paint. That is ALL color is.

paint(w, h, numbering, palette) -> Picture. Every existing constructor is
a special case of this machine; every future metric is a new numbering for
free. Stdlib only, lookup only.
"""
from __future__ import annotations

from typing import Callable, Dict, Sequence, Tuple

from PixelForge.picture import Picture
from PixelForge.rgb import _CARRY, _EMIT

Color = Tuple[int, int, int]
Numbering = Callable[[int, int], int]          # (x, y) -> small int


# ─── Palettes (paint pots — pure lookup) ──────────────────────────────────────

# The 8 chart states, each wire lighting its channel: the canonical pot.
CHART_PALETTE: Tuple[Color, ...] = tuple(
    (220 if L else 25, 220 if C else 25, 220 if R else 25)
    for L in (0, 1) for C in (0, 1) for R in (0, 1)
)

# Carry density 0..8: equilibrium blues -> active-rollout fire.
CARRY_PALETTE: Tuple[Color, ...] = tuple(
    (int(20 + 235 * k / 8), int(30 + 90 * k / 8), int(120 - 110 * k / 8))
    for k in range(9)
)

# Anneal steps 0..3: how far from rest (Lie conjugate) the cell sits.
ANNEAL_PALETTE: Tuple[Color, ...] = (
    (16, 24, 48), (60, 120, 180), (240, 200, 80), (250, 90, 60),
)

# VOA sector: vacuum (weight 0) vs excited (weight 5).
VOA_PALETTE: Dict[int, Color] = {0: (12, 12, 28), 5: (255, 180, 40)}

# Digital roots 1..9 (0 = void): nine pots around the wheel.
DR_PALETTE: Tuple[Color, ...] = tuple(
    (int(127 + 127 * __import__("math").cos(k * 0.698)),
     int(127 + 127 * __import__("math").cos(k * 0.698 + 2.09)),
     int(127 + 127 * __import__("math").cos(k * 0.698 + 4.19)))
    for k in range(10)
)


# ─── The machine ──────────────────────────────────────────────────────────────

def paint(width: int, height: int, numbering: Numbering,
          palette: "Sequence[Color] | Dict[int, Color]",
          default: Color = (0, 0, 0)) -> Picture:
    """The whole machine: tools number the sheet, the palette paints it."""
    pic = Picture(width, height)
    is_map = isinstance(palette, dict)
    n = None if is_map else len(palette)
    for y in range(height):
        for x in range(width):
            k = numbering(x, y)
            if is_map:
                pic.set(x, y, palette.get(k, default))
            else:
                pic.set(x, y, palette[k % n])
    return pic


# ─── Numberings from the substrate (tools, not colors) ───────────────────────

def chart_numbering(seed: int = 1, width: int = 0) -> Numbering:
    """Each row emitted from the last by T_EMISSION; the number at (x, y)
    is the local chart state index (0-7). The emission law numbers the sheet."""
    rows: list = []

    def ensure(y: int, w: int):
        if not rows:
            rows.append([(seed >> (x % 31)) & 1 if x != w // 2 else 1
                         for x in range(w)])
        while len(rows) <= y:
            r = rows[-1]
            rows.append([_EMIT[(r[(x - 1) % w], r[x], r[(x + 1) % w])]
                         for x in range(w)])

    def number(x: int, y: int) -> int:
        w = width or (x + 1)
        ensure(y, w)
        r = rows[y]
        return (r[(x - 1) % len(r)] << 2) | (r[x % len(r)] << 1) | r[(x + 1) % len(r)]

    return number


def carry_numbering(base: Picture) -> Numbering:
    """Number an existing picture by per-pixel carry density (0-8)."""
    from PixelForge.rgb import pixel_carry
    return lambda x, y: pixel_carry(*base.get(x, y))


def state_of(x: int, y: int, rowfn) -> Tuple[int, int, int]:
    r = rowfn(y)
    w = len(r)
    return (r[(x - 1) % w], r[x % w], r[(x + 1) % w])


def anneal_numbering(seed: int = 1, width: int = 0) -> Numbering:
    """Number each cell by S3 anneal steps to its Lie conjugate (0-3) —
    distance from rest, straight from the wrap theorem."""
    chart = chart_numbering(seed, width)
    _LIE = {0b000, 0b010, 0b101, 0b111}
    _SWAPS = ((2, 1, 0), (1, 0, 2), (0, 2, 1))   # T_LR, T_LC, T_CR on bit triples

    def steps(k: int) -> int:
        bits = [(k >> 2) & 1, (k >> 1) & 1, k & 1]
        cur = tuple(bits)
        for i, sw in enumerate(_SWAPS):
            ki = (cur[0] << 2) | (cur[1] << 1) | cur[2]
            if ki in _LIE:
                return i
            cur = (cur[sw[0]], cur[sw[1]], cur[sw[2]])
        return 3

    return lambda x, y: steps(chart(x, y))
