"""Composed CQE Rule 30 nth-bit tool built from existing lattice-forge parts."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .chart_codec_d4 import ANTIPODAL_LABEL, SHEET_SIGN, encode_d4, rule30_chart_trajectory
from .cqe_idempotent_cache import CQEIdempotentLibCache
from .d12_action import d12_acts_on_d4_state, verify_d12_idempotent_chain
from .jordan_j3 import J3O
from .rule30_block_extractor import Rule30BlockExtractor
from .rule30_predictor import predict_then_oracle
from .rule90_linearization import rule30_center_via_decomposition

BUILT_PARTS = (
    "rule30_block_extractor",
    "rule90_linearization",
    "chart_codec_d4",
    "jordan_j3",
    "d12_action",
    "rule30_predictor",
)


class Rule30CQETool:
    """Analyze Rule 30 nth bits by composing the existing proof/runtime parts."""

    def __init__(
        self,
        max_depth: int = 4096,
        base_page: int = 64,
        max_level: int = 3,
        *,
        idempotent_cache: CQEIdempotentLibCache | None = None,
    ) -> None:
        self.max_depth = max_depth
        self.base_page = base_page
        self.max_level = max_level
        self.idempotent_cache = idempotent_cache
        self._extractor = Rule30BlockExtractor(
            max_depth=max_depth,
            base_page=base_page,
            max_level=max_level,
        )

    def analyze_nth_bit(self, n: int) -> dict[str, Any]:
        if n < 1:
            raise ValueError("n must be >= 1")
        if n > self.max_depth:
            raise ValueError(f"n={n} exceeds configured max_depth={self.max_depth}")

        representative = self._representative_for_prediction(n)
        encoded = encode_d4([representative])
        axis = encoded["labels"][0]
        sheet = encoded["sheets"][0]
        jordan = J3O.from_diagonal(*representative)
        d12 = verify_d12_idempotent_chain()
        d12_reflected_state = d12_acts_on_d4_state((0, 1), (axis, sheet))
        predictor = predict_then_oracle(
            n,
            representative,
            representative_source="chart_codec_d4.rule30_chart_trajectory",
        )
        bounded_io = self._extractor.nth_bit(n)
        linear = rule30_center_via_decomposition(n)
        cache_stage = self._cache_stage(n, representative)
        verified = (
            predictor["match"]
            and predictor["predicted_bit"] == bounded_io["bit"]
            and predictor["predicted_bit"] == linear["bit"]
            and (
                cache_stage["status"] != "hit"
                or cache_stage["rule30_depth"]["value"]["bit"] == predictor["predicted_bit"]
            )
            and linear["match"]
        )

        return {
            "status": "verified" if verified else "mismatch",
            "n": n,
            "representative": {
                "lcr": representative,
                "source": "chart_codec_d4.rule30_chart_trajectory",
                "depth": n - 1,
            },
            "bits": {
                "predictor": predictor["predicted_bit"],
                "block_extractor": bounded_io["bit"],
                "rule90_decomposition": linear["bit"],
                "oracle": predictor["oracle_bit"],
                "lib_cache": (
                    cache_stage["rule30_depth"]["value"]["bit"]
                    if cache_stage["status"] == "hit"
                    else None
                ),
            },
            "stages": {
                "idempotent_cache": cache_stage,
                "bounded_io": {
                    "module": "rule30_block_extractor",
                    "method": bounded_io["method"],
                    "anchor_depth": bounded_io["anchor_depth"],
                    "replay_steps": bounded_io["replay_steps"],
                },
                "linear_decomposition": {
                    "module": "rule90_linearization",
                    "base_lucas": linear["base_lucas"],
                    "contributing_terms": linear["contributing_terms"],
                    "lucas_nonzero_cells": linear["lucas_nonzero_cells"],
                    "match": linear["match"],
                },
                "d4_codec": {
                    "module": "chart_codec_d4",
                    "axis": axis,
                    "sheet": sheet,
                    "antipodal_label": ANTIPODAL_LABEL[representative],
                    "sheet_sign": SHEET_SIGN[representative],
                },
                "jordan_bridge": {
                    "module": "jordan_j3",
                    "diag": jordan.diag,
                    "trace": jordan.trace(),
                    "is_idempotent": jordan.is_idempotent(),
                    "weyl_13_diag": jordan.weyl_13_transposition().diag,
                },
                "d12_action": {
                    "module": "d12_action",
                    "status": d12["status"],
                    "sub_results": d12["sub_results"],
                    "input_d4_state": (axis, sheet),
                    "weyl_13_reflected_d4_state": d12_reflected_state,
                    "role": "action_envelope_over_d4_axis_classes",
                },
                "prediction": predictor,
            },
            "using_built_parts": BUILT_PARTS,
            "claim_boundary": {
                "local_readout": "O(1)_GIVEN_REPRESENTATIVE",
                "bounded_io": "CHECKPOINTED_REPLAY_WITH_BUILD_PHASE",
                "rule90_term": "O(log_N)_LUCAS_BIT",
                "depth_only_sublog_proven": False,
                "open_gap": "DEPTH_TO_REPRESENTATIVE_SHORTCUT_MISSING",
            },
        }

    def analyze_many(self, depths: Iterable[int]) -> dict[str, Any]:
        results = [self.analyze_nth_bit(n) for n in depths]
        matches = sum(1 for result in results if result["status"] == "verified")
        return {
            "status": "verified" if matches == len(results) else "mismatch",
            "count": len(results),
            "matches": matches,
            "results": results,
            "using_built_parts": BUILT_PARTS,
            "depth_only_sublog_proven": False,
        }

    @staticmethod
    def _representative_for_prediction(n: int) -> tuple[int, int, int]:
        trajectory = rule30_chart_trajectory(n - 1)
        return trajectory[-1]

    def _cache_stage(self, n: int, representative: tuple[int, int, int]) -> dict[str, Any]:
        if self.idempotent_cache is None:
            return {"status": "disabled"}
        chart_state = self.idempotent_cache.lookup_chart_state(representative)
        rule30_depth = self.idempotent_cache.lookup_rule30_depth(n)
        if chart_state is None or rule30_depth is None:
            return {
                "status": "miss",
                "chart_state": chart_state,
                "rule30_depth": rule30_depth,
            }
        return {
            "status": "hit",
            "chart_state": chart_state,
            "rule30_depth": rule30_depth,
            "rule": "bonded_exact_idempotent_terms",
        }


def analyze_rule30_nth_bit(
    n: int,
    *,
    max_depth: int = 4096,
    base_page: int = 64,
    max_level: int = 3,
) -> dict[str, Any]:
    return Rule30CQETool(
        max_depth=max_depth,
        base_page=base_page,
        max_level=max_level,
    ).analyze_nth_bit(n)
