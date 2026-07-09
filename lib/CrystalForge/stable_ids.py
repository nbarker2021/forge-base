"""Content-addressed stable IDs — no uuid4 identity churn at receipt level."""
from __future__ import annotations

import hashlib
import json
from typing import List, Optional


def crystal_id_for_name(name: str, namespace: str = "crystalforge") -> str:
    """Deterministic crystal primary key from human name."""
    return "c" + hashlib.sha256(f"{namespace}:{name}".encode()).hexdigest()[:11]


def node_id_for(crystal_id: str, content: str, labels: Optional[List[str]] = None) -> str:
    """Deterministic node id from crystal + content (+ labels)."""
    payload = json.dumps(
        {"crystal_id": crystal_id, "content": content[:2000], "labels": labels or []},
        sort_keys=True,
        separators=(",", ":"),
    )
    return "node-" + hashlib.sha256(payload.encode()).hexdigest()[:12]


def brain_row_id(agent_id: str) -> str:
    """Brain DB row key == agent id (never brain-{uuid})."""
    if not agent_id:
        raise ValueError("agent_id required for stable brain row key")
    return agent_id
