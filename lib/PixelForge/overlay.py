"""
PixelForge Overlay — KRR-GS-006: chart overlay and provenance inspection
(the overlay half; SplatForge.provenance_panel is the receipt-inspection
half).

Pure visualization: a translucent per-tile color wash over a copy of an
already-rendered Picture, using PixelForge.splat.classify_tile_lcr's
existing per-tile (L,C,R) classification (no new math) and
PixelForge.rgb.blend_rgb (the existing alpha-compositing primitive
rasterize_splats already uses) for the actual color mix. Never mutates the
source Picture — always returns a new one, consistent with this build's
"renderer visualizes, never mutates" discipline (GS-04's docstring).
"""
from __future__ import annotations

from typing import Dict, Tuple

from PixelForge.picture import Picture
from PixelForge.rgb import blend_rgb

# vacuum: empty tile or fully-interior occupied tile -> green wash
# chiral_doublet: a correction-firing boundary tile -> amber wash
# other: a mixed/asymmetric boundary tile -> gray wash
_WASH_COLOR: Dict[str, Tuple[int, int, int]] = {
    "vacuum": (40, 200, 90),
    "chiral_doublet": (230, 160, 30),
    "other": (140, 140, 150),
}
DEFAULT_WASH_ALPHA = 0.35


def draw_tile_chart_overlay(picture: Picture, tile_states: Dict[Tuple[int, int], str],
                             tile_size: int, alpha: float = DEFAULT_WASH_ALPHA) -> Picture:
    """A copy of `picture` with each screen-space tile washed by its
    classify_tile_lcr label color, at `alpha` opacity. `tile_states` is
    classify_tile_lcr(...)["tile_states"] — this function does no
    classification itself, only visualization."""
    out = picture.copy()
    for (tx, ty), label in tile_states.items():
        color = _WASH_COLOR.get(label, _WASH_COLOR["other"])
        x0, y0 = tx * tile_size, ty * tile_size
        x1, y1 = min(picture.width, x0 + tile_size), min(picture.height, y0 + tile_size)
        if x0 >= picture.width or y0 >= picture.height:
            continue
        for y in range(y0, y1):
            for x in range(x0, x1):
                out.set(x, y, blend_rgb(out.get(x, y), color, alpha))
    return out
