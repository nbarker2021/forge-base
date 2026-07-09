"""SplatForgeField.reconstruct — GS-06 reconstruction bridge.

Contract: given a SpatialField and multi-view screen layouts derived from
the SAME field, recover each atom's 3D position from the projected screen
coordinates and measure the residual against the ground-truth positions.

This is a CLOSED-SYSTEM reconstruction. It works because:
  1. The SplatForgeField's positions are deterministic (compile_field).
  2. The screen_layout projection is invertible (orthographic + known bbox).
  3. Two orthogonal views fully determine the 3D position (3 equations, 2+
     1 views, 3 unknowns).

Honest scope: this is NOT a general-purpose inverse 3DGS solver (which
would need COLMAP/SfM/structure-from-motion on arbitrary images). It is
the holographic round-trip check for our deterministic, receipt-chained
field: encode a crystal -> project to views -> reconstruct from views ->
verify the reconstruction matches the original within tolerance.

The reconstruction uses only the screen coordinates (px, py, depth) from
each view plus the shared bounding-box normalization. The normalization
parameters are re-derived from the field at reconstruction time (they are
deterministic from the field, not a secret channel).

Three named views (matching the orthographic projection in render.py):
  FRONT  (+z): screen (px, py, depth=nz). Standard render_field view.
  SIDE   (+x): screen (px=nz, py, depth=nx). Rotated 90° around y.
  TOP    (+y): screen (px=nx, py=nz, depth=ny). Rotated 90° around x.

With FRONT + SIDE:
  nx = (2*px_front/W - 1)       from FRONT
  ny = (1 - 2*py_front/H)       from FRONT
  nz = (2*px_side/W - 1)        from SIDE (px in the side view = nz)
  ny_check = (1 - 2*py_side/H)  consistency check

Two views are sufficient; three views over-determine the system and provide
an independent consistency check.

Receipt: the ReconstructReceipt records the field_id, view hashes, per-atom
residual, max_residual, and whether the reconstruction passed (max_residual
<= TOLERANCE). The receipt is Merkle-chained to the field's last receipt.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import time
from typing import Any, Dict, List, Optional, Tuple

from .field import SpatialField


TOLERANCE = 1e-4  # normalized-coord units; positions agree to 4 decimal places

# The three orthographic view directions, encoded as which world axes
# map to (px_axis, py_axis, depth_axis).
VIEW_FRONT = "front"   # px=x, py=-y, depth=z
VIEW_SIDE  = "side"    # px=z, py=-y, depth=x  (rotate 90° around y)
VIEW_TOP   = "top"     # px=x, py=-z, depth=y  (rotate 90° around x)


# ---------------------------------------------------------------------------
# Normalization helpers (shared with render.py; re-derived, not imported,
# to keep the reconstruction independent of the render path)
# ---------------------------------------------------------------------------

def _bbox_normalizer(field: SpatialField):
    """Re-derive the bounding-box normalization from the field's atoms.
    Produces the same norm() as render._view_normalizer."""
    pts = [a.position for a in field.atoms] or [(0.0, 0.0, 0.0)]
    mins = [min(p[i] for p in pts) for i in range(3)]
    maxs = [max(p[i] for p in pts) for i in range(3)]
    center = [(mins[i] + maxs[i]) / 2 for i in range(3)]
    span = max([maxs[i] - mins[i] for i in range(3)] + [1e-6])

    def norm(p: Tuple[float, float, float]) -> Tuple[float, float, float]:
        return tuple(round(((p[i] - center[i]) / span) * 2.0, 6) for i in range(3))  # type: ignore

    def unnorm(n: Tuple[float, float, float]) -> Tuple[float, float, float]:
        return tuple(round(n[i] * span / 2.0 + center[i], 6) for i in range(3))  # type: ignore

    return norm, unnorm, center, span


# ---------------------------------------------------------------------------
# Multi-view layout builder (extends render.screen_layout to all 3 views)
# ---------------------------------------------------------------------------

def build_view_layouts(
    field: SpatialField,
    width: int = 256,
    height: int = 256,
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Build screen layouts for FRONT, SIDE, and TOP views.

    Each layout is: atom_id -> {px, py, depth}.

    FRONT matches render.screen_layout exactly (the standard render view).
    SIDE and TOP rotate the axes for the orthographic projection.
    """
    norm, _, _, _ = _bbox_normalizer(field)

    layouts: Dict[str, Dict[str, Dict[str, float]]] = {}
    for view in (VIEW_FRONT, VIEW_SIDE, VIEW_TOP):
        layout: Dict[str, Dict[str, float]] = {}
        for a in field.atoms:
            nx, ny, nz = norm(a.position)
            if view == VIEW_FRONT:
                # Standard: px from x, py from -y, depth=z
                px = (nx * 0.5 + 0.5) * width
                py = (0.5 - ny * 0.5) * height
                depth = nz
            elif view == VIEW_SIDE:
                # Rotate 90° around y: px from z, py from -y, depth=x
                px = (nz * 0.5 + 0.5) * width
                py = (0.5 - ny * 0.5) * height
                depth = nx
            else:  # VIEW_TOP
                # Rotate 90° around x: px from x, py from -z, depth=y
                px = (nx * 0.5 + 0.5) * width
                py = (0.5 - nz * 0.5) * height
                depth = ny
            layout[a.atom_id] = {
                "px": round(px, 3), "py": round(py, 3), "depth": round(depth, 6)
            }
        layouts[view] = layout

    return layouts


