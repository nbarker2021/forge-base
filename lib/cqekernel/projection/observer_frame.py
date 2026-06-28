"""
The four-frame observer/projection model.

The kernel represents the observer cycle as 4 frames::

    Frame 0: C-centroid
    Frame 1: R-centroid
    Frame 2: C-flipped / antipodal
    Frame 3: L-centroid

The governance rule is::

    selected = 1
    latent obligations = 3

The kernel never deletes unselected frames. They are marked as latent
obligations and can be revisited on replay.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


FRAME_NAMES: List[str] = [
    "C_CENTROID",
    "R_CENTROID",
    "C_FLIPPED",
    "L_CENTROID",
]


@dataclass
class ObserverFrame:
    """A single observer frame."""

    frame_index: int
    frame_name: str
    selected: bool
    latent: bool
    source_carrier_hash: str
    obligations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "frame_name": self.frame_name,
            "selected": self.selected,
            "latent": self.latent,
            "source_carrier_hash": self.source_carrier_hash,
            "obligations": list(self.obligations),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ObserverFrame":
        return cls(
            frame_index=int(data["frame_index"]),
            frame_name=data["frame_name"],
            selected=bool(data["selected"]),
            latent=bool(data["latent"]),
            source_carrier_hash=data["source_carrier_hash"],
            obligations=list(data.get("obligations", [])),
        )


def four_frames(
    source_carrier_hash: str,
    *,
    selected_index: int = 0,
    obligation_id_prefix: Optional[str] = None,
) -> List[ObserverFrame]:
    """Build the four observer frames. Exactly one is ``selected``; the
    other three are ``latent`` and carry obligation ids."""
    if selected_index not in (0, 1, 2, 3):
        raise ValueError("selected_index must be 0..3")
    prefix = obligation_id_prefix or str(uuid.uuid4())
    frames: List[ObserverFrame] = []
    for i, name in enumerate(FRAME_NAMES):
        is_selected = (i == selected_index)
        if is_selected:
            obligations: List[str] = []
        else:
            obligations = [f"{prefix}:frame:{i}"]
        frames.append(
            ObserverFrame(
                frame_index=i,
                frame_name=name,
                selected=is_selected,
                latent=not is_selected,
                source_carrier_hash=source_carrier_hash,
                obligations=obligations,
            )
        )
    return frames


def check_governance(frames: List[ObserverFrame]) -> bool:
    """Verify the selected=1, latent-obligations=3 governance rule."""
    selected = sum(1 for f in frames if f.selected)
    latent = sum(1 for f in frames if f.latent)
    latent_with_obligations = sum(1 for f in frames if f.latent and f.obligations)
    return selected == 1 and latent == 3 and latent_with_obligations == 3
