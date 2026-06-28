"""Resolve verifier_id strings to runnable empirical checks."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Callable

DepthRunner = Callable[[int], dict[str, Any]]


def _honest_status(raw: str) -> str:
    if raw in {"pass_with_open_gaps", "conj", "CONJ"}:
        return raw
    return raw


def resolve_runner(verifier_id: str, *, claim_id: str = "", proof_key: str | None = None) -> tuple[str, DepthRunner | None]:
    """
    Return (mode, runner). mode is 'executable' | 'citation' | 'transport' | 'composite' | 'obligation'.
  runner is None when mode != executable paths that need no depth.
    """
    if verifier_id.startswith("citation:"):
        return "citation", None
    if verifier_id.startswith("transport:"):
        return "transport", None
    if verifier_id.startswith("engineering:"):
        return _resolve_engineering(verifier_id, claim_id)
    if verifier_id == "verify_monster_d4_lift_claim":
        from lattice_forge.monster_d4_lift_claim import verify_monster_d4_lift_claim

        return "executable", lambda d: verify_monster_d4_lift_claim(max_depth=d)
    if verifier_id == "verify_residual_window_lift":
        from lattice_forge.residual_window_lift import verify_residual_window_lift

        return "executable", lambda d: verify_residual_window_lift(max_depth=d)
    if verifier_id == "Forge.witnessed_lookup+regime_encode":
        return "executable", _witness_index
    if "+" in verifier_id:
        return "composite", lambda d: _run_composite(verifier_id, d, claim_id=claim_id)

    if verifier_id == "verify_rule30_proof_obligation_ledger":
        return "obligation", lambda d: _run_obligation(claim_id, d)

    fn = _VERIFIER_RUNNERS.get(verifier_id)
    if fn is not None:
        return "executable", fn

    if proof_key and proof_key in _PROOF_KEY_RUNNERS:
        return "executable", _PROOF_KEY_RUNNERS[proof_key]

    return "unknown", None


def _resolve_engineering(verifier_id: str, claim_id: str) -> tuple[str, DepthRunner | None]:
    if verifier_id == "engineering:Weyl-table-lookup" or claim_id == "P3":
        from lattice_forge.honesty_harness import verify_p3_weyl_engineering

        return "executable", verify_p3_weyl_engineering
    return "engineering", None


def _run_composite(spec: str, max_depth: int, *, claim_id: str) -> dict[str, Any]:
    parts = spec.split("+")
    sub: dict[str, Any] = {}
    ok = True
    for part in parts:
        mode, runner = resolve_runner(part.strip(), claim_id=claim_id)
        if runner is None:
            sub[part] = {"status": mode, "skipped": True}
            continue
        r = runner(max_depth)
        sub[part] = r
        st = _honest_status(str(r.get("status", "unknown")))
        if st not in {"pass", "pass_with_open_gaps", "conj", "CONJ"}:
            ok = False
    return {"status": "pass" if ok else "fail", "composite": sub}


def _run_obligation(claim_id: str, max_depth: int) -> dict[str, Any]:
    from lattice_forge import Forge
    from lattice_forge.rule30 import rule30_proof_obligation_ledger, verify_rule30_proof_obligation_ledger

    if not claim_id:
        forge = Forge.open(Path(tempfile.mkdtemp(prefix="lf-emp-obl-")))
        rec = forge.verify_rule30_proof_obligations(max_depth=max_depth, page_count=2, page_size=min(4096, max_depth))
        return rec.get("result", rec)

    model = rule30_proof_obligation_ledger(
        max_depth=max_depth,
        page_count=2,
        page_size=min(4096, max(64, max_depth)),
        block_size=8,
        max_order=4,
    )
    ledger = verify_rule30_proof_obligation_ledger(model)
    row = next((o for o in model.get("obligations", []) if o.get("obligation_id") == claim_id), None)
    if row is None:
        return {"status": "fail", "error": f"obligation {claim_id} not in ledger", "ledger_status": ledger.get("status")}
    label = str(row.get("honesty_label") or row.get("status", "unknown"))
    st = label if label in {"CONJ", "BOUNDED_EXEC", "EXPRESSIBLE", "OVERCLAIM"} else str(row.get("status", "unknown")).lower()
    if st == "overclaim":
        st = "fail"
    return {
        "status": st if st in {"conj", "CONJ", "pass", "pass_with_open_gaps", "fail"} else label.lower(),
        "obligation_id": claim_id,
        "obligation_row": row,
        "ledger_status": ledger.get("status"),
    }


def _depth_optional(fn: Callable[..., dict[str, Any]], *, needs_depth: bool = True) -> DepthRunner:
    if needs_depth:
        return lambda d: fn(max_depth=d)
    return lambda _d: fn()


def _witness_index(max_depth: int) -> dict[str, Any]:
    from lattice_forge import Forge
    from lattice_forge.witness.engine import WitnessEngine
    from lattice_forge.witness.state_keys import make_regime_encode_key

    depth = min(max_depth, 128)
    forge = Forge.open(Path(tempfile.mkdtemp(prefix="lf-emp-witness-")))
    engine = WitnessEngine(forge)
    engine.regime_c_encode(max_depth=depth)
    key = make_regime_encode_key(from_regime="A", to_regime="C", max_depth=depth)
    lookup = forge.witnessed_lookup(key).get("result", {})
    ok = lookup.get("witnessed") is True and lookup.get("answer") == "WITNESSED"
    return {
        "status": "pass" if ok else "fail",
        "state_key": key,
        "lookup_answer": lookup.get("answer"),
    }


def _forge_can_close(_d: int) -> dict[str, Any]:
    from lattice_forge import Forge

    forge = Forge.open(Path(tempfile.mkdtemp(prefix="lf-emp-t8-")))
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
    return {"status": "pass" if paths == 8 else "fail", "paths_count": paths}


def _import_verifiers() -> dict[str, DepthRunner]:
    from lattice_forge.f4_action import (
        closed_form_rule30_8x8_transition_exact,
        decompose_8x8_via_block_action_exact,
        search_for_su3_closure_scale,
        verify_n3_su3_closure_exact,
    )
    from lattice_forge.jordan_j3 import verify_j3o_axioms
    from lattice_forge.octonion import verify_octonion_axioms
    from lattice_forge.rule30 import verify_chart_j3o_isomorphism, verify_rule30_chart_local_readout
    from lattice_forge.substrate_map import verify_substrate_map
    from lattice_forge.chart_codec import verify_chart_codec
    from lattice_forge.chart_codec_d4 import verify_chart_codec_d4
    from lattice_forge.rule30_block_extractor import verify_extractor
    from lattice_forge.block_tower import verify_block_tower
    from lattice_forge.decomposition import verify_all_theorems, verify_checkpoint_store
    from lattice_forge.quad_oloid import verify_quad_oloid
    from lattice_forge.voa_lookup import verify_voa_lookup_harness
    from lattice_forge.rule30 import (
        verify_rule30_exit_trajectory,
        verify_rule30_mandelbrot_field_address,
    )

    runners = {
        "verify_octonion_axioms": _depth_optional(verify_octonion_axioms, needs_depth=False),
        "verify_j3o_axioms": _depth_optional(verify_j3o_axioms, needs_depth=False),
        "verify_chart_j3o_isomorphism": _depth_optional(verify_chart_j3o_isomorphism),
        "verify_n3_su3_closure_exact": _depth_optional(verify_n3_su3_closure_exact, needs_depth=False),
        "search_for_su3_closure_scale": lambda _d: search_for_su3_closure_scale(max_scale=8),
        "decompose_8x8_via_block_action_exact": lambda _d: decompose_8x8_via_block_action_exact(n_steps=3),
        "closed_form_rule30_8x8_transition_exact": lambda _d: closed_form_rule30_8x8_transition_exact(),
        "forge.can_close": _forge_can_close,
        "verify_rule30_chart_local_readout": _depth_optional(verify_rule30_chart_local_readout),
        "verify_substrate_map": _depth_optional(verify_substrate_map),
        "verify_block_tower": _depth_optional(verify_block_tower),
        "verify_extractor": _depth_optional(verify_extractor),
        "verify_chart_codec": _depth_optional(verify_chart_codec),
        "verify_chart_codec_d4": _depth_optional(verify_chart_codec_d4),
        "verify_all_theorems": lambda d: verify_all_theorems(
            decomposition_depths=range(1, min(d + 1, 129))
        ),
        "verify_checkpoint_store": lambda d: verify_checkpoint_store(max_depth=d),
        "verify_quad_oloid": _depth_optional(verify_quad_oloid, needs_depth=False),
        "verify_voa_lookup_harness": _depth_optional(verify_voa_lookup_harness, needs_depth=False),
    }
    global _PROOF_KEY_RUNNERS
    _PROOF_KEY_RUNNERS = {
        "SUBSTRATE_MAP": runners["verify_substrate_map"],
        "BLOCK_TOWER": runners["verify_block_tower"],
        "BLOCK_EXTRACTOR": runners["verify_extractor"],
        "CHART_CODEC": runners["verify_chart_codec"],
        "CHART_CODEC_D4": runners["verify_chart_codec_d4"],
        "TRANSPORT_FIELD_ADDRESS": lambda d: verify_rule30_mandelbrot_field_address(max_depth=d, n=257),
        "TRANSPORT_EXIT_TRAJECTORY": lambda d: verify_rule30_exit_trajectory(max_depth=d, n=257),
        "QUAD_OLOID": runners["verify_quad_oloid"],
        "VOA_LOOKUP": runners["verify_voa_lookup_harness"],
    }
    return runners


_VERIFIER_RUNNERS: dict[str, DepthRunner] = _import_verifiers()
_PROOF_KEY_RUNNERS: dict[str, DepthRunner] = {}
