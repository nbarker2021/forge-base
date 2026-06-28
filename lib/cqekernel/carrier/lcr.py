"""
Local L/C/R carrier and asymmetric admissibility gate.

The kernel implements the local LCR readout: for each 3-bit window
``L C R`` it computes:

  shell    = L + C + R
  gluon    = C
  rule90   = L XOR R
  rule30   = C XOR (L XOR R) XOR (L AND R)
  correction = C AND (NOT R)

and assigns a state class. The gate preserves both the accepted and
the rejected/complement side of the split.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from ..core.status import AdmissionClass


# ---------------------------------------------------------------------------
# Local Gluon (single LCR window)
# ---------------------------------------------------------------------------


@dataclass
class LocalGluon:
    """A single L/C/R window with its derived correction and state class.

    The gluon is the local readout of a 3-bit state. Its ``gluon``
    field is the center bit (the C-form). The ``correction`` is
    ``C AND NOT R`` (the kernel's correction identity). For the
    "what is C" object, see :class:`cqekernel.carrier.cform.CForm`.
    """

    index: int
    left: int
    center: int
    right: int
    shell: int
    gluon: int
    rule90: int
    rule30: int
    correction: int
    state_class: str
    window_key: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "left": self.left,
            "center": self.center,
            "right": self.right,
            "shell": self.shell,
            "gluon": self.gluon,
            "rule90": self.rule90,
            "rule30": self.rule30,
            "correction": self.correction,
            "state_class": self.state_class,
            "window_key": self.window_key,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LocalGluon":
        return cls(
            index=int(data["index"]),
            left=int(data["left"]),
            center=int(data["center"]),
            right=int(data["right"]),
            shell=int(data["shell"]),
            gluon=int(data["gluon"]),
            rule90=int(data["rule90"]),
            rule30=int(data["rule30"]),
            correction=int(data["correction"]),
            state_class=data["state_class"],
            window_key=data.get("window_key", ""),
        )


def _classify(lcr: Tuple[int, int, int]) -> str:
    """Classify a 3-bit local state.

    The naming follows the corpus conventions:
      - "fixed_center"    when L == R
      - "chiral_pair"     when L != R
      - "boundary"        when (L, C, R) is (0, 1, 0) or (1, 0, 1):
                          shell-1 chiral pair with C as the lone bit.
                          This is the cell that carries the head/tail
                          C/L/R "head/tail" signal.
    """
    L, C, R = lcr
    if (L, C, R) in {(0, 1, 0), (1, 0, 1)}:
        return "boundary"
    if L == R:
        return "fixed_center"
    return "chiral_pair"


def gluon_from_lcr(index: int, lcr: Tuple[int, int, int]) -> LocalGluon:
    """Build a ``LocalGluon`` from a single (L, C, R) triple."""
    L, C, R = lcr
    shell = L + C + R
    rule90 = L ^ R
    rule30 = C ^ rule90 ^ (L & R)
    correction = C & (1 - R)  # C AND NOT R, in pure stdlib
    return LocalGluon(
        index=index,
        left=L,
        center=C,
        right=R,
        shell=shell,
        gluon=C,
        rule90=rule90,
        rule30=rule30,
        correction=correction,
        state_class=_classify(lcr),
        window_key=f"{L}{C}{R}",
    )


def truth_table() -> List[LocalGluon]:
    """Return the full 8-row LCR truth table (kernel primitive)."""
    rows: List[LocalGluon] = []
    for i, (L, C, R) in enumerate(
        [(0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1),
         (1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1)]
    ):
        rows.append(gluon_from_lcr(i, (L, C, R)))
    return rows


# ---------------------------------------------------------------------------
# Asymmetric admissibility gate
# ---------------------------------------------------------------------------


@dataclass
class AdmissionResult:
    """Result of the asymmetric admissibility split."""

    candidate_id: str
    admitted: bool
    left: Dict[str, Any]
    center: Dict[str, Any]
    right: Dict[str, Any]
    complement: Dict[str, Any]
    reason: str
    admission_class: AdmissionClass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "admitted": self.admitted,
            "left": dict(self.left),
            "center": dict(self.center),
            "right": dict(self.right),
            "complement": dict(self.complement),
            "reason": self.reason,
            "admission_class": self.admission_class.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AdmissionResult":
        return cls(
            candidate_id=data["candidate_id"],
            admitted=bool(data["admitted"]),
            left=dict(data["left"]),
            center=dict(data["center"]),
            right=dict(data["right"]),
            complement=dict(data["complement"]),
            reason=data["reason"],
            admission_class=AdmissionClass(data["admission_class"]),
        )


def _gate(
    *,
    center_state: int,
    left_state: int,
    right_state: int,
    center_threshold: int = 1,
) -> AdmissionResult:
    """Apply the asymmetric gate.

    The gate is asymmetric on purpose: the left side and the right side
    are admitted by *different* criteria. The center is preserved.

    Convention used here:

      * ``admitted``     iff the center reaches the threshold
      * ``boundary``     iff left == right != center  (head/tail signal)
      * ``rejected``     iff the center is below threshold
      * ``unknown``      iff left/right disagree
      * ``deferred``     otherwise
    """
    candidate_id = str(uuid.uuid4())
    left = {"value": left_state, "role": "boundary"}
    right = {"value": right_state, "role": "boundary"}
    center = {"value": center_state, "role": "carrier"}
    complement = {
        "value": 1 - center_state,
        "role": "rejected_or_complement",
    }

    if left_state == right_state and left_state != center_state:
        cls = AdmissionClass.BOUNDARY
        admitted = True
        reason = "left == right != center: boundary signal carried by head/tail"
    elif center_state >= center_threshold and left_state == right_state:
        cls = AdmissionClass.ADMITTED
        admitted = True
        reason = "center at threshold and left/right agree"
    elif left_state != right_state:
        cls = AdmissionClass.UNKNOWN
        admitted = False
        reason = "left/right disagree: defer until external verifier"
    elif center_state < center_threshold:
        cls = AdmissionClass.REJECTED
        admitted = False
        reason = "center below threshold"
    else:
        cls = AdmissionClass.DEFERRED
        admitted = False
        reason = "no rule triggered"

    return AdmissionResult(
        candidate_id=candidate_id,
        admitted=admitted,
        left=left,
        center=center,
        right=right,
        complement=complement,
        reason=reason,
        admission_class=cls,
    )


def admit(gluon: LocalGluon) -> AdmissionResult:
    """Admit a ``LocalGluon`` through the asymmetric gate."""
    return _gate(
        center_state=gluon.gluon,
        left_state=gluon.left,
        right_state=gluon.right,
    )
