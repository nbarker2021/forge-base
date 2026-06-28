"""
SplatForge.physics_binding — GS-04: bind declared simulation state to
splats, graph overlays, trajectories, and residuals, without the renderer
ever mutating anything.

Scope deliberately minimal, matching the work order's own wording exactly:
"bind DECLARED simulation states to splats... without render-driven
mutation" — not "compute" or "simulate" them. A PhysicsState is always
caller-supplied data; this module only attaches it, read-only, to the
splats whose existing `physics_state_id` (already populated by
SplatForge.vignette4d — previously always null on the GS-02-only path)
matches. It does not run a physics simulation and does not derive a
PhysicsState's value from anything — that decision belongs entirely to
the caller, the same "no generic default for a context-dependent value"
discipline PixelForge.blotlift now documents for its own moderation vector.

GaussianSplatInstance is a frozen dataclass, and `material_channels` isn't
even one of its stored fields — it's a literal dict built fresh inside
`to_dict()` (`{"mode": "scientific"}`, see compiler.py). So binding
operates on the dict form — what every renderer actually consumes
(`PixelForge.splat.rasterize_splats`/`_vulkan` and `SplatForge.raster.
render_pass` all call `.to_dict()` internally already) — producing NEW
dicts. The source GaussianSplatInstance, and any dict already in hand, is
never mutated in place.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Union

from .compiler import GaussianSplatInstance

SplatLike = Union[GaussianSplatInstance, Dict[str, Any]]


@dataclass(frozen=True)
class PhysicsState:
    """One declared simulation state. `value` and `source` are always
    supplied by the caller — this module never computes either."""

    physics_state_id: str
    field_name: str
    value: float
    source: str  # who/what declared this value; never "renderer"


def _as_dict(splat: SplatLike) -> Dict[str, Any]:
    return splat.to_dict() if hasattr(splat, "to_dict") else dict(splat)


def bind_physics_states(
    splats: Sequence[SplatLike],
    states: Dict[str, PhysicsState],
) -> List[Dict[str, Any]]:
    """For each splat whose `physics_state_id` is a key in `states`,
    attach that state's declared value into a NEW dict's
    `material_channels`. A splat with no matching `physics_state_id`
    passes through as a fresh, otherwise-unchanged dict — never the
    original object, so a caller cannot accidentally observe this
    function mutating a splat it was handed."""
    bound: List[Dict[str, Any]] = []
    for splat in splats:
        d = dict(_as_dict(splat))
        pid = d.get("physics_state_id")
        state = states.get(pid) if pid else None
        channels = dict(d.get("material_channels") or {})
        if state is not None:
            channels["bound_physics"] = {
                "physics_state_id": state.physics_state_id,
                "field_name": state.field_name,
                "value": state.value,
                "source": state.source,
            }
        d["material_channels"] = channels
        bound.append(d)
    return bound


def physics_residual_series(
    frame_states: Sequence[Dict[str, PhysicsState]],
    physics_state_id: str,
    field_name: str,
) -> List[float]:
    """The frame-to-frame change in one bound physics value across a
    sequence of frames (e.g. one set of states per SplatForge.
    vignette4d_playback.sweep_vignette coordinate value) — a residual/
    trajectory series, attached as evidence the same way
    genesis_correction_density is already attached per-frame elsewhere in
    this build. Computed only from the declared values already present in
    frame_states — this raises KeyError rather than silently treating a
    missing state as zero, since "no declared value" and "declared value
    of zero" are not the same claim."""
    values: List[float] = []
    for states in frame_states:
        state = states.get(physics_state_id)
        if state is None:
            raise KeyError(f"{physics_state_id!r} not present in this frame's states")
        if state.field_name != field_name:
            raise KeyError(
                f"{physics_state_id!r} is bound to field {state.field_name!r}, not {field_name!r}"
            )
        values.append(state.value)
    return [b - a for a, b in zip(values, values[1:])]
