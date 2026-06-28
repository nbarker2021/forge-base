from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .morphonics import morphonics_model_v0_2, verify_morphonics_model
from .overlay import OverlayStore
from .rule30 import (
    rule30_color_chirality_cipher,
    rule30_dihedral_block_hypervisor,
    rule30_discrete_lagrangian,
    rule30_hypervisor_extension_tape,
    rule30_lagrangian_depth_trace,
    rule30_mandelbrot_boundary_scalar,
    rule30_mandelbrot_field_address,
    rule30_morphon_hardened,
    rule30_moving_frame,
    rule30_nth_bit_expression,
    rule30_oloid_antipodal_winding,
    rule30_oloid_parameterization_scan,
    rule30_oloid_winding_from_n,
    rule30_exit_trajectory,
    rule30_physics_method_stack,
    rule30_proof_obligation_ledger,
    rule30_readout_ribbon_machine,
    rule30_reduced_alphabet_catalog,
    rule30_julia_resolution,
    rule30_sheet_operator,
    rule30_sheet_lift,
    rule30_symmetry_environment,
    rule30_torsor_functor_term,
    rule30_whole_integer_n_scalar_coverage,
    rule30_vignette_algebra,
    rule30_spinor_oloid_model,
    rule30_winding_number_proof,
    verify_rule30_color_chirality_cipher,
    verify_rule30_dihedral_block_hypervisor,
    verify_rule30_discrete_lagrangian,
    verify_rule30_hypervisor_extension_tape,
    verify_rule30_lagrangian_depth_trace,
    verify_rule30_mandelbrot_boundary_scalar,
    verify_rule30_mandelbrot_field_address,
    verify_rule30_morphon,
    verify_rule30_moving_frame,
    verify_rule30_nth_bit_expression,
    verify_rule30_oloid_antipodal_winding,
    verify_rule30_oloid_winding_from_n,
    verify_rule30_exit_trajectory,
    verify_rule30_physics_method_stack,
    verify_rule30_proof_obligation_ledger,
    verify_rule30_readout_ribbon_machine,
    verify_rule30_reduced_alphabet_catalog,
    verify_rule30_julia_resolution,
    verify_rule30_sheet_operator,
    verify_rule30_sheet_lift,
    verify_rule30_symmetry_environment,
    verify_rule30_torsor_functor_term,
    verify_rule30_whole_integer_n_scalar_coverage,
    verify_rule30_vignette_algebra,
    verify_rule30_spinor_oloid_model,
    verify_rule30_winding_number_proof,
)
from .seed import SeedStore
from .witness_state_store import WitnessStateStore