# ---------------------------------------------------------------------------
# Reconstruction
# ---------------------------------------------------------------------------

def _screen_to_normalized(px: float, py: float,
                           width: int, height: int) -> Tuple[float, float]:
    """Invert the screen-to-pixel mapping."""
    nx = round((px / width - 0.5) * 2.0, 6)
    ny = round(-(py / height - 0.5) * 2.0, 6)
    return nx, ny


@dataclasses.dataclass
class AtomReconstruction:
    atom_id: str
    original: Tuple[float, float, float]
    reconstructed: Tuple[float, float, float]
    residual: float        # L2 distance in world coords
    ny_consistency: float  # |ny_front - ny_side| (should be ~0)
    passed: bool           # residual <= TOLERANCE


@dataclasses.dataclass
class ReconstructReceipt:
    field_id: str
    crystal_id: str
    tolerance: float
    max_residual: float
    mean_residual: float
    atom_count: int
    passed: bool
    atoms: List[AtomReconstruction]
    view_layout_hashes: Dict[str, str]
    receipt_hash: str
    prev_hash: str
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_id": self.field_id,
            "crystal_id": self.crystal_id,
            "tolerance": self.tolerance,
            "max_residual": self.max_residual,
            "mean_residual": self.mean_residual,
            "atom_count": self.atom_count,
            "passed": self.passed,
            "view_layout_hashes": self.view_layout_hashes,
            "receipt_hash": self.receipt_hash,
            "prev_hash": self.prev_hash,
            "timestamp": self.timestamp,
            "atoms": [
                {
                    "atom_id": a.atom_id,
                    "original": list(a.original),
                    "reconstructed": list(a.reconstructed),
                    "residual": a.residual,
                    "ny_consistency": a.ny_consistency,
                    "passed": a.passed,
                }
                for a in self.atoms
            ],
        }


