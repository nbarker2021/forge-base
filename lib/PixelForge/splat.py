"""
PixelForge Splat — Gaussian/ellipse footprint rasterization onto a Picture.

KRR-GS-003 (point/ellipse/tile-bin rasterizer with a deterministic frame
receipt) composes existing PixelForge primitives rather than inventing a
parallel renderer:

  PixelForge.projection.to_screen   3D point -> logical [0,1]^2 screen + depth.
                                     Written for points already through
                                     project() (E8->3D); reused here directly
                                     on splat-space mean_position, since
                                     to_screen's actual contract is "any 3D
                                     point" — a new call pattern on an
                                     existing function, not a new function.
  PixelForge.rgb.blend_rgb          the alpha-compositing arithmetic, reused
                                     per-pixel weighted by the Gaussian
                                     falloff instead of a uniform layer alpha.
  PixelForge.picture.Picture        the output RGB24 canvas, unchanged.

Genuinely new ground in this module (did not exist anywhere in this corpus
before): the elliptical/Gaussian screen-space footprint itself (world scale
-> screen radius -> falloff weight) and the screen-space tile-bin partition.
CPU-reference splats are isotropic (orientation quaternion is always identity
per ecology/schemas/gaussian_splat_instance.schema.json) so the footprint
drawn here is circular; a non-identity orientation would need true elliptical
(covariance-matrix) footprints — not implemented, open ground, not silently
approximated as something it isn't.

"Tile bins" here are screen-space pixel-block rasterization bins (the
standard tile-based splat rasterization technique) — a different sense of
"tile" from SplatForge's lattice TileInstance, sharing the word because both
are this corpus's own GBS vocabulary. Binning bounds each splat's work to its
own footprint instead of the whole canvas, and is the exact seam a GPU
backend mirrors: one compute workgroup per bin (see splat_vulkan.py).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from PixelForge.picture import Picture
from PixelForge.projection import to_screen
from PixelForge.rgb import blend_rgb

TILE_SIZE = 16          # screen-space rasterization bin, pixels per side
FALLOFF_SIGMA_CUTOFF = 3.0   # truncate the Gaussian footprint past this many sigma
MIN_WEIGHT = 1.0 / 1024.0    # below this, a splat's contribution is dropped


@dataclass(frozen=True)
class ScreenSplat:
    """One splat already projected to screen space — the backend-agnostic
    record both the CPU rasterizer and any GPU backend consume, so both
    start from an identical input and their pixel outputs are directly
    comparable (the workplan's 'GPU output is compared, not assumed
    authoritative')."""
    cx: float                    # screen-space center x, pixels
    cy: float                    # screen-space center y, pixels
    depth: float                 # camera-space depth (z); smaller = farther
    radius_px: float             # isotropic 1-sigma screen-space radius, pixels
    color: Tuple[int, int, int]  # 0..255 RGB
    opacity: float                # 0..1


def project_splats(splats: Sequence[Dict], width: int, height: int,
                    scale: float = 0.25, depth_cam: float = 5.0) -> List[ScreenSplat]:
    """GaussianSplatInstance dicts (or .to_dict() equivalents) -> ScreenSplat[].
    mean_position is splat tile-space, not an E8 state — to_screen accepts
    any 3D point, so no project() / E8 step is needed first."""
    out: List[ScreenSplat] = []
    for s in splats:
        x, y, z = s["mean_position"]
        lx, ly, depth = to_screen((x, y, z), scale=scale, depth_cam=depth_cam)
        w = depth_cam / max(0.1, depth_cam - z)
        sx, sy, sz = s["covariance_or_scale"]
        radius_world = (sx + sy + sz) / 3.0
        radius_px = radius_world * scale * w * max(width, height)
        r, g, b = s["appearance_coefficients"]
        color = (int(round(max(0.0, min(1.0, r)) * 255)),
                 int(round(max(0.0, min(1.0, g)) * 255)),
                 int(round(max(0.0, min(1.0, b)) * 255)))
        out.append(ScreenSplat(cx=lx * width, cy=ly * height, depth=depth,
                                radius_px=max(0.5, radius_px),
                                color=color, opacity=float(s["opacity"])))
    return out


def bin_splats(splats: Sequence[ScreenSplat], width: int, height: int,
                tile_size: int = TILE_SIZE) -> Dict[Tuple[int, int], List[int]]:
    """Screen-space tile bins: (tx, ty) -> indices of every splat whose
    truncated footprint overlaps that bin. Mirrors the GPU backend's
    one-workgroup-per-tile dispatch grid."""
    bins: Dict[Tuple[int, int], List[int]] = {}
    tiles_x = max(1, (width + tile_size - 1) // tile_size)
    tiles_y = max(1, (height + tile_size - 1) // tile_size)
    for i, sp in enumerate(splats):
        reach = sp.radius_px * FALLOFF_SIGMA_CUTOFF
        x0 = max(0, int((sp.cx - reach) // tile_size))
        x1 = min(tiles_x - 1, int((sp.cx + reach) // tile_size))
        y0 = max(0, int((sp.cy - reach) // tile_size))
        y1 = min(tiles_y - 1, int((sp.cy + reach) // tile_size))
        if x1 < 0 or y1 < 0 or x0 >= tiles_x or y0 >= tiles_y:
            continue
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                bins.setdefault((tx, ty), []).append(i)
    return bins


# Correction operator C AND NOT R, fires at the chiral doublet
# {(0,1,0),(1,1,0)} -- the proven (L,C,R) chart mechanism shared by
# rule90_linearization.py's Rule_30 = Rule_90 (+) correction identity and
# CQE-paper-093/094 (Spectre Theorems S-1/S-2: Spectre tile = this
# correction's geometric realization, 7-fold substitution closing exactly
# at depth 3). Applied here to a domain neither paper covers: screen-space
# tile-bin OCCUPANCY rather than a CA cell or a pixel bitplane. This is not
# a claim that tile occupancy literally evolves under Rule 30 -- it reuses
# the proven 3-bit classification as a structural diagnostic of where a
# splat cluster's boundary sits along each tile row (L,C,R = previous,
# this, next tile occupied), exactly the corpus's own "boundary collision /
# deterministic repair" vocabulary, read for what it actually proves
# (chiral-doublet classification) rather than the still-open literal
# geometry claim (verify_spectre_geometry.py remains "Partial" even at
# this paper's "Affirmative" status -- the chart-level mechanism is
# proven, the real monotile vertex correspondence is not, and this
# function only uses the former).
_CHIRAL_DOUBLET = frozenset({(0, 1, 0), (1, 1, 0)})
_VACUA = frozenset({(0, 0, 0), (1, 1, 1)})


def classify_tile_lcr(bins: Dict[Tuple[int, int], List[int]],
                       tiles_x: int, tiles_y: int) -> Dict:
    """Classify every screen-space tile row position by the (L,C,R)
    horizontal-occupancy state and the proven correction = C AND NOT R.
    chiral_doublet tiles are exactly the right edge of each run of
    occupied tile bins along a row -- the rendered frame's actual
    "boundary collision" sites in this tile layout."""
    def occ(tx: int, ty: int) -> int:
        return 1 if (0 <= tx < tiles_x and bins.get((tx, ty))) else 0

    counts = {"vacuum": 0, "chiral_doublet": 0, "other": 0}
    firing_tiles: List[Tuple[int, int]] = []
    tile_states: Dict[Tuple[int, int], str] = {}
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            state = (occ(tx - 1, ty), occ(tx, ty), occ(tx + 1, ty))
            if state in _VACUA:
                label = "vacuum"
            elif state in _CHIRAL_DOUBLET:
                label = "chiral_doublet"
                firing_tiles.append((tx, ty))
            else:
                label = "other"
            counts[label] += 1
            tile_states[(tx, ty)] = label
    total = max(1, tiles_x * tiles_y)
    return {
        "tile_chart_counts": counts,
        "correction_firing_tile_count": len(firing_tiles),
        "correction_firing_fraction": round(len(firing_tiles) / total, 4),
        "tile_states": tile_states,
    }


def rasterize_splats(splats: Sequence[Dict], width: int, height: int,
                      background: Tuple[int, int, int] = (0, 0, 0),
                      scale: float = 0.25, depth_cam: float = 5.0,
                      tile_size: int = TILE_SIZE) -> Tuple[Picture, Dict]:
    """CPU reference rasterizer: GaussianSplatInstance dicts -> Picture.
    Per tile bin, splats draw farthest-first (back-to-front) so nearer
    splats correctly composite on top; the falloff weight reuses
    PixelForge.rgb.blend_rgb for the actual color mix.

    Returns (picture, stats); stats carries the bin layout so a GPU
    backend's dispatch grid can be checked against this CPU pass tile-for-tile."""
    screen = project_splats(splats, width, height, scale=scale, depth_cam=depth_cam)
    bins = bin_splats(screen, width, height, tile_size=tile_size)
    tiles_x = max(1, (width + tile_size - 1) // tile_size)
    tiles_y = max(1, (height + tile_size - 1) // tile_size)
    pic = Picture.solid(width, height, background)

    for (tx, ty), indices in bins.items():
        order = sorted(indices, key=lambda i: screen[i].depth)  # farthest (smaller z) first
        x0, y0 = tx * tile_size, ty * tile_size
        x1, y1 = min(width, x0 + tile_size), min(height, y0 + tile_size)
        for i in order:
            sp = screen[i]
            reach = sp.radius_px * FALLOFF_SIGMA_CUTOFF
            r2 = sp.radius_px * sp.radius_px
            px0 = max(x0, int(sp.cx - reach)); px1 = min(x1, int(sp.cx + reach) + 1)
            py0 = max(y0, int(sp.cy - reach)); py1 = min(y1, int(sp.cy + reach) + 1)
            for py in range(py0, py1):
                for px in range(px0, px1):
                    dx, dy = px + 0.5 - sp.cx, py + 0.5 - sp.cy
                    d2 = dx * dx + dy * dy
                    if d2 > r2 * FALLOFF_SIGMA_CUTOFF * FALLOFF_SIGMA_CUTOFF:
                        continue
                    weight = sp.opacity * math.exp(-0.5 * d2 / max(1e-6, r2))
                    if weight <= MIN_WEIGHT:
                        continue
                    existing = pic.get(px, py)
                    pic.set(px, py, blend_rgb(existing, sp.color, weight))

    stats = {
        "splat_count": len(splats),
        "width": width, "height": height,
        "tile_size": tile_size,
        "tile_count": len(bins),
        "max_splats_per_tile": max((len(v) for v in bins.values()), default=0),
        **classify_tile_lcr(bins, tiles_x, tiles_y),
    }
    return pic, stats
