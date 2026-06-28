"""Deployment-shaped verification lanes for versioned runtime receipts."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from .cache import FormulaicBillionAddressLibrary


REPO_ROOT = Path(__file__).resolve().parents[2]


def _deployed_formulaic_address(n: int) -> tuple[subprocess.CompletedProcess[str], Any]:
    env = dict(os.environ)
    src = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "cmplx_r30.cli",
            "library",
            "address",
            "--n",
            str(n),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        receipt = json.loads(process.stdout)
    except json.JSONDecodeError:
        receipt = None
    return process, receipt


def verify_formulaic_address_deployment_lane(n: int) -> dict[str, Any]:
    """Verify one formulaic address through DTT, TDD, and TTD receipts."""
    if n < 0:
        raise ValueError("N must be non-negative")
    first_process, first_receipt = _deployed_formulaic_address(n)
    library = FormulaicBillionAddressLibrary()
    in_process_receipt = library.compile(n)
    flatten_round_trip_exact = library.flatten(in_process_receipt) == n
    second_process, second_receipt = _deployed_formulaic_address(n)

    dtt = {
        "deployed_cli_exit_zero": first_process.returncode == 0,
        "deployed_receipt_json": isinstance(first_receipt, dict),
    }
    tdd = {
        "in_process_replay_exact": first_receipt == in_process_receipt,
        "flatten_round_trip_exact": flatten_round_trip_exact,
    }
    ttd = {
        "second_deployed_cli_exit_zero": second_process.returncode == 0,
        "deployed_receipt_deterministic": second_receipt == first_receipt,
    }
    passed = all(dtt.values()) and all(tdd.values()) and all(ttd.values())
    return {
        "status": "pass" if passed else "fail",
        "lane": "DTT|TDD|TTD",
        "N": n,
        "DTT": dtt,
        "TDD": tdd,
        "TTD": ttd,
        "receipt": first_receipt,
        "proof_boundary": (
            "deployment-shaped address receipt verification; semantic Weyl and "
            "Cartan classification remain separate"
        ),
    }
