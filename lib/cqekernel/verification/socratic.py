"""
Socratic wrapping engine.

For each claim/object the kernel asks the canonical eight questions:

  1. What upstream object does this inherit?
  2. What downstream object does it feed?
  3. Is this terminal or mid-chain?
  4. What evidence class is attached?
  5. What would falsify it?
  6. What obligation remains?
  7. What slot is unfilled?
  8. What receipt supports it?

The questions are deterministic. They are emitted as a list of
``SocraticQuestion`` records.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List

from ..core.status import EvidenceStatus


@dataclass
class SocraticQuestion:
    question_id: str
    target_id: str
    question: str
    purpose: str
    required_answer_type: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "target_id": self.target_id,
            "question": self.question,
            "purpose": self.purpose,
            "required_answer_type": self.required_answer_type,
        }


_CANONICAL: List[Dict[str, str]] = [
    ("upstream", "What upstream object does this inherit?", "text", "object_id"),
    ("downstream", "What downstream object does it feed?", "text", "object_id"),
    ("role", "Is this terminal or mid-chain?", "enum", "terminal|mid_chain"),
    ("evidence", "What evidence class is attached?", "enum",
     "|".join(e.value for e in EvidenceStatus)),
    ("falsifier", "What would falsify it?", "text", "test_description"),
    ("obligation", "What obligation remains?", "text", "obligation_id"),
    ("slot", "What slot is unfilled?", "enum", "C|L|R|B|T|O|W|A|none"),
    ("receipt", "What receipt supports it?", "text", "receipt_id"),
]


def wrap(target_id: str) -> List[SocraticQuestion]:
    """Build the canonical 8 questions for a target."""
    out: List[SocraticQuestion] = []
    for purpose, q, rat, _ in [(c[0], c[1], c[2], c[3]) for c in _CANONICAL]:
        out.append(
            SocraticQuestion(
                question_id=str(uuid.uuid4()),
                target_id=target_id,
                question=q,
                purpose=purpose,
                required_answer_type=rat,
            )
        )
    return out


@dataclass
class RoleClassification:
    """How the target sits in the proof chain."""

    target_id: str
    role: str  # "terminal" or "mid_chain"
    evidence_class: str
    has_receipt: bool
    filled_slots: List[str]
    missing_slots: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "role": self.role,
            "evidence_class": self.evidence_class,
            "has_receipt": self.has_receipt,
            "filled_slots": list(self.filled_slots),
            "missing_slots": list(self.missing_slots),
        }


def classify(
    target_id: str,
    *,
    evidence_class: EvidenceStatus,
    has_receipt: bool,
    filled_slots: List[str],
    missing_slots: List[str],
) -> RoleClassification:
    """Classify the proof-chain role of a target."""
    role = "terminal" if not missing_slots else "mid_chain"
    return RoleClassification(
        target_id=target_id,
        role=role,
        evidence_class=evidence_class.value,
        has_receipt=has_receipt,
        filled_slots=list(filled_slots),
        missing_slots=list(missing_slots),
    )
