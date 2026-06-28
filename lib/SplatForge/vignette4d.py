"""
SplatForge.vignette4d — the 4D-vignette consumer.

TileInstance (3D, from .tiling) + a named 4th coordinate + a required
moderation/physics state -> GaussianSplatInstance, via
PixelForge.blotlift's 8D moderation-layer lift (R^4 (+) R^4 = R^8, the
D4+D4-in-E8 sublattice embedding; see blotlift.py's docstring for the
algebraic grounding).

Scope honesty: this is GS-07's (4D vignette playback) CPU-side
algebraic-mapping prerequisite, not GS-07 itself. It produces one projected
splat per (tile, extra-coordinate sample), deterministically, on CPU. It
does not play a 4D scene back over time/phase/depth/energy on a GPU, and it
does not discharge VignetteState.reconstruction_test's obligation — that is
a declared *test name/procedure* the caller must still supply and actually
run; this module only refuses to construct a spatial_dimension==4
VignetteState that leaves it null, mirroring
vignette_state.schema.json's own description for that field.

Division of responsibility: PixelForge.blotlift is a generic 4D->8D->3D
linear map with no opinion about what the two 4-vectors mean. This module
supplies the GBS-specific opinion — vector one is
(tile.position, named_extra_coordinate value); vector two is a
caller-supplied physics/observer moderation state, tagged with a
physics_state_id that flows straight into GaussianSplatInstance's
previously-always-null physics_state_id field.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from PixelForge.blotlift import project_blot4d

from .compiler import GaussianSplatInstance, _PALETTE, _stable_hash
from .tiling import TileInstance, generate_tile_instances

Vec4 = Tuple[float, float, float, float]
Mat4 = Tuple[Vec4, Vec4, Vec4, Vec4]


def _diag4(values: Tuple[float, float, float, float]) -> Mat4:
    """4x4 diagonal covariance from 4 independent-axis variances."""
    rows = []
    for i in range(4):
        row = [0.0, 0.0, 0.0, 0.0]
        row[i] = float(values[i])
        rows.append(tuple(row))
    return tuple(rows)  # type: ignore[return-value]


@dataclass(frozen=True)
class VignetteState:
    """Mirrors ecology/schemas/vignette_state.schema.json."""

    vignette_state_id: str
    spatial_dimension: int
    slicing_projection: str
    observer_window_id: str
    named_extra_coordinate: Optional[str] = None
    camera: Optional[Dict] = None
    filters: Tuple[str, ...] = ()
    chart_binding: Optional[str] = None
    simulation_binding: Optional[str] = None
    reconstruction_test: Optional[str] = None

    def __post_init__(self) -> None:
        if not (1 <= self.spatial_dimension <= 4):
            raise ValueError("spatial_dimension must be in 1..4")
        if self.spatial_dimension == 4:
            if not self.named_extra_coordinate:
                raise ValueError(
                    "a spatial_dimension==4 VignetteState requires "
                    "named_extra_coordinate (what the 4th axis means)"
                )
            if not self.reconstruction_test:
                raise ValueError(
                    "a spatial_dimension==4 VignetteState requires a non-null "
                    "reconstruction_test, per vignette_state.schema.json's own "
                    "description for that field"
                )

    def to_dict(self) -> Dict:
        return {
            "vignette_state_id": self.vignette_state_id,
            "spatial_dimension": self.spatial_dimension,
            "named_extra_coordinate": self.named_extra_coordinate,
            "slicing_projection": self.slicing_projection,
            "camera": self.camera,
            "filters": list(self.filters),
            "chart_binding": self.chart_binding,
            "simulation_binding": self.simulation_binding,
            "observer_window_id": self.observer_window_id,
            "reconstruction_test": self.reconstruction_test,
        }


def compile_tile_to_4d_splat(
    tile: TileInstance,
    extra_coordinate_value: float,
    extra_coordinate_variance: float,
    moderation_state4: Vec4,
    moderation_variance4: Vec4,
    physics_state_id: str,
    vignette: VignetteState,
    spatial_variance3: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    tile_family_rgb: Optional[Tuple[float, float, float]] = None,
    projection_kind: str = "standard",
) -> GaussianSplatInstance:
    """One TileInstance + one 4th-coordinate sample -> one GaussianSplatInstance,
    lifted through PixelForge.blotlift's 8D moderation layer."""
    if vignette.spatial_dimension != 4:
        raise ValueError(
            f"compile_tile_to_4d_splat requires a spatial_dimension==4 "
            f"VignetteState, got {vignette.spatial_dimension}"
        )

    mean4 = (tile.position[0], tile.position[1], tile.position[2], float(extra_coordinate_value))
    cov4 = _diag4((spatial_variance3[0], spatial_variance3[1], spatial_variance3[2],
                   float(extra_coordinate_variance)))
    mod_mean4 = tuple(float(v) for v in moderation_state4)
    mod_cov4 = _diag4(tuple(float(v) for v in moderation_variance4))

    record = project_blot4d(mean4, cov4, mod_mean4, mod_cov4, kind=projection_kind)

    rgb = tile_family_rgb if tile_family_rgb is not None else _PALETTE.get(
        tile.tile_family_id, (0.5, 0.5, 0.5)
    )

    return GaussianSplatInstance(
        splat_id=f"splat4d:{tile.tile_instance_id}:{vignette.vignette_state_id}",
        source_class="DD",
        source_asset_id=tile.tile_family_id,
        mean_position=tuple(record["p3"]),
        covariance_or_scale=tuple(record["covariance_diag_3d"]),
        opacity=1.0,
        appearance_coefficients=rgb,
        tile_instance_id=tile.tile_instance_id,
        vignette_state_id=vignette.vignette_state_id,
        observer_window_id=vignette.observer_window_id,
        physics_state_id=physics_state_id,
    )


