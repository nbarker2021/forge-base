"""
SplatForge.vignette4d_playback — KRR-GS-007: 4D vignette slice/sweep
renderer and linked chart tests.

Composes two pieces that already exist, built in earlier slices, rather
than inventing a new playback mechanism:

  SplatForge.vignette4d.compile_family_to_4d_splats   the CPU mapping from
                                                        (TileInstance, 4th-
                                                        coordinate value) to
                                                        GaussianSplatInstance,
                                                        via PixelForge.blotlift.
  SplatForge.raster.render_pass                        already accepts a
                                                        shared FrameStream
                                                        across calls
                                                        ("a sweep/orbit/
                                                        animation" — its own
                                                        docstring) and
                                                        already supports
                                                        backend="vulkan", so
                                                        GPU sweep playback
                                                        falls out for free.

sweep_vignette holds the named 4th coordinate at one value per frame
(constant across all tiles within that frame, varying frame-to-frame) — the
"time/phase/depth/energy... slicing, sweep" the work order describes. A
caller wanting per-tile coordinate variation within a single frame should
call compile_family_to_4d_splats directly with its own extra_coordinate_fn;
this module is the sweep-across-frames case specifically.

"Linked chart tests" (the backlog item's own phrase) means asserting the
FrameStream's transition-legality obligations as the coordinate sweeps —
reused unchanged from PixelForge.frame.FrameStream, not new governance math.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from PixelForge.frame import FrameStream
from PixelForge.picture import Picture

from .raster import render_pass
from .vignette4d import VignetteState, Vec4, compile_family_to_4d_splats


def sweep_vignette(
    crystal_id: str,
    vignette: VignetteState,
    coordinate_values: Sequence[float],
    width: int,
    height: int,
    extent: Tuple[int, int, int] = (2, 2, 2),
    extra_coordinate_variance: float = 0.0,
    moderation_state4: Vec4 = (0.0, 0.0, 0.0, 0.0),
    moderation_variance4: Vec4 = (0.0, 0.0, 0.0, 0.0),
    physics_state_id: str = "sweep.default",
    spatial_variance3: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    projection_kind: str = "coxeter",
    backend: str = "cpu_reference",
    stream: Optional[FrameStream] = None,
    **render_kwargs,
) -> Tuple[List[Picture], List[Dict], FrameStream]:
    """One frame per value in coordinate_values: compile the whole crystal
    family at that 4th-coordinate value, then render_pass it onto a shared
    FrameStream. Requires vignette.spatial_dimension == 4 (the same
    requirement compile_tile_to_4d_splat already enforces) and a non-empty
    coordinate_values (a zero-frame "sweep" is a caller error, not silently
    accepted as an empty result).

    projection_kind defaults to "coxeter", not blotlift's own "standard"
    default: PROJECTIONS["standard"] is exactly (I,0) on the first 3 of the
    8 lifted axes (see PixelForge.projection.PROJECTIONS), so it multiplies
    the swept 4th coordinate (lifted to mean8[3]) by zero on every output
    row -- every frame would be pixel-identical regardless of
    coordinate_values, silently. Caught by running this function and
    diffing frame hashes, not by inspection. "coxeter"'s third row is
    `(0, 0, phi, 1/phi, 0,0,0,0)`, which does multiply mean8[3] by a nonzero
    coefficient, so the sweep is actually visible. Pass projection_kind=
    "standard" explicitly if a no-op sweep (e.g. a regression-test
    baseline) is genuinely what's wanted."""
    if not coordinate_values:
        raise ValueError("coordinate_values must be non-empty")

    frames: List[Picture] = []
    frame_receipts: List[Dict] = []
    for value in coordinate_values:
        def _const_coordinate(_tile, _value=value):
            return (_value, extra_coordinate_variance)

        splats = compile_family_to_4d_splats(
            crystal_id, extent, vignette,
            extra_coordinate_fn=_const_coordinate,
            moderation_state4=moderation_state4,
            moderation_variance4=moderation_variance4,
            physics_state_id=physics_state_id,
            spatial_variance3=spatial_variance3,
            projection_kind=projection_kind,
        )
        pic, frame_receipt, stream = render_pass(
            splats, width, height, backend=backend, stream=stream, **render_kwargs
        )
        frames.append(pic)
        frame_receipts.append(frame_receipt)

    return frames, frame_receipts, stream


def sweep_video_hash(frames: Sequence[Picture]) -> str:
    """Deterministic identity for a whole sweep — same hashing pattern as
    PixelForge.video.VideoSynth.render()'s video_hash, reused unchanged."""
    import hashlib

    h = hashlib.sha256()
    for pic in frames:
        h.update(pic.content_hash().encode())
    return h.hexdigest()[:16]
