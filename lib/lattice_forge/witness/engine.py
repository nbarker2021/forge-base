"""Witness readout engine — canonical suite → CMPLX surface."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

from ..chart_codec import encode as encode_shell2
from ..chart_codec import rule30_chart_trajectory, shell2_subtrajectory
from ..chart_codec_d4 import encode_d4
from ..forge import Forge
from ..rule30_block_extractor import Rule30BlockExtractor
from ..tools import MORSRTool, TarpitTool, TransportTool
from .formal import WitnessHonesty, WitnessKind
from .state_keys import record_encode_keys


def _witness_max_depth(requested: int) -> int:
    cap = int(os.environ.get("FORGE_WITNESS_MAX_DEPTH", "4096"))
    return min(requested, cap)


def _honesty_from_status(status: str) -> str:
    if status == "pass":
        return WitnessHonesty.PROVEN.value
    if status == "pass_with_open_gaps":
        return WitnessHonesty.PASS_WITH_OPEN_GAPS.value
    if status == "fail":
        return WitnessHonesty.FAIL.value
    return WitnessHonesty.ENGINEERING.value


class WitnessEngine:
    """Thin engine over Forge and Regime A solver modules."""

    def __init__(self, forge: Forge) -> None:
        self._forge = forge
        self._extractors: dict[tuple[int, int], Rule30BlockExtractor] = {}

    def _extractor(self, max_depth: int, base_page: int) -> Rule30BlockExtractor:
        key = (max_depth, base_page)
        if key not in self._extractors:
            self._extractors[key] = Rule30BlockExtractor(
                max_depth=max_depth,
                base_page=base_page,
                forge=self._forge,
            )
        return self._extractors[key]

    def classify(
        self,
        *,
        source_id: str | None = None,
        target_id: str | None = None,
        morphism_id: str | None = None,
    ) -> dict[str, Any]:
        envelope = self._forge.witnesses(
            source_id=source_id,
            target_id=target_id,
            morphism_id=morphism_id,
        )
        witnesses = envelope.get("result", {}).get("witnesses", [])
        return {
            "kind": WitnessKind.LEDGER.value,
            "status": "available" if witnesses else "empty",
            "honesty": WitnessHonesty.PROVEN.value,
            "result": envelope,
            "provenance": {"module": "lattice_forge.witness", "space": "lf-witness"},
        }

    def regime_a_query(
        self,
        *,
        n: int,
        max_depth: int = 4096,
        base_page: int = 64,
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        extractor = self._extractor(max_depth, base_page)
        query = extractor.nth_bit(n)
        build_s = time.perf_counter() - t0
        status = str(query.get("status", "pass"))
        return {
            "kind": WitnessKind.REGIME_A.value,
            "status": status,
            "honesty": _honesty_from_status(status),
            "result": query,
            "provenance": {
                "module": "lattice_forge.witness",
                "space": "lf-solver",
                "build_seconds": build_s,
                "store_info": extractor.store_info,
            },
        }

    def regime_a_range(
        self,
        *,
        start: int,
        end: int,
        max_depth: int = 4096,
        base_page: int = 64,
    ) -> dict[str, Any]:
        extractor = self._extractor(max_depth, base_page)
        query = extractor.bit_range(start, end)
        status = str(query.get("status", "pass"))
        return {
            "kind": WitnessKind.REGIME_A.value,
            "status": status,
            "honesty": _honesty_from_status(status),
            "result": query,
            "provenance": {
                "module": "lattice_forge.witness",
                "space": "lf-solver",
                "store_info": extractor.store_info,
            },
        }

    def proof_bundle(
        self,
        *,
        max_depth: int = 128,
        page_count: int = 2,
        page_size: int = 128,
        block_size: int = 8,
        max_order: int = 4,
        verify: bool = True,
    ) -> dict[str, Any]:
        if verify:
            envelope = self._forge.verify_rule30_proof_obligations(
                max_depth=max_depth,
                page_count=page_count,
                page_size=page_size,
                block_size=block_size,
                max_order=max_order,
            )
        else:
            envelope = self._forge.rule30_proof_obligations(
                max_depth=max_depth,
                page_count=page_count,
                page_size=page_size,
                block_size=block_size,
                max_order=max_order,
            )
        result = envelope.get("result", envelope)
        status = str(result.get("status", "unknown"))
        return {
            "kind": WitnessKind.PROOF_BUNDLE.value,
            "status": status,
            "honesty": _honesty_from_status(status),
            "result": envelope,
            "provenance": {
                "module": "lattice_forge.witness",
                "space": "lf-ledger",
                "verify": verify,
            },
        }

    def regime_c_encode(self, *, max_depth: int = 512) -> dict[str, Any]:
        max_depth = _witness_max_depth(max_depth)
        traj = rule30_chart_trajectory(max_depth)
        encoded = encode_shell2(shell2_subtrajectory(traj))
        state_keys = record_encode_keys(from_regime="A", to_regime="C", max_depth=max_depth)
        TransportTool().invoke(
            step="regime_encode",
            from_regime="A",
            to_regime="C",
            payload={"max_depth": max_depth, "state_keys": state_keys},
        )
        self._forge.record_witnessed_encode(
            state_keys,
            encoded=encoded,
            from_regime="A",
            to_regime="C",
            max_depth=max_depth,
        )
        return {
            "kind": WitnessKind.REGIME_C.value,
            "status": "pass",
            "honesty": WitnessHonesty.ENGINEERING.value,
            "result": {**encoded, "state_keys": state_keys},
            "provenance": {"module": "lattice_forge.witness", "space": "lf-solver", "max_depth": max_depth},
        }

    def regime_cprime_encode(self, *, max_depth: int = 512) -> dict[str, Any]:
        max_depth = _witness_max_depth(max_depth)
        traj = rule30_chart_trajectory(max_depth)
        encoded = encode_d4(traj)
        state_keys = record_encode_keys(from_regime="A", to_regime="Cprime", max_depth=max_depth)
        TransportTool().invoke(
            step="regime_encode",
            from_regime="A",
            to_regime="Cprime",
            payload={"max_depth": max_depth, "state_keys": state_keys},
        )
        self._forge.record_witnessed_encode(
            state_keys,
            encoded=encoded,
            from_regime="A",
            to_regime="Cprime",
            max_depth=max_depth,
        )
        return {
            "kind": WitnessKind.REGIME_CPRIME.value,
            "status": "pass",
            "honesty": WitnessHonesty.ENGINEERING.value,
            "result": {**encoded, "state_keys": state_keys},
            "provenance": {"module": "lattice_forge.witness", "space": "lf-solver", "max_depth": max_depth},
        }

    def syndrome_report(
        self,
        *,
        syndrome_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        keys = syndrome_keys or ["non_glue", "ecc_shed"]
        labels = []
        for key in keys:
            label = TarpitTool.label_syndrome(key)
            labels.append(
                {
                    "syndrome_key": key,
                    "canonical_label": label.get("canonical_label", f"syndrome:{key}"),
                    "tarpit": label,
                }
            )
        return {
            "kind": WitnessKind.SYNDROME.value,
            "status": "available",
            "honesty": WitnessHonesty.ENGINEERING.value,
            "result": {"syndromes": labels, "shed_non_glue": True},
            "provenance": {"module": "lattice_forge.witness", "space": "lf-witness"},
        }

    def proof_bundle_full(self, *, quick: bool = False, max_depth: int | None = None) -> dict[str, Any]:
        project_root = Path(__file__).resolve().parents[3]
        scripts = project_root / "scripts" / "run_all_proofs.py"
        if str(project_root / "src") not in sys.path:
            sys.path.insert(0, str(project_root / "src"))
        import importlib.util

        spec = importlib.util.spec_from_file_location("run_all_proofs", scripts)
        if spec is None or spec.loader is None:
            raise RuntimeError("run_all_proofs.py not found")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        depth = 256 if quick else _witness_max_depth(max_depth or 4096)
        report = mod.run_proofs(max_depth=depth)
        status = str(report.get("overall_status", "unknown"))
        if status == "fail":
            MORSRTool().invoke(
                failure_kind="proof_bundle_full",
                context={"failures": report.get("failures", [])},
            )
        return {
            "kind": WitnessKind.PROOF_BUNDLE_FULL.value,
            "status": status,
            "honesty": _honesty_from_status(status),
            "result": report,
            "provenance": {
                "module": "lattice_forge.witness",
                "space": "lf-proofs",
                "quick": quick,
                "max_depth": depth,
            },
        }
