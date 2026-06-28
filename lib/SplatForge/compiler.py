"""
SplatForge.compiler — the CPU reference Tile-to-Splat Compiler.

Deterministic TileInstance[] -> GaussianSplatInstance[] compilation, per
CQECMPLX_Tile_Physics_Graphics_Engine_Workplan_v1_1_3DGS.md's GS-02
workstream and its "Mandatory build order": a CPU reference compiler with
golden fixtures comes before any GPU renderer. No GPU/Vulkan/D3D12/CUDA
dependency anywhere in this module.

This compiles GBS (Gaussian Blot Spatter) mode only: tile -> splat, with
source_class "DD" (internally derived) throughout, never ED/ID (those are
for imported photo/video/SfM scenes — out of scope here, see GS-01).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .tiling import TileInstance, build_tile_family_asset, generate_tile_instances

ADAPTER_ID = "SplatForge.compiler.TileToSplatCompiler"
ADAPTER_VERSION = "0.1.0"

# Scientific-mode declared palette: one flat RGB per family, deterministic.
# Per the workplan's Material-mode rule ("declared mapping; no unproven
# material claim") this is cosmetic only — it is not a claim about any real
# material's optical appearance.
_PALETTE: Dict[str, Tuple[float, float, float]] = {
    "SquareTile": (0.70, 0.70, 0.70), "HexagonTile": (0.55, 0.70, 0.85),
    "FCCTile": (0.85, 0.55, 0.30), "BCCTile": (0.40, 0.55, 0.85),
    "HCPTile": (0.55, 0.85, 0.55), "DiamondTile": (0.90, 0.90, 0.95),
    "GrapheneTile": (0.20, 0.20, 0.20), "KagomeTile": (0.85, 0.30, 0.55),
    "PyrochloreTile": (0.65, 0.40, 0.80),
}

SPLAT_SCALE_FRACTION = 0.25  # isotropic splat radius, as a fraction of nn distance


@dataclass(frozen=True)
class GaussianSplatInstance:
    """Mirrors ecology/schemas/gaussian_splat_instance.schema.json."""

    splat_id: str
    source_class: str
    source_asset_id: str
    mean_position: Tuple[float, float, float]
    covariance_or_scale: Tuple[float, float, float]
    opacity: float
    appearance_coefficients: Tuple[float, float, float]
    tile_instance_id: str
    vignette_state_id: str
    observer_window_id: str
    receipt_id: str = ""
    physics_state_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "splat_id": self.splat_id,
            "source_class": self.source_class,
            "source_asset_id": self.source_asset_id,
            "adapter_id": ADAPTER_ID,
            "adapter_version": ADAPTER_VERSION,
            "mean_position": list(self.mean_position),
            "covariance_or_scale": list(self.covariance_or_scale),
            "orientation": [0.0, 0.0, 0.0, 1.0],
            "opacity": self.opacity,
            "appearance_coefficients": list(self.appearance_coefficients),
            "tile_instance_id": self.tile_instance_id,
            "lattice_state_id": None,
            "physics_state_id": self.physics_state_id,
            "LCR_window_id": None,
            "observer_window_id": self.observer_window_id,
            "vignette_state_id": self.vignette_state_id,
            "material_channels": {"mode": "scientific"},
            "receipt_id": self.receipt_id,
            "backend_agnostic_flags": {"cpu_reference": True, "gpu_status": "not_built"},
        }


def _stable_hash(obj) -> str:
    body = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


class TileToSplatCompiler:
    """Deterministic compiler: the same (crystal_id, extent) always produces
    the same splat buffer, byte-for-byte — this is what the golden fixtures
    pin down (the workplan's Reproducibility success criterion)."""

    def compile(
        self,
        crystal_id: str,
        extent: Tuple[int, int, int] = (2, 2, 2),
        vignette_state_id: str = "vignette.default.3d",
        observer_window_id: str = "observer.default",
    ) -> List[GaussianSplatInstance]:
        family = build_tile_family_asset(crystal_id)
        tiles: List[TileInstance] = generate_tile_instances(crystal_id, extent)
        scale = family.nearest_neighbor_distance * SPLAT_SCALE_FRACTION
        rgb = _PALETTE.get(family.tile_family_id, (0.5, 0.5, 0.5))

        splats: List[GaussianSplatInstance] = []
        for tile in tiles:
            splats.append(GaussianSplatInstance(
                splat_id=f"splat:{tile.tile_instance_id}",
                source_class="DD",
                source_asset_id=crystal_id,
                mean_position=tile.position,
                covariance_or_scale=(scale, scale, scale),
                opacity=1.0,
                appearance_coefficients=rgb,
                tile_instance_id=tile.tile_instance_id,
                vignette_state_id=vignette_state_id,
                observer_window_id=observer_window_id,
            ))
        return splats

    def compile_and_hash(
        self, crystal_id: str, extent: Tuple[int, int, int] = (2, 2, 2)
    ) -> Tuple[List[GaussianSplatInstance], str, str]:
        """Returns (splats, input_hash, output_hash) for receipt minting.
        Hashes are computed before any receipt_id is stamped, so they only
        ever reflect the compiler's own deterministic output."""
        splats = self.compile(crystal_id, extent)
        input_hash = _stable_hash({"crystal_id": crystal_id, "extent": list(extent)})
        output_hash = _stable_hash([s.to_dict() for s in splats])
        return splats, input_hash, output_hash
