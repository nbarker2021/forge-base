"""Witness readout API constants."""
from __future__ import annotations

from typing import Any

ROUTER_PREFIX = "/witness"

ENDPOINTS = (
    "/witness/spec",
    "/witness/readout/classify",
    "/witness/readout/nth-bit",
    "/witness/participation",
    "/witness/classify",
    "/witness/regime-a/query",
    "/witness/regime-a/range",
    "/witness/regime-c/encode",
    "/witness/regime-cprime/encode",
    "/witness/syndrome",
    "/witness/proof-bundle",
    "/witness/proof-bundle/full",
)


def witness_spec_dict() -> dict[str, Any]:
    from .readout import classify_lcr  # noqa: F401

    return {
        "version": "0.2.0-family",
        "router_prefix": ROUTER_PREFIX,
        "endpoints": list(ENDPOINTS),
        "rule30_bit": "L ^ C ^ R ^ (C & R)",
        "spaces": [
            "lf-core",
            "lf-algebra",
            "lf-ledger",
            "lf-solver",
            "lf-theory",
            "lf-proofs",
            "lf-service",
            "lf-witness",
            "r30-decomposition",
        ],
    }

DEFAULT_REGIME_A_MAX_DEPTH = 4096
DEFAULT_REGIME_A_BASE_PAGE = 64
