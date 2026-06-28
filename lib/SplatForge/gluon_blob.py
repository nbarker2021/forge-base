"""
SplatForge.gluon_blob — a splat whose shape, color, and name are all
derived from this corpus's own proven algebra instead of an arbitrary
isotropic scale and a hand-picked palette RGB.

Four real pieces, composed, none invented for this module except the
specific blend arithmetic (called out below where it occurs):

  lattice_forge.block_d4.chart_state_to_d4   maps any (L,C,R) state onto
                                              one of exactly 4 D4 sub-block
                                              axes (0-3) — a real "4-term
                                              family."
  lattice_forge.rule90_linearization         lucas_bit / correction: the
                                              proven Rule_30 = Rule_90 (+)
                                              correction algebra, applied
                                              here to a lattice tile's own
                                              boundary state (not a CA
                                              cell or a pixel bitplane —
                                              a third domain for the same
                                              proven primitives).
  CQE-PAPER-092 Theorem 92 (tiling theory <-> U(1)->SU(2)->SU(3))         +
  block_d4.SHELL2_STATES / CHART_TO_D4        the proven 3-coloring: axis
                                              0/1/2 (d1/d2/d3) ARE the QCD-
                                              isomorphic color charges. The
                                              base hue below is read from
                                              SplatForge.weyl_address.
                                              full_spectrum_color, which
                                              gives trace-2 (this 3-coloring)
                                              an RGB primary per axis, and
                                              extends it (new composition,
                                              not separately proven) so
                                              trace-1 gets the exact RGB
                                              complement at the matching
                                              ordinal stratum index — the
                                              antiquark/anticolor reading —
                                              and the 2 vacua get black/
                                              white, so all 8 states are
                                              individually colored instead
                                              of 5 of them collapsing to one
                                              shared neutral gray.
  ChromaForge.morphon                        e8_embed/morphon_delta/
                                              sector_split: a real, kappa-
                                              bounded (kappa=ln(phi)/16,
                                              CQE-paper-09) conserved
                                              scalar, used here as an
                                              *intensity* modulation on top
                                              of the QCD-derived hue, not
                                              as the hue itself (sector_
                                              split returns delta_phi/3
                                              three times — it does not
                                              differentiate channels, so
                                              this module does not pretend
                                              it does).

The radius blend formula in lucas_correction_radii and the full 8-state
color ladder in weyl_address.full_spectrum_color (used as gluon_color's
base hue) ARE new — composing the proven primitives above in a way none
of them individually specify. Said plainly here, not implied to be proven
elsewhere.

TileToSplatCompiler.compile() is never modified — this module wraps its
output via dataclasses.replace() (GaussianSplatInstance is frozen) and
returns dicts with gluon_channel/qcd_color_axis/etc. stamped into
material_channels, the same non-mutating pattern
SplatForge.physics_binding.bind_physics_states already established.
"""
from __future__ import annotations

import dataclasses
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from lattice_forge.block_d4 import chart_state_to_d4
from lattice_forge.rule90_linearization import correction, lucas_bit
from ChromaForge.morphon import kappa, morphon_delta, sector_split

from PixelForge.rgb import pixel_gluon
from PixelForge.spectral import decompose_band

from .compiler import SPLAT_SCALE_FRACTION, TileToSplatCompiler
from .tiling import TileInstance, build_tile_family_asset, generate_tile_instances

LCRState = Tuple[int, int, int]


def lattice_neighbor_state(tile: TileInstance, extent: Tuple[int, int, int]) -> LCRState:
    """A tile's own (L,C,R) from whether its x-adjacent lattice cells are
    themselves inside the compiled extent — a real boundary signal (edge
    of the compiled block vs. bulk interior) at the lattice level, distinct
    from PixelForge.splat.classify_tile_lcr's screen-space version."""
    ix = tile.cell_index[0]
    left = 1 if ix - 1 >= 0 else 0
    right = 1 if ix + 1 < extent[0] else 0
    return (left, 1, right)


