"""
The combined ribbon module.

Re-exports the slot/ribbon/arity types from ``slot.py`` plus a
``Ribbon`` facade. Kept thin so that downstream code can
``from cqekernel.ribbon.ribbon import Ribbon`` without ambiguity.
"""

from .slot import (
    SLOT_NAMES,
    PROOF_BEARING,
    OBLIGATED,
    RibbonSlot,
    Ribbon,
    ArityReport,
    make_slot,
    make_ribbon,
    arity_report,
)

__all__ = [
    "SLOT_NAMES",
    "PROOF_BEARING",
    "OBLIGATED",
    "RibbonSlot",
    "Ribbon",
    "ArityReport",
    "make_slot",
    "make_ribbon",
    "arity_report",
]
