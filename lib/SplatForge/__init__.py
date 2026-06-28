"""
SplatForge — the Tile-to-Splat compiler and CPU reference render pass for the
CQECMPLX Tile Physics Graphics Engine (CQECMPLX_Tile_Physics_Graphics_Engine_Workplan_v1_1_3DGS.md).

Scope of this forge:
  GS-02 (done, CPU): Crystal Zoo tile family -> deterministic TileInstance[]
    -> GaussianSplatInstance[] -> SplatReceipt.
  GS-07 mapping (done): 4D vignette -> 8D moderation layer -> 3D splat
    (vignette4d.py), via PixelForge.blotlift.
  GS-03/GS-05/GS-08 (done): GaussianSplatInstance[] -> Picture +
    deterministic frame receipt, CPU or Vulkan (raster.py), via
    PixelForge.splat/splat_vulkan and PixelForge.frame.FrameStream's
    governance ledger; CPU/GPU parity measured and recorded, not assumed.
  GS-07 sweep (done): vignette4d_playback.py — multi-frame 4D coordinate
    sweep on one shared FrameStream, CPU or GPU.

Still open: 3DGS import/export (GS-01 / KRR-GS-004), the capture/
reconstruction bridge (GS-06), D3D12/CUDA backends (GS-05 optional half,
KRR-GS-008), and chart-overlay/provenance UI (KRR-GS-006 — a distinct
backlog item from GS-06, despite the shared "06"; see this package's
promotion slice docs for current, dated status — multiple slices exist,
read the latest.
"""
from __future__ import annotations

from .compiler import ADAPTER_ID, ADAPTER_VERSION, GaussianSplatInstance, TileToSplatCompiler
from .receipts import SplatReceiptLedger, compile_with_receipt, ledger
from .tiling import (
    CRYSTAL_IDS,
    TileFamilyAsset,
    TileInstance,
    build_tile_family_asset,
    generate_tile_instances,
)
from .vignette4d import (
    VignetteState,
    compile_family_to_4d_splats,
    compile_family_to_4d_splats_and_hash,
    compile_tile_to_4d_splat,
)
from .raster import (
    RASTER_ADAPTER_ID,
    RASTER_ADAPTER_VERSION,
    render_pass,
    render_pass_and_mint,
    render_pass_with_parity,
)
from .vignette4d_playback import sweep_vignette, sweep_video_hash
from .physics_binding import PhysicsState, bind_physics_states, physics_residual_series
from .provenance_panel import render_provenance_html, write_provenance_panel
from .gluon_blob import (
    compile_gluon_blobs,
    gluon_color,
    lattice_neighbor_state,
    lucas_correction_radii,
    qcd_color_axis,
    sweep_spectral_residue,
)
from .gluon_hologram import (
    GluonBit,
    decode_jordan_diagonal_windows,
    jordan_diagonal_windows,
    lock_gluon,
    verify_lossless_round_trip,
)
from .fracture_cascade import (
    SEVEN_PATHS,
    apply_path,
    close_tear,
    detect_tear,
    fracture_cascade,
    repaired_state,
    verify_every_state_has_a_void_slot,
    verify_repaired_state_is_well_defined,
)
from .state_recipe_table import (
    ALL_STATES,
    STATE_RECIPE_TABLE,
    lookup as lookup_state_recipe,
    verify as verify_state_recipe_table,
)
from .bitmatrix64 import (
    compression_report as bitmatrix64_compression_report,
    fracture_cascade_void_matrix,
    pack_8x8_to_uint64,
    unpack_uint64_to_8x8,
)
from .circuit_breaker import (
    CircuitBreaker,
    crystal_breaker_map,
    verify_no_chatter,
)
from .weyl_address import (
    ADDRESS_TABLE,
    ANTICOLORS,
    PRIMARY_COLORS,
    TRACE1_ORDER,
    TRACE2_ORDER,
    VACUA,
    VACUUM_COLORS,
    full_spectrum_color,
    weyl_address,
    verify as verify_weyl_address,
    verify_color_ladder,
)
from .crystal_pipeline import (
    render_repaired_crystal,
    repaired_crystal_splats,
    repaired_crystal_splats_3axis,
)
from .multi_perspective import (
    blend_view_direction_color,
    boundary_state_along_axis,
    compile_multi_perspective_blobs,
    render_from_view_direction,
    tile_perspective_recipes,
)
from .fold_anneal import (
    BRAID_WORD,
    run_damascus_folds,
    state_at_fold,
    verify as verify_fold_anneal,
)
from .fold_anneal_render import (
    compile_fold_state_blobs,
    render_fold_sequence,
)

__version__ = "0.1.0"

