"""
Token map for the analog workbook.

Tokens correspond to physical materials the analog workbench uses::

  GRID_2X2       — 2x2 grid paper
  CHART_2X4      — 2x4 chart
  TOKEN           — small token / chip
  COLOR_PENCIL    — colored pencil (3 colors: red/green/blue)
  STRING          — physical string for folding
  STICKER         — sticker
  TAPE            — tape
  NOTEBOOK        — notebook page
  FOLDED_SHEET    — folded sheet
  OVERLAY_SHEET   — overlay sheet
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List


class MaterialToken(str, Enum):
    GRID_2X2 = "grid_2x2"
    CHART_2X4 = "chart_2x4"
    TOKEN = "token"
    COLOR_PENCIL = "color_pencil"
    STRING = "string"
    STICKER = "sticker"
    TAPE = "tape"
    NOTEBOOK = "notebook"
    FOLDED_SHEET = "folded_sheet"
    OVERLAY_SHEET = "overlay_sheet"


DIGITAL_TWIN: Dict[str, List[str]] = {
    MaterialToken.GRID_2X2.value:       ["carrier.fourbit", "lcr.truth_table"],
    MaterialToken.CHART_2X4.value:      ["ribbon.slot", "projection.observer_frame"],
    MaterialToken.TOKEN.value:          ["lcr.gluon", "cform.cform"],
    MaterialToken.COLOR_PENCIL.value:   ["projection.boundary_aperture", "admission"],
    MaterialToken.STRING.value:         ["ribbon.hydrate", "transport"],
    MaterialToken.STICKER.value:        ["ribbon.slot", "ledger.receipt"],
    MaterialToken.TAPE.value:           ["carrier.binary_boundary", "ledger.snapshot"],
    MaterialToken.NOTEBOOK.value:       ["ledger.event", "verification.socratic"],
    MaterialToken.FOLDED_SHEET.value:   ["projection.eversion", "projection.closure"],
    MaterialToken.OVERLAY_SHEET.value:  ["projection.light_cone", "projection.boundary_aperture"],
}
