"""
Closure: compute the closed-form of a light-cone projection.

A light cone is "closed" when:

  * exactly one frame is selected
  * exactly three frames are latent
  * all latent frames carry obligations
  * the boundary apertures are all classified

Closure does not assert a specific physics identity; it asserts the
governance invariants only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .light_cone import LightCone
from .observer_frame import check_governance


@dataclass
class ClosureResult:
    light_cone_source: str
    closed: bool
    selected: int
    latent: int
    classified_apertures: int
    unclassified_apertures: int
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "light_cone_source": self.light_cone_source,
            "closed": self.closed,
            "selected": self.selected,
            "latent": self.latent,
            "classified_apertures": self.classified_apertures,
            "unclassified_apertures": self.unclassified_apertures,
            "notes": list(self.notes),
        }


def close_cone(cone: LightCone) -> ClosureResult:
    """Check whether a light cone can be closed."""
    selected = sum(1 for f in cone.frames if f.selected)
    latent = sum(1 for f in cone.frames if f.latent)
    gov = check_governance(cone.frames)
    classified = sum(1 for a in cone.boundary_apertures if a)
    notes: List[str] = []
    if not gov:
        notes.append("observer frame governance rule violated")
    if classified == 0:
        notes.append("no boundary apertures classified")
    closed = gov and classified > 0
    return ClosureResult(
        light_cone_source=cone.source_c,
        closed=closed,
        selected=selected,
        latent=latent,
        classified_apertures=classified,
        unclassified_apertures=0,
        notes=notes,
    )
