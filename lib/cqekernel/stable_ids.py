"""Content-addressed stable IDs for cqe-kernel — no uuid4 identity churn."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple


def _canon(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _hash(payload: Dict[str, Any], length: int = 32) -> str:
    return hashlib.sha256(_canon(payload).encode()).hexdigest()[:length]


def request_id_for(
    raw_hash: str,
    mode: str,
    source_type: str,
    observer_id: Optional[str] = None,
) -> str:
    return "req-" + _hash(
        {
            "raw_hash": raw_hash,
            "mode": mode,
            "source_type": source_type,
            "observer": observer_id or "",
        },
        16,
    )


def event_id_for(
    event_type: str,
    payload: Dict[str, Any],
    request_id: Optional[str],
    input_hash: Optional[str],
    output_hash: Optional[str],
) -> str:
    return "evt-" + _hash(
        {
            "event_type": event_type,
            "payload": payload,
            "request_id": request_id,
            "input_hash": input_hash,
            "output_hash": output_hash,
        },
        16,
    )


def cform_id_for(canonical_hash: str, index: int, source_carrier_hash: str) -> str:
    return "cform-" + _hash(
        {"canonical_hash": canonical_hash, "index": index, "source": source_carrier_hash},
        12,
    )


def placement_id_for(
    source_request_id: str,
    left: Dict[str, Any],
    center: Dict[str, Any],
    right: Dict[str, Any],
    orientation: str,
) -> str:
    return "plc-" + _hash(
        {
            "request": source_request_id,
            "left": left,
            "center": center,
            "right": right,
            "orientation": orientation,
        },
        12,
    )


def carrier_id_for(canonical_hash: str, source_hash: str) -> str:
    return "4bit-" + _hash(
        {"canonical_hash": canonical_hash, "source_hash": source_hash},
        12,
    )


def admission_id_for(
    left_state: int,
    center_state: int,
    right_state: int,
    center_threshold: int,
) -> str:
    return "adm-" + _hash(
        {"l": left_state, "c": center_state, "r": right_state, "t": center_threshold},
        12,
    )


def snapshot_id_for(
    request_id: str,
    source_hash: str,
    carrier_hash: str,
    ribbon_hash: str,
    ledger_hash: str,
    parent_snapshot: Optional[str],
) -> str:
    return "snap-" + _hash(
        {
            "request_id": request_id,
            "source_hash": source_hash,
            "carrier_hash": carrier_hash,
            "ribbon_hash": ribbon_hash,
            "ledger_hash": ledger_hash,
            "parent": parent_snapshot,
        },
        16,
    )


def analog_step_id(
    digital_equivalent: str,
    analog_action: str,
    expected_receipt: str,
) -> str:
    return "step-" + _hash(
        {
            "digital": digital_equivalent,
            "action": analog_action,
            "expected": expected_receipt,
        },
        12,
    )


def socratic_question_id(target_id: str, purpose: str, question: str) -> str:
    return "sq-" + _hash({"target": target_id, "purpose": purpose, "q": question}, 12)


def obligation_prefix_for(source_carrier_hash: str, selected_index: int) -> str:
    return "obl-" + _hash({"source": source_carrier_hash, "selected": selected_index}, 12)


def aperture_id_for(
    kind: str,
    position: Tuple[int, ...],
    local_state: Dict[str, Any],
) -> str:
    return "apr-" + _hash(
        {"kind": kind, "position": list(position), "state": local_state},
        12,
    )
