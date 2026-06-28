"""
honesty_harness.py — Formalize open CONJ claims into bounded, machine-checked harnesses.

Each verifier returns:
  - status: pass | pass_with_open_gaps | fail
  - honesty_label: target promotion label (CONJ only when theorem genuinely open)
  - claim_id, proof_key, evidence

Policy: promote to BOUNDED_EXEC when a finite-window property is verified.
Keep CONJ only for all-depth / sublinear / external-grade claims still open.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Ring 1 obligations (ledger-aligned)
# ---------------------------------------------------------------------------


def verify_sheet_power_law_bounded(
    page_count: int = 2,
    page_size: int = 4096,
    block_size: int = 8,
    max_order: int = 4,
) -> dict[str, Any]:
    """Tested pages share one sheet-operator hash (not yet all-page induction)."""
    from .rule30 import rule30_sheet_operator, verify_rule30_sheet_operator

    model = rule30_sheet_operator(
        page_count=page_count,
        page_size=page_size,
        block_size=block_size,
        max_order=max_order,
    )
    verified = verify_rule30_sheet_operator(model)
    power = model.get("power_law", {})
    stable = bool(power.get("same_operator_reused"))
    ok = verified.get("status") in ("pass", "pass_with_open_gaps") and stable
    return {
        "claim_id": "rule30.sheet_operator.power_law",
        "proof_key": "SHEET_POWER_LAW_BOUNDED",
        "status": "pass" if ok else "fail",
        "honesty_label": "BOUNDED_EXEC" if ok else "CONJ",
        "promoted_from": "CONJ",
        "narrowed_claim": (
            "Over the declared finite page window, sheet pages reuse one stable "
            "relative-table operator hash (T_page^k on tested pages)."
        ),
        "still_conj": "All-integer page induction T_page^k for unbounded k",
        "evidence": power,
        "verifier": verified,
    }


def verify_depth_extraction_accounting(max_depth: int = 256) -> dict[str, Any]:
    """
    BOUNDED_EXEC surrogate for extraction: block tower + extractor match canonical column.
    The sublinear depth-only shortcut theorem remains CONJ.
    """
    from .block_tower import verify_block_tower
    from .rule30_block_extractor import verify_extractor as verify_block_extractor

    depth = min(max_depth, 4096)
    bt = verify_block_tower(max_depth=depth)
    ex = verify_block_extractor(max_depth=depth)
    surrogate_ok = (
        bt.get("status") == "pass"
        and ex.get("status") == "pass"
        and ex.get("individual_mismatch_count", 1) == 0
    )
    return {
        "claim_id": "rule30.prize.depth_only_shortcut",
        "proof_key": "DEPTH_EXTRACTION_ACCOUNTING",
        "status": "pass" if surrogate_ok else "fail",
        "honesty_label": "CONJ",
        "surrogate_label": "BOUNDED_EXEC",
        "surrogate_claim_id": "rule30.extraction.block_addressed",
        "promoted_from": "CONJ",
        "narrowed_claim": (
            f"At tested depth {depth}, center column is recoverable via block-addressed "
            "checkpoint I/O (not a constant-time closed form in n alone)."
        ),
        "still_conj": "Sublinear or O(1) extraction from n without replaying CA depth",
        "block_tower": bt,
        "block_extractor": ex,
        "surrogate_ok": surrogate_ok,
    }


def verify_nonperiodicity_density_bounded(
    max_depth: int = 256,
    max_period: int = 128,
    sample_depth: int | None = None,
) -> dict[str, Any]:
    """No period in prefix scan + density in (0,1) at tested depth."""
    from .block_tower import rule30_center_column

    depth = sample_depth or min(max_depth, 512)
    bits = rule30_center_column(depth)
    ones = sum(bits)
    density = ones / depth if depth else 0.0
    period_hits: list[int] = []
    for p in range(2, min(max_period + 1, depth)):
        if all(bits[i] == bits[i + p] for i in range(min(len(bits) - p, 64))):
            period_hits.append(p)
    no_small_period = len(period_hits) == 0
    density_ok = 0.1 < density < 0.9
    ok = no_small_period and density_ok and depth >= 64
    return {
        "claim_id": "rule30.prize.nonperiodicity_density",
        "proof_key": "NONPERIODICITY_DENSITY_BOUNDED",
        "status": "pass" if ok else "pass_with_open_gaps" if density_ok else "fail",
        "honesty_label": "BOUNDED_EXEC" if ok else "CONJ",
        "promoted_from": "CONJ",
        "narrowed_claim": (
            f"No period p≤{max_period} in first 64 offsets at depth {depth}; "
            f"center density={density:.4f}."
        ),
        "still_conj": "External-grade nonperiodicity proof for all n",
        "evidence": {
            "max_depth": depth,
            "density": density,
            "ones": ones,
            "period_hits_in_prefix": period_hits,
        },
    }


def verify_p3_weyl_engineering(max_depth: int = 256) -> dict[str, Any]:
    """P3 engineering: executable 8-state Weyl routing table + substrate verification."""
    from .substrate_map import WEYL_ROUTING_TABLE, verify_substrate_map

    sub = verify_substrate_map(max_depth=max_depth)
    table_ok = len(WEYL_ROUTING_TABLE) == 8 and all(len(row) == 8 for row in WEYL_ROUTING_TABLE)
    ok = sub.get("status") == "pass" and table_ok
    return {
        "claim_id": "P3",
        "proof_key": "P3_WEYL_ENGINEERING",
        "status": "pass" if ok else "fail",
        "honesty_label": "BOUNDED_EXEC" if ok else "CONJ",
        "promoted_from": "CONJ",
        "narrowed_claim": (
            "Weyl involution and 8×8 routing table are executable and match "
            "canonical Rule 30 traces at tested depth."
        ),
        "still_conj": "Full prize D1 Weyl-table lookup moonshine closure",
        "substrate_map": sub,
        "weyl_table_shape": [len(WEYL_ROUTING_TABLE), len(WEYL_ROUTING_TABLE[0]) if table_ok else 0],
    }


# ---------------------------------------------------------------------------
# Ring 2 / umbrella
# ---------------------------------------------------------------------------


def verify_voa_lookup_promoted(max_depth: int = 256) -> dict[str, Any]:
    from .voa_harness import verify_voa_harness

    r = verify_voa_harness(max_depth=max_depth)
    hypothesis_honesty = r.get("honesty", "CONJ")
    # Harness execution is bounded; hypothesis may remain CONJ at low match rate.
    label = "BOUNDED_EXEC" if r.get("status") == "pass" else "CONJ"
    return {
        "claim_id": "VOA_LOOKUP",
        "proof_key": "VOA_HARNESS",
        "status": r.get("status", "fail"),
        "honesty_label": label,
        "harness_honesty": hypothesis_honesty,
        "hypothesis_supported": hypothesis_honesty not in ("CONJ",),
        "promoted_from": "CONJ",
        "evidence": {
            "best_hypothesis": r.get("best_hypothesis"),
            "best_min_rate": r.get("best_min_rate_across_classes"),
            "trigger_status": r.get("trigger_status"),
        },
        "full": r,
    }


def ledger_status_overrides(
    max_depth: int = 256,
    page_count: int = 2,
    page_size: int = 4096,
) -> dict[str, dict[str, Any]]:
    """Obligation_id → {status, blocks_release, evidence_patch} for ledger synthesis."""
    sheet = verify_sheet_power_law_bounded(page_count, page_size)
    depth = verify_depth_extraction_accounting(max_depth)
    density = verify_nonperiodicity_density_bounded(max_depth)
    overrides: dict[str, dict[str, Any]] = {}
    if sheet["honesty_label"] == "BOUNDED_EXEC":
        overrides["rule30.sheet_operator.power_law"] = {
            "status": "BOUNDED_EXEC",
            "blocks_release": False,
            "evidence_status": "exact_computation",
            "next_required_work": "all-page T_page^k induction (still open)",
        }
    if density["honesty_label"] == "BOUNDED_EXEC":
        overrides["rule30.prize.nonperiodicity_density"] = {
            "status": "BOUNDED_EXEC",
            "blocks_release": False,
            "evidence_status": "exact_computation",
            "evidence": density["evidence"],
            "next_required_work": "external-grade nonperiodicity for all n",
        }
    if depth.get("surrogate_ok"):
        overrides["rule30.prize.depth_only_shortcut"] = {
            "status": "CONJ",
            "blocks_release": True,
            "evidence_status": "computed_profile",
            "evidence": {
                "sublinear_theorem": "still_open",
                "bounded_surrogate": depth["proof_key"],
                "surrogate_claim": depth["surrogate_claim_id"],
                "block_extractor": depth["block_extractor"],
            },
            "next_required_work": depth["still_conj"],
        }
    return overrides


def run_open_claims_harness(max_depth: int = 256, *, quick: bool = False) -> dict[str, Any]:
    """Run all promotion harnesses; return unified report + registry patch hints."""
    if quick:
        max_depth = min(max_depth, 256)
    from .monster_d4_lift_claim import verify_monster_d4_lift_claim
    from .residual_window_lift import verify_residual_window_lift
    from .rule30 import rule30_proof_obligation_ledger, verify_rule30_proof_obligation_ledger

    page_count = 2
    page_size = min(4096, max_depth)

    monster = verify_monster_d4_lift_claim(max_depth)
    residual = verify_residual_window_lift(max_depth)
    entries = [
        verify_sheet_power_law_bounded(page_count, page_size),
        verify_depth_extraction_accounting(max_depth),
        verify_nonperiodicity_density_bounded(max_depth),
        verify_p3_weyl_engineering(max_depth),
        verify_voa_lookup_promoted(max_depth),
        {**monster, "proof_key": "MONSTER_D4_LIFT"},
        {**residual, "proof_key": "RESIDUAL_WINDOW_LIFT"},
    ]

    model = rule30_proof_obligation_ledger(
        max_depth=max_depth,
        page_count=page_count,
        page_size=page_size,
    )
    overrides = ledger_status_overrides(max_depth, page_count, page_size)
    for row in model.get("obligations", []):
        oid = row.get("obligation_id")
        if oid in overrides:
            row.update(overrides[oid])
    ledger_verify = verify_rule30_proof_obligation_ledger(model)

    promotions: list[dict[str, Any]] = []
    failures: list[str] = []
    proofs: dict[str, Any] = {}
    for e in entries:
        pk = e.get("proof_key", e.get("claim_id"))
        proofs[pk] = {
            "status": e.get("status"),
            "honesty_label": e.get("honesty_label"),
            "claim_id": e.get("claim_id"),
        }
        if e.get("status") not in ("pass", "pass_with_open_gaps"):
            failures.append(str(pk))
        if e.get("promoted_from") == "CONJ" and e.get("honesty_label") != "CONJ":
            promotions.append(
                {
                    "claim_id": e["claim_id"],
                    "from": "CONJ",
                    "to": e["honesty_label"],
                    "proof_key": pk,
                }
            )
        sur = e.get("surrogate_label")
        if sur and sur != "CONJ":
            promotions.append(
                {
                    "claim_id": e.get("surrogate_claim_id"),
                    "from": "implicit",
                    "to": sur,
                    "proof_key": e.get("proof_key"),
                }
            )

    still_conj = [e["claim_id"] for e in entries if e.get("honesty_label") == "CONJ"]
    blocking = model.get("release_summary", {}).get("blocking_obligations", [])

    return {
        "submission": "lattice-forge open-claims honesty harness v1.0",
        "max_depth_tested": max_depth,
        "quick": quick,
        "proofs": proofs,
        "entries": entries,
        "promotions": promotions,
        "still_conj": still_conj,
        "ledger": {
            "model_status": model.get("status"),
            "verify": ledger_verify,
            "blocking_obligations": blocking,
            "status_counts": model.get("release_summary", {}).get("status_counts"),
        },
        "registry_patch": _registry_patch_from_entries(entries),
        "failures": failures,
        "overall_status": "pass" if not failures and ledger_verify.get("status") != "fail" else "fail",
        "honesty_policy": {
            "BOUNDED_EXEC": "Finite-window verified property",
            "CONJ": "Theorem or all-n claim still open",
            "depth_only_shortcut": "Stays CONJ for sublinear; block_addressed surrogate is BOUNDED_EXEC",
        },
    }


def _registry_patch_from_entries(entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    patch: list[dict[str, str]] = []
    for e in entries:
        cid = e.get("claim_id")
        label = e.get("honesty_label")
        if not cid or label == "CONJ":
            continue
        patch.append({"claim_id": cid, "honesty_label": label, "proof_key": e.get("proof_key", "")})
    if any(e.get("surrogate_ok") for e in entries):
        patch.append(
            {
                "claim_id": "rule30.extraction.block_addressed",
                "honesty_label": "BOUNDED_EXEC",
                "proof_key": "DEPTH_EXTRACTION_ACCOUNTING",
            }
        )
    return patch


_NEW_REGISTRY_ROWS: dict[str, dict[str, Any]] = {
    "rule30.extraction.block_addressed": {
        "claim_id": "rule30.extraction.block_addressed",
        "ring": 1,
        "kind": "obligation",
        "honesty_label": "BOUNDED_EXEC",
        "verifier_id": "verify_depth_extraction_accounting",
        "proof_key": "DEPTH_EXTRACTION_ACCOUNTING",
        "implicated_by": ["rule30.prize.depth_only_shortcut", "regime.a.block_tower"],
    },
    "VOA_LOOKUP": {
        "claim_id": "VOA_LOOKUP",
        "ring": 1,
        "kind": "umbrella_harness",
        "honesty_label": "BOUNDED_EXEC",
        "verifier_id": "verify_voa_lookup_harness",
        "proof_key": "VOA_HARNESS",
        "not_in_ring1": True,
    },
}


def apply_registry_patch(patch: list[dict[str, str]], registry_path: str | None = None) -> int:
    """Update claims/registry.jsonl honesty_label and proof_key; append new claim rows."""
    import json
    from pathlib import Path

    path = Path(registry_path) if registry_path else Path(__file__).resolve().parents[2] / "claims" / "registry.jsonl"
    by_id = {p["claim_id"]: p for p in patch}
    lines_out: list[str] = []
    changed = 0
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        cid = row.get("claim_id")
        seen.add(cid)
        if cid in by_id:
            upd = by_id[cid]
            if upd.get("honesty_label"):
                row["honesty_label"] = upd["honesty_label"]
            if upd.get("proof_key"):
                row["proof_key"] = upd["proof_key"]
            changed += 1
        lines_out.append(json.dumps(row, ensure_ascii=False))
    for cid, template in _NEW_REGISTRY_ROWS.items():
        if cid not in seen and cid in by_id:
            row = dict(template)
            upd = by_id[cid]
            row.update({k: v for k, v in upd.items() if v})
            lines_out.append(json.dumps(row, ensure_ascii=False))
            changed += 1
    path.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    return changed
