"""Machine-falsifiable Tier A checks for Ring 1 prize core."""

from __future__ import annotations

import json
import pathlib
import tempfile
from typing import Any, Callable

from lattice_forge.f4_action import (
    closed_form_rule30_8x8_transition_exact,
    decompose_8x8_via_block_action_exact,
    search_for_su3_closure_scale,
    verify_n3_su3_closure_exact,
)
from lattice_forge.forge import Forge
from lattice_forge.jordan_j3 import verify_j3o_axioms
from lattice_forge.witness.engine import WitnessEngine
from lattice_forge.witness.state_keys import make_regime_encode_key
from lattice_forge.octonion import verify_octonion_axioms
from lattice_forge.decomposition import verify_all_theorems, verify_checkpoint_store
from lattice_forge.rule30 import (
    verify_chart_j3o_isomorphism,
    verify_rule30_chart_local_readout,
)

BreakRunner = Callable[[int], dict[str, Any]]


def tier_a_break_specs() -> list[dict[str, str]]:
    return [
        {"break_id": "B-T1", "claim_id": "T1", "verifier_id": "verify_octonion_axioms"},
        {"break_id": "B-T2", "claim_id": "T2", "verifier_id": "verify_j3o_axioms"},
        {"break_id": "B-T3", "claim_id": "T3", "verifier_id": "verify_chart_j3o_isomorphism"},
        {"break_id": "B-T4", "claim_id": "T4", "verifier_id": "verify_n3_su3_closure_exact"},
        {"break_id": "B-T5", "claim_id": "T5", "verifier_id": "search_for_su3_closure_scale"},
        {"break_id": "B-T6", "claim_id": "T6", "verifier_id": "decompose_8x8_via_block_action_exact"},
        {
            "break_id": "B-T7",
            "claim_id": "T7",
            "verifier_id": "closed_form_rule30_8x8_transition_exact",
        },
        {"break_id": "B-T8", "claim_id": "T8", "verifier_id": "forge.can_close"},
        {
            "break_id": "B-decomp",
            "claim_id": "DECOMP-PAPER",
            "verifier_id": "verify_all_theorems+verify_checkpoint_store",
        },
        {
            "break_id": "B-BONUS",
            "claim_id": "BONUS",
            "verifier_id": "verify_rule30_chart_local_readout",
        },
        {
            "break_id": "B-WITNESS",
            "claim_id": "WITNESS-INDEX",
            "verifier_id": "Forge.witnessed_lookup+regime_encode",
        },
    ]


def _honest_status(raw: str) -> str:
    """Never upgrade pass_with_open_gaps or conj to pass."""
    if raw in {"pass_with_open_gaps", "conj", "CONJ"}:
        return raw
    return raw


def _run_break(
    break_id: str,
    runner: BreakRunner,
    *,
    max_depth: int,
    require_pass: bool = True,
) -> dict[str, Any]:
    result = runner(max_depth)
    status = _honest_status(str(result.get("status", "unknown")))
    passed = status == "pass" if require_pass else status in {"pass", "pass_with_open_gaps"}
    return {
        "break_id": break_id,
        "status": status,
        "passed": passed,
        "result": result,
    }


