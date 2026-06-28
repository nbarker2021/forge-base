"""
SplatForge.fold_anneal_render — renders the "Damascus x10" fold/anneal
process for the first time, instead of leaving it as a numeric-only
receipt. Composes, unmodified:

  SplatForge.gluon_blob.compile_gluon_blobs       shape (covariance_or_scale)
                                        for every splat -- untouched; this
                                        module only ever recolors.
  SplatForge.gluon_blob.lattice_neighbor_state     each tile's real,
                                        original (L,C,R) boundary state.
  lattice_forge.centroid_voa.anneal_to_lie_conjugate / SplatForge.
  fold_anneal.state_at_fold             the proven, already-tested
                                        per-tile fold trajectory (see
                                        fold_anneal.py's own docstring for
                                        the full citation chain to
                                        verify_hamming_centroid_universality).
  SplatForge.weyl_address.full_spectrum_color      the proven color ladder,
                                        applied to each tile's CURRENT
                                        state at a given fold depth instead
                                        of its original state.
  SplatForge.raster.render_pass         unchanged rendering.

What's new: pointing fold_anneal's per-fold state at full_spectrum_color
and a real render, so the proven "closes by fold 3, zero change after"
claim becomes a literal, visually checkable rendered image instead of only
a waste_fraction number.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from lattice_forge.centroid_voa import anneal_to_lie_conjugate

from .compiler import SPLAT_SCALE_FRACTION
from .fold_anneal import state_at_fold
from .gluon_blob import compile_gluon_blobs, lattice_neighbor_state
from .raster import render_pass
from .tiling import generate_tile_instances
from .weyl_address import full_spectrum_color

LCRState = Tuple[int, int, int]


def compile_fold_state_blobs(crystal_id: str, fold_index: int,
                              extent: Tuple[int, int, int] = (2, 2, 2),
                              base_scale_fraction: float = SPLAT_SCALE_FRACTION,
                              ) -> List[Dict[str, Any]]:
    """compile_gluon_blobs (unmodified) for shape, then every splat is
    recolored by its tile's CURRENT (L,C,R) state at `fold_index` (its own
    anneal_to_lie_conjugate trajectory, frozen once closed) instead of its
    original lattice boundary state -- full_spectrum_color applied to
    whatever the fold has annealed that tile to so far."""
    splats = compile_gluon_blobs(crystal_id, extent, base_scale_fraction)
    tiles = generate_tile_instances(crystal_id, extent)

    for d, tile in zip(splats, tiles):
        original_state = lattice_neighbor_state(tile, extent)
        trajectory = anneal_to_lie_conjugate(original_state)["trajectory"]
        current_state = state_at_fold(trajectory, fold_index)
        rgb = full_spectrum_color(current_state)
        d["appearance_coefficients"] = [c / 255.0 for c in rgb]
        mc = d["material_channels"]
        mc["fold_state"] = {
            "fold": fold_index,
            "original_state": original_state,
            "current_state": current_state,
            "closed": current_state == trajectory[-1] and len(trajectory) - 1 <= fold_index,
        }
    return splats


def render_fold_sequence(crystal_id: str, fold_indices: Sequence[int] = (1, 2, 3, 10),
                          extent: Tuple[int, int, int] = (2, 2, 2),
                          width: int = 128, height: int = 128,
                          background: Tuple[int, int, int] = (5, 5, 5),
                          ) -> Dict[int, Dict[str, Any]]:
    """One rendered frame per requested fold depth -- the literal
    sequence a viewer would see watching the lattice anneal fold by fold."""
    results: Dict[int, Dict[str, Any]] = {}
    for fold_index in fold_indices:
        splats = compile_fold_state_blobs(crystal_id, fold_index, extent)
        pic, frame_receipt, _stream = render_pass(splats, width, height, background=background)
        results[fold_index] = {"picture": pic, "frame_receipt": frame_receipt, "splats": splats}
    return results