def lucas_correction_radii(tile: TileInstance, extent: Tuple[int, int, int],
                            base_scale: float) -> Tuple[float, float, float]:
    """Three radii (not necessarily equal) from lucas_bit/correction
    evaluated at this tile's depth and D4 axis. The multiplier formula
    (1 + 0.5*lucas - 0.25*corr, clamped >= 0.25) is new composition, not a
    formula proven elsewhere — it exists to give a deterministic,
    bounded-positive, non-arbitrary anisotropy instead of the isotropic
    (scale,scale,scale) TileToSplatCompiler.compile() always uses."""
    state = lattice_neighbor_state(tile, extent)
    axis = chart_state_to_d4(state)[0]
    depth = sum(tile.cell_index) + 1  # >= 1
    corr = correction(*state)
    radii = []
    for spatial_axis in range(3):
        lucas = lucas_bit(depth, spatial_axis - axis)
        multiplier = max(0.25, 1.0 + 0.5 * lucas - 0.25 * corr)
        radii.append(round(base_scale * multiplier, 6))
    return tuple(radii)  # type: ignore[return-value]


def qcd_color_axis(state: LCRState) -> int:
    """The proven D4 axis (0-3) for a chart state — axis 0/1/2 are the
    QCD-isomorphic color-charge axes; see this module's docstring."""
    return chart_state_to_d4(state)[0]


def intensity_decay_factor(splat_id: str, distance_fraction: float = 0.0) -> Tuple[float, Dict[str, Any]]:
    """The morphon-derived intensity*decay scalar gluon_color applies to its
    base hue, extracted so other modules (SplatForge.multi_perspective) can
    apply the exact same factor to a color that wasn't built via
    gluon_color directly, instead of silently skipping it. ChromaForge.
    morphon's kappa-bounded conserved delta (keyed deterministically on
    splat_id) sets the intensity; distance_fraction (0 at the lattice
    block's near corner, 1 at its farthest) drives the exp(-ln(2)*x)
    half-life-form decay — the literal radioactive-decay shape, structurally
    the same exponential already used for the rasterizer's Gaussian alpha
    falloff."""
    delta = morphon_delta(splat_id, affinity=1.0)
    k = kappa()
    sectors = sector_split(delta)
    intensity = max(0.5, min(1.0, 1.0 + sectors["delta_n"] / k)) if k else 1.0
    decay = math.exp(-math.log(2.0) * max(0.0, distance_fraction))
    diagnostics = {
        "morphon_delta": delta,
        "sector_split": sectors,
        "intensity": round(intensity, 6),
        "decay": round(decay, 6),
    }
    return intensity * decay, diagnostics


def gluon_color(state: LCRState, splat_id: str,
                distance_fraction: float = 0.0) -> Tuple[Tuple[int, int, int], Dict[str, Any]]:
    """Every one of the 8 chart states sets its own base hue — trace-2
    (the proven QCD color-charge axis) gets an RGB primary, trace-1 gets
    that primary's exact RGB complement (the antiquark/anticolor reading,
    SplatForge.weyl_address.full_spectrum_color), the 2 vacua get black/
    white. This replaces the earlier 4-bucket palette (axis 0/1/2 colored,
    axis 3 = one shared neutral gray for all 5 non-shell2 states) — those 5
    states are now individually distinguishable instead of collapsing to
    one color. ChromaForge.morphon's kappa-bounded conserved delta (keyed
    deterministically on splat_id) sets an *intensity* scalar on top of
    that hue (sector_split's three values are identical by its own
    definition, so this is one factor, not three). distance_fraction (0 at
    the lattice block's near corner, 1 at its farthest) drives an
    exp(-ln(2)*x) half-life-form falloff — the literal radioactive-decay
    shape, structurally the same exponential already used for the
    rasterizer's Gaussian alpha falloff."""
    from .weyl_address import full_spectrum_color  # lazy: avoids a circular
    # import, since weyl_address imports qcd_color_axis from this module

    axis = qcd_color_axis(state)
    base = full_spectrum_color(state)
    factor, diagnostics = intensity_decay_factor(splat_id, distance_fraction)
    rgb = tuple(max(0, min(255, int(round(c * factor)))) for c in base)
    diagnostics = {"qcd_color_axis": axis, **diagnostics}
    return rgb, diagnostics  # type: ignore[return-value]