def compile_family_to_4d_splats(
    crystal_id: str,
    extent: Tuple[int, int, int],
    vignette: VignetteState,
    extra_coordinate_fn: Callable[[TileInstance], Tuple[float, float]],
    moderation_state4: Vec4,
    moderation_variance4: Vec4,
    physics_state_id: str,
    spatial_variance3: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    projection_kind: str = "standard",
) -> List[GaussianSplatInstance]:
    """Bulk form of compile_tile_to_4d_splat over one crystal family's tiles.

    extra_coordinate_fn(tile) -> (value, variance) lets the caller decide
    what the named 4th axis means per tile (a time/phase/depth/energy
    function of tile position, or a constant) — this module makes no
    physics assumption of its own, mirroring blotlift's own no-default rule.
    """
    tiles = generate_tile_instances(crystal_id, extent)
    splats: List[GaussianSplatInstance] = []
    for tile in tiles:
        value, variance = extra_coordinate_fn(tile)
        splats.append(compile_tile_to_4d_splat(
            tile, value, variance, moderation_state4, moderation_variance4,
            physics_state_id, vignette,
            spatial_variance3=spatial_variance3, projection_kind=projection_kind,
        ))
    return splats


def compile_family_to_4d_splats_and_hash(
    crystal_id: str,
    extent: Tuple[int, int, int],
    vignette: VignetteState,
    extra_coordinate_fn: Callable[[TileInstance], Tuple[float, float]],
    moderation_state4: Vec4,
    moderation_variance4: Vec4,
    physics_state_id: str,
    spatial_variance3: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    projection_kind: str = "standard",
) -> Tuple[List[GaussianSplatInstance], str, str]:
    """Same contract as TileToSplatCompiler.compile_and_hash: returns
    (splats, input_hash, output_hash) for receipt minting."""
    splats = compile_family_to_4d_splats(
        crystal_id, extent, vignette, extra_coordinate_fn,
        moderation_state4, moderation_variance4, physics_state_id,
        spatial_variance3=spatial_variance3, projection_kind=projection_kind,
    )
    input_hash = _stable_hash({
        "crystal_id": crystal_id, "extent": list(extent),
        "vignette": vignette.to_dict(),
        "moderation_state4": list(moderation_state4),
        "moderation_variance4": list(moderation_variance4),
        "physics_state_id": physics_state_id,
        "spatial_variance3": list(spatial_variance3),
        "projection_kind": projection_kind,
    })
    output_hash = _stable_hash([s.to_dict() for s in splats])
    return splats, input_hash, output_hash