def tier_a_breaks(max_depth: int = 256) -> dict[str, Any]:
    """Run Tier A falsification checks (B-T1..B-T8 + B-BONUS)."""
    checks: list[dict[str, Any]] = []

    checks.append(
        _run_break("B-T1", lambda _d: verify_octonion_axioms(), max_depth=max_depth)
    )
    checks.append(
        _run_break("B-T2", lambda _d: verify_j3o_axioms(), max_depth=max_depth)
    )
    checks.append(
        _run_break(
            "B-T3",
            lambda d: verify_chart_j3o_isomorphism(max_depth=d),
            max_depth=max_depth,
        )
    )
    checks.append(
        _run_break(
            "B-T4",
            lambda _d: verify_n3_su3_closure_exact(),
            max_depth=max_depth,
        )
    )

    t5 = search_for_su3_closure_scale(max_scale=8)
    t5_status = "pass" if t5.get("best_scale") == 3 and t5.get("closed_at_a_scale") else "fail"
    checks.append(
        {
            "break_id": "B-T5",
            "status": t5_status,
            "passed": t5_status == "pass",
            "result": t5,
        }
    )

    t6 = decompose_8x8_via_block_action_exact(n_steps=3)
    t6_ok = t6["claim"]["both_trace_blocks_close_as_s3_elements"]
    checks.append(
        {
            "break_id": "B-T6",
            "status": "pass" if t6_ok else "fail",
            "passed": t6_ok,
            "result": t6,
        }
    )

    t7 = closed_form_rule30_8x8_transition_exact()
    row_sums_ok = all(str(sum(t7["matrix"][i])) == "1" for i in range(len(t7["states"])))
    checks.append(
        {
            "break_id": "B-T7",
            "status": "pass" if row_sums_ok else "fail",
            "passed": row_sums_ok,
            "result": {"n_states": len(t7["states"]), "all_row_sums_unity": row_sums_ok},
        }
    )

    forge = Forge.open(pathlib.Path(tempfile.mkdtemp(prefix="lf-falsify-")))
    niemeiers = [
        "Niemeier:E8^3",
        "Niemeier:D16_E8",
        "Niemeier:A17_E7",
        "Niemeier:D10_E7^2",
        "Niemeier:A11_D7_E6",
        "Niemeier:E6^4",
        "Niemeier:A5^4_D4",
        "Niemeier:D4^6",
    ]
    paths = sum(
        1
        for tgt in niemeiers
        if forge.can_close("F4", tgt)
        .get("result", {})
        .get("can_close", {})
        .get("answer", "")
        .startswith("yes")
    )
    checks.append(
        {
            "break_id": "B-T8",
            "status": "pass" if paths == 8 else "fail",
            "passed": paths == 8,
            "result": {"paths_count": paths, "expected_paths_count": 8},
        }
    )

    checks.append(
        _run_break(
            "B-BONUS",
            lambda d: verify_rule30_chart_local_readout(max_depth=d),
            max_depth=max_depth,
        )
    )

    witness_depth = min(max_depth, 128)
    forge_w = Forge.open(pathlib.Path(tempfile.mkdtemp(prefix="lf-falsify-witness-")))
    engine = WitnessEngine(forge_w)
    engine.regime_c_encode(max_depth=witness_depth)
    primary_key = make_regime_encode_key(
        from_regime="A", to_regime="C", max_depth=witness_depth
    )
    lookup = forge_w.witnessed_lookup(primary_key).get("result", {})
    witness_ok = lookup.get("witnessed") is True and lookup.get("answer") == "WITNESSED"
    checks.append(
        {
            "break_id": "B-WITNESS",
            "status": "pass" if witness_ok else "fail",
            "passed": witness_ok,
            "result": {
                "state_key": primary_key,
                "lookup_answer": lookup.get("answer"),
                "witnessed": lookup.get("witnessed"),
            },
            "not_in_ring1": True,
        }
    )

    theorem_depths = range(1, 33) if max_depth <= 256 else range(1, 129)
    decomp_theorems = verify_all_theorems(decomposition_depths=theorem_depths)
    decomp_checkpoints = verify_checkpoint_store(max_depth=max_depth)
    decomp_ok = (
        decomp_theorems.get("status") == "pass"
        and decomp_checkpoints.get("status") == "pass"
    )
    checks.append(
        {
            "break_id": "B-decomp",
            "status": "pass" if decomp_ok else "fail",
            "passed": decomp_ok,
            "result": {"theorems": decomp_theorems, "checkpoints": decomp_checkpoints},
            "not_in_ring1": True,
        }
    )

    failures = [c["break_id"] for c in checks if not c["passed"]]
    return {
        "tier": "A",
        "max_depth": max_depth,
        "checks": checks,
        "breaks": checks,
        "failures": failures,
        "overall_status": "pass" if not failures else "fail",
    }


def run_tier_a(
    *,
    max_depth: int = 256,
    quick: bool = False,
    registry_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    depth = 256 if quick else max_depth
    report = tier_a_breaks(max_depth=depth)
    if registry_path is None:
        default = pathlib.Path(__file__).resolve().parents[3] / "claims" / "registry.jsonl"
        if default.is_file():
            registry_path = default
    if registry_path and registry_path.is_file():
        claim_ids = []
        with registry_path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row.get("ring") == 1 and str(row.get("honesty_label", "")).upper() == "PROVEN":
                    claim_ids.append(row["claim_id"])
        report["registry_ring1_proven_claim_ids"] = claim_ids
    return report
