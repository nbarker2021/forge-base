"""
OloidChart: the 8-state chart the oloid winding classifies over
a pre-existing state.

The state the oloid "rolls" is not generated; it is **looked up**
from the pre-existing rule-30 million-bit (or billion-bit)
chart via ``CmplxLookupCache.lookup_rule30_bit(n)``. That
bit is the canonical answer for position ``n``; the chart is
already addressed.

What the oloid *does* is **classify** that pre-existing bit
across 8 lanes -- 7 selection modes plus 1 view axis. Each
mode is a different *choice* of emit bit; the antipodal
winding produces all 8 bit values plus a per-mode defect
vector plus a ``best_mode`` decision. The classification is
deterministic: same ``n`` + same ``config`` always produces the
same chart.

This module turns that 8-mode output into a typed 8-state
chart. The chart is content-addressed (SHA-256 of the canonical
JSON form), so the host can re-verify it on every boot.
The chart slots into the LCRKernel as a new C-lane dispatch
type; the AMK can call ``build_oloid_chart(n, lane, config)``
to get a typed 8-state chart for any ``n >= 1`` that exists
in the CAME.

Lanes, in order:
  1. FORWARD                 -- emit under the viewed sheet
  2. ANTIPODE                -- emit under the counter-sheet
  3. XOR                     -- forward XOR antipode
  4. OR                      -- forward OR antipode
  5. AND                     -- forward AND antipode
  6. PARITY_CORRECTED_FORWARD -- forward with parity correction
  7. SIDE_CORRECTED_FORWARD  -- forward with side correction
  8. VIEW_AXIS               -- the structural choice of
                                 which sheet (viewed or counter)
                                 to commit to
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# The 8 lanes the oloid chart produces per n.
class OloidMode(str, Enum):
    """One of the 8 lane states the oloid chart produces per n.

    The first 7 are the selection modes; the 8th is the
    structural view-axis choice (which is *not* a mode but
    a half-bit that the antipodal definition adds).
    """

    FORWARD                 = "forward"
    ANTIPODE                = "antipode"
    XOR                     = "xor"
    OR                      = "or"
    AND                     = "and"
    PARITY_CORRECTED_FORWARD = "parity_corrected_forward"
    SIDE_CORRECTED_FORWARD  = "side_corrected_forward"
    VIEW_AXIS               = "view_axis"  # the 8th slot


# Every OloidState has the same payload -- the oloid chart is
# value-equivalent across the 8 lanes, with the *emit bit* as
# the chart's per-state value. The chart is a *selection* of
# which of the 8 to take.
@dataclass(frozen=True)
class OloidState:
    """One of the 8 lane states of the oloid chart."""

    lane: OloidMode
    emitted_bit: int
    shell: int
    side: int
    reference_vector: Tuple[float, float, float]
    # The mode-level defect count for this state. 0 means the
    # mode produced the right answer; >0 means it was wrong.
    # The view_axis lane's defect is 0 (structural, not a
    # selection -- the antipode is what it is).
    defect: int = 0
    # Whether this lane is the best mode for the n we asked
    # about. Exactly one of the 8 lanes has best=True for
    # any given n.
    is_best: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lane": self.lane.value,
            "emitted_bit": self.emitted_bit,
            "shell": self.shell,
            "side": self.side,
            "reference_vector": list(self.reference_vector),
            "defect": self.defect,
            "is_best": self.is_best,
        }


# All fields the oloid chart exposes in its serialised form.
# Listed explicitly so content_hash is computed only from the
# canonical fields, never from a self-reference.
_OLOID_CHART_FIELDS = (
    "n",
    "chart_id",
    "center_bit",
    "best_lane",
    "config",
    "antipodal_definition",
    "state_count",
    "states",
    "notes",
)


@dataclass(frozen=True)
class OloidChart:
    """The full 8-state oloid chart for one n.

    The chart is a content-addressed record: the SHA-256 of the
    canonical JSON form is the chart's content_hash. A host
    can re-verify it on every boot by recomputing the hash.

    The state itself is the pre-existing rule-30 bit at position
    n; the chart classifies that pre-existing bit across 8 lanes.
    The chart's content_hash is computed only from the canonical
    fields (not from the content_hash itself), so to_dict() and
    content_hash do not recurse.
    """

    n: int                                    # the rolling parameter
    center_bit: int                          # the canonical answer (from CAME)
    states: Tuple[OloidState, ...]           # exactly 8, one per OloidMode
    config: Dict[str, Any]                   # the 6-tuple that produced the chart
    best_lane: OloidMode                     # which lane to take
    antipodal_definition: Dict[str, Any]     # why the antipode exists
    notes: str = ""

    @property
    def chart_id(self) -> str:
        return f"oloid:{self.n}:{self.best_lane.value}"

    @property
    def content_hash(self) -> str:
        body = json.dumps(
            self._canonical_dict(), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    def _canonical_dict(self) -> Dict[str, Any]:
        """The canonical JSON form. Excludes content_hash itself
        so the hash is well-defined (no self-reference)."""
        return {
            "n": self.n,
            "chart_id": self.chart_id,
            "center_bit": self.center_bit,
            "best_lane": self.best_lane.value,
            "config": dict(self.config),
            "antipodal_definition": dict(self.antipodal_definition),
            "state_count": self.state_count,
            "states": [s.to_dict() for s in self.states],
            "notes": self.notes,
        }

    @property
    def state_count(self) -> int:
        return len(self.states)

    def to_dict(self) -> Dict[str, Any]:
        """The serialised form, with content_hash included."""
        d = self._canonical_dict()
        d["content_hash"] = self.content_hash
        return d

    def lane(self, mode: OloidMode) -> OloidState:
        """Return the state for one lane."""
        for s in self.states:
            if s.lane == mode:
                return s
        raise KeyError(f"lane {mode!r} not in chart")

    @property
    def best_state(self) -> OloidState:
        """Return the state for the best lane."""
        return self.lane(self.best_lane)


# The 8 modes, in order. Used by the AMK C lane.
OLOID_CHART_LANES: Tuple[OloidMode, ...] = tuple(OloidMode)


def _ensure_lf_on_path() -> None:
    """Add the lattice_forge source dir to sys.path once."""
    import sys
    abs_p = str(
        (Path(__file__).resolve().parents[3]
         / "production/packages/cqecmplx-forge/src").resolve()
    )
    if abs_p not in sys.path:
        sys.path.insert(0, abs_p)


def build_oloid_chart(
    n: int,
    config: Optional[Dict[str, Any]] = None,
) -> OloidChart:
    """Build the 8-state oloid chart for one rolling parameter.

    The state is the pre-existing rule-30 bit at position ``n``
    (looked up from the CAME). The chart classifies that
    pre-existing bit across 8 lanes. The chart is deterministic:
    same ``n`` + same ``config`` always produces the same
    content_hash.

    The oloid antipodal winding requires ``n >= 1``; for
    ``n == 0`` the chart is degenerate (all modes have the
    same forward state). The function returns a valid chart
    for any non-negative ``n`` by treating ``n == 0`` as a
    chart with a single best-mode = FORWARD.
    """
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")
    _ensure_lf_on_path()
    import lattice_forge as lf

    if n == 0:
        # Degenerate case: the oloid's n must be a positive
        # integer depth. We return a chart with a single
        # forward state and no antipode; the best_mode is
        # FORWARD by default.
        forward = {
            "reference_vector": [0.0, 0.0, 0.0],
            "shell": 0,
            "side": 0,
            "emitted_bit": 0,
        }
        modes_dict = {m.value: 0 for m in OloidMode if m != OloidMode.VIEW_AXIS}
        defects_dict = {m.value: 0 for m in OloidMode if m != OloidMode.VIEW_AXIS}
        best_mode_str = OloidMode.FORWARD.value
        center_bit = 0
        antipode = {
            "reference_vector": [0.0, 0.0, 0.0],
            "shell": 0,
            "side": 0,
            "emitted_bit": 0,
        }
        antipodal_definition = {
            "meaning": "n=0 is a degenerate chart (no antipode resolved)",
            "counter_sheet": "0",
            "antipode_operation": "identity",
            "visible_sheet": "0 viewed",
            "hidden_sheet": "0 antipodal",
            "why": "n=0 has no positive depth, so the oloid's antipodal "
                   "winding is not invoked",
        }
    else:
        # Get the per-mode witness for this n. The oloid's
        # center_bit is the canonical answer for position n;
        # it should match the CAME bit at n (the oloid and the
        # CAME both index the same million-bit rule-30 stream).
        witness = lf.rule30_oloid_antipodal_winding(n, **(config or {}))
        modes_dict = witness["selection_modes"]
        defects_dict = witness["defects"]
        best_mode_str = witness["best_mode"]
        center_bit = int(witness["center_bit"])
        forward = witness["forward"]
        antipode = witness["antipode"]
        antipodal_definition = witness["antipodal_definition"]

    # The 7 selection modes all use the forward state's
    # reference vector + shell + side -- the mode is a *choice*
    # of emit bit, not a different reference vector.
    rv = tuple(forward["reference_vector"])
    shell = int(forward["shell"])
    side = int(forward["side"])

    # The 8th lane (view_axis) is structural: it carries the
    # antipode's reference vector (sign-flipped) and shell. The
    # antipode is the hidden counter-sheet.
    view_rv = tuple(antipode["reference_vector"])
    view_shell = int(antipode["shell"])

    # Build the 8 states, in lane order.
    states: List[OloidState] = []
    for mode in OloidMode:
        if mode == OloidMode.VIEW_AXIS:
            # The 8th lane: structural view choice.
            # Its "defect" is 0 because it's a definition, not a
            # prediction; the antipode is what it is.
            states.append(OloidState(
                lane=mode,
                emitted_bit=int(antipode["emitted_bit"]),
                shell=view_shell,
                side=int(antipode["side"]),
                reference_vector=view_rv,
                defect=0,
                is_best=(best_mode_str == OloidMode.VIEW_AXIS.value),
            ))
            continue
        # The 7 selection modes.
        bit = int(modes_dict.get(mode.value, 0))
        defect = int(defects_dict.get(mode.value, 0))
        states.append(OloidState(
            lane=mode,
            emitted_bit=bit,
            shell=shell,
            side=side,
            reference_vector=rv,
            defect=defect,
            is_best=(best_mode_str == mode.value),
        ))

    best_lane = OloidMode(best_mode_str)

    # Compute the chart's notes honestly.
    n_modes = max(1, len(defects_dict))
    n_correct = sum(1 for v in defects_dict.values() if v == 0)
    accuracy = n_correct / n_modes

    return OloidChart(
        n=n,
        center_bit=center_bit,
        states=tuple(states),
        config=dict(witness.get("config", {}) if n > 0 else {}),
        best_lane=best_lane,
        antipodal_definition=antipodal_definition,
        notes=(
            f"OloidChart for n={n}; best_lane={best_mode_str}; "
            f"state is the pre-existing rule-30 bit at position n; "
            f"adaptive-selector accuracy over the 7 selection modes: "
            f"{n_correct}/{n_modes} = {accuracy:.0%}"
        ),
    )


__all__ = [
    "OloidMode",
    "OloidState",
    "OloidChart",
    "OLOID_CHART_LANES",
    "build_oloid_chart",
]
