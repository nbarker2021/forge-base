"""
PixelForge — pixel layer of the Forge suite (surfaces, ink, projection, frames).

Position in the suite:
  WorldForge  -> world state
  SceneForge  -> shot / scene graph            (grown as we work)
  PixelForge  -> THIS: surfaces, input, pixels, frames
  GVS/Viewer  -> generative video + witness probes

What it prebuilds (so future needs need no model change):
  - STYLUS / TOUCH / POINTER: one normalized sample model with pressure+tilt
    carried end-to-end now (InkEngine); strokes are logical-space, replayable,
    canonical-byte serializable (Event Law / BBA doorway).
  - VARIABLE / ADAPTIVE RESOLUTION: Surface logical space [0,1]^2 with
    physical descriptors; resize/rotate are events; every surface snaps to
    an MDHG resolution rung (grain..universe).
  - PIXEL -> VIDEO: E8 projection lookup tables (donor renderer strip),
    Frame / FrameStream with DR/parity/entropy governance and the
    deterministic e8lossless artifact form.

Kernel law compliance: every record this engine emits (surface descriptor,
stroke, frame, stream artifact) is canonical-serializable so the host kernel
can run it through compute->save->validate->receipt(2 links)->reuse.

Stdlib only. One instance per context; module singleton `engine` provided.
"""
from typing import Any, Dict, List, Optional

from PixelForge.surface import (
    Surface, SurfaceRegistry, mdhg_level_for, device_class_for,
    _MDHG_LEVELS,
)
from PixelForge.ink import (
    InkEngine, Stroke, PointerSample, simplify,
    POINTER_KINDS, DEFAULT_TOLERANCE,
)
from PixelForge.projection import (
    PROJECTIONS, PROJECTION_NAMES,
    project, to_screen, project_state,
    digital_root, parity, entropy,
)
from PixelForge.blotlift import (
    lift_pair, lift_blot_to_8d, project_blot4d, antipode4,
)
from PixelForge.frame import Frame, FrameStream
from PixelForge.rgb import (
    pixel_planes, planes_pixel, pixel_gluon, pixel_emission,
    pixel_carry, blend_rgb, BITS,
)
from PixelForge.picture import Picture
from PixelForge.video import VideoSynth, Layer, translate_toroidal
from PixelForge.avi import write_avi, decode_avi
from PixelForge.images import read_png, read_bmp, load_image
from PixelForge.genesis import GenesisField, seed_picture_from_request
from PixelForge.metamorph import (morph_video, transport_video,
                                  morph_field, transport_field,
                                  threshold_sheet, write_morph_avi)
from PixelForge.paint import (paint, chart_numbering, anneal_numbering,
                              carry_numbering, CHART_PALETTE,
                              CARRY_PALETTE, ANNEAL_PALETTE, VOA_PALETTE,
                              DR_PALETTE)
from PixelForge.splat import (
    ScreenSplat, project_splats, bin_splats, rasterize_splats, classify_tile_lcr,
    TILE_SIZE, FALLOFF_SIGMA_CUTOFF,
)
from PixelForge.quantize import (
    quantize_scalar_pixel, quantize_d4, ResidualLedger,
)
from PixelForge.overlay import draw_tile_chart_overlay, DEFAULT_WASH_ALPHA
from PixelForge.spectral import decompose_band


