"""
Light-cone container.

A bounded projection container holding a list of observer frames,
the projection depth (0..3), and any boundary apertures that opened
during projection. The kernel does not implement physics; it only
holds the container and the receipts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .observer_frame import ObserverFrame


@dataclass
class LightCone:
    """Bounded projection container over a source C."""

    source_c: str
    frames: List[ObserverFrame]
    projection_depth: int
    boundary_apertures: List[str] = field(default_factory=list)
    status: str = "OPEN"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_c": self.source_c,
            "frames": [f.to_dict() for f in self.frames],
            "projection_depth": self.projection_depth,
            "boundary_apertures": list(self.boundary_apertures),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LightCone":
        return cls(
            source_c=data["source_c"],
            frames=[ObserverFrame.from_dict(f) for f in data["frames"]],
            projection_depth=int(data["projection_depth"]),
            boundary_apertures=list(data.get("boundary_apertures", [])),
            status=data.get("status", "OPEN"),
        )


def open_cone(
    *,
    source_c: str,
    frames: List[ObserverFrame],
    projection_depth: int = 0,
    apertures: Optional[List[str]] = None,
) -> LightCone:
    """Open a light cone over a source C with the given frames."""
    if projection_depth not in (0, 1, 2, 3):
        raise ValueError("projection_depth must be 0..3")
    return LightCone(
        source_c=source_c,
        frames=list(frames),
        projection_depth=projection_depth,
        boundary_apertures=list(apertures or []),
        status="OPEN",
    )
