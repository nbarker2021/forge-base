"""
SplatForge.multi_perspective — render the same compiled Crystal Zoo lattice
differently depending on a chosen viewing direction, with no training and
no ML: a tile's boundary-state classification is parameterized over which
spatial axis is "left/right" (3 discrete perspectives instead of one
hardcoded axis), each axis's appearance is looked up via the already-built
per-state tables, and a queried view direction blends across the 3 axes
via the existing generic PixelForge.rgb.blend_rgb primitive.

Checked directly before building this, not assumed:
  GaussianSplatInstance.observer_window_id (compiler.py)   already a real,
                                              schema-first-class field —
                                              always the single constant
                                              "observer.default" until this
                                              module, never genuinely
                                              varied. The slot for "which
                                              viewpoint this splat's
                                              appearance was computed for"
                                              already existed, unused.
  gluon_blob.lattice_neighbor_state          only ever checks the x-axis
                                              (left=occ(ix-1), right=
                                              occ(ix+1), center hardcoded
                                              to 1) -- never modified here,
                                              this module's
                                              boundary_state_along_axis is
                                              a new, parameterized sibling
                                              that reduces to the exact
                                              same logic at axis=0.
  state_recipe_table.lookup                  the already-built O(1)
                                              per-state table; its
                                              base_hue field IS
                                              weyl_address.full_spectrum_color
                                              -- reused directly, no new
                                              color algebra.
  fracture_cascade.repaired_state            the verified DAG (state ->
                                              its one canonical repair
                                              target, 4 sinks/Lie
                                              conjugates, zero cycles) --
                                              carried alongside each
                                              per-axis entry as real,
                                              inspectable metadata.
  PixelForge.rgb.blend_rgb                   the existing generic pairwise
                                              linear color blend (the same
                                              primitive the rasterizer's
                                              own alpha compositing uses).

What's new in this module: boundary_state_along_axis's axis parameter
itself, blend_view_direction_color's specific blend formula (composing 3
colors via blend_rgb in axis order, weighted by an L1-normalized view
direction), and triangulated_radii's per-axis shape formula -- new
composition, not claimed proven elsewhere.

Genuine triangulation, closing a scope limit from this module's earlier
slices (confirmed directly, not assumed: boundary_state_along_axis /
chart_state_to_d4 / correction / lucas_bit are all total functions across
every Crystal Zoo family, multiple extents, and all 3 axes -- there is
never a tile this fails for): triangulated_radii derives each of the 3
output radii from its OWN axis's (L,C,R) window instead of all 3
borrowing the single x-axis window gluon_blob.lucas_correction_radii
uses. Shape is intrinsic to the tile (the same regardless of
view_direction, matching how a real Gaussian's covariance doesn't change
with viewing angle); only color is view-dependent here.

Remaining named scope limit: the circuit breaker's repair *pairing*
(which boundary pairs actually trip) remains x-axis-only
(crystal_pipeline.py); repaired_state is exposed per axis here purely as
informational metadata, not wired into a y/z-aware breaker.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from lattice_forge.block_d4 import chart_state_to_d4
from lattice_forge.rule90_linearization import correction, lucas_bit

from PixelForge.rgb import blend_rgb

from .compiler import SPLAT_SCALE_FRACTION
from .fracture_cascade import repaired_state
from .gluon_blob import compile_gluon_blobs, intensity_decay_factor
from .provenance_panel import write_provenance_panel
from .raster import render_pass
from .state_recipe_table import lookup as lookup_state_recipe
from .tiling import TileInstance, build_tile_family_asset, generate_tile_instances

RGB = Tuple[int, int, int]
LCRState = Tuple[int, int, int]

_AXIS_NAMES = ("x", "y", "z")


def boundary_state_along_axis(tile: TileInstance, extent: Tuple[int, int, int], axis: int) -> LCRState:
    """gluon_blob.lattice_neighbor_state's exact occupancy-check logic,
    generalized to any of the 3 spatial axes (0=x, 1=y, 2=z) instead of
    hardcoded x. Center stays hardcoded to 1 (the tile itself always
    exists in the compiled lattice) -- the same honest invariant the
    color-ladder slice already documented for the x-only version."""
    if axis not in (0, 1, 2):
        raise ValueError(f"axis must be 0, 1, or 2; got {axis!r}")
    i = tile.cell_index[axis]
    left = 1 if i - 1 >= 0 else 0
    right = 1 if i + 1 < extent[axis] else 0
    return (left, 1, right)


def tile_perspective_recipes(tile: TileInstance, extent: Tuple[int, int, int]) -> Dict[int, Dict[str, Any]]:
    """One entry per spatial axis: the tile's boundary state seen along
    that axis, its base_hue (state_recipe_table's already-built
    full_spectrum_color lookup), and its repaired_state DAG target
    (fracture_cascade) -- no new color or repair algebra, pure reuse."""
    recipes: Dict[int, Dict[str, Any]] = {}
    for axis in (0, 1, 2):
        state = boundary_state_along_axis(tile, extent, axis)
        recipe = lookup_state_recipe(state)
        recipes[axis] = {
            "axis": axis,
            "axis_name": _AXIS_NAMES[axis],
            "state": state,
            "base_hue": recipe["base_hue"],
            "repaired_state": repaired_state(state),
        }
    return recipes


def triangulated_radii(tile: TileInstance, extent: Tuple[int, int, int],
                        base_scale: float) -> Tuple[float, float, float]:
    """The genuine triangulation: each of the 3 output radii is derived
    from its OWN axis's (L,C,R) window (boundary_state_along_axis)
    instead of all 3 borrowing the single x-axis window gluon_blob.
    lucas_correction_radii uses. x, y, and z are each independently
    derivable from their own LCR reading -- checked directly before
    building this, not assumed: boundary_state_along_axis,
    chart_state_to_d4, correction, and lucas_bit are all total functions
    (confirmed across all 9 Crystal Zoo families, 3 different extents,
    and all 3 axes -- there is never a tile this fails for). Same
    multiplier formula gluon_blob.lucas_correction_radii uses (new
    composition, not claimed proven elsewhere), applied per axis to its
    own window instead of one window borrowed by all 3."""
    return triangulated_radii_with_overrides(tile, extent, base_scale, {})


def _radius_for_state(state: LCRState, depth: int, base_scale: float) -> float:
    """The one-axis multiplier formula, extracted so it can be applied to
    an arbitrary state (e.g. a repair target) instead of only a state
    read off the tile itself — the same extract-for-reuse pattern already
    used for gluon_blob.intensity_decay_factor."""
    axis_d4 = chart_state_to_d4(state)[0]
    corr = correction(*state)
    lucas = lucas_bit(depth, axis_d4)
    multiplier = max(0.25, 1.0 + 0.5 * lucas - 0.25 * corr)
    return round(base_scale * multiplier, 6)


def triangulated_radii_with_overrides(tile: TileInstance, extent: Tuple[int, int, int],
                                       base_scale: float,
                                       overrides: Dict[int, LCRState]) -> Tuple[float, float, float]:
    """triangulated_radii, but any axis present in `overrides` uses that
    state instead of the tile's own boundary_state_along_axis reading —
    so a repair that only changed, say, the y-axis state can recompute
    just the y radius from the repaired state, leaving x and z as the
    tile's real, observed shape. Empty overrides reduces to exactly
    triangulated_radii's own behavior (this is what triangulated_radii
    itself calls)."""
    depth = sum(tile.cell_index) + 1
    radii = []
    for spatial_axis in (0, 1, 2):
        state = overrides.get(spatial_axis) or boundary_state_along_axis(tile, extent, spatial_axis)
        radii.append(_radius_for_state(state, depth, base_scale))
    return tuple(radii)  # type: ignore[return-value]


def blend_view_direction_color(recipes: Dict[int, Dict[str, Any]],
                                view_direction: Tuple[float, float, float]) -> RGB:
    """L1-normalizes view_direction into 3 non-negative axis weights, then
    sequentially composes the 3 axes' base_hue colors via the existing
    generic blend_rgb (pairwise, in axis order, t = each step's share of
    the running weight total). New composition, not claimed proven
    elsewhere. A pure-axis direction (e.g. (1,0,0)) reduces to exactly
    that axis's raw color -- the tie-back to the existing, proven
    single-axis system."""
    weights = [abs(float(v)) for v in view_direction]
    total = sum(weights)
    if total <= 0.0:
        raise ValueError(f"view_direction must be non-zero; got {view_direction!r}")
    weights = [w / total for w in weights]

    color = recipes[0]["base_hue"]
    running = weights[0]
    for axis in (1, 2):
        w = weights[axis]
        if w <= 0.0:
            continue
        new_running = running + w
        t = w / new_running
        color = blend_rgb(color, recipes[axis]["base_hue"], t)
        running = new_running
    return color


def compile_multi_perspective_blobs(crystal_id: str,
                                     extent: Tuple[int, int, int] = (2, 2, 2),
                                     view_direction: Tuple[float, float, float] = (1.0, 0.0, 0.0),
                                     base_scale_fraction: float = SPLAT_SCALE_FRACTION,
                                     ) -> List[Dict[str, Any]]:
    """compile_gluon_blobs for the base splat buffer, then every splat's
    shape is overwritten with triangulated_radii (genuine per-axis shape
    derived from all 3 axes' own LCR windows, instead of the one x-axis
    window compile_gluon_blobs's shape uses -- closing a named scope
    limit from this module's earlier slices) and color is overwritten
    with blend_view_direction_color. Shape is intrinsic to the tile (the
    same regardless of view_direction, matching how a real Gaussian's
    covariance doesn't change with viewing angle in 3DGS); only color is
    view-dependent here. The previously-inert observer_window_id field
    finally carries real, view-dependent information instead of one
    constant default. The blended hue gets the exact same morphon
    intensity/decay factor gluon_color applies to its own base hue
    (gluon_blob.intensity_decay_factor, extracted from gluon_color for
    this reuse)."""
    splats = compile_gluon_blobs(crystal_id, extent, base_scale_fraction)
    tiles = generate_tile_instances(crystal_id, extent)
    family = build_tile_family_asset(crystal_id)
    base_scale = family.nearest_neighbor_distance * base_scale_fraction
    observer_window_id = f"view:{view_direction}"
    max_depth = max(1, sum(max(0, e - 1) for e in extent) + 1)

    for d, tile in zip(splats, tiles):
        d["covariance_or_scale"] = triangulated_radii(tile, extent, base_scale)
        recipes = tile_perspective_recipes(tile, extent)
        blended = blend_view_direction_color(recipes, view_direction)
        depth = sum(tile.cell_index) + 1
        distance_fraction = (depth - 1) / max_depth
        factor, decay_diag = intensity_decay_factor(d["splat_id"], distance_fraction)
        rgb = tuple(max(0, min(255, int(round(c * factor)))) for c in blended)
        d["appearance_coefficients"] = [c / 255.0 for c in rgb]
        d["observer_window_id"] = observer_window_id
        mc = d["material_channels"]
        mc["perspective"] = {
            "view_direction": view_direction,
            "blended_base_hue": blended,
            "intensity": decay_diag["intensity"],
            "decay": decay_diag["decay"],
            "triangulated_radii": d["covariance_or_scale"],
            "per_axis": {
                axis: {"state": r["state"], "repaired_state": r["repaired_state"]}
                for axis, r in recipes.items()
            },
        }
    return splats


def render_from_view_direction(crystal_id: str,
                                extent: Tuple[int, int, int] = (2, 2, 2),
                                view_direction: Tuple[float, float, float] = (1.0, 0.0, 0.0),
                                width: int = 128, height: int = 128,
                                background: Tuple[int, int, int] = (5, 5, 5),
                                panel_path: Optional[str] = None,
                                **kwargs: Any) -> Dict[str, Any]:
    """compile_multi_perspective_blobs, then rendered + receipted +
    (optionally) written to an inspectable provenance HTML panel -- the
    literal payoff: the same compiled lattice, rendered differently from
    a different chosen perspective, with zero training."""
    splats = compile_multi_perspective_blobs(crystal_id, extent, view_direction, **kwargs)
    pic, frame_receipt, stream = render_pass(splats, width, height, background=background)

    result: Dict[str, Any] = {
        "picture": pic,
        "frame_receipt": frame_receipt,
        "stream": stream,
        "splats": splats,
        "view_direction": view_direction,
    }
    if panel_path is not None:
        result["provenance_path"] = write_provenance_panel(
            frame_receipt, panel_path, title=f"{crystal_id} view {view_direction}"
        )
    return result
