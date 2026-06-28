"""
Analog workbook schema.

The kernel represents the analog workbook protocol in stdlib JSON. A
workbook is a sequence of ``AnalogStep`` records, each describing:

  * the physical action
  * the digital twin (which kernel object it maps to)
  * the required materials
  * the expected receipt
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .token_map import DIGITAL_TWIN, MaterialToken


@dataclass
class AnalogStep:
    step_id: str
    analog_action: str
    digital_equivalent: str
    required_materials: List[str]
    expected_receipt: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "analog_action": self.analog_action,
            "digital_equivalent": self.digital_equivalent,
            "required_materials": list(self.required_materials),
            "expected_receipt": self.expected_receipt,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalogStep":
        return cls(
            step_id=data["step_id"],
            analog_action=data["analog_action"],
            digital_equivalent=data["digital_equivalent"],
            required_materials=list(data["required_materials"]),
            expected_receipt=data["expected_receipt"],
        )


# Default workbook: a canonical 6-step protocol that exercises every
# kernel primitive. Each step's expected_receipt names the event_type
# the kernel should emit when this analog step completes.
DEFAULT_WORKBOOK: List[AnalogStep] = [
    AnalogStep(
        step_id=str(uuid.uuid4()),
        analog_action="write request on a notebook page; circle the request id",
        digital_equivalent="core.request.ObservedRequest",
        required_materials=[MaterialToken.NOTEBOOK.value, MaterialToken.COLOR_PENCIL.value],
        expected_receipt="REQUEST_OBSERVED",
    ),
    AnalogStep(
        step_id=str(uuid.uuid4()),
        analog_action="translate the request into bytes and tape them onto a 2x2 grid",
        digital_equivalent="carrier.binary_boundary.BinaryBoundaryFrame",
        required_materials=[MaterialToken.GRID_2X2.value, MaterialToken.TAPE.value],
        expected_receipt="BOUNDARY_FRAME_CREATED",
    ),
    AnalogStep(
        step_id=str(uuid.uuid4()),
        analog_action="mark each byte as 4-bit nibbles on a 2x4 chart",
        digital_equivalent="carrier.fourbit.FourBitCarrier",
        required_materials=[MaterialToken.CHART_2X4.value, MaterialToken.COLOR_PENCIL.value],
        expected_receipt="FOURBIT_ENCODED",
    ),
    AnalogStep(
        step_id=str(uuid.uuid4()),
        analog_action="place tokens on each L/C/R window; mark center with sticker",
        digital_equivalent="carrier.cform.cform_from_gluon",
        required_materials=[MaterialToken.TOKEN.value, MaterialToken.STICKER.value],
        expected_receipt="C_FORM_CREATED",
    ),
    AnalogStep(
        step_id=str(uuid.uuid4()),
        analog_action="compute the correction = C AND NOT R on each window; mark with red pencil",
        digital_equivalent="carrier.correction.correction_table",
        required_materials=[MaterialToken.COLOR_PENCIL.value, MaterialToken.NOTEBOOK.value],
        expected_receipt="CORRECTION_COMPUTED",
    ),
    AnalogStep(
        step_id=str(uuid.uuid4()),
        analog_action="fold the chart along its center; bind with string; record the ribbon hash",
        digital_equivalent="ribbon.slot.make_ribbon + ribbon.hydrate",
        required_materials=[
            MaterialToken.STRING.value,
            MaterialToken.FOLDED_SHEET.value,
            MaterialToken.NOTEBOOK.value,
        ],
        expected_receipt="RIBBON_CREATED",
    ),
]


def digital_twins_for(material: str) -> List[str]:
    """Return the digital twin objects for a material token."""
    return list(DIGITAL_TWIN.get(material, []))