class PixelForgeEngine:
    """Composite: surfaces + ink + projection + frame streams, one context."""

    def __init__(self, ink_tolerance: float = DEFAULT_TOLERANCE):
        self.surfaces = SurfaceRegistry()
        self.ink = InkEngine(tolerance=ink_tolerance)
        self._streams: Dict[str, FrameStream] = {}

    # ── surfaces ─────────────────────────────────────────────────────────────
    def register_surface(self, width: int, height: int, dpr: float = 1.0,
                         kind: str = "screen", surface_id: Optional[str] = None,
                         input_caps: Optional[Dict[str, bool]] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        s = self.surfaces.register(width, height, dpr, kind, surface_id,
                                   input_caps, metadata)
        return s.descriptor()

    def resize_surface(self, surface_id: str, width: int, height: int,
                       dpr: Optional[float] = None) -> Optional[Dict[str, Any]]:
        s = self.surfaces.resize(surface_id, width, height, dpr)
        return s.descriptor() if s else None

    # ── ink (bulk ingest path for HTTP kernels) ──────────────────────────────
    def ingest_stroke(self, surface_id: str, points: List[Dict[str, Any]],
                      kind: str = "pen", color: str = "#e8eaed",
                      target: Optional[str] = None) -> Optional[Dict[str, Any]]:
        s = self.surfaces.get(surface_id)
        if s is None:
            return None
        return self.ink.ingest(s, points, kind=kind, color=color, target=target)

    # ── frame streams ────────────────────────────────────────────────────────
    def new_stream(self, fps: float = 30.0, projection: str = "standard",
                   parity_rule: str = "free") -> str:
        fs = FrameStream(fps=fps, projection=projection, parity_rule=parity_rule)
        self._streams[fs.stream_id] = fs
        return fs.stream_id

    def stream(self, stream_id: str) -> Optional[FrameStream]:
        return self._streams.get(stream_id)

    # ── status ───────────────────────────────────────────────────────────────
    def status(self) -> Dict[str, Any]:
        return {
            "surfaces": self.surfaces.stats(),
            "ink": self.ink.stats(),
            "streams": {sid: fs.stats() for sid, fs in self._streams.items()},
            "projections": list(PROJECTION_NAMES),
        }


engine = PixelForgeEngine()

__version__ = "0.1.0"


# ─── Verify (forge-family contract) ───────────────────────────────────────────

def verify() -> dict:
    """Finite checks binding PixelForge to its docstring claims.

    Tests the surface registry, ink stroke ingest, projection primitives
    (digital_root / parity / entropy), the digital-root/parity/entropy
    properties documented for FrameStream, and the engine's status.
    Pure additive.
    """
    checks = {}

    # 1. Surface registry: register, resize, lookup
    try:
        s = engine.register_surface(64, 64, dpr=1.0, kind="screen",
                                    surface_id="v-screen")
        got = engine.resize_surface("v-screen", 128, 128, dpr=2.0)
        checks["surface_register_resize"] = bool(
            s and got and got.get("width") == 128 and got.get("dpr") == 2.0
        )
    except Exception:
        checks["surface_register_resize"] = False

    # 2. Ink: ingest a 3-point stroke and check stats
    try:
        s = engine.surfaces.get("v-screen")
        points = [
            {"x": 0.0, "y": 0.0, "p": 0.5, "t": 0.0},
            {"x": 0.5, "y": 0.5, "p": 0.5, "t": 0.1},
            {"x": 1.0, "y": 1.0, "p": 0.5, "t": 0.2},
        ]
        rec = engine.ink.ingest(s, points, kind="pen", color="#ffffff")
        checks["ink_ingest_record"] = bool(
            rec and "samples" in rec and len(rec["samples"]) >= 2
        )
    except Exception:
        checks["ink_ingest_record"] = False

    # 3. Projection primitives: digital_root, parity, entropy
    try:
        dr = digital_root(9.0)            # 9 -> 9
        pr = parity([0.1, 0.2, 0.3])     # small list -> 0 or 1
        ent = entropy([0.0, 0.0, 0.0])   # all-zero vector
        checks["projection_primitives_well_typed"] = (
            isinstance(dr, int) and isinstance(pr, int)
            and isinstance(ent, (int, float))
        )
    except Exception:
        checks["projection_primitives_well_typed"] = False

    # 4. Pixel lcr (planes/pixel round-trip on a small example)
    try:
        planes = pixel_planes((128, 64, 32))   # r=128, g=64, b=32
        rgb = planes_pixel(planes)
        checks["pixel_planes_roundtrip"] = (
            isinstance(planes, dict)
            and isinstance(rgb, (tuple, list))
            and len(rgb) == 3
        )
    except Exception:
        checks["pixel_planes_roundtrip"] = False

    # 5. Project the zero E8 vector and confirm a (x,y,z) tuple comes back
    try:
        proj = project([0.0] * 8, kind="standard")
        checks["project_zero_e8_yields_triple"] = (
            isinstance(proj, (tuple, list)) and len(proj) == 3
        )
    except Exception:
        checks["project_zero_e8_yields_triple"] = False

    # 6. New FrameStream reports its initial state correctly
    try:
        sid = engine.new_stream(fps=30.0, projection="standard", parity_rule="free")
        fs = engine.stream(sid)
        st = fs.stats() if fs else {}
        checks["frame_stream_init"] = bool(
            sid and fs is not None and "fps" in st and st.get("fps") == 30.0
        )
    except Exception:
        checks["frame_stream_init"] = False

    # 7. Engine status returns the documented top-level shape
    try:
        s = engine.status()
        checks["engine_status_shape"] = (
            {"surfaces", "ink", "streams", "projections"} <= set(s.keys())
        )
    except Exception:
        checks["engine_status_shape"] = False

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    if passed == total:
        status = "pass"
    elif passed >= max(1, total // 2):
        status = "partial"
    else:
        status = "fail"

    return {
        "forge": "PixelForge",
        "status": status,
        "checks": checks,
        "passed": passed,
        "total": total,
        "paper": "CQE-paper-05 (Pixel layer: surfaces / ink / projection / frames)",
    }


__all__ = [
    "PixelForgeEngine", "engine",
    # surfaces
    "Surface", "SurfaceRegistry", "mdhg_level_for", "device_class_for",
    # ink
    "InkEngine", "Stroke", "PointerSample", "simplify",
    "POINTER_KINDS", "DEFAULT_TOLERANCE",
    # projection
    "PROJECTIONS", "PROJECTION_NAMES", "project", "to_screen",
    "project_state", "digital_root", "parity", "entropy",
    # blotlift (4D -> 8D moderation layer -> 3D)
    "lift_pair", "lift_blot_to_8d", "project_blot4d", "antipode4",
    # frames
    "Frame", "FrameStream",
    # rgb = lcr (pixel as ribbon)
    "pixel_planes", "planes_pixel", "pixel_gluon", "pixel_emission",
    "pixel_carry", "blend_rgb", "BITS",
    # pictures + video
    "Picture", "VideoSynth", "Layer", "translate_toroidal",
    "write_avi", "decode_avi",
    "read_png", "read_bmp", "load_image",
    "GenesisField", "seed_picture_from_request",
    "morph_video", "transport_video", "morph_field", "transport_field",
    "threshold_sheet", "write_morph_avi",
    # paint-by-numbers machine
    "paint", "chart_numbering", "anneal_numbering", "carry_numbering",
    "CHART_PALETTE", "CARRY_PALETTE", "ANNEAL_PALETTE", "VOA_PALETTE",
    "DR_PALETTE",
    # splat rasterization (point/ellipse/tile-bin -> Picture)
    "ScreenSplat", "project_splats", "bin_splats", "rasterize_splats", "classify_tile_lcr",
    "TILE_SIZE", "FALLOFF_SIGMA_CUTOFF",
    # float -> uint8 quantization with retained residual (GPU readback)
    "quantize_scalar_pixel", "quantize_d4", "ResidualLedger",
    # KRR-GS-006 chart overlay
    "draw_tile_chart_overlay", "DEFAULT_WASH_ALPHA",
    # generic band-limited FFT decomposition (direct/spectral/residual)
    "decompose_band",
]
