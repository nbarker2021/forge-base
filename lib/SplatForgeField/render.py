"""SplatForgeField.render — WP-03 CPU reference render core.

Turns a SpatialField into (a) a real, deterministic rendered frame via the
existing SplatForge CPU rasterizer, and (b) an explicit screen layout + pick
function for selection (the ID-buffer the desktop GUI consumes). No GPU, no
window: this is the headless-verifiable foundation the trackball app wraps.

Composition (no new rasterizer):
  - field splats are normalized into a [-1,1] view box (shared by render and
    pick so selection lines up with what is drawn), then
  - SplatForge.raster.render_pass does the actual rasterization + frame receipt.

The render uses SplatForge's perspective camera; the pick uses the shared
orthographic normalization. For v0.1 these agree closely; exact camera
reconciliation is the GUI integration step (WP-03 GUI).
"""
from __future__ import annotations

import dataclasses
from typing import Any, Dict, Optional, Tuple

from SplatForge.raster import render_pass
from .field import SpatialField


def _view_normalizer(field: SpatialField):
    """Return a function mapping a 3D world position into a [-1,1]^3 view box,
    deterministic from the field's own bounding box."""
    pts = [a.position for a in field.atoms] or [(0.0, 0.0, 0.0)]
    mins = [min(p[i] for p in pts) for i in range(3)]
    maxs = [max(p[i] for p in pts) for i in range(3)]
    center = [(mins[i] + maxs[i]) / 2 for i in range(3)]
    span = max([maxs[i] - mins[i] for i in range(3)] + [1e-6])

    def norm(p: Tuple[float, float, float]) -> Tuple[float, float, float]:
        return tuple(round(((p[i] - center[i]) / span) * 2.0, 6) for i in range(3))  # type: ignore[return-value]

    return norm


def render_field(field: SpatialField, width: int = 256, height: int = 256,
                 backend: str = "cpu_reference") -> Dict[str, Any]:
    """Render the field to one deterministic frame. Same field -> same
    frame_hash. Returns the frame receipt plus the Picture object."""
    norm = _view_normalizer(field)
    render_splats = [dataclasses.replace(s, mean_position=norm(s.mean_position))
                     for s in field.splats]
    pic, frame_receipt, _stream = render_pass(render_splats, width, height, backend=backend)
    return {
        "field_id": field.field_id,
        "crystal_id": field.crystal_id,
        "frame_hash": frame_receipt["frame_hash"],
        "width": width, "height": height,
        "splat_count": frame_receipt["splat_count"],
        "genesis_correction_density": frame_receipt.get("genesis_correction_density"),
        "backend": backend,
        "picture": pic,
        "frame_receipt": frame_receipt,
    }


def screen_layout(field: SpatialField, width: int = 256, height: int = 256) -> Dict[str, Dict[str, float]]:
    """Deterministic atom_id -> screen (px, py, depth) map, sharing the render
    normalization. This is the ID-buffer the GUI uses for picking."""
    norm = _view_normalizer(field)
    layout: Dict[str, Dict[str, float]] = {}
    for a in field.atoms:
        nx, ny, nz = norm(a.position)
        px = (nx * 0.5 + 0.5) * width
        py = (0.5 - ny * 0.5) * height
        layout[a.atom_id] = {"px": round(px, 3), "py": round(py, 3), "depth": round(nz, 6)}
    return layout


def pick(layout: Dict[str, Dict[str, float]], px: float, py: float) -> Optional[str]:
    """Return the atom_id nearest to (px, py), or None if the layout is empty.
    Ties broken deterministically by atom_id."""
    best: Optional[str] = None
    best_d = float("inf")
    for atom_id in sorted(layout):
        s = layout[atom_id]
        d = (s["px"] - px) ** 2 + (s["py"] - py) ** 2
        if d < best_d:
            best_d = d
            best = atom_id
    return best
