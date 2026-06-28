"""Witness readout FastAPI router."""
from __future__ import annotations

from typing import Any, Callable, Optional

from .engine import WitnessEngine
from .model import (
    ClassifyRequest,
    LCRReadoutRequest,
    MaxDepthRequest,
    NthBitRequest,
    ParticipationRequest,
    ProofBundleFullRequest,
    ProofBundleRequest,
    RegimeAQueryRequest,
    RegimeARangeRequest,
    SyndromeRequest,
)
from .readout import classify_lcr, nth_bit_readout, participation_stats
from .spec import ROUTER_PREFIX, witness_spec_dict

MintFn = Callable[[str, dict[str, Any]], None]


def _maybe_mint(mint_fn: Optional[MintFn], op: str, envelope: dict[str, Any]) -> None:
    if mint_fn is None:
        return
    mint_fn(
        op,
        {
            "status": envelope.get("status"),
            "honesty": envelope.get("honesty"),
        },
    )


def create_witness_router(forge: Any, provider: Any = None, mint_fn: Optional[MintFn] = None):
    """Build /witness/* router. Pass provider for receipt-minting ledger/regime routes."""
    try:
        from fastapi import APIRouter
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install witness dependencies: pip install lattice-forge[witness,server]") from exc

    engine = WitnessEngine(forge)
    router = APIRouter(prefix=ROUTER_PREFIX, tags=["witness"])

    def _ledger_classify(**kwargs: Any) -> dict[str, Any]:
        if provider is not None and hasattr(provider, "witness_classify"):
            return provider.witness_classify(**kwargs, mint_receipt=mint_fn is not None)
        envelope = engine.classify(**kwargs)
        _maybe_mint(mint_fn, "witness_classify", envelope)
        return envelope

    def _regime_a_query(**kwargs: Any) -> dict[str, Any]:
        if provider is not None and hasattr(provider, "witness_regime_a_query"):
            return provider.witness_regime_a_query(**kwargs, mint_receipt=mint_fn is not None)
        envelope = engine.regime_a_query(**kwargs)
        _maybe_mint(mint_fn, "witness_regime_a_query", envelope)
        return envelope

    def _proof_bundle(**kwargs: Any) -> dict[str, Any]:
        if provider is not None and hasattr(provider, "witness_proof_bundle"):
            return provider.witness_proof_bundle(**kwargs, mint_receipt=mint_fn is not None)
        envelope = engine.proof_bundle(**kwargs)
        _maybe_mint(mint_fn, "witness_proof_bundle", envelope)
        return envelope

    @router.get("/spec")
    def witness_spec() -> dict[str, Any]:
        return witness_spec_dict()

    @router.post("/readout/classify")
    def readout_classify(body: LCRReadoutRequest) -> dict[str, Any]:
        return classify_lcr(body.left, body.center, body.right)

    @router.post("/readout/nth-bit")
    def readout_nth_bit(body: NthBitRequest) -> dict[str, Any]:
        return nth_bit_readout(body.depth, body.path)

    @router.post("/participation")
    def participation(body: ParticipationRequest) -> dict[str, Any]:
        return participation_stats(body.max_depth)

    @router.post("/classify")
    def classify(body: ClassifyRequest) -> dict[str, Any]:
        return _ledger_classify(**body.model_dump())

    @router.get("/classify")
    def classify_get(
        source_id: str | None = None,
        target_id: str | None = None,
        morphism_id: str | None = None,
    ) -> dict[str, Any]:
        return _ledger_classify(
            source_id=source_id,
            target_id=target_id,
            morphism_id=morphism_id,
        )

    @router.post("/regime-a/query")
    def regime_a_query(body: RegimeAQueryRequest) -> dict[str, Any]:
        return _regime_a_query(**body.model_dump())

    @router.post("/regime-a/range")
    def regime_a_range(body: RegimeARangeRequest) -> dict[str, Any]:
        return engine.regime_a_range(**body.model_dump())

    @router.post("/regime-c/encode")
    def regime_c_encode(body: MaxDepthRequest) -> dict[str, Any]:
        if provider is not None and hasattr(provider, "witness_regime_c_encode"):
            return provider.witness_regime_c_encode(max_depth=body.max_depth)
        return engine.regime_c_encode(max_depth=body.max_depth)

    @router.post("/regime-cprime/encode")
    def regime_cprime_encode(body: MaxDepthRequest) -> dict[str, Any]:
        if provider is not None and hasattr(provider, "witness_regime_cprime_encode"):
            return provider.witness_regime_cprime_encode(max_depth=body.max_depth)
        return engine.regime_cprime_encode(max_depth=body.max_depth)

    @router.post("/syndrome")
    def syndrome(body: SyndromeRequest) -> dict[str, Any]:
        if provider is not None and hasattr(provider, "witness_syndrome"):
            return provider.witness_syndrome(syndrome_keys=body.syndrome_keys)
        return engine.syndrome_report(syndrome_keys=body.syndrome_keys)

    @router.post("/proof-bundle")
    def proof_bundle(body: ProofBundleRequest) -> dict[str, Any]:
        return _proof_bundle(**body.model_dump())

    @router.post("/proof-bundle/full")
    def proof_bundle_full(body: ProofBundleFullRequest) -> dict[str, Any]:
        if provider is not None and hasattr(provider, "witness_proof_bundle_full"):
            return provider.witness_proof_bundle_full(
                quick=body.quick,
                max_depth=body.max_depth,
                mint_receipt=mint_fn is not None,
            )
        envelope = engine.proof_bundle_full(quick=body.quick, max_depth=body.max_depth)
        _maybe_mint(mint_fn, "witness_proof_bundle_full", envelope)
        return envelope

    return router
