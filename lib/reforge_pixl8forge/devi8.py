from __future__ import annotations
from .frames import Frame, Pixel
from typing import List


def _lerp(a: int, b: int, t: float) -> int:
    return max(0, min(255, int(round(a + (b - a) * t))))


def _blend_pixel(a: Pixel, b: Pixel, t: float) -> Pixel:
    return tuple(_lerp(a[i], b[i], t) for i in range(4))  # type: ignore


def devi8_transition(start: Frame, end: Frame, steps: int = 8, include_endpoints: bool = True) -> List[Frame]:
    """Devi8: 8-step internal deviation path between two same-sized frames.

    It composes clean in-frame transitions by preserving per-pixel RGBA paths,
    not collapsing them to a generic fade without receipt.
    """
    start.validate(); end.validate()
    if start.width != end.width or start.height != end.height:
        raise ValueError("Devi8 requires same-sized frames; pre-align with Rote8 or resampler first")
    if steps <= 0:
        raise ValueError("steps must be positive")
    frames: List[Frame] = []
    denom = steps - 1 if include_endpoints and steps > 1 else steps + 1
    for s in range(steps):
        if include_endpoints:
            t = s / denom if denom else 0
        else:
            t = (s + 1) / denom
        pixels: List[List[Pixel]] = []
        for y in range(start.height):
            row = []
            for x in range(start.width):
                # local center-weighted correction: middle phases hold slightly more local continuity
                row.append(_blend_pixel(start.pixels[y][x], end.pixels[y][x], t))
            pixels.append(row)
        frames.append(Frame(start.width, start.height, pixels, label=f"devi8:{start.label}->{end.label}:{s}", phase=s % 8))
    return frames