def extract_answer(kind: str, result: Any) -> str | None:
    if not isinstance(result, dict):
        return None
    if kind == "verify":
        return str(result.get("status")) if result.get("status") is not None else None
    if kind in {
        "terminal_tree",
        "terminal_trees",
        "verify_terminal_trees",
        "morphonics_model",
        "verify_morphonics",
        "rule30_morphon",
        "verify_rule30",
        "rule30_vignettes",
        "verify_rule30_vignettes",
        "rule30_moving_frame",
        "verify_rule30_moving_frame",
        "rule30_color_chirality",
        "verify_rule30_color_chirality",
        "rule30_lagrangian",
        "verify_rule30_lagrangian",
        "rule30_lagrangian_depth_trace",
        "verify_rule30_lagrangian_depth_trace",
        "rule30_mandelbrot_scalar",
        "verify_rule30_mandelbrot_scalar",
        "rule30_reduced_alphabet",
        "verify_rule30_reduced_alphabet",
        "rule30_symmetry_environment",
        "verify_rule30_symmetry_environment",
        "rule30_physics_method_stack",
        "verify_rule30_physics_method_stack",
        "rule30_whole_integer_n_scalar_coverage",
        "verify_rule30_whole_integer_n_scalar_coverage",
        "rule30_readout_ribbon_machine",
        "verify_rule30_readout_ribbon_machine",
        "rule30_dihedral_block_hypervisor",
        "verify_rule30_dihedral_block_hypervisor",
        "rule30_hypervisor_extension_tape",
        "verify_rule30_hypervisor_extension_tape",
        "rule30_sheet_operator",
        "verify_rule30_sheet_operator",
        "rule30_mandelbrot_field_address",
        "verify_rule30_mandelbrot_field_address",
        "rule30_exit_trajectory",
        "verify_rule30_exit_trajectory",
        "rule30_sheet_lift",
        "verify_rule30_sheet_lift",
        "rule30_julia_resolution",
        "verify_rule30_julia_resolution",
        "rule30_torsor_functor_term",
        "verify_rule30_torsor_functor_term",
        "rule30_spinor_oloid_model",
        "verify_rule30_spinor_oloid_model",
        "rule30_oloid_winding_from_n",
        "rule30_oloid_antipodal_winding",
        "rule30_oloid_parameterization_scan",
        "verify_rule30_oloid_winding_from_n",
        "verify_rule30_oloid_antipodal_winding",
        "rule30_winding_number_proof",
        "verify_rule30_winding_number_proof",
        "rule30_nth_bit_expression",
        "verify_rule30_nth_bit_expression",
        "rule30_proof_obligation_ledger",
        "verify_rule30_proof_obligation_ledger",
    }:
        return str(result.get("status")) if result.get("status") is not None else None
    closure = result.get("closure") or result.get("can_close") or result
    if isinstance(closure, dict) and closure.get("answer") is not None:
        return str(closure.get("answer"))
    if kind in {
        "object",
        "future_cone",
        "exactness_dashboard",
        "export_object",
        "terminal_tree",
        "terminal_trees",
        "verify_terminal_trees",
        "morphonics_model",
        "verify_morphonics",
        "rule30_morphon",
        "verify_rule30",
        "rule30_vignettes",
        "verify_rule30_vignettes",
        "rule30_moving_frame",
        "verify_rule30_moving_frame",
        "rule30_color_chirality",
        "verify_rule30_color_chirality",
        "rule30_lagrangian",
        "verify_rule30_lagrangian",
        "rule30_lagrangian_depth_trace",
        "verify_rule30_lagrangian_depth_trace",
        "rule30_mandelbrot_scalar",
        "verify_rule30_mandelbrot_scalar",
        "rule30_reduced_alphabet",
        "verify_rule30_reduced_alphabet",
        "rule30_symmetry_environment",
        "verify_rule30_symmetry_environment",
        "rule30_physics_method_stack",
        "verify_rule30_physics_method_stack",
        "rule30_whole_integer_n_scalar_coverage",
        "verify_rule30_whole_integer_n_scalar_coverage",
        "rule30_readout_ribbon_machine",
        "verify_rule30_readout_ribbon_machine",
        "rule30_dihedral_block_hypervisor",
        "verify_rule30_dihedral_block_hypervisor",
        "rule30_hypervisor_extension_tape",
        "verify_rule30_hypervisor_extension_tape",
        "rule30_sheet_operator",
        "verify_rule30_sheet_operator",
        "rule30_mandelbrot_field_address",
        "verify_rule30_mandelbrot_field_address",
        "rule30_exit_trajectory",
        "verify_rule30_exit_trajectory",
        "rule30_sheet_lift",
        "verify_rule30_sheet_lift",
        "rule30_julia_resolution",
        "verify_rule30_julia_resolution",
        "rule30_torsor_functor_term",
        "verify_rule30_torsor_functor_term",
        "rule30_spinor_oloid_model",
        "verify_rule30_spinor_oloid_model",
        "rule30_oloid_winding_from_n",
        "rule30_oloid_antipodal_winding",
        "rule30_oloid_parameterization_scan",
        "verify_rule30_oloid_winding_from_n",
        "verify_rule30_oloid_antipodal_winding",
        "rule30_winding_number_proof",
        "verify_rule30_winding_number_proof",
        "rule30_nth_bit_expression",
        "verify_rule30_nth_bit_expression",
        "rule30_proof_obligation_ledger",
        "verify_rule30_proof_obligation_ledger",
    }:
        return "available" if result else "missing"
    if kind in {"witnesses", "obstructions"}:
        rows = next((v for v in result.values() if isinstance(v, list)), None)
        return "rows" if rows else "empty"
    return None


def evidence_level(kind: str, result: Any) -> str:
    if kind == "verify":
        return "self_check" if isinstance(result, dict) and result.get("status") == "pass" else "failed_self_check"
    if kind in {
        "verify_terminal_trees",
        "verify_morphonics",
        "verify_rule30",
        "verify_rule30_vignettes",
        "verify_rule30_moving_frame",
        "verify_rule30_color_chirality",
        "verify_rule30_lagrangian",
        "verify_rule30_lagrangian_depth_trace",
        "verify_rule30_mandelbrot_scalar",
        "verify_rule30_reduced_alphabet",
        "verify_rule30_symmetry_environment",
        "verify_rule30_physics_method_stack",
        "verify_rule30_whole_integer_n_scalar_coverage",
        "verify_rule30_readout_ribbon_machine",
        "verify_rule30_dihedral_block_hypervisor",
        "verify_rule30_hypervisor_extension_tape",
        "verify_rule30_sheet_operator",
        "verify_rule30_mandelbrot_field_address",
        "verify_rule30_exit_trajectory",
        "verify_rule30_sheet_lift",
        "verify_rule30_julia_resolution",
        "verify_rule30_torsor_functor_term",
        "verify_rule30_spinor_oloid_model",
        "verify_rule30_oloid_winding_from_n",
        "verify_rule30_oloid_antipodal_winding",
        "verify_rule30_winding_number_proof",
        "verify_rule30_nth_bit_expression",
        "verify_rule30_proof_obligation_ledger",
    } and isinstance(result, dict):
        return "self_check" if str(result.get("status", "")).startswith("pass") else "failed_self_check"
    status_values = []

    def collect(value: Any, key: str | None = None) -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                collect(child_value, str(child_key))
        elif isinstance(value, list):
            for child in value:
                collect(child, key)
        elif isinstance(value, str) and key in {
            "answer",
            "evidence_level",
            "evidence_status",
            "exactness",
            "glue_status",
            "status",
            "surface_type",
        }:
            status_values.append(value)

    collect(result)
    text = json.dumps(status_values, sort_keys=True, default=str).lower()
    if "pending_import" in text:
        return "pending_import"
    if "template" in text or "placeholder" in text or "cosets_pending" in text:
        return "template"
    if "conceptual" in text:
        return "conceptual"
    if "computed_profile" in text or "computed" in text or kind in {"nsl", "path_metrics"}:
        return "computed_profile"
    if "exact" in text:
        return "exact"
    return "unclassified"