__all__ = [
    "CRYSTAL_IDS",
    "TileFamilyAsset",
    "TileInstance",
    "build_tile_family_asset",
    "generate_tile_instances",
    "GaussianSplatInstance",
    "TileToSplatCompiler",
    "ADAPTER_ID",
    "ADAPTER_VERSION",
    "SplatReceiptLedger",
    "ledger",
    "compile_with_receipt",
    # GS-07 CPU-prototype: 4D vignette -> 8D moderation layer -> 3D splat
    "VignetteState",
    "compile_tile_to_4d_splat",
    "compile_family_to_4d_splats",
    "compile_family_to_4d_splats_and_hash",
    # GS-03/GS-05 CPU reference render pass: splats -> Picture + frame receipt
    "RASTER_ADAPTER_ID",
    "RASTER_ADAPTER_VERSION",
    "render_pass",
    "render_pass_and_mint",
    "render_pass_with_parity",
    # GS-07 sweep: multi-frame 4D coordinate playback on one shared FrameStream
    "sweep_vignette",
    "sweep_video_hash",
    # GS-04: declared physics/chart state binding, no render-driven mutation
    "PhysicsState",
    "bind_physics_states",
    "physics_residual_series",
    # KRR-GS-006 provenance inspection
    "render_provenance_html",
    "write_provenance_panel",
    # gluon blob: Lucas+correction shape, QCD-axis color, spectral residue
    "compile_gluon_blobs",
    "gluon_color",
    "lattice_neighbor_state",
    "lucas_correction_radii",
    "qcd_color_axis",
    "sweep_spectral_residue",
    # gluon hologram: bit -> color-locked gluon, 3 Jordan-diagonal LCR windows
    "GluonBit",
    "lock_gluon",
    "jordan_diagonal_windows",
    "decode_jordan_diagonal_windows",
    "verify_lossless_round_trip",
    # fracture cascade: tears closed by the proven <=3-step centroid anneal
    "SEVEN_PATHS",
    "apply_path",
    "fracture_cascade",
    "close_tear",
    "detect_tear",
    "verify_every_state_has_a_void_slot",
    "repaired_state",
    "verify_repaired_state_is_well_defined",
    # state recipe table: the O(1) reverse-library pattern over the 8 states
    "ALL_STATES",
    "STATE_RECIPE_TABLE",
    "lookup_state_recipe",
    "verify_state_recipe_table",
    # bitmatrix64: 8x8 binary matrix <-> one 64-bit integer, exact
    "pack_8x8_to_uint64",
    "unpack_uint64_to_8x8",
    "fracture_cascade_void_matrix",
    "bitmatrix64_compression_report",
    # circuit breaker: hysteresis-gated tear detection, pre-provisioned per crystal
    "CircuitBreaker",
    "crystal_breaker_map",
    "verify_no_chatter",
    # weyl address: preallocated (Weyl element, QCD axis) address for all 8 states
    "ADDRESS_TABLE",
    "TRACE1_ORDER",
    "TRACE2_ORDER",
    "VACUA",
    "weyl_address",
    "verify_weyl_address",
    # color ladder: every one of the 8 states gets its own RGB (primary/
    # anticolor/black/white), not just the 3 trace-2 states
    "PRIMARY_COLORS",
    "ANTICOLORS",
    "VACUUM_COLORS",
    "full_spectrum_color",
    "verify_color_ladder",
    # crystal pipeline: the complete workflow -- compile, color, repair, render, provenance
    "render_repaired_crystal",
    "repaired_crystal_splats",
    "repaired_crystal_splats_3axis",
    # multi perspective: per-axis boundary classification + view-direction color blend, no ML
    "boundary_state_along_axis",
    "tile_perspective_recipes",
    "blend_view_direction_color",
    "compile_multi_perspective_blobs",
    "render_from_view_direction",
    # fold anneal: Damascus x10 read structurally through the proven
    # Hamming-centroid annealing, applied across real Crystal Zoo lattices
    "BRAID_WORD",
    "run_damascus_folds",
    "state_at_fold",
    "verify_fold_anneal",
    # fold anneal render: the Damascus x10 process, actually rendered for the first time
    "compile_fold_state_blobs",
    "render_fold_sequence",
]


def verify() -> dict:
    """Smoke-verify all 9 Crystal Zoo families compile deterministically, and
    that the CPU render pass produces the same frame hash twice for one
    family (the rasterizer's own determinism, independent of the compiler's)."""
    compiler = TileToSplatCompiler()
    results = {}
    for crystal_id in CRYSTAL_IDS:
        splats, in_hash, out_hash = compiler.compile_and_hash(crystal_id)
        splats2, in_hash2, out_hash2 = compiler.compile_and_hash(crystal_id)
        results[crystal_id] = {
            "splat_count": len(splats),
            "deterministic": in_hash == in_hash2 and out_hash == out_hash2,
        }
    ok = all(r["deterministic"] and r["splat_count"] > 0 for r in results.values())

    probe_splats = compiler.compile(CRYSTAL_IDS[0])
    pic_a, _, _ = render_pass(probe_splats, 64, 64)
    pic_b, _, _ = render_pass(probe_splats, 64, 64)
    raster_ok = pic_a.content_hash() == pic_b.content_hash()

    return {"forge": "SplatForge", "status": "pass" if (ok and raster_ok) else "fail",
            "families": results, "raster_deterministic": raster_ok}