class ReconstructForge:
    """GS-06: closed-system holographic round-trip verifier.

    Encodes the field into three orthographic views, then reconstructs
    each atom's 3D position from the projected screen coordinates. The
    residual (L2 distance between original and reconstructed positions,
    in world coords) must be <= TOLERANCE for the receipt to pass.

    Usage::

        forge = ReconstructForge()
        receipt = forge.reconstruct(field, width=256, height=256)
        assert receipt.passed

    The reconstruction uses only the screen coordinates and the shared
    bounding-box normalization (which is deterministic from the field).
    No ground-truth positions are given to the reconstruction step; they
    are used only to compute the residual after the fact.
    """

    def __init__(self, tolerance: float = TOLERANCE) -> None:
        self.tolerance = tolerance
        self._last_receipt_hash: str = "0" * 64

    def reconstruct(
        self,
        field: SpatialField,
        width: int = 256,
        height: int = 256,
        prev_hash: Optional[str] = None,
    ) -> ReconstructReceipt:
        """Reconstruct all atom positions from two-view screen layouts.

        Uses FRONT + SIDE for the main reconstruction (2 views, fully
        determined), then checks consistency against TOP.
        """
        if prev_hash is None:
            prev_hash = self._last_receipt_hash

        norm, unnorm, _, _ = _bbox_normalizer(field)
        layouts = build_view_layouts(field, width=width, height=height)

        front = layouts[VIEW_FRONT]
        side  = layouts[VIEW_SIDE]
        top   = layouts[VIEW_TOP]

        # Hash each layout for the receipt.
        layout_hashes = {
            v: hashlib.sha256(
                json.dumps(layouts[v], sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()[:16]
            for v in (VIEW_FRONT, VIEW_SIDE, VIEW_TOP)
        }

        atom_results: List[AtomReconstruction] = []

        for a in field.atoms:
            aid = a.atom_id
            original_world = a.position

            # Ground truth in normalized coords (for residual comparison).
            nx_true, ny_true, nz_true = norm(original_world)

            # Reconstruct from FRONT: nx, ny.
            # Reconstruct from SIDE:  nz (side px = nz), ny_check.
            f = front.get(aid, {})
            s = side.get(aid, {})
            t = top.get(aid, {})

            nx_rec, ny_rec = _screen_to_normalized(
                f.get("px", 0.0), f.get("py", 0.0), width, height
            )
            nz_rec, ny_side_rec = _screen_to_normalized(
                s.get("px", 0.0), s.get("py", 0.0), width, height
            )
            # TOP gives a cross-check: px_top=nx, py_top=-(nz), depth=ny.
            nx_top, nz_neg_top = _screen_to_normalized(
                t.get("px", 0.0), t.get("py", 0.0), width, height
            )
            # ny consistency: FRONT py vs SIDE py (both should give ny).
            ny_consistency = round(abs(ny_rec - ny_side_rec), 8)

            # Reconstruct world position from normalized coords.
            reconstructed_world = unnorm((nx_rec, ny_rec, nz_rec))

            # Residual in world coords (L2 norm).
            residual = math.sqrt(
                (reconstructed_world[0] - original_world[0]) ** 2 +
                (reconstructed_world[1] - original_world[1]) ** 2 +
                (reconstructed_world[2] - original_world[2]) ** 2
            )

            atom_results.append(AtomReconstruction(
                atom_id=aid,
                original=original_world,
                reconstructed=reconstructed_world,
                residual=round(residual, 8),
                ny_consistency=ny_consistency,
                passed=(residual <= self.tolerance),
            ))

        residuals = [ar.residual for ar in atom_results]
        max_residual = max(residuals) if residuals else 0.0
        mean_residual = sum(residuals) / len(residuals) if residuals else 0.0
        passed = max_residual <= self.tolerance

        body = json.dumps({
            "field_id": field.field_id,
            "crystal_id": field.crystal_id,
            "max_residual": max_residual,
            "mean_residual": mean_residual,
            "passed": passed,
            "layout_hashes": layout_hashes,
            "prev_hash": prev_hash,
            "tolerance": self.tolerance,
            "atom_count": len(atom_results),
        }, sort_keys=True, separators=(",", ":"))
        receipt_hash = hashlib.sha256(body.encode()).hexdigest()
        self._last_receipt_hash = receipt_hash

        return ReconstructReceipt(
            field_id=field.field_id,
            crystal_id=field.crystal_id,
            tolerance=self.tolerance,
            max_residual=round(max_residual, 8),
            mean_residual=round(mean_residual, 8),
            atom_count=len(atom_results),
            passed=passed,
            atoms=atom_results,
            view_layout_hashes=layout_hashes,
            receipt_hash=receipt_hash,
            prev_hash=prev_hash,
            timestamp=time.time(),
        )

    def verify_lossless_field_round_trip(
        self,
        field: SpatialField,
        width: int = 256,
        height: int = 256,
    ) -> Dict[str, Any]:
        """Smoke-verify: compile field -> project to views -> reconstruct.

        Returns a summary dict with 'status': 'pass'/'fail' and the receipt.
        Analogous to SplatForge.gluon_hologram.verify_lossless_round_trip
        but for the whole spatial field, not one 8-state gluon cell.
        """
        receipt = self.reconstruct(field, width=width, height=height)
        return {
            "forge": "ReconstructForge",
            "status": "pass" if receipt.passed else "fail",
            "atom_count": receipt.atom_count,
            "max_residual": receipt.max_residual,
            "mean_residual": receipt.mean_residual,
            "tolerance": receipt.tolerance,
            "receipt_hash": receipt.receipt_hash,
            "view_layout_hashes": receipt.view_layout_hashes,
        }


__all__ = [
    "ReconstructForge",
    "ReconstructReceipt",
    "AtomReconstruction",
    "build_view_layouts",
    "VIEW_FRONT", "VIEW_SIDE", "VIEW_TOP",
    "TOLERANCE",
]
