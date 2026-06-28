from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Any, Dict, List

COLORS = ("red", "green", "blue", "white", "black", "grey", "neon", "clear")
FOLLOWUPS = ("proof", "obligation", "boundary", "deferred")

@dataclass(frozen=True)
class Paper00Claim:
    claim_id: str
    statement: str
    local_object: str
    tool_or_solver: str
    target: str
    expected_receipt: str

@dataclass(frozen=True)
class TransportRow:
    transport_id: str
    paper: str
    claim_id: str
    source_object: str
    target_object: str
    tool_or_solver: str
    preserved_quantity: str
    receipt: str
    followup: str
    color_state: str
    proof_tree: List[str]


def _digest(*parts: str) -> str:
    return sha256("|".join(parts).encode("utf-8", errors="replace")).hexdigest()[:12]


def _color_from_claim(claim: Paper00Claim) -> str:
    n = sum(claim.statement.encode("utf-8", errors="replace")) + len(claim.local_object)
    return COLORS[n % len(COLORS)]


def build_transport_row(claim: Paper00Claim, preserved_quantity: str = "identity-through-receipt") -> TransportRow:
    """Convert a paper claim into a receipted transport row.

    Paper 00 rule: no prose claim is accepted as paper-bound until it is mapped
    into claim -> local object -> tool/solver -> receipt -> target.
    """
    tid = "P00-" + _digest(claim.claim_id, claim.statement, claim.local_object)
    color = _color_from_claim(claim)
    followup = "proof" if all([claim.statement, claim.local_object, claim.tool_or_solver, claim.expected_receipt]) else "obligation"
    proof_tree = [
        f"claim:{claim.claim_id}",
        f"local_object:{claim.local_object}",
        f"tool:{claim.tool_or_solver}",
        f"receipt:{claim.expected_receipt}",
        f"target:{claim.target}",
    ]
    return TransportRow(
        transport_id=tid,
        paper="Paper 00",
        claim_id=claim.claim_id,
        source_object=claim.local_object,
        target_object=claim.target,
        tool_or_solver=claim.tool_or_solver,
        preserved_quantity=preserved_quantity,
        receipt=claim.expected_receipt,
        followup=followup,
        color_state=color,
        proof_tree=proof_tree,
    )


def validate_transport_row(row: TransportRow) -> Dict[str, Any]:
    missing = []
    for field in ["transport_id", "claim_id", "source_object", "target_object", "tool_or_solver", "receipt"]:
        if not getattr(row, field):
            missing.append(field)
    ok_followup = row.followup in FOLLOWUPS
    ok_color = row.color_state in COLORS
    ok_tree = len(row.proof_tree) >= 5 and row.proof_tree[0].startswith("claim:")
    return {
        "ok": not missing and ok_followup and ok_color and ok_tree,
        "missing": missing,
        "ok_followup": ok_followup,
        "ok_color": ok_color,
        "ok_proof_tree": ok_tree,
        "row": asdict(row),
    }


def run_manufacturing_example() -> Dict[str, Any]:
    """Practical IRL example: manufacturing defect claim transport.

    An observed defect is not accepted as a cause claim until it transports from
    observation to local object, tool, receipt, and target corrective action.
    """
    claims = [
        Paper00Claim(
            claim_id="QA-OBS-001",
            statement="Observed hairline crack on batch A panel near left fastener.",
            local_object="photo crop + batch id + station log",
            tool_or_solver="PixleForge patch receipt + ResearchCraft provenance row",
            target="defect-localization claim",
            expected_receipt="receipt:defect_patch_batchA_station3",
        ),
        Paper00Claim(
            claim_id="QA-CAUSE-001",
            statement="Fastener torque variance may have produced local stress.",
            local_object="torque log + crack position + material lot",
            tool_or_solver="Paper00 transport validator",
            target="cause obligation pending stress test",
            expected_receipt="receipt:torque_variance_obligation",
        ),
        Paper00Claim(
            claim_id="QA-ACTION-001",
            statement="Retest station 3 torque calibration before next run.",
            local_object="calibration procedure + station 3 tool id",
            tool_or_solver="ResearchCraft action ledger",
            target="corrective-action proof path",
            expected_receipt="receipt:station3_calibration_action",
        ),
    ]
    rows = [build_transport_row(c) for c in claims]
    validations = [validate_transport_row(r) for r in rows]
    return {
        "example_id": "paper00_manufacturing_qa_transport",
        "focus": "manufacturing quality assurance defect triage",
        "rows": [asdict(r) for r in rows],
        "validations": validations,
        "ok": all(v["ok"] for v in validations),
    }


def build_workbook_sheet() -> Dict[str, Any]:
    """Analog workbook sheet for Paper 00."""
    return {
        "sheet_id": "P00-WB-001",
        "paper": "Paper 00",
        "title": "Transport Contract Workbook Sheet",
        "physical_grid": "2x2 origin grid with grey substrate and black/white follow-up lane",
        "colors": {
            "grey": "unresolved claim substrate",
            "white": "claim transported to proof receipt",
            "black": "claim carried as obligation",
            "red_green_blue": "local object / tool / receipt triad",
            "clear": "temporary overlay for reviewer challenge",
            "neon": "boundary-active claim requiring recheck",
        },
        "hand_steps": [
            "Write one claim on a grey card.",
            "Place claim in the center C square of the 2x2 grid.",
            "Assign red to local object, green to tool/solver, blue to receipt.",
            "If all three are present, move the card to the white proof lane.",
            "If any of the three is missing, move the card to the black obligation lane.",
            "Bind white cards into Paper 00 appendix; keep black cards loose until resolved.",
        ],
        "digital_equivalent": "forgefactory.papers.paper00_transport_contract",
    }
