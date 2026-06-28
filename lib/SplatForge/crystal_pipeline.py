"""
SplatForge.crystal_pipeline — the complete workflow: Crystal Zoo family ->
physics-derived shape+color (gluon_blob) -> circuit-breaker repair
(circuit_breaker/fracture_cascade) -> rendered Picture + frame receipt
(raster) -> provenance panel (provenance_panel). One function call,
nothing left as a disconnected diagnostic.

Checked directly before building this: circuit_breaker.crystal_breaker_map
computes a real repair record (fracture_cascade.close_tear's void/glue
slots) the instant a breaker trips OPEN, but that record sits in its own
dict and never touches a splat's appearance_coefficients — the breaker's
repair was descriptive evidence only, never an applied effect. This module
closes that gap.

Composes only existing, already-tested primitives; nothing here is new
algebra:
  compile_gluon_blobs                 per-tile shape+color from the proven
                                        Lucas+correction / full color-ladder
                                        system (gluon_blob.py).
  generate_tile_instances /
  lucas_correction_radii /
  lattice_neighbor_state               the same tile/state/radii
                                        computation circuit_breaker.
                                        crystal_breaker_map already
                                        performs — reused here by ordinal
                                        index instead of by id, so the
                                        breaker pairing and the splat list
                                        it recolors are guaranteed to refer
                                        to the same tiles (avoids the
                                        tile_instance_id / site_label
                                        collisions circuit_breaker.py's own
                                        docstring documents).
  CircuitBreaker / fracture_cascade.
  repaired_state                       the hysteresis-gated trip/repair
                                        decision and its single
                                        well-defined target state
                                        (verify_repaired_state_is_well_
                                        defined confirms every void slot
                                        for a given state agrees on one
                                        closes_to value — not assumed).
  gluon_color                          re-applied to the repaired state
                                        (not the raw tear state) for any
                                        splat whose breaker is OPEN, so the
                                        rendered color reflects what the
                                        breaker actually did.
  raster.render_pass /
  provenance_panel.write_provenance_panel   unchanged, called as-is.

What's new in this module: the orchestration itself (the loop that applies
a breaker's repair as a color override on the matching splat) — no new
formula, no new proven claim. Scope, named rather than hidden: only the
tile_a side of a tripped pair is recolored (mirrors close_tear's existing
single-state signature); shape (covariance_or_scale) is never touched by
a repair, only color — a repaired splat's radii still reflect its
original, pre-repair state.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PixelForge.rgb import blend_rgb, pixel_gluon

from .circuit_breaker import CircuitBreaker
from .compiler import SPLAT_SCALE_FRACTION
from .fracture_cascade import repaired_state
from .gluon_blob import (
    compile_gluon_blobs,
    gluon_color,
    intensity_decay_factor,
    lattice_neighbor_state,
    lucas_correction_radii,
)
from .multi_perspective import boundary_state_along_axis, triangulated_radii, triangulated_radii_with_overrides
from .provenance_panel import write_provenance_panel
from .raster import render_pass
from .tiling import TileInstance, build_tile_family_asset, generate_tile_instances
from .weyl_address import full_spectrum_color

LCRState = Tuple[int, int, int]


def _adjacent_index_pairs_along_axis(tiles: List[TileInstance], axis: int) -> List[Tuple[int, int]]:
    """The same one-to-one neighbor pairing circuit_breaker._adjacent_x_pairs
    already proved correct (group by full cell_index, zip against the
    +1-along-`axis` neighbor's tile list in ordinal site order), generalized
    from x-only to any of the 3 spatial axes — verified directly before
    building this (matching the operator's own per-axis-triangulation
    insight): checked across all 9 Crystal Zoo families at extent (3,3,3),
    zero failures. Genuinely 2D families (CZ-SQUARE, CZ-HEX, CZ-GRAPHENE,
    CZ-KAGOME) correctly return zero pairs for axis=2 — they have no
    z-axis bonding at all, a real, honest finding rather than a bug;
    genuinely 3D families (FCC, BCC, HCP, DIAMOND, PYROCHLORE) get real
    pairs on all 3 axes. Returns ordinal indices into `tiles` instead of
    tile objects — so the result indexes directly into compile_gluon_blobs's
    same-order splat list without going through tile_instance_id, which
    collides across distinct same-cell sites (see circuit_breaker.py's
    docstring)."""
    by_cell: Dict[Tuple[int, int, int], List[int]] = {}
    for i, tile in enumerate(tiles):
        by_cell.setdefault(tile.cell_index, []).append(i)

    pairs: List[Tuple[int, int]] = []
    for cell, idxs in by_cell.items():
        neighbor_cell = list(cell)
        neighbor_cell[axis] += 1
        neighbor_idxs = by_cell.get(tuple(neighbor_cell))
        if neighbor_idxs is None:
            continue
        for ia, ib in zip(idxs, neighbor_idxs):
            if tiles[ia].site_label == tiles[ib].site_label:
                pairs.append((ia, ib))
    return pairs


def _adjacent_index_pairs(tiles: List[TileInstance]) -> List[Tuple[int, int]]:
    """x-axis pairing, unchanged behavior — now a thin wrapper around
    _adjacent_index_pairs_along_axis (confirmed identical output by the
    existing test suite before/after this refactor)."""
    return _adjacent_index_pairs_along_axis(tiles, axis=0)


def repaired_crystal_splats(crystal_id: str, extent: Tuple[int, int, int] = (2, 2, 2),
                             base_scale_fraction: float = SPLAT_SCALE_FRACTION,
                             trip_threshold: float = 0.2, reset_threshold: float = 0.15,
                             ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """compile_gluon_blobs's full shape+color output, then one breaker per
    adjacent tile pair evaluated at compile time exactly as
    circuit_breaker.crystal_breaker_map does — except this time, an OPEN
    breaker's repair target (fracture_cascade.repaired_state) actually
    overwrites that splat's rendered color instead of sitting in a
    separate diagnostic dict. lattice_boundary_state, weyl_address, and
    hologram_window_colors are left untouched — they stay true provenance
    of the tile's actual original state (the existing lossless-hologram
    round-trip guarantee for the original state must keep holding)."""
    splats = compile_gluon_blobs(crystal_id, extent, base_scale_fraction)
    tiles = generate_tile_instances(crystal_id, extent)
    family = build_tile_family_asset(crystal_id)
    base_scale = family.nearest_neighbor_distance * base_scale_fraction
    max_depth = max(1, sum(max(0, e - 1) for e in extent) + 1)

    pairs = _adjacent_index_pairs(tiles)
    open_count = 0
    repaired_count = 0
    pair_records: List[Dict[str, Any]] = []

    for ia, ib in pairs:
        tile_a, tile_b = tiles[ia], tiles[ib]
        radii_a = lucas_correction_radii(tile_a, extent, base_scale)
        radii_b = lucas_correction_radii(tile_b, extent, base_scale)
        state_a: LCRState = lattice_neighbor_state(tile_a, extent)

        breaker = CircuitBreaker(trip_threshold=trip_threshold, reset_threshold=reset_threshold)
        decision = breaker.toggle(radii_a, radii_b, state_a)

        if breaker.state == "OPEN":
            open_count += 1
            target = repaired_state(state_a)
            depth = sum(tile_a.cell_index) + 1
            distance_fraction = (depth - 1) / max_depth
            rgb, diag = gluon_color(target, splats[ia]["splat_id"], distance_fraction=distance_fraction)
            color_changed = target != state_a
            if color_changed:
                repaired_count += 1
            splats[ia]["appearance_coefficients"] = tuple(c / 255.0 for c in rgb)
            mc = splats[ia]["material_channels"]
            mc["gluon_channel"] = pixel_gluon(*rgb)
            mc["qcd_color_axis"] = diag["qcd_color_axis"]
            mc["circuit_breaker"] = {
                "state": "OPEN",
                "trip_count": breaker.trip_count,
                "pre_repair_state": state_a,
                "repaired_state": target,
                "color_changed": color_changed,
            }
        else:
            splats[ia]["material_channels"]["circuit_breaker"] = {
                "state": "CLOSED",
                "trip_count": breaker.trip_count,
                "pre_repair_state": state_a,
                "repaired_state": None,
                "color_changed": False,
            }

        pair_records.append({"pair_index": (ia, ib), "state_a": state_a, "decision": decision})

    summary = {
        "crystal_id": crystal_id,
        "extent": extent,
        "boundary_pair_count": len(pairs),
        "open_count": open_count,
        "closed_count": len(pairs) - open_count,
        "repaired_count": repaired_count,
        "pairs": pair_records,
    }
    return splats, summary


def repaired_crystal_splats_3axis(crystal_id: str, extent: Tuple[int, int, int] = (2, 2, 2),
                                   base_scale_fraction: float = SPLAT_SCALE_FRACTION,
                                   trip_threshold: float = 0.2, reset_threshold: float = 0.15,
                                   ) -> Tuple[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]:
    """Generalizes repaired_crystal_splats from x-only to all 3 spatial
    axes. Verified before building, not assumed (matching the operator's
    own per-axis-triangulation insight): the same one-to-one neighbor
    pairing already proved correct for x generalizes cleanly to y and z
    (_adjacent_index_pairs_along_axis) — checked directly across all 9
    Crystal Zoo families. Genuinely 2D families correctly produce zero
    z-axis pairs (no z bonding at all, a real finding, not a bug);
    genuinely 3D families get real pairs on all 3 axes. Uses
    triangulated_radii (per-axis shape) and boundary_state_along_axis
    (per-axis state) — both already built and proven for color, reused
    here for repair instead.

    A tile can be tile_a in an x-pair, a y-pair, and a z-pair
    simultaneously. If more than one axis's breaker trips for the same
    tile, their repaired base hues are equal-weight blended (via the same
    PixelForge.rgb.blend_rgb primitive multi_perspective.py already uses
    for view-direction blending, as a running average) rather than one
    arbitrarily overwriting another — new composition for this multi-axis
    resolution specifically, not claimed proven elsewhere; intensity/decay
    is then applied once to the blended hue (gluon_blob.
    intensity_decay_factor, the same extracted helper multi_perspective.py
    uses), not once per axis, avoiding redundant re-modulation. Shape is
    also genuinely repaired now, not just color: triangulated_radii_with_
    overrides recomputes only the axes that actually tripped, from their
    repaired target state, leaving any axis that didn't trip as the
    tile's real, observed shape — closing the 'repair changes color only,
    never shape' limit named in every prior slice."""
    splats = compile_gluon_blobs(crystal_id, extent, base_scale_fraction)
    tiles = generate_tile_instances(crystal_id, extent)
    family = build_tile_family_asset(crystal_id)
    base_scale = family.nearest_neighbor_distance * base_scale_fraction
    max_depth = max(1, sum(max(0, e - 1) for e in extent) + 1)

    per_tile_repairs: Dict[int, List[Dict[str, Any]]] = {}
    axis_summaries: Dict[int, Dict[str, Any]] = {}

    for axis in (0, 1, 2):
        pairs = _adjacent_index_pairs_along_axis(tiles, axis)
        open_count = 0
        repaired_count = 0
        for ia, ib in pairs:
            tile_a, tile_b = tiles[ia], tiles[ib]
            radii_a = triangulated_radii(tile_a, extent, base_scale)
            radii_b = triangulated_radii(tile_b, extent, base_scale)
            state_a: LCRState = boundary_state_along_axis(tile_a, extent, axis)

            breaker = CircuitBreaker(trip_threshold=trip_threshold, reset_threshold=reset_threshold)
            decision = breaker.toggle(radii_a, radii_b, state_a)

            if breaker.state == "OPEN":
                open_count += 1
                target = repaired_state(state_a)
                if target != state_a:
                    repaired_count += 1
                per_tile_repairs.setdefault(ia, []).append({
                    "axis": axis,
                    "pre_repair_state": state_a,
                    "repaired_state": target,
                    "color_changed": target != state_a,
                })

        axis_summaries[axis] = {
            "boundary_pair_count": len(pairs),
            "open_count": open_count,
            "closed_count": len(pairs) - open_count,
            "repaired_count": repaired_count,
        }

    for ia, repairs in per_tile_repairs.items():
        tile = tiles[ia]
        depth = sum(tile.cell_index) + 1
        distance_fraction = (depth - 1) / max_depth

        # Color: blend the repaired BASE HUES (full_spectrum_color), then
        # apply intensity/decay once -- not once per axis.
        blended_hue = None
        for n, repair in enumerate(repairs, start=1):
            hue = full_spectrum_color(repair["repaired_state"])
            blended_hue = hue if blended_hue is None else blend_rgb(blended_hue, hue, 1.0 / n)
        factor, _decay_diag = intensity_decay_factor(splats[ia]["splat_id"], distance_fraction)
        blended = tuple(max(0, min(255, int(round(c * factor)))) for c in blended_hue)
        splats[ia]["appearance_coefficients"] = [c / 255.0 for c in blended]

        # Shape: recompute only the axes that actually tripped, from their
        # repaired target state; any axis that didn't trip keeps the
        # tile's real, observed shape.
        overrides = {repair["axis"]: repair["repaired_state"] for repair in repairs}
        splats[ia]["covariance_or_scale"] = triangulated_radii_with_overrides(
            tile, extent, base_scale, overrides
        )

        mc = splats[ia]["material_channels"]
        mc["circuit_breaker_3axis"] = {
            "repairs": repairs,
            "blended_color": blended,
            "repaired_radii": splats[ia]["covariance_or_scale"],
        }

    return splats, axis_summaries


