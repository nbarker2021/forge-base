"""Content-addressed ids for SplatForgeField — no uuid/time churn."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


def _canon(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def field_child_name(parent_id: str, op: str, payload: Dict[str, Any]) -> str:
    h = hashlib.sha256(_canon({"parent": parent_id, "op": op, "payload": payload}).encode())
    return f"fld-{h.hexdigest()[:16]}"