def compile_gluon_blobs(crystal_id: str, extent: Tuple[int, int, int] = (2, 2, 2),
                         base_scale_fraction: float = SPLAT_SCALE_FRACTION) -> List[Dict[str, Any]]:
    """TileToSplatCompiler.compile() unchanged, then each splat's shape and
    color are replaced (dataclasses.replace — GaussianSplatInstance is
    frozen, never mutated) with the Lucas+correction radii and the QCD-
    color-axis gluon color. distance_fraction is each tile's depth
    normalized by the compiled block's maximum possible depth, so splats
    farther from the block's near corner genuinely decay. Returns dicts
    (not GaussianSplatInstance objects) — gluon_channel/qcd_color_axis/
    lattice_boundary_state/morphon are stamped into material_channels the
    same way SplatForge.physics_binding.bind_physics_states attaches
    declared state, and material_channels isn't a stored dataclass field
    to begin with (see compiler.py)."""
    from .state_recipe_table import lookup as lookup_state_recipe  # lazy: avoids a
    # circular import, since state_recipe_table imports qcd_color_axis from
    # this module

    base_splats = TileToSplatCompiler().compile(crystal_id, extent)
    tiles = generate_tile_instances(crystal_id, extent)
    family = build_tile_family_asset(crystal_id)
    base_scale = family.nearest_neighbor_distance * base_scale_fraction
    max_depth = max(1, sum(max(0, e - 1) for e in extent) + 1)

    out: List[Dict[str, Any]] = []
    for splat, tile in zip(base_splats, tiles):
        state = lattice_neighbor_state(tile, extent)
        recipe = lookup_state_recipe(state)  # O(1): the 8-state table, not recomputed per splat
        radii = lucas_correction_radii(tile, extent, base_scale)
        depth = sum(tile.cell_index) + 1
        distance_fraction = (depth - 1) / max_depth
        rgb, diag = gluon_color(state, splat.splat_id, distance_fraction=distance_fraction)
        rgb_float = tuple(c / 255.0 for c in rgb)

        updated = dataclasses.replace(splat, covariance_or_scale=radii,
                                       appearance_coefficients=rgb_float)
        d = updated.to_dict()
        channels = dict(d.get("material_channels") or {})
        channels["gluon_channel"] = pixel_gluon(*rgb)
        channels["qcd_color_axis"] = diag["qcd_color_axis"]
        channels["lattice_boundary_state"] = list(state)
        channels["morphon"] = {
            "delta": diag["morphon_delta"],
            "intensity": diag["intensity"],
            "decay": diag["decay"],
        }
        # Lossless: decode_jordan_diagonal_windows(these colors) recovers
        # `state` exactly — see state_recipe_table.verify() and
        # test_gluon_blob_carries_a_lossless_hologram_of_its_own_state.
        channels["hologram_window_colors"] = recipe["hologram_window_colors"]
        channels["fracture"] = {
            "void_slot_count": recipe["void_slot_count"],
            "glue_slot_count": recipe["glue_slot_count"],
            "is_tear_prone": recipe["is_tear_prone"],
        }
        channels["weyl_address"] = recipe["weyl_address"]
        d["material_channels"] = channels
        out.append(d)
    return out


def sweep_spectral_residue(frame_receipts: Sequence[Dict[str, Any]],
                            min_period: float = 3.0,
                            max_period: Optional[float] = None,
                            top_n: int = 3) -> Dict[str, Any]:
    """Pulls correction_firing_fraction out of each frame receipt's
    tile_chart_classification (already produced by SplatForge.raster.
    render_pass for every frame of a SplatForge.vignette4d_playback.
    sweep_vignette run) into one series, and runs PixelForge.spectral.
    decompose_band on it — the residual is real evidence about how that
    boundary signal evolves across the sweep, not a fabricated metric."""
    series = [fr["tile_chart_classification"]["correction_firing_fraction"] for fr in frame_receipts]
    return decompose_band(series, min_period=min_period, max_period=max_period, top_n=top_n)
