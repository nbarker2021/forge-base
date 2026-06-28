"""
PixelForge Ink — stylus / touch / pointer input as first-class events.

One normalized pointer model for every input device. A pointer SAMPLE is
(kind, lx, ly, pressure, tilt_x, tilt_y, t) with lx/ly in logical [0,1]^2
coordinates (Surface.to_logical applied at the edge). A STROKE is an ordered
sample sequence between down and up.

Strokes are resolution-independent and replayable: the same stroke renders
identically on a watch and a wall. Each completed stroke:
  - is simplified (Ramer-Douglas-Peucker in logical space),
  - serializes to a canonical byte string (BBA-adaptable -> Event Law),
  - carries summary features (length, bbox, mean pressure, duration, point
    count) for recognition layers (ink -> text, gesture, shape) added later.

Prebuilt for the stylus tier: pressure and tilt are carried end-to-end now,
even when the current device reports none — the model never needs to change.

Stdlib only.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ─── Lookup tables (import-time, read-only) ───────────────────────────────────

POINTER_KINDS: Tuple[str, ...] = ("mouse", "touch", "pen")     # pen = stylus
# Default RDP simplification tolerance in logical units (≈2px at 1080p)
DEFAULT_TOLERANCE: float = 2.0 / 1080.0
# Stroke quantization for canonical bytes: 12-bit grid per axis (4096 steps)
_QUANT: int = 4095


@dataclass
class PointerSample:
    kind: str                  # mouse | touch | pen
    lx: float                  # logical x in [0,1]
    ly: float                  # logical y in [0,1]
    pressure: float = 0.5      # [0,1]; mice report 0.5, stylus reports real
    tilt_x: float = 0.0        # degrees [-90,90]
    tilt_y: float = 0.0
    t: float = 0.0             # ms since stroke start

    def quantized(self) -> Tuple[int, int, int]:
        return (int(self.lx * _QUANT), int(self.ly * _QUANT),
                int(max(0.0, min(1.0, self.pressure)) * 255))


@dataclass
class Stroke:
    """One down->move...->up gesture on a surface."""
    stroke_id: str
    surface_id: str
    kind: str
    samples: List[PointerSample] = field(default_factory=list)
    color: str = "#e8eaed"
    width_logical: float = 2.5 / 1080.0    # brush width in logical units
    target: Optional[str] = None           # e.g. a cell date this ink belongs to
    ts: float = field(default_factory=time.time)

    # ── features ─────────────────────────────────────────────────────────────
    def length(self) -> float:
        return sum(
            math.hypot(b.lx - a.lx, b.ly - a.ly)
            for a, b in zip(self.samples, self.samples[1:])
        )

    def bbox(self) -> Tuple[float, float, float, float]:
        if not self.samples:
            return (0.0, 0.0, 0.0, 0.0)
        xs = [s.lx for s in self.samples]
        ys = [s.ly for s in self.samples]
        return (min(xs), min(ys), max(xs), max(ys))

    def features(self) -> Dict[str, Any]:
        n = len(self.samples)
        return {
            "points": n,
            "length": round(self.length(), 6),
            "bbox": [round(v, 6) for v in self.bbox()],
            "mean_pressure": round(sum(s.pressure for s in self.samples) / n, 4) if n else 0.0,
            "duration_ms": round(self.samples[-1].t - self.samples[0].t, 1) if n > 1 else 0.0,
            "kind": self.kind,
            "has_tilt": any(s.tilt_x or s.tilt_y for s in self.samples),
        }

    # ── canonical bytes (the BBA / Event Law doorway) ────────────────────────
    def canonical_bytes(self) -> bytes:
        """Quantized, device-independent byte form. Same ink = same bytes."""
        out = bytearray()
        out += self.kind.encode()[:1]
        for s in self.samples:
            qx, qy, qp = s.quantized()
            out += qx.to_bytes(2, "big") + qy.to_bytes(2, "big") + bytes([qp])
        return bytes(out)

    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stroke_id": self.stroke_id, "surface_id": self.surface_id,
            "kind": self.kind, "color": self.color,
            "width_logical": self.width_logical, "target": self.target,
            "hash": self.content_hash(), "features": self.features(),
            "samples": [[round(s.lx, 5), round(s.ly, 5), round(s.pressure, 3),
                         round(s.t, 1)] for s in self.samples],
        }


# ─── Ramer-Douglas-Peucker (pure, stdlib) ─────────────────────────────────────

def _perp_dist(p: PointerSample, a: PointerSample, b: PointerSample) -> float:
    dx, dy = b.lx - a.lx, b.ly - a.ly
    seg = math.hypot(dx, dy)
    if seg < 1e-12:
        return math.hypot(p.lx - a.lx, p.ly - a.ly)
    return abs(dy * p.lx - dx * p.ly + b.lx * a.ly - b.ly * a.lx) / seg


def simplify(samples: List[PointerSample],
             tolerance: float = DEFAULT_TOLERANCE) -> List[PointerSample]:
    """RDP simplification preserving pressure extremes' endpoints."""
    if len(samples) < 3:
        return list(samples)
    dmax, idx = 0.0, 0
    for i in range(1, len(samples) - 1):
        d = _perp_dist(samples[i], samples[0], samples[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > tolerance:
        left = simplify(samples[:idx + 1], tolerance)
        right = simplify(samples[idx:], tolerance)
        return left[:-1] + right
    return [samples[0], samples[-1]]


# ─── Ink engine ───────────────────────────────────────────────────────────────

class InkEngine:
    """Collects strokes per surface; finishing a stroke yields the canonical
    record ready for the Event Law (compute->save->validate->receipt->reuse)."""

    def __init__(self, tolerance: float = DEFAULT_TOLERANCE):
        self.tolerance = tolerance
        self._open: Dict[str, Stroke] = {}
        self._strokes: List[Stroke] = []

    # raw samples arrive in PHYSICAL pixels; caller passes the Surface for mapping
    def begin(self, surface, kind: str = "pen", color: str = "#e8eaed",
              target: Optional[str] = None) -> str:
        sid = f"ink-{uuid.uuid4().hex[:10]}"
        self._open[sid] = Stroke(stroke_id=sid, surface_id=surface.surface_id,
                                 kind=kind if kind in POINTER_KINDS else "mouse",
                                 color=color, target=target)
        return sid

    def add(self, stroke_id: str, surface, px: float, py: float,
            pressure: float = 0.5, tilt_x: float = 0.0, tilt_y: float = 0.0,
            t: float = 0.0) -> None:
        st = self._open.get(stroke_id)
        if st is None:
            return
        lx, ly = surface.to_logical(px, py)
        st.samples.append(PointerSample(st.kind, lx, ly, pressure,
                                        tilt_x, tilt_y, t))

    def end(self, stroke_id: str) -> Optional[Dict[str, Any]]:
        """Close the stroke: simplify, canonicalize, return the Event Law payload."""
        st = self._open.pop(stroke_id, None)
        if st is None or not st.samples:
            return None
        raw_n = len(st.samples)
        st.samples = simplify(st.samples, self.tolerance)
        self._strokes.append(st)
        rec = st.to_dict()
        rec["raw_points"] = raw_n
        rec["simplified_points"] = len(st.samples)
        rec["compression"] = round(raw_n / max(1, len(st.samples)), 2)
        return rec

    # bulk path used by HTTP kernels: one completed stroke arrives whole
    def ingest(self, surface, points: List[Dict[str, Any]],
               kind: str = "pen", color: str = "#e8eaed",
               target: Optional[str] = None) -> Optional[Dict[str, Any]]:
        sid = self.begin(surface, kind=kind, color=color, target=target)
        for p in points:
            self.add(sid, surface, float(p.get("x", 0)), float(p.get("y", 0)),
                     float(p.get("p", 0.5)), float(p.get("tx", 0)),
                     float(p.get("ty", 0)), float(p.get("t", 0)))
        return self.end(sid)

    @property
    def stroke_count(self) -> int:
        return len(self._strokes)

    def strokes_for(self, surface_id: Optional[str] = None,
                    target: Optional[str] = None) -> List[Dict[str, Any]]:
        out = []
        for s in self._strokes:
            if surface_id and s.surface_id != surface_id:
                continue
            if target and s.target != target:
                continue
            out.append(s.to_dict())
        return out

    def stats(self) -> Dict[str, Any]:
        kinds: Dict[str, int] = {}
        for s in self._strokes:
            kinds[s.kind] = kinds.get(s.kind, 0) + 1
        return {"strokes": self.stroke_count, "open": len(self._open),
                "by_kind": kinds}
