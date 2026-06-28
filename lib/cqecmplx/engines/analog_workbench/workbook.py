from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict

@dataclass
class WorkbookSheet:
    sheet_id: str
    title: str
    active_center: str
    source_notebook: str
    loose_page: str
    gradient_colors: List[str]
    decision_question: str
    continue_or_new_page: str
    proof_or_obligation: str
    legal_bindings: List[str] = field(default_factory=list)
    strings: List[Dict[str, str]] = field(default_factory=list)
    receipt_id: str = ""
    next_action: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def blank_sheet(sheet_id: str = "sheet-001") -> WorkbookSheet:
    return WorkbookSheet(
        sheet_id=sheet_id,
        title="Analog Forge Workbook Action Sheet",
        active_center="C token not yet placed",
        source_notebook="grey_gradient:notebook:01",
        loose_page="grey_gradient:loose_paper:01",
        gradient_colors=["red", "green", "blue"],
        decision_question="Can this state continue on the current page?",
        continue_or_new_page="undecided",
        proof_or_obligation="undecided",
        next_action="Place C token, add three-color gradient, then decide proof/obligation.",
    )
