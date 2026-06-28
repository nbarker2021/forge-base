"""
PixelForge Projection — E8 -> 3D -> screen mapping (stripped donor renderer).

The donor generative-video engine ("Scene8") projects E8 lattice states to
3D via four projection families and rasterizes to pixels. This module is the
stdlib-only strip of that projection core: the four projection matrices are
import-time lookup tables; projecting is three dot products; screen mapping
lands in logical [0,1]^2 so any Surface can realize it at its own resolution.

This is the bridge to GraphStax: a pixel addressed at (surface, lx, ly) with
an E8 state is exactly a Stax identity — the pixel IS a C on its sheet size.

Governance carried per projected state (donor-faithful):
  digital_root, parity, entropy — the DR/parity/DeltaPhi channels the video
  layer (frame.py) uses for frame-transition legality.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

# ─── Projection matrices (import-time lookup tables, donor-faithful) ─────────

_PHI: float = (1.0 + math.sqrt(5.0)) / 2.0
_S2: float = 1.0 / math.sqrt(2.0)

def _norm_rows(m: List[List[float]]) -> Tuple[Tuple[float, ...], ...]:
    out = []
    for row in m:
        n = math.sqrt(sum(v * v for v in row)) or 1.0
        out.append(tuple(v / n for v in row))
    return tuple(out)

PROJECTIONS: Dict[str, Tuple[Tuple[float, ...], ...]] = {
    # take first 3 dims
    "standard": (
        (1, 0, 0, 0, 0, 0, 0, 0),
        (0, 1, 0, 0, 0, 0, 0, 0),
        (0, 0, 1, 0, 0, 0, 0, 0),
    ),
    # Hopf-fibration-inspired (quaternionic head)
    "hopf": _norm_rows([
        [1, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0],
    ]),
    # Coxeter-plane flavored (golden ratio)
    "coxeter": _norm_rows([
        [1, 0, 0, 0, 0, 0, 0, 0],
        [0, math.cos(math.pi / 5), math.sin(math.pi / 5), 0, 0, 0, 0, 0],
        [0, 0, _PHI, 1.0 / _PHI, 0, 0, 0, 0],
    ]),
    # orthographic pair-sum
    "orthographic": (
        (_S2, _S2, 0, 0, 0, 0, 0, 0),
        (0, 0, _S2, _S2, 0, 0, 0, 0),
        (0, 0, 0, 0, _S2, _S2, 0, 0),
    ),
}

PROJECTION_NAMES: Tuple[str, ...] = tuple(PROJECTIONS.keys())


# ─── Governance scalars (donor-faithful, stdlib) ──────────────────────────────

def digital_root(x: float) -> int:
    n = int(abs(round(x)))
    return 9 if n and n % 9 == 0 else n % 9 if n else 0


def parity(vec: Sequence[float]) -> int:
    """Even/odd channel: parity of the rounded coordinate sum."""
    return int(abs(round(sum(vec)))) & 1


def entropy(vec: Sequence[float]) -> float:
    """Shannon entropy of the normalized absolute components."""
    total = sum(abs(v) for v in vec)
    if total <= 0:
        return 0.0
    h = 0.0
    for v in vec:
        p = abs(v) / total
        if p > 1e-12:
            h -= p * math.log2(p)
    return round(h, 6)


# ─── Projection ───────────────────────────────────────────────────────────────

def project(e8: Sequence[float], kind: str = "standard") -> Tuple[float, float, float]:
    """E8 (8,) -> 3D via lookup matrix. O(1)."""
    m = PROJECTIONS.get(kind, PROJECTIONS["standard"])
    v = list(e8[:8]) + [0.0] * max(0, 8 - len(e8))
    return tuple(sum(m[r][c] * v[c] for c in range(8)) for r in range(3))  # type: ignore


def to_screen(p3: Sequence[float], scale: float = 0.25,
              depth_cam: float = 5.0) -> Tuple[float, float, float]:
    """3D -> logical screen [0,1]^2 + depth, simple perspective at z-camera."""
    x, y, z = p3[0], p3[1], p3[2]
    w = depth_cam / max(0.1, depth_cam - z)
    lx = 0.5 + x * scale * w
    ly = 0.5 - y * scale * w
    return (max(0.0, min(1.0, lx)), max(0.0, min(1.0, ly)), z)


def project_state(e8: Sequence[float], kind: str = "standard") -> Dict[str, object]:
    """Full projected record: 3D, logical screen point, governance scalars.
    This record is BBA-adaptable and is the unit the frame layer consumes."""
    p3 = project(e8, kind)
    lx, ly, depth = to_screen(p3)
    return {
        "e8": [round(v, 6) for v in list(e8[:8])],
        "p3": [round(v, 6) for v in p3],
        "screen": [round(lx, 6), round(ly, 6)],
        "depth": round(depth, 6),
        "projection": kind if kind in PROJECTIONS else "standard",
        "digital_root": digital_root(sum(e8)),
        "parity": parity(e8),
        "entropy": entropy(e8),
    }
