"""
SplatForge.raster — the render-pass consumer: GaussianSplatInstance[] ->
Picture, with a deterministic frame receipt and a chained SplatReceipt.

KRR-GS-003 (point/ellipse/tile-bin rasterizer + deterministic frame receipt).
Division of responsibility mirrors this forge's existing vignette4d.py
precedent (SplatForge supplies the GBS-specific opinion; PixelForge supplies
the generic pixel-layer primitive):

  PixelForge.splat.rasterize_splats   the actual point/ellipse/tile-bin
                                       rasterizer (generic: position+scale+
                                       opacity+color -> Picture, no opinion
                                       about what a "splat" represents)
  PixelForge.frame.FrameStream        the existing deterministic frame-
                                       governance ledger, reused exactly as
                                       PixelForge.video.VideoSynth.render()
                                       already reuses it: a per-frame 8-vector
                                       feeds add_state(), and stream.artifact()
                                       / stream.stats() become the frame
                                       receipt's governance evidence. The
                                       8-vector here summarizes splats/tiles
                                       drawn instead of VideoSynth's layer
                                       motion — the same composition pattern,
                                       recombined for this build's own
                                       meaningful quantities.
  .receipts.SplatReceiptLedger        the existing Merkle-chained SplatReceipt
                                       ledger (.mint() already had backend /
                                       render_pass / benchmark_metrics fields
                                       reserved in ecology/schemas/
                                       splat_receipt.schema.json since Phase 1
                                       — this module is the first caller to
                                       actually fill them in).

backend is a free-text label, not a dispatch switch: this module always runs
the CPU rasterizer. A GPU backend (splat_vulkan.py) implements the same
(splats, width, height) -> (Picture, stats) contract so callers can render
with either and diff the two Pictures directly — see render_pass(backend=...)
for the parameter that records which path produced a given receipt.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple, Union

from PixelForge.frame import FrameStream
from PixelForge.genesis import GenesisField
from PixelForge.picture import Picture
from PixelForge.rgb import pixel_carry, pixel_emission
from PixelForge.splat import TILE_SIZE, rasterize_splats

from .compiler import GaussianSplatInstance, _stable_hash
from .receipts import ledger

RASTER_ADAPTER_ID = "SplatForge.raster.RenderPass"
RASTER_ADAPTER_VERSION = "0.1.0"

# backend label -> (splats_dicts, width, height, **kwargs) -> (Picture, stats),
# the one place render_pass() picks which rasterizer actually runs. Both
# entries satisfy the identical contract (PixelForge.splat.rasterize_splats'
# signature), so adding a third backend later is one more dict entry, not a
# branch anywhere else in this module.
def _cpu_backend(dicts, width, height, **kw):
    return rasterize_splats(dicts, width, height, **kw)


def _vulkan_backend(dicts, width, height, **kw):
    from PixelForge.splat_vulkan import rasterize_splats_vulkan  # lazy: only needs Vulkan if used
    return rasterize_splats_vulkan(dicts, width, height, **kw)


_BACKENDS = {"cpu_reference": _cpu_backend, "vulkan": _vulkan_backend}


def _frame_governance_vector(pic: Picture, stats: Dict) -> List[float]:
    """Sampled 8-vector summarizing one rasterized frame, in the same
    sample-and-normalize style as PixelForge.video.VideoSynth._frame_e8
    (mean R/G/B, mean emission, mean carry density), with the remaining
    three slots carrying this build's own meaningful quantities (tile
    occupancy, peak tile load, splat count) instead of layer motion."""
    n = pic.width * pic.height
    step = max(1, n // 256)
    sr = sg = sb = se = sc = 0
    count = 0
    for i in range(0, n, step):
        x, y = i % pic.width, i // pic.width
        r, g, b = pic.get(x, y)
        sr += r; sg += g; sb += b
        se += pixel_emission(r, g, b)
        sc += pixel_carry(r, g, b)
        count = count + 1
    count = max(1, count)
    return [
        sr / count / 255, sg / count / 255, sb / count / 255,
        se / count / 255, sc / count / 8,
        min(1.0, stats.get("tile_count", 0) / 256.0),
        min(1.0, stats.get("max_splats_per_tile", 0) / 64.0),
        min(1.0, stats.get("splat_count", 0) / 4096.0),
    ]


def render_pass(splats: Sequence[Union[GaussianSplatInstance, Dict]], width: int, height: int,
                 background: Tuple[int, int, int] = (0, 0, 0),
                 scale: float = 0.25, depth_cam: float = 5.0,
                 tile_size: int = TILE_SIZE, backend: str = "cpu_reference",
                 stream: Optional[FrameStream] = None,
                 ) -> Tuple[Picture, Dict, FrameStream]:
    """Rasterize one pass and record it as one more frame on a FrameStream.
    Pass the same `stream` across multiple render_pass calls to build a
    multi-frame deterministic stream (a sweep/orbit/animation); omit it to
    get a fresh single-frame stream.

    backend selects which rasterizer actually runs (see _BACKENDS) — both
    implement the identical (splats, width, height) -> (Picture, stats)
    contract, so the rest of this function (governance vector, GenesisField
    correction density, schema-shaped receipt) is backend-independent.

    splats may be GaussianSplatInstance objects or already-built dicts (the
    output of SplatForge.physics_binding.bind_physics_states, which attaches
    declared physics state into material_channels and returns dicts, not
    GaussianSplatInstance — see that module's docstring for why)."""
    if backend not in _BACKENDS:
        raise ValueError(f"unknown backend {backend!r}; known: {sorted(_BACKENDS)}")
    dicts = [s.to_dict() if hasattr(s, "to_dict") else s for s in splats]
    pic, raster_stats = _BACKENDS[backend](dicts, width, height, background=background,
                                            scale=scale, depth_cam=depth_cam,
                                            tile_size=tile_size)
    if stream is None:
        stream = FrameStream(fps=0.0, projection="standard",
                              parity_rule="free", entropy_slack=1.0)
    vec = _frame_governance_vector(pic, raster_stats)
    stream.add_state(vec, metadata={"frame_hash": pic.content_hash(),
                                     "backend": backend, **raster_stats})

    # The proven Rule_30 = Rule_90 (XOR-linear) + correction (C AND NOT R)
    # decomposition (CQE-paper-010 LCR Triality; lattice_forge/
    # rule90_linearization.py), applied here exactly as PixelForge.genesis
    # already applies it to any 8-bit picture: an EXACT, lossless seed +
    # correction-bitplane re-expression of the rendered frame (not an
    # approximation — regenerate() reproduces this frame's hash exactly).
    # density() is the correction-firing fraction per channel: the frame's
    # measured distance from the linear (Rule90) law, i.e. how much of this
    # frame's information genuinely needs the nonlinear correction term
    # rather than the free linear evolution — real compression-quality
    # evidence, not an invented metric.
    genesis_density = GenesisField.from_picture(pic).density()

    # Shape mirrors ecology/schemas/render_pass.schema.json exactly, so a GPU
    # backend emitting the same dict shape (gpu_profile set, backend="vulkan")
    # is a drop-in, schema-conformant alternative to this CPU path.
    frame_receipt = {
        "frame_hash": pic.content_hash(),
        "backend": backend,
        "gpu_profile": raster_stats.get("gpu_profile"),
        "width": width, "height": height,
        "tile_size": raster_stats["tile_size"],
        "splat_count": raster_stats["splat_count"],
        "tile_count": raster_stats["tile_count"],
        "max_splats_per_tile": raster_stats["max_splats_per_tile"],
        "quantization": raster_stats.get("quantization"),
        "genesis_correction_density": genesis_density,
        "tile_chart_classification": {
            "tile_chart_counts": raster_stats.get("tile_chart_counts"),
            "correction_firing_tile_count": raster_stats.get("correction_firing_tile_count"),
            "correction_firing_fraction": raster_stats.get("correction_firing_fraction"),
        },
        "parity_backend": None,
        "governance": stream.stats(),
    }
    return pic, frame_receipt, stream


def render_pass_with_parity(splats: Sequence[GaussianSplatInstance], width: int, height: int,
                             primary_backend: str = "cpu_reference",
                             parity_backend: str = "vulkan",
                             **render_kwargs,
                             ) -> Tuple[Picture, Dict, FrameStream]:
    """render_pass() on primary_backend, then render the identical splats
    again on parity_backend and diff the two Pictures via Picture.compare —
    GS-08 (GPU output is compared, not assumed authoritative) closed for
    real: both backends actually run, on the same splat buffer, and the
    measured per-channel delta is recorded in the receipt rather than
    asserted from "the code paths are supposed to match."""
    pic, frame_receipt, stream = render_pass(splats, width, height,
                                              backend=primary_backend, **render_kwargs)
    other_pic, other_receipt, _ = render_pass(splats, width, height,
                                               backend=parity_backend, **render_kwargs)
    diff = pic.compare(other_pic)
    frame_receipt["parity_backend"] = {
        "backend": parity_backend,
        "frame_hash": other_receipt["frame_hash"],
        "max_channel_delta": diff["max_channel_delta"],
        "mean_channel_delta": diff["mean_channel_delta"],
        "within_tolerance": diff["max_channel_delta"] <= 4,
    }
    return pic, frame_receipt, stream


def render_pass_and_mint(splats: Sequence[GaussianSplatInstance], width: int, height: int,
                          source_assets: Optional[List[str]] = None,
                          output_paths: Optional[List[str]] = None,
                          **render_kwargs,
                          ) -> Tuple[Picture, Dict, Dict]:
    """render_pass(), then mint exactly one SplatReceipt for the whole frame
    — render_pass/backend/benchmark_metrics filled in this time, not the
    always-null placeholders compile_with_receipt's CPU-compile-only receipts
    carry. Returns (picture, splat_receipt, frame_receipt)."""
    pic, frame_receipt, _stream = render_pass(splats, width, height, **render_kwargs)
    splat_ids = [s.splat_id if hasattr(s, "splat_id") else s["splat_id"] for s in splats]
    asset_ids = {s.source_asset_id if hasattr(s, "source_asset_id") else s["source_asset_id"]
                 for s in splats}
    assets = source_assets if source_assets is not None else sorted(asset_ids)
    input_hash = _stable_hash({
        "splat_ids": splat_ids,
        "width": width, "height": height,
        "backend": frame_receipt["backend"],
    })
    receipt = ledger.mint(
        source_assets=assets,
        adapter_id=RASTER_ADAPTER_ID,
        input_hash=input_hash,
        output_hash=pic.content_hash(),
        backend=frame_receipt["backend"],
        parameters={"width": width, "height": height,
                    "tile_size": frame_receipt["tile_size"],
                    "splat_count": frame_receipt["splat_count"]},
        render_pass=frame_receipt["frame_hash"],
        output_paths=output_paths,
        benchmark_metrics={
            "tile_count": frame_receipt["tile_count"],
            "max_splats_per_tile": frame_receipt["max_splats_per_tile"],
        },
    )
    return pic, receipt, frame_receipt
