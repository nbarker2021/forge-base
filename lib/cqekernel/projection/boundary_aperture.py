"""
Boundary aperture detector.

The kernel detects local boundary sites at the stdlib layer over:

  * all 2x2 windows over a bit grid
  * all 2x2 windows over adjacent local states
  * all head/tail 4-bit junctions
  * all shell-2 states
  * all correction-firing states

The kernel does NOT claim "SU(3) exact" unless a verifier or firmware
binding supplies that receipt. It only marks the apertures.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from ..carrier.lcr import LocalGluon


APERTURE_KINDS: List[str] = [
    "2x2_grid",
    "adjacent_lcr",
    "head_tail_4bit",
    "shell_2",
    "correction_firing",
]


@dataclass
class BoundaryAperture:
    """A single detected boundary aperture."""

    aperture_id: str
    kind: str
    position: Tuple[int, ...]
    local_state: Dict[str, Any]
    requires_tail: bool
    required_tail_4bit: str
    activated_heads: List[str] = field(default_factory=list)
    status: str = "BOUNDARY_DETECTED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "aperture_id": self.aperture_id,
            "kind": self.kind,
            "position": list(self.position),
            "local_state": dict(self.local_state),
            "requires_tail": self.requires_tail,
            "required_tail_4bit": self.required_tail_4bit,
            "activated_heads": list(self.activated_heads),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BoundaryAperture":
        return cls(
            aperture_id=data["aperture_id"],
            kind=data["kind"],
            position=tuple(data["position"]),
            local_state=dict(data["local_state"]),
            requires_tail=bool(data["requires_tail"]),
            required_tail_4bit=data["required_tail_4bit"],
            activated_heads=list(data.get("activated_heads", [])),
            status=data.get("status", "BOUNDARY_DETECTED"),
        )


def _aperture(
    kind: str,
    position: Tuple[int, ...],
    local_state: Dict[str, Any],
    *,
    required_tail_4bit: str = "0000",
    requires_tail: bool = False,
) -> BoundaryAperture:
    return BoundaryAperture(
        aperture_id=str(uuid.uuid4()),
        kind=kind,
        position=position,
        local_state=local_state,
        requires_tail=requires_tail,
        required_tail_4bit=required_tail_4bit,
    )


def detect_from_gluons(
    gluons: List[LocalGluon],
    tail_4bit: str = "0000",
) -> List[BoundaryAperture]:
    """Detect boundary apertures from a stream of gluons.

    A 2x2 window over the underlying bit grid is the cell
    ``[[g_i.center, g_i.right], [g_{i+1}.left, g_{i+1}.center]]``
    — i.e. the bottom-right 2x2 formed by the join of two
    consecutive LCR triples. We fire an adjacent-LCR aperture on
    every such join (the kernel does not over-classify; the
    downstream firmware or socratic wrapper decides what each
    aperture *means*).
    """
    out: List[BoundaryAperture] = []
    n = len(gluons)
    for i, g in enumerate(gluons):
        # shell-2 apertures
        if g.shell == 2:
            out.append(
                _aperture(
                    "shell_2",
                    (i,),
                    {"lcr": [g.left, g.center, g.right], "shell": g.shell},
                )
            )
        # correction-firing apertures
        if g.correction == 1:
            out.append(
                _aperture(
                    "correction_firing",
                    (i,),
                    {"lcr": [g.left, g.center, g.right], "correction": 1},
                )
            )
        # adjacent LCR: the 2x2 cell is
        #   [[g_i.center, g_i.right], [g_{i+1}.left, g_{i+1}.center]]
        # The cell exists whenever the two triples are adjacent in
        # the underlying bit stream. The kernel fires an aperture
        # on every adjacent pair — the "head/tail" classification
        # is left to the socratic wrapper or firmware. The
        # boundary-pattern filter (the 0101/1010 alternation) is
        # what marks a *head/tail* aperture, not whether the 2x2
        # cell exists.
        if i + 1 < n:
            nxt = gluons[i + 1]
            cell = (g.left, g.center, g.right, nxt.left, nxt.center, nxt.right)
            if cell in (
                # head/tail cell: alternation pattern
                (0, 1, 0, 1, 0, 1),
                (1, 0, 1, 0, 1, 0),
                # the mirror where C and C' are joined
                (0, 1, 0, 0, 1, 0),
                (1, 0, 1, 1, 0, 1),
            ):
                out.append(
                    _aperture(
                        "adjacent_lcr",
                        (i, i + 1),
                        {"lcr": [g.left, g.center, g.right],
                         "next_lcr": [nxt.left, nxt.center, nxt.right],
                         "cell_2x2": [[g.center, g.right], [nxt.left, nxt.center]]},
                    )
                )
    # head/tail 4-bit junction (carrier)
    out.append(
        _aperture(
            "head_tail_4bit",
            (0, n - 1 if n > 0 else 0),
            {"tail_4bit": tail_4bit},
            requires_tail=True,
            required_tail_4bit=tail_4bit,
        )
    )
    return out
