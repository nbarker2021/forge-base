"""Content-addressed stable IDs for PixelForge — no uuid4 identity churn."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional


def _canon(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def surface_id_for(
    width: int,
    height: int,
    dpr: float,
    kind: str,
    input_caps: Optional[Dict[str, bool]] = None,
) -> str:
    body = {
        "width": int(width),
        "height": int(height),
        "dpr": round(float(dpr), 6),
        "kind": kind,
        "input_caps": input_caps or {},
    }
    return "srf-" + hashlib.sha256(_canon(body).encode()).hexdigest()[:10]


def stroke_id_for(
    surface_id: str,
    kind: str,
    color: str,
    target: Optional[str],
    seq: int,
) -> str:
    body = {
        "surface": surface_id,
        "kind": kind,
        "color": color,
        "target": target or "",
        "seq": seq,
    }
    return "ink-" + hashlib.sha256(_canon(body).encode()).hexdigest()[:10]


def stream_id_for(
    fps: float,
    projection: str,
    parity_rule: str,
    entropy_slack: float,
) -> str:
    body = {
        "fps": round(float(fps), 6),
        "projection": projection,
        "parity_rule": parity_rule,
        "entropy_slack": round(float(entropy_slack), 6),
    }
    return "fs-" + hashlib.sha256(_canon(body).encode()).hexdigest()[:10]
