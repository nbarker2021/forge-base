"""Run empirical platforms across depth ladders."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from lattice_forge.empirical.exhaust import ladder_for_mode
from lattice_forge.empirical.manifest import (
    EmpiricalPlatform,
    default_ladder_for_label,
    load_platform_manifest,
    platform_by_claim,
)
from lattice_forge.empirical.resolver import resolve_runner


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def _normalize_result(verifier_id: str, raw: dict[str, Any]) -> dict[str, Any]:
    if "status" in raw:
        return raw
    if verifier_id == "search_for_su3_closure_scale":
        ok = raw.get("best_scale") == 3 and raw.get("closed_at_a_scale")
        return {**raw, "status": "pass" if ok else "fail"}
    if verifier_id == "decompose_8x8_via_block_action_exact":
        ok = raw.get("claim", {}).get("both_trace_blocks_close_as_s3_elements")
        return {**raw, "status": "pass" if ok else "fail"}
    if verifier_id == "closed_form_rule30_8x8_transition_exact":
        matrix = raw.get("matrix", [])
        ok = matrix and all(sum(matrix[i]) == 1 for i in range(len(matrix)))
        return {**raw, "status": "pass" if ok else "fail"}
    return {**raw, "status": "unknown"}


def _expected_pass(honesty_label: str, status: str) -> bool:
    if honesty_label == "CONJ":
        return status in {"conj", "CONJ", "pass_with_open_gaps", "pass"}
    if honesty_label == "BOUNDED_EXEC":
        return status in {"pass", "pass_with_open_gaps", "bounded_exec", "BOUNDED_EXEC"}
    if honesty_label == "EXPRESSIBLE":
        return status in {"pass", "pass_with_open_gaps", "expressible", "EXPRESSIBLE"}
    if honesty_label in {"PROVEN", "TRANSPORTED"}:
        return status == "pass"
    return status in {"pass", "pass_with_open_gaps"}


def run_claim_platform(
    claim_id: str,
    *,
    exhaustion_mode: str = "standard",
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    platforms = load_platform_manifest(manifest_path)
    pl = platform_by_claim(platforms, claim_id)
    if pl is None:
        return {"claim_id": claim_id, "status": "fail", "error": "platform not in manifest"}
    ladder = pl.depth_ladder or default_ladder_for_label(pl.honesty_label, exhaustion_mode)
    if not ladder:
        ladder = ladder_for_mode(exhaustion_mode)
    mode, runner = resolve_runner(pl.verifier_id, claim_id=pl.claim_id, proof_key=pl.proof_key)
    depth_results: list[dict[str, Any]] = []
    t0 = time.perf_counter()
    if mode in {"citation", "transport", "engineering", "unknown"} and runner is None:
        return {
            "claim_id": claim_id,
            "platform_id": pl.platform_id,
            "verifier_id": pl.verifier_id,
            "honesty_label": pl.honesty_label,
            "resolution_mode": mode,
            "status": "skipped",
            "depth_ladder": ladder,
            "notes": pl.notes or f"non-executable verifier ({mode})",
            "elapsed_s": round(time.perf_counter() - t0, 3),
        }
    if runner is None:
        return {
            "claim_id": claim_id,
            "status": "fail",
            "error": f"no runner for {pl.verifier_id}",
            "resolution_mode": mode,
        }
    overall_ok = True
    for depth in ladder:
        raw = _normalize_result(pl.verifier_id, runner(depth))
        status = str(raw.get("status", "unknown"))
        ok = _expected_pass(pl.honesty_label, status)
        depth_results.append(
            {"max_depth": depth, "status": status, "passed": ok, "result": _json_safe(raw)}
        )
        if not ok and pl.honesty_label in {"PROVEN", "TRANSPORTED", "BOUNDED_EXEC", "EXPRESSIBLE"}:
            overall_ok = False
    worst = depth_results[-1]["status"] if depth_results else "unknown"
    return {
        "claim_id": claim_id,
        "platform_id": pl.platform_id,
        "verifier_id": pl.verifier_id,
        "honesty_label": pl.honesty_label,
        "falsify_break": pl.falsify_break,
        "resolution_mode": mode,
        "depth_ladder": ladder,
        "depth_results": depth_results,
        "status": "pass" if overall_ok else "fail",
        "worst_status": worst,
        "elapsed_s": round(time.perf_counter() - t0, 3),
    }


def run_empirical_matrix(
    *,
    exhaustion_mode: str = "quick",
    claim_ids: list[str] | None = None,
    manifest_path: Path | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    platforms = load_platform_manifest(manifest_path)
    if claim_ids:
        platforms = [p for p in platforms if p.claim_id in claim_ids]
    results: list[dict[str, Any]] = []
    failures: list[str] = []
    for pl in platforms:
        row = run_claim_platform(pl.claim_id, exhaustion_mode=exhaustion_mode, manifest_path=manifest_path)
        results.append(row)
        if row.get("status") == "fail":
            failures.append(pl.claim_id)
        elif row.get("status") == "skipped":
            continue
    report = {
        "exhaustion_mode": exhaustion_mode,
        "platform_count": len(platforms),
        "failures": failures,
        "overall_status": "pass" if not failures else "fail",
        "claims": results,
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(_json_safe(report), indent=2) + "\n", encoding="utf-8")
    return report
