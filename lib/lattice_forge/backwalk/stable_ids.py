"""Content-addressed run ids for lattice_forge backwalk — no uuid4 churn."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


def _canon(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def backwalk_run_id(phase: str, work_db: str, config: Dict[str, Any]) -> str:
    body = {"phase": phase, "work_db": work_db, "config": config}
    return "bw-" + hashlib.sha256(_canon(body).encode()).hexdigest()[:16]


def weyl_run_id(work_db: str, quadrant_plan: list, concat_only: bool) -> str:
    body = {
        "work_db": work_db,
        "quadrants": quadrant_plan,
        "concat_only": concat_only,
    }
    return "weyl-" + hashlib.sha256(_canon(body).encode()).hexdigest()[:16]


def lattice_space_run_id(work_db: str, resume: bool) -> str:
    body = {"work_db": work_db, "resume": resume}
    return "lsp-" + hashlib.sha256(_canon(body).encode()).hexdigest()[:16]
