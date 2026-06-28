"""
Eversion: turn a closed light cone inside out, exposing the latent
obligations as next-step candidates.

Eversion is the dual of closure: where closure says "this is done
modulo obligations", eversion says "here are the obligations, ordered
for the next cycle".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .light_cone import LightCone


@dataclass
class EversionPlan:
    """A list of obligations ordered for the next projection cycle."""

    light_cone_source: str
    obligations: List[str]
    next_selected_index: int
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "light_cone_source": self.light_cone_source,
            "obligations": list(self.obligations),
            "next_selected_index": self.next_selected_index,
            "rationale": self.rationale,
        }


def evert(cone: LightCone) -> EversionPlan:
    """Build the eversion plan from a light cone's latent obligations.

    If no frames are latent (a fully-selected cone), the next-selected
    index is set to ``-1`` to signal that the cone is exhausted and no
    further cycle is required.
    """
    obligations: List[str] = []
    for f in cone.frames:
        if f.latent:
            for ob in f.obligations:
                obligations.append(ob)
    latent_indices = [f.frame_index for f in cone.frames if f.latent]
    next_idx = latent_indices[0] if latent_indices else -1
    return EversionPlan(
        light_cone_source=cone.source_c,
        obligations=obligations,
        next_selected_index=next_idx,
        rationale=("eversion: latent obligations surfaced for next cycle"
                   if obligations else
                   "eversion: no latent obligations; cone is fully selected"),
    )
