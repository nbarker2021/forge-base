"""
PixelForge Surface — adaptive-resolution render targets.

A Surface is any pixel-bearing display area: a wall screen, a phone, a tablet,
a canvas region, a single calendar cell. Surfaces are RESOLUTION-INDEPENDENT:
all content addresses live in logical space [0,1] x [0,1]; the surface
descriptor carries the physical mapping (width, height, device pixel ratio,
orientation). Resizing or rotating a surface never moves content — it only
changes the descriptor, and the change is an EVENT (Event Law: computed,
saved, validated, receipted).

Resolution ladder: every surface snaps to an MDHG sheet level by pixel count
(the same grain..universe ladder the corpus uses). A watch face and a video
wall are the same surface at different rungs.

Stdlib only. Prebuilt for: stylus/touch input mapping, variable resolutions,
orientation changes, multi-surface layouts (one engine, many panes).
"""
from __future__ import annotations

import hashlib
import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ─── Lookup tables (import-time, read-only) ───────────────────────────────────

# MDHG rung by total pixel count: log2(pixels) bands -> 9 levels
_MDHG_LEVELS: Tuple[str, ...] = (
    "grain", "dust", "triad", "block", "cluster",
    "domain", "region", "planet", "universe",
)
# thresholds: <=2^10 grain ... >=2^26 universe (2-bit steps per rung)
_LEVEL_BITS: Tuple[int, ...] = (10, 12, 14, 16, 18, 20, 22, 24, 26)

# Common device classes for fast classification (informational labels)
_DEVICE_CLASSES: Tuple[Tuple[int, str], ...] = (
    (320 * 240,    "micro"),       # tiny embedded panel
    (800 * 480,    "panel"),       # small HMI / e-ink class
    (1280 * 720,   "hd"),
    (1920 * 1080,  "fhd"),         # the wall-calendar class
    (2560 * 1440,  "qhd"),
    (3840 * 2160,  "uhd"),
    (10 ** 12,     "wall"),        # video-wall class
)


def mdhg_level_for(pixels: int) -> Tuple[int, str]:
    """Snap a pixel count to its MDHG resolution rung."""
    if pixels <= 0:
        return 0, _MDHG_LEVELS[0]
    bits = math.log2(pixels)
    for i, b in enumerate(_LEVEL_BITS):
        if bits <= b:
            return i, _MDHG_LEVELS[i]
    return 8, _MDHG_LEVELS[8]


def device_class_for(pixels: int) -> str:
    for threshold, name in _DEVICE_CLASSES:
        if pixels <= threshold:
            return name
    return "wall"


# ─── Surface descriptor ───────────────────────────────────────────────────────

@dataclass
class Surface:
    """One adaptive render target. Logical space is always [0,1]^2."""

    surface_id: str
    width: int                       # physical CSS/pixel width
    height: int
    dpr: float = 1.0                 # device pixel ratio (retina etc.)
    orientation: str = "landscape"   # landscape | portrait
    color_depth: int = 24
    kind: str = "screen"             # screen | cell | widget | offscreen
    input_caps: Dict[str, bool] = field(default_factory=lambda: {
        "mouse": True, "touch": False, "stylus": False, "pressure": False,
    })
    metadata: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def __post_init__(self):
        # orientation always derives from the dimensions, however constructed
        self.orientation = "portrait" if self.height > self.width else "landscape"

    # ── derived ──────────────────────────────────────────────────────────────
    @property
    def pixels(self) -> int:
        return int(self.width * self.dpr) * int(self.height * self.dpr)

    @property
    def aspect(self) -> float:
        return self.width / self.height if self.height else 1.0

    @property
    def mdhg(self) -> Tuple[int, str]:
        return mdhg_level_for(self.pixels)

    @property
    def device_class(self) -> str:
        return device_class_for(self.pixels)

    # ── coordinate mapping (the whole point) ─────────────────────────────────
    def to_logical(self, px: float, py: float) -> Tuple[float, float]:
        """Physical pixel -> logical [0,1]^2. Input events arrive here."""
        return (
            max(0.0, min(1.0, px / self.width if self.width else 0.0)),
            max(0.0, min(1.0, py / self.height if self.height else 0.0)),
        )

    def to_physical(self, lx: float, ly: float) -> Tuple[int, int]:
        """Logical [0,1]^2 -> physical pixel. Rendering leaves here."""
        return (int(round(lx * self.width)), int(round(ly * self.height)))

    def descriptor(self) -> Dict[str, Any]:
        level, name = self.mdhg
        return {
            "surface_id": self.surface_id,
            "width": self.width, "height": self.height, "dpr": self.dpr,
            "orientation": self.orientation, "color_depth": self.color_depth,
            "kind": self.kind, "pixels": self.pixels, "aspect": round(self.aspect, 4),
            "mdhg_level": level, "mdhg_name": name,
            "device_class": self.device_class,
            "input_caps": dict(self.input_caps),
        }

    def fingerprint(self) -> str:
        """Stable identity of the surface configuration (for Event Law keys)."""
        d = self.descriptor()
        d.pop("surface_id", None)
        canon = repr(sorted(d.items()))
        return hashlib.sha256(canon.encode()).hexdigest()[:16]


# ─── Surface registry ─────────────────────────────────────────────────────────

class SurfaceRegistry:
    """All live surfaces for one engine context. Resize/rotate = new descriptor
    + an event; history is kept so layout adaptation is replayable."""

    def __init__(self):
        self._surfaces: Dict[str, Surface] = {}
        self._history: List[Dict[str, Any]] = []

    def register(self, width: int, height: int, dpr: float = 1.0,
                 kind: str = "screen", surface_id: Optional[str] = None,
                 input_caps: Optional[Dict[str, bool]] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> Surface:
        sid = surface_id or f"srf-{uuid.uuid4().hex[:10]}"
        s = Surface(
            surface_id=sid, width=int(width), height=int(height), dpr=float(dpr),
            orientation="portrait" if height > width else "landscape",
            kind=kind,
            input_caps=input_caps or {"mouse": True, "touch": False,
                                      "stylus": False, "pressure": False},
            metadata=metadata or {},
        )
        self._surfaces[sid] = s
        self._history.append({"op": "register", "surface": s.descriptor(),
                              "fingerprint": s.fingerprint(), "ts": s.ts})
        return s

    def resize(self, surface_id: str, width: int, height: int,
               dpr: Optional[float] = None) -> Optional[Surface]:
        s = self._surfaces.get(surface_id)
        if s is None:
            return None
        s.width, s.height = int(width), int(height)
        if dpr is not None:
            s.dpr = float(dpr)
        s.orientation = "portrait" if s.height > s.width else "landscape"
        s.ts = time.time()
        self._history.append({"op": "resize", "surface": s.descriptor(),
                              "fingerprint": s.fingerprint(), "ts": s.ts})
        return s

    def get(self, surface_id: str) -> Optional[Surface]:
        return self._surfaces.get(surface_id)

    def all(self) -> List[Dict[str, Any]]:
        return [s.descriptor() for s in self._surfaces.values()]

    @property
    def count(self) -> int:
        return len(self._surfaces)

    def stats(self) -> Dict[str, Any]:
        by_class: Dict[str, int] = {}
        for s in self._surfaces.values():
            by_class[s.device_class] = by_class.get(s.device_class, 0) + 1
        return {"count": self.count, "by_class": by_class,
                "history_len": len(self._history)}
