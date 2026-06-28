from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List
import json

from .kit import build_eightfold_kit
from .receipts import receipt_from_action, Receipt
from .operators import roll_dice, draw_card, legal_binding, string_relation
from .workbook import WorkbookSheet

class WorkbenchSimulator:
    """Small deterministic simulator for the analog workbook loop."""

    def __init__(self, copies: int = 8):
        self.manifest = build_eightfold_kit(copies=copies)
        self.receipts: List[Receipt] = []
        self.sheets: List[WorkbookSheet] = []

    def run_action(self, action_id: str, observed_action: str, colors: List[str], continue_here: bool = True) -> Dict[str, object]:
        receipt = receipt_from_action(action_id, observed_action, colors, continue_here)
        binding_ok, binding_kind = legal_binding(colors)
        die = roll_dice("Is the unresolved route randomness or a possible legal branch?", seed=len(action_id))
        card = draw_card(seed=len(observed_action))
        relation = string_relation("loose_grey_sheet_001", receipt.bound_destination or "black:obligation_sheet:01", colors[0] if colors else "grey_gradient")
        if binding_ok and receipt.followup == "proof":
            receipt.strings_connected.append(relation["relation"] + ":" + relation["color"])
        elif not binding_ok:
            receipt.open_obligations.append(f"binding failed: {binding_kind}")
            receipt.followup = "obligation"
            receipt.bound_destination = None
        sheet = WorkbookSheet(
            sheet_id=f"sheet-{action_id}",
            title="Analog Forge Workbook Action Sheet",
            active_center="token:C:01",
            source_notebook="grey_gradient:notebook:01",
            loose_page="grey_gradient:loose_paper:01",
            gradient_colors=colors,
            decision_question="Can this state continue on the current page?",
            continue_or_new_page="continue" if continue_here else "new_page",
            proof_or_obligation=receipt.followup,
            legal_bindings=[binding_kind] if binding_ok else [],
            strings=[relation],
            receipt_id=receipt.action_id,
            next_action="bind receipt" if receipt.followup == "proof" else "resolve open obligation",
        )
        self.receipts.append(receipt)
        self.sheets.append(sheet)
        return {
            "receipt": receipt.to_dict(),
            "sheet": sheet.to_dict(),
            "dice_event": asdict(die),
            "card_event": asdict(card),
            "binding": {"ok": binding_ok, "kind": binding_kind},
        }

    def demo(self) -> Dict[str, object]:
        result = self.run_action(
            "demo-001",
            "Observe a claim, place it on grey substrate, add RGB gradient, and bind if idempotent.",
            ["red", "green", "blue"],
            True,
        )
        return {
            "kit_object_count": self.manifest["object_count"],
            "run": result,
            "receipt_count": len(self.receipts),
            "sheet_count": len(self.sheets),
        }

    def export(self, out_dir: str | Path) -> Dict[str, str]:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        paths = {}
        paths["kit_manifest"] = str(out / "kit_manifest.json")
        (out / "kit_manifest.json").write_text(json.dumps(self.manifest, indent=2))
        paths["receipts"] = str(out / "receipts.json")
        (out / "receipts.json").write_text(json.dumps([r.to_dict() for r in self.receipts], indent=2))
        paths["workbook_sheets"] = str(out / "workbook_sheets.json")
        (out / "workbook_sheets.json").write_text(json.dumps([s.to_dict() for s in self.sheets], indent=2))
        return paths