class Forge:
    """High-level facade for seed queries plus overlay receipts."""

    def __init__(
        self,
        seed: SeedStore,
        overlay: OverlayStore,
        witness_db: Path | str | None = None,
    ):
        self.seed = seed
        self.overlay = overlay
        self._witness_store = WitnessStateStore(witness_db)

    @classmethod
    def open(cls, root: str | Path | None = None) -> "Forge":
        overlay_root = Path(root) if root is not None else None
        witness_db: Path | None = None
        env_db = os.environ.get("FORGE_WITNESS_DB")
        if env_db:
            witness_db = Path(env_db)
        elif overlay_root is not None:
            witness_db = overlay_root / "witness" / "state.sqlite"
        return cls(
            seed=SeedStore.packaged(),
            overlay=OverlayStore.open(root),
            witness_db=witness_db,
        )

    def _record(self, kind: str, query: dict[str, Any], result: Any) -> dict[str, Any]:
        level = evidence_level(kind, result)
        answer = extract_answer(kind, result)
        receipt_id = self.overlay.record_receipt(kind, {"query": query, "answer": answer})
        event_id = self.overlay.record_event(
            kind,
            {"query": query, "result": result},
            evidence_level=level,
            receipt_id=receipt_id,
        )
        query_id = self.overlay.record_query(
            kind,
            query,
            result,
            answer=answer,
            evidence_level=level,
            event_id=event_id,
        )
        return {
            "query_kind": kind,
            "query": query,
            "answer": answer,
            "evidence_level": level,
            "result": result,
            "receipt_id": receipt_id,
            "event_id": event_id,
            "query_id": query_id,
        }

    def status(self) -> dict[str, Any]:
        summary = self.seed.summary()
        return {
            "package": "lattice-forge",
            "seed_db": str(self.seed.db_path),
            "seed_sha256": self.seed.sha256(),
            "seed_integrity": self.seed.integrity_check(),
            "overlay_db": str(self.overlay.db_path),
            "summary": summary,
        }

    def verify_seed(self) -> dict[str, Any]:
        result = self.seed.verify()
        return self._record("verify", {}, result)

    def object(self, object_id: str) -> dict[str, Any]:
        with self.seed.ledger() as ledger:
            result = {
                "object": ledger.object(object_id),
                "rag_card": ledger.rag_card(object_id),
                "construction_status": ledger.construction_status(object_id),
                "morphisms_from": ledger.morphisms_from(object_id),
                "morphisms_to": ledger.morphisms_to(object_id),
            }
        return self._record("object", {"object_id": object_id}, result)

    def can_close(self, source_id: str, target_id: str, max_depth: int = 10) -> dict[str, Any]:
        with self.seed.ledger() as ledger:
            result = ledger.closure_report(source_id, target_id, max_depth=max_depth)
            if "closure" not in result and "can_close" in result:
                result = {**result, "closure": result["can_close"]}
        return self._record(
            "can_close",
            {"source_id": source_id, "target_id": target_id, "max_depth": max_depth},
            result,
        )

    def terminal_tree(self, terminal_id: str) -> dict[str, Any]:
        with self.seed.ledger() as ledger:
            result = ledger.terminal_tree(terminal_id)
        return self._record("terminal_tree", {"terminal_id": terminal_id}, result)

    def terminal_trees(self) -> dict[str, Any]:
        with self.seed.ledger() as ledger:
            terminals = ledger.terminal_trees()
            result = {"status": "available", "terminal_count": len(terminals), "terminals": terminals}
        return self._record("terminal_trees", {}, result)

    def verify_terminal_trees(self) -> dict[str, Any]:
        with self.seed.ledger() as ledger:
            result = ledger.verify_terminal_trees()
        return self._record("verify_terminal_trees", {}, result)

    def morphonics_model(self) -> dict[str, Any]:
        with self.seed.ledger() as ledger:
            terminal_verification = ledger.verify_terminal_trees()
        result = morphonics_model_v0_2(terminal_tree_verification=terminal_verification)
        return self._record("morphonics_model", {"model_id": result["model_id"]}, result)

    def verify_morphonics(self) -> dict[str, Any]:
        with self.seed.ledger() as ledger:
            terminal_verification = ledger.verify_terminal_trees()
        model = morphonics_model_v0_2(terminal_tree_verification=terminal_verification)
        result = verify_morphonics_model(model)
        return self._record("verify_morphonics", {"model_id": model["model_id"]}, result)

    def rule30_morphon(self, max_depth: int = 7, sample_count: int = 512) -> dict[str, Any]:
        result = rule30_morphon_hardened(max_depth=max_depth, sample_count=sample_count)
        return self._record(
            "rule30_morphon",
            {"max_depth": max_depth, "sample_count": sample_count},
            result,
        )

    def verify_rule30(self, max_depth: int = 7, sample_count: int = 512) -> dict[str, Any]:
        model = rule30_morphon_hardened(max_depth=max_depth, sample_count=sample_count)
        result = verify_rule30_morphon(model)
        return self._record(
            "verify_rule30",
            {"max_depth": max_depth, "sample_count": sample_count},
            result,
        )

    def rule30_vignettes(self, max_order: int = 4) -> dict[str, Any]:
        result = rule30_vignette_algebra(max_order=max_order)
        return self._record("rule30_vignettes", {"max_order": max_order}, result)

    def verify_rule30_vignettes(self, max_order: int = 4) -> dict[str, Any]:
        model = rule30_vignette_algebra(max_order=max_order)
        result = verify_rule30_vignette_algebra(model)
        return self._record("verify_rule30_vignettes", {"max_order": max_order}, result)

    def rule30_moving_frame(self, max_depth: int = 12, max_order: int = 4) -> dict[str, Any]:
        result = rule30_moving_frame(max_depth=max_depth, max_order=max_order)
        return self._record(
            "rule30_moving_frame",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def verify_rule30_moving_frame(self, max_depth: int = 12, max_order: int = 4) -> dict[str, Any]:
        model = rule30_moving_frame(max_depth=max_depth, max_order=max_order)
        result = verify_rule30_moving_frame(model)
        return self._record(
            "verify_rule30_moving_frame",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def rule30_color_chirality(self, max_depth: int = 12, max_order: int = 4) -> dict[str, Any]:
        result = rule30_color_chirality_cipher(max_depth=max_depth, max_order=max_order)
        return self._record(
            "rule30_color_chirality",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def verify_rule30_color_chirality(self, max_depth: int = 12, max_order: int = 4) -> dict[str, Any]:
        model = rule30_color_chirality_cipher(max_depth=max_depth, max_order=max_order)
        result = verify_rule30_color_chirality_cipher(model)
        return self._record(
            "verify_rule30_color_chirality",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def rule30_lagrangian(self, max_depth: int = 12, max_order: int = 4) -> dict[str, Any]:
        result = rule30_discrete_lagrangian(max_depth=max_depth, max_order=max_order)
        return self._record(
            "rule30_lagrangian",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def verify_rule30_lagrangian(self, max_depth: int = 12, max_order: int = 4) -> dict[str, Any]:
        model = rule30_discrete_lagrangian(max_depth=max_depth, max_order=max_order)
        result = verify_rule30_discrete_lagrangian(model)
        return self._record(
            "verify_rule30_lagrangian",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def rule30_lagrangian_depth_trace(self, max_depth: int = 256, max_order: int = 4) -> dict[str, Any]:
        result = rule30_lagrangian_depth_trace(max_depth=max_depth, max_order=max_order)
        return self._record(
            "rule30_lagrangian_depth_trace",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def verify_rule30_lagrangian_depth_trace(self, max_depth: int = 256, max_order: int = 4) -> dict[str, Any]:
        model = rule30_lagrangian_depth_trace(max_depth=max_depth, max_order=max_order)
        result = verify_rule30_lagrangian_depth_trace(model)
        return self._record(
            "verify_rule30_lagrangian_depth_trace",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def rule30_mandelbrot_scalar(self, max_depth: int = 256, max_order: int = 4) -> dict[str, Any]:
        result = rule30_mandelbrot_boundary_scalar(max_depth=max_depth, max_order=max_order)
        return self._record(
            "rule30_mandelbrot_scalar",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def verify_rule30_mandelbrot_scalar(self, max_depth: int = 256, max_order: int = 4) -> dict[str, Any]:
        model = rule30_mandelbrot_boundary_scalar(max_depth=max_depth, max_order=max_order)
        result = verify_rule30_mandelbrot_boundary_scalar(model)
        return self._record(
            "verify_rule30_mandelbrot_scalar",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def rule30_reduced_alphabet(self, max_depth: int = 1024, max_order: int = 4) -> dict[str, Any]:
        result = rule30_reduced_alphabet_catalog(max_depth=max_depth, max_order=max_order)
        return self._record(
            "rule30_reduced_alphabet",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def verify_rule30_reduced_alphabet(self, max_depth: int = 1024, max_order: int = 4) -> dict[str, Any]:
        model = rule30_reduced_alphabet_catalog(max_depth=max_depth, max_order=max_order)
        result = verify_rule30_reduced_alphabet_catalog(model)
        return self._record(
            "verify_rule30_reduced_alphabet",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def rule30_symmetry_environment(
        self,
        max_depth: int = 1024,
        max_period: int = 128,
        max_order: int = 4,
    ) -> dict[str, Any]:
        result = rule30_symmetry_environment(
            max_depth=max_depth,
            max_period=max_period,
            max_order=max_order,
        )
        return self._record(
            "rule30_symmetry_environment",
            {"max_depth": max_depth, "max_period": max_period, "max_order": max_order},
            result,
        )

    def verify_rule30_symmetry_environment(
        self,
        max_depth: int = 1024,
        max_period: int = 128,
        max_order: int = 4,
    ) -> dict[str, Any]:
        model = rule30_symmetry_environment(
            max_depth=max_depth,
            max_period=max_period,
            max_order=max_order,
        )
        result = verify_rule30_symmetry_environment(model)
        return self._record(
            "verify_rule30_symmetry_environment",
            {"max_depth": max_depth, "max_period": max_period, "max_order": max_order},
            result,
        )

    def rule30_physics_method_stack(
        self,
        max_depth: int = 1024,
        max_period: int = 128,
        max_order: int = 4,
        max_block: int = 8,
    ) -> dict[str, Any]:
        result = rule30_physics_method_stack(
            max_depth=max_depth,
            max_period=max_period,
            max_order=max_order,
            max_block=max_block,
        )
        return self._record(
            "rule30_physics_method_stack",
            {"max_depth": max_depth, "max_period": max_period, "max_order": max_order, "max_block": max_block},
            result,
        )

    def verify_rule30_physics_method_stack(
        self,
        max_depth: int = 1024,
        max_period: int = 128,
        max_order: int = 4,
        max_block: int = 8,
    ) -> dict[str, Any]:
        model = rule30_physics_method_stack(
            max_depth=max_depth,
            max_period=max_period,
            max_order=max_order,
            max_block=max_block,
        )
        result = verify_rule30_physics_method_stack(model)
        return self._record(
            "verify_rule30_physics_method_stack",
            {"max_depth": max_depth, "max_period": max_period, "max_order": max_order, "max_block": max_block},
            result,
        )

    def rule30_whole_integer_n_coverage(
        self,
        max_depth: int = 4096,
        max_order: int = 4,
    ) -> dict[str, Any]:
        result = rule30_whole_integer_n_scalar_coverage(max_depth=max_depth, max_order=max_order)
        return self._record(
            "rule30_whole_integer_n_scalar_coverage",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def verify_rule30_whole_integer_n_coverage(
        self,
        max_depth: int = 4096,
        max_order: int = 4,
    ) -> dict[str, Any]:
        model = rule30_whole_integer_n_scalar_coverage(max_depth=max_depth, max_order=max_order)
        result = verify_rule30_whole_integer_n_scalar_coverage(model)
        return self._record(
            "verify_rule30_whole_integer_n_scalar_coverage",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def rule30_readout_ribbon_machine(
        self,
        max_depth: int = 4096,
        max_order: int = 4,
    ) -> dict[str, Any]:
        result = rule30_readout_ribbon_machine(max_depth=max_depth, max_order=max_order)
        return self._record(
            "rule30_readout_ribbon_machine",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def verify_rule30_readout_ribbon_machine(
        self,
        max_depth: int = 4096,
        max_order: int = 4,
    ) -> dict[str, Any]:
        model = rule30_readout_ribbon_machine(max_depth=max_depth, max_order=max_order)
        result = verify_rule30_readout_ribbon_machine(model)
        return self._record(
            "verify_rule30_readout_ribbon_machine",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def rule30_dihedral_block_hypervisor(
        self,
        max_depth: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        result = rule30_dihedral_block_hypervisor(
            max_depth=max_depth,
            block_size=block_size,
            max_order=max_order,
        )
        return self._record(
            "rule30_dihedral_block_hypervisor",
            {"max_depth": max_depth, "block_size": block_size, "max_order": max_order},
            result,
        )

    def verify_rule30_dihedral_block_hypervisor(
        self,
        max_depth: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        model = rule30_dihedral_block_hypervisor(
            max_depth=max_depth,
            block_size=block_size,
            max_order=max_order,
        )
        result = verify_rule30_dihedral_block_hypervisor(model)
        return self._record(
            "verify_rule30_dihedral_block_hypervisor",
            {"max_depth": max_depth, "block_size": block_size, "max_order": max_order},
            result,
        )

    def rule30_hypervisor_extension_tape(
        self,
        page_count: int = 2,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        result = rule30_hypervisor_extension_tape(
            page_count=page_count,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        return self._record(
            "rule30_hypervisor_extension_tape",
            {"page_count": page_count, "page_size": page_size, "block_size": block_size, "max_order": max_order},
            result,
        )

    def verify_rule30_hypervisor_extension_tape(
        self,
        page_count: int = 2,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        model = rule30_hypervisor_extension_tape(
            page_count=page_count,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        result = verify_rule30_hypervisor_extension_tape(model)
        return self._record(
            "verify_rule30_hypervisor_extension_tape",
            {"page_count": page_count, "page_size": page_size, "block_size": block_size, "max_order": max_order},
            result,
        )

    def rule30_sheet_operator(
        self,
        page_count: int = 2,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        result = rule30_sheet_operator(
            page_count=page_count,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        return self._record(
            "rule30_sheet_operator",
            {"page_count": page_count, "page_size": page_size, "block_size": block_size, "max_order": max_order},
            result,
        )

    def verify_rule30_sheet_operator(
        self,
        page_count: int = 2,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        model = rule30_sheet_operator(
            page_count=page_count,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        result = verify_rule30_sheet_operator(model)
        return self._record(
            "verify_rule30_sheet_operator",
            {"page_count": page_count, "page_size": page_size, "block_size": block_size, "max_order": max_order},
            result,
        )

    def rule30_mandelbrot_field_address(
        self,
        n: int,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        result = rule30_mandelbrot_field_address(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        return self._record(
            "rule30_mandelbrot_field_address",
            {"n": n, "page_size": page_size, "block_size": block_size, "max_order": max_order},
            result,
        )

    def verify_rule30_mandelbrot_field_address(
        self,
        n: int,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        model = rule30_mandelbrot_field_address(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        result = verify_rule30_mandelbrot_field_address(model)
        return self._record(
            "verify_rule30_mandelbrot_field_address",
            {"n": n, "page_size": page_size, "block_size": block_size, "max_order": max_order},
            result,
        )

    def rule30_exit_trajectory(
        self,
        n: int,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        result = rule30_exit_trajectory(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        return self._record(
            "rule30_exit_trajectory",
            {"n": n, "page_size": page_size, "block_size": block_size, "max_order": max_order},
            result,
        )

    def verify_rule30_exit_trajectory(
        self,
        n: int,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        model = rule30_exit_trajectory(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        result = verify_rule30_exit_trajectory(model)
        return self._record(
            "verify_rule30_exit_trajectory",
            {"n": n, "page_size": page_size, "block_size": block_size, "max_order": max_order},
            result,
        )

    def rule30_sheet_lift(
        self,
        n: int,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        result = rule30_sheet_lift(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        return self._record(
            "rule30_sheet_lift",
            {"n": n, "page_size": page_size, "block_size": block_size, "max_order": max_order},
            result,
        )

    def verify_rule30_sheet_lift(
        self,
        n: int,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        model = rule30_sheet_lift(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        result = verify_rule30_sheet_lift(model)
        return self._record(
            "verify_rule30_sheet_lift",
            {"n": n, "page_size": page_size, "block_size": block_size, "max_order": max_order},
            result,
        )

    def rule30_julia_resolution(
        self,
        n: int,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        result = rule30_julia_resolution(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        return self._record(
            "rule30_julia_resolution",
            {"n": n, "page_size": page_size, "block_size": block_size, "max_order": max_order},
            result,
        )

    def verify_rule30_julia_resolution(
        self,
        n: int,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        model = rule30_julia_resolution(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        result = verify_rule30_julia_resolution(model)
        return self._record(
            "verify_rule30_julia_resolution",
            {"n": n, "page_size": page_size, "block_size": block_size, "max_order": max_order},
            result,
        )

    def rule30_torsor_functor_term(
        self,
        n: int,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        result = rule30_torsor_functor_term(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        return self._record(
            "rule30_torsor_functor_term",
            {"n": n, "page_size": page_size, "block_size": block_size, "max_order": max_order},
            result,
        )

    def verify_rule30_torsor_functor_term(
        self,
        n: int,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        model = rule30_torsor_functor_term(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        result = verify_rule30_torsor_functor_term(model)
        return self._record(
            "verify_rule30_torsor_functor_term",
            {"n": n, "page_size": page_size, "block_size": block_size, "max_order": max_order},
            result,
        )

    def rule30_spinor_oloid_model(
        self,
        max_depth: int = 4096,
        max_order: int = 4,
    ) -> dict[str, Any]:
        result = rule30_spinor_oloid_model(max_depth=max_depth, max_order=max_order)
        return self._record(
            "rule30_spinor_oloid_model",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def verify_rule30_spinor_oloid_model(
        self,
        max_depth: int = 4096,
        max_order: int = 4,
    ) -> dict[str, Any]:
        model = rule30_spinor_oloid_model(max_depth=max_depth, max_order=max_order)
        result = verify_rule30_spinor_oloid_model(model)
        return self._record(
            "verify_rule30_spinor_oloid_model",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def rule30_oloid_winding_from_n(
        self,
        n: int,
        axis_angle: float = 1.5707963267948966,
        pattern: str = "alternating_xy",
        shell_axis: str = "z",
        side_axis: str = "x",
        shell_offset: float = 0.0,
        side_threshold: float = 0.05,
        parameterization: str = "identity",
    ) -> dict[str, Any]:
        result = rule30_oloid_winding_from_n(
            n,
            axis_angle=axis_angle,
            pattern=pattern,
            shell_axis=shell_axis,
            side_axis=side_axis,
            shell_offset=shell_offset,
            side_threshold=side_threshold,
            parameterization=parameterization,
        )
        return self._record(
            "rule30_oloid_winding_from_n",
            {
                "n": n,
                "axis_angle": axis_angle,
                "pattern": pattern,
                "shell_axis": shell_axis,
                "side_axis": side_axis,
                "shell_offset": shell_offset,
                "side_threshold": side_threshold,
                "parameterization": parameterization,
            },
            result,
        )

    def rule30_oloid_parameterization_scan(self, max_depth: int = 256) -> dict[str, Any]:
        result = rule30_oloid_parameterization_scan(max_depth=max_depth)
        return self._record("rule30_oloid_parameterization_scan", {"max_depth": max_depth}, result)

    def rule30_oloid_antipodal_winding(
        self,
        n: int,
        axis_angle: float = 1.5707963267948966,
        pattern: str = "alternating_xy",
        shell_axis: str = "z",
        side_axis: str = "x",
        shell_offset: float = 0.0,
        side_threshold: float = 0.05,
        parameterization: str = "identity",
    ) -> dict[str, Any]:
        result = rule30_oloid_antipodal_winding(
            n,
            axis_angle=axis_angle,
            pattern=pattern,
            shell_axis=shell_axis,
            side_axis=side_axis,
            shell_offset=shell_offset,
            side_threshold=side_threshold,
            parameterization=parameterization,
        )
        return self._record(
            "rule30_oloid_antipodal_winding",
            {
                "n": n,
                "axis_angle": axis_angle,
                "pattern": pattern,
                "shell_axis": shell_axis,
                "side_axis": side_axis,
                "shell_offset": shell_offset,
                "side_threshold": side_threshold,
                "parameterization": parameterization,
            },
            result,
        )

    def verify_rule30_oloid_winding_from_n(
        self,
        max_depth: int = 256,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = verify_rule30_oloid_winding_from_n(max_depth=max_depth, config=config)
        return self._record(
            "verify_rule30_oloid_winding_from_n",
            {"max_depth": max_depth, "config": config or {}},
            result,
        )

    def verify_rule30_oloid_antipodal_winding(
        self,
        max_depth: int = 256,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = verify_rule30_oloid_antipodal_winding(max_depth=max_depth, config=config)
        return self._record(
            "verify_rule30_oloid_antipodal_winding",
            {"max_depth": max_depth, "config": config or {}},
            result,
        )

    def rule30_winding_number_proof(
        self,
        max_depth: int = 4096,
        max_order: int = 4,
    ) -> dict[str, Any]:
        result = rule30_winding_number_proof(max_depth=max_depth, max_order=max_order)
        return self._record(
            "rule30_winding_number_proof",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def verify_rule30_winding_number_proof(
        self,
        max_depth: int = 4096,
        max_order: int = 4,
    ) -> dict[str, Any]:
        model = rule30_winding_number_proof(max_depth=max_depth, max_order=max_order)
        result = verify_rule30_winding_number_proof(model)
        return self._record(
            "verify_rule30_winding_number_proof",
            {"max_depth": max_depth, "max_order": max_order},
            result,
        )

    def rule30_nth_bit_expression(
        self,
        n: int,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        result = rule30_nth_bit_expression(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        return self._record(
            "rule30_nth_bit_expression",
            {"n": n, "page_size": page_size, "block_size": block_size, "max_order": max_order},
            result,
        )

    def verify_rule30_nth_bit_expression(
        self,
        n: int,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        model = rule30_nth_bit_expression(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        result = verify_rule30_nth_bit_expression(model)
        return self._record(
            "verify_rule30_nth_bit_expression",
            {"n": n, "page_size": page_size, "block_size": block_size, "max_order": max_order},
            result,
        )

    def rule30_proof_obligations(
        self,
        max_depth: int = 4096,
        page_count: int = 2,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        result = rule30_proof_obligation_ledger(
            max_depth=max_depth,
            page_count=page_count,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        return self._record(
            "rule30_proof_obligation_ledger",
            {
                "max_depth": max_depth,
                "page_count": page_count,
                "page_size": page_size,
                "block_size": block_size,
                "max_order": max_order,
            },
            result,
        )

    def verify_rule30_proof_obligations(
        self,
        max_depth: int = 4096,
        page_count: int = 2,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ) -> dict[str, Any]:
        model = rule30_proof_obligation_ledger(
            max_depth=max_depth,
            page_count=page_count,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )
        result = verify_rule30_proof_obligation_ledger(model)
        return self._record(
            "verify_rule30_proof_obligation_ledger",
            {
                "max_depth": max_depth,
                "page_count": page_count,
                "page_size": page_size,
                "block_size": block_size,
                "max_order": max_order,
            },
            result,
        )

    def future_cone(self, object_id: str, max_depth: int = 8) -> dict[str, Any]:
        with self.seed.ledger() as ledger:
            result = ledger.future_cone(object_id, max_depth=max_depth)
        return self._record("future_cone", {"object_id": object_id, "max_depth": max_depth}, result)

    def exactness_dashboard(self, object_id: str) -> dict[str, Any]:
        with self.seed.ledger() as ledger:
            result = ledger.exactness_dashboard(object_id)
        return self._record("exactness_dashboard", {"object_id": object_id}, result)

    def witnesses(
        self,
        source_id: str | None = None,
        target_id: str | None = None,
        morphism_id: str | None = None,
    ) -> dict[str, Any]:
        with self.seed.ledger() as ledger:
            result = {
                "witnesses": ledger.morphism_witnesses(
                    source_id=source_id,
                    target_id=target_id,
                    morphism_id=morphism_id,
                )
            }
        return self._record(
            "witnesses",
            {"source_id": source_id, "target_id": target_id, "morphism_id": morphism_id},
            result,
        )

    def record_witnessed_encode(
        self,
        state_keys: list[str],
        *,
        encoded: dict[str, Any],
        from_regime: str,
        to_regime: str,
        max_depth: int,
    ) -> None:
        """Store regime-encode payload under canonical keys (primary + stub suffix)."""
        base = {
            "from_regime": from_regime,
            "to_regime": to_regime,
            "max_depth": max_depth,
            "encoded": encoded,
        }
        for key in state_keys:
            if key.endswith("/witness_stub"):
                continue
            self._witness_store.put(key, {**base, "state_key": key})

    def witnessed_lookup(self, state_key: str) -> dict[str, Any]:
        """Return witnessed encode payload when present; else honest NOT_WITNESSED."""
        from lattice_forge.witness.state_keys import parse_state_key

        parsed = parse_state_key(state_key)
        stored = self._witness_store.get(state_key)
        if stored is not None and parsed.get("valid"):
            result = {
                "state_key": state_key,
                "answer": "WITNESSED",
                "witnessed": True,
                "grammar": parsed,
                "payload": stored,
            }
        else:
            result = {
                "state_key": state_key,
                "answer": "NOT_WITNESSED",
                "witnessed": False,
                "grammar": parsed,
            }
        return self._record("witnessed_lookup", {"state_key": state_key}, result)

    def obstructions(
        self,
        source_id: str | None = None,
        target_id: str | None = None,
    ) -> dict[str, Any]:
        with self.seed.ledger() as ledger:
            result = {
                "obstructions": ledger.closure_obstructions(
                    source_id=source_id,
                    target_id=target_id,
                )
            }
        return self._record("obstructions", {"source_id": source_id, "target_id": target_id}, result)

    def export_object(self, object_id: str, vector_limit: int = 12) -> dict[str, Any]:
        with self.seed.ledger() as ledger:
            result = ledger.export_object_bundle(object_id, vector_limit=vector_limit)
        return self._record(
            "export_object",
            {"object_id": object_id, "vector_limit": vector_limit},
            result,
        )

    def latest_events(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.overlay.latest_events(limit)

    def latest_receipts(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.overlay.latest_receipts(limit)

    def snapshot(self, limit: int = 100) -> dict[str, Any]:
        return {
            "status": self.status(),
            "overlay": self.overlay.snapshot(limit=limit),
        }

    def record_solver_event(
        self,
        *,
        operation: str = "record_solver_event",
        landauer_cost: float,
        shannon_residue: float = 0.0,
        noether_residue: float = 0.0,
        obligation_delta: float = 0.0,
        v_before: float = 0.0,
        v_after: float = 0.0,
        **metadata: Any,
    ) -> dict[str, Any]:
        """Record solver build/query cost via NSL boundary term + optional CMPLX port."""
        from .ledger.nsl import NSLTerm
        from .tools.nsl import NSLTool

        term = NSLTerm(
            noether_residue=noether_residue if noether_residue else obligation_delta,
            shannon_residue=shannon_residue,
            landauer_cost=landauer_cost,
        )
        nsl_result = NSLTool().invoke(
            term=term,
            v_before=(v_before, v_before, v_before),
            v_after=(v_after, v_after, v_after),
            operation=operation,
        )
        result = {
            "operation": operation,
            "nsl_term": term.as_dict(),
            "nsl_port": nsl_result,
            "nsl_available": NSLTool.available(),
            **metadata,
        }
        return self._record(
            "solver_event",
            {"operation": operation, **metadata},
            result,
        )