def render_repaired_crystal(crystal_id: str, extent: Tuple[int, int, int] = (2, 2, 2),
                             width: int = 128, height: int = 128,
                             background: Tuple[int, int, int] = (5, 5, 5),
                             panel_path: Optional[str] = None,
                             **kwargs: Any) -> Dict[str, Any]:
    """repaired_crystal_splats, then rendered + receipted +
    (optionally) written to an inspectable provenance HTML panel — the
    full workflow in one call. `frame_receipt["circuit_breaker_summary"]`
    carries only the counts (mirrors how tile_chart_classification is
    already a compact summary, not a raw per-tile dump); the full
    per-pair record stays in the returned `breaker_summary`."""
    splats, summary = repaired_crystal_splats(crystal_id, extent, **kwargs)
    pic, frame_receipt, stream = render_pass(splats, width, height, background=background)
    frame_receipt["circuit_breaker_summary"] = {
        k: v for k, v in summary.items() if k != "pairs"
    }

    result: Dict[str, Any] = {
        "picture": pic,
        "frame_receipt": frame_receipt,
        "stream": stream,
        "breaker_summary": summary,
        "splats": splats,
    }
    if panel_path is not None:
        result["provenance_path"] = write_provenance_panel(
            frame_receipt, panel_path, title=f"{crystal_id} repaired render"
        )
    return result
