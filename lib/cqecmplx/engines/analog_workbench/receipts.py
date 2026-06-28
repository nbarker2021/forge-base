from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional
from datetime import datetime
import json

VALID_FOLLOWUPS = {"proof", "obligation", "new_page", "defer"}

@dataclass
class Receipt:
    action_id: str
    observed_action: str
    source_page: str
    colors_used: List[str]
    gradient_valid: bool
    decision_continue: bool
    followup: str
    loose_objects: List[str] = field(default_factory=list)
    bound_destination: Optional[str] = None
    strings_connected: List[str] = field(default_factory=list)
    cards_used: List[str] = field(default_factory=list)
    dice_used: List[str] = field(default_factory=list)
    closure_formula: str = ""
    idempotence_status: str = "untested"
    open_obligations: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def validate(self) -> List[str]:
        errors: List[str] = []
        if len(set(self.colors_used)) < 3:
            errors.append("At least three distinct colors are required for a live gradient readout.")
        if self.followup not in VALID_FOLLOWUPS:
            errors.append(f"Invalid followup: {self.followup}")
        if self.followup == "proof" and not self.bound_destination:
            errors.append("Proof followup requires a bound destination.")
        if self.followup == "obligation" and not self.open_obligations:
            errors.append("Obligation followup should name at least one open obligation.")
        return errors

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def receipt_from_action(action_id: str, observed_action: str, colors_used: List[str], continue_here: bool) -> Receipt:
    gradient_valid = len(set(colors_used)) >= 3
    followup = "proof" if continue_here and gradient_valid else "obligation"
    return Receipt(
        action_id=action_id,
        observed_action=observed_action,
        source_page="loose_grey_sheet_001",
        colors_used=colors_used,
        gradient_valid=gradient_valid,
        decision_continue=continue_here,
        followup=followup,
        loose_objects=["grey_gradient:loose_paper:01", "clear:clear_sleeve:01"],
        bound_destination="white:notebook:01" if followup == "proof" else None,
        closure_formula="read(action)->state; read(state)->same_class" if followup == "proof" else "open_route->obligation",
        idempotence_status="passed" if followup == "proof" else "deferred",
        open_obligations=[] if followup == "proof" else ["resolve missing gradient or binding route"],
    )
