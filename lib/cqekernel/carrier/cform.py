"""
The local C-form carrier and the triadic L/C/R placement object.

The C-form is the *center* of an LCR triple. For each 3-bit window we
record:

  C-form  = the center bit
  L-form  = the left boundary bit
  R-form  = the right boundary bit
  shell   = L + C + R
  chiral  = (L != R)

A triadic placement bundles the three forms for one observation into a
single addressable object.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict

from .lcr import LocalGluon


def _stable_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass
class CForm:
    """The local C-form (the center of an LCR triple)."""

    cform_id: str
    source_carrier_hash: str
    index: int
    value: int
    left: int
    right: int
    shell: int
    chiral: bool
    canonical_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cform_id": self.cform_id,
            "source_carrier_hash": self.source_carrier_hash,
            "index": self.index,
            "value": self.value,
            "left": self.left,
            "right": self.right,
            "shell": self.shell,
            "chiral": self.chiral,
            "canonical_hash": self.canonical_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CForm":
        return cls(
            cform_id=data["cform_id"],
            source_carrier_hash=data["source_carrier_hash"],
            index=int(data["index"]),
            value=int(data["value"]),
            left=int(data["left"]),
            right=int(data["right"]),
            shell=int(data["shell"]),
            chiral=bool(data["chiral"]),
            canonical_hash=data["canonical_hash"],
        )


def cform_from_gluon(gluon: LocalGluon, source_carrier_hash: str) -> CForm:
    """Build a ``CForm`` from a ``LocalGluon``."""
    body = json.dumps(
        {
            "source_carrier_hash": source_carrier_hash,
            "index": gluon.index,
            "value": gluon.gluon,
            "left": gluon.left,
            "right": gluon.right,
            "shell": gluon.shell,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return CForm(
        cform_id=str(uuid.uuid4()),
        source_carrier_hash=source_carrier_hash,
        index=gluon.index,
        value=gluon.gluon,
        left=gluon.left,
        right=gluon.right,
        shell=gluon.shell,
        chiral=(gluon.left != gluon.right),
        canonical_hash=_stable_hash(body),
    )


# ---------------------------------------------------------------------------
# Triadic placement
# ---------------------------------------------------------------------------


@dataclass
class TriadicPlacement:
    """A single L/C/R placement.

    Tracks swap-preservation of the center, shell, shell-2, fixed-center
    and chiral-pair states. The orientation is one of "natural",
    "swapped", "complement".
    """

    placement_id: str
    source_request_id: str
    left: Dict[str, Any]
    center: Dict[str, Any]
    right: Dict[str, Any]
    center_hash: str
    complement_hash: str
    orientation: str
    shell: int = 0
    shell_2: bool = False
    fixed_center: bool = False
    chiral_pair: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "placement_id": self.placement_id,
            "source_request_id": self.source_request_id,
            "left": dict(self.left),
            "center": dict(self.center),
            "right": dict(self.right),
            "center_hash": self.center_hash,
            "complement_hash": self.complement_hash,
            "orientation": self.orientation,
            "shell": self.shell,
            "shell_2": self.shell_2,
            "fixed_center": self.fixed_center,
            "chiral_pair": self.chiral_pair,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TriadicPlacement":
        return cls(
            placement_id=data["placement_id"],
            source_request_id=data["source_request_id"],
            left=dict(data["left"]),
            center=dict(data["center"]),
            right=dict(data["right"]),
            center_hash=data["center_hash"],
            complement_hash=data["complement_hash"],
            orientation=data["orientation"],
            shell=int(data.get("shell", 0)),
            shell_2=bool(data.get("shell_2", False)),
            fixed_center=bool(data.get("fixed_center", False)),
            chiral_pair=bool(data.get("chiral_pair", False)),
        )


def _hash_dict(d: Dict[str, Any]) -> str:
    return _stable_hash(
        json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def place(gluon: LocalGluon, source_request_id: str) -> TriadicPlacement:
    """Build a ``TriadicPlacement`` from a single ``LocalGluon``."""
    left = {"value": gluon.left, "role": "left", "index": gluon.index}
    right = {"value": gluon.right, "role": "right", "index": gluon.index}
    center = {"value": gluon.gluon, "role": "center", "index": gluon.index}
    return TriadicPlacement(
        placement_id=str(uuid.uuid4()),
        source_request_id=source_request_id,
        left=left,
        center=center,
        right=right,
        center_hash=_hash_dict(center),
        complement_hash=_hash_dict(
            {"value": 1 - gluon.gluon, "role": "complement", "index": gluon.index}
        ),
        orientation="natural",
        shell=gluon.shell,
        shell_2=(gluon.shell == 2),
        fixed_center=(gluon.left == gluon.right),
        chiral_pair=(gluon.left != gluon.right),
    )


def swap_lr(placement: TriadicPlacement) -> TriadicPlacement:
    """Return a new placement with L and R swapped (C preserved)."""
    new = TriadicPlacement(
        placement_id=str(uuid.uuid4()),
        source_request_id=placement.source_request_id,
        left=dict(placement.right),
        right=dict(placement.left),
        center=dict(placement.center),
        center_hash=placement.center_hash,
        complement_hash=placement.complement_hash,
        orientation="swapped",
        shell=placement.shell,
        shell_2=placement.shell_2,
        fixed_center=placement.fixed_center,
        chiral_pair=placement.chiral_pair,
    )
    return new
