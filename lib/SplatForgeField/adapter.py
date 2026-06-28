"""SplatForgeField.adapter — WP-05 LCR ring adapter for the spatial forge.

The adapter enforces the WP-05 kernel-ring controls:

  * View ops     -> allowed locally; no ring required.
  * Semantic ops -> must pass C-lane grant from the TypedKernel.
  * Export       -> must pass R-lane grant from the TypedKernel.
  * No renderer  -> can silently overwrite a promoted (active) crystal;
                    all semantic edits ALWAYS fork a child crystal.

The adapter wraps a FieldRuntime and a TypedKernel. The TypedKernel
carries the policy; the adapter enforces the lane check before
delegating to the runtime for semantic ops.

Exit gate (WP-05 spec): "a renderer cannot silently overwrite a
promoted crystal." Enforcement: (a) all semantic ops go through
C-lane check_lane(), which raises KernelPolicyError if the policy
denies center_dispatch; (b) all semantic ops fork a new child crystal
(never mutate the parent in place); (c) exports require R-lane grant.

Two factory constructors cover the two normal contexts:

  SpatialForgeAdapter.for_semantic_edits(runtime)
    -> C-lane open + R-lane open (edit + export allowed)

  SpatialForgeAdapter.for_readonly(runtime)
    -> all lanes denied (renderer-safe: only view ops pass through)
"""
from __future__ import annotations

import dataclasses
import json
from typing import Any, Dict, List, Optional

from .field import SpatialField
from .runtime import FieldRuntime, classify_op, VIEW_OPS, SEMANTIC_OPS


class SpatialForgeError(Exception):
    """Raised when the adapter rejects an operation."""


# The C-lane operation prefix used in grant receipts.
_RING_OP_PREFIX = "field"


class SpatialForgeAdapter:
    """LCR ring adapter: policy-gated surface over FieldRuntime.

    All view ops pass through immediately (no ring overhead).
    All semantic ops require an explicit C-lane grant from the
    TypedKernel policy before the FieldRuntime forks a child crystal.
    All exports require an explicit R-lane grant.

    The adapter never modifies the FieldRuntime's state directly;
    it delegates everything after the gate check.
    """

    def __init__(self, runtime: FieldRuntime, typed_kernel: Any) -> None:
        self.runtime = runtime
        self.typed_kernel = typed_kernel
        self._grants: List[Dict[str, Any]] = []

    # --- interaction ---------------------------------------------------------

    def interact(self, field: SpatialField, op: str, **payload: Any) -> Dict[str, Any]:
        """Route one interaction through the ring.

        View ops bypass the ring entirely (local read-only).
        Semantic ops require a C-lane grant; denied -> SpatialForgeError.
        """
        op_class = classify_op(op)

        if op_class == "view":
            result = self.runtime.interact(field, op, **payload)
            result["ring_gate"] = "bypassed_view"
            return result

        # Semantic: C-lane required.
        try:
            from cqekernel.lcr.typed_kernel import Lane
            grant = self.typed_kernel.check_lane(f"{_RING_OP_PREFIX}.{op}", Lane.C)
            self._grants.append(grant.to_dict())
        except Exception as exc:
            raise SpatialForgeError(
                f"semantic op {op!r} blocked by ring: {exc}"
            ) from exc

        result = self.runtime.interact(field, op, **payload)
        result["ring_gate"] = "c_lane_granted"
        result["lane_grant"] = self._grants[-1]
        return result

    # --- export --------------------------------------------------------------

    def export_field(self, field: SpatialField, format: str = "json") -> Dict[str, Any]:
        """Serialize the field for external consumption.

        Requires an explicit R-lane grant. Denied -> SpatialForgeError.
        The export carries a copy of the grant receipt so downstream
        systems can verify the export was authorized.
        """
        try:
            from cqekernel.lcr.typed_kernel import Lane
            grant = self.typed_kernel.check_lane(f"{_RING_OP_PREFIX}.export", Lane.R)
            self._grants.append(grant.to_dict())
        except Exception as exc:
            raise SpatialForgeError(
                f"export blocked by ring: {exc}"
            ) from exc

        atoms = [a.to_dict() for a in field.atoms]
        bonds = [b.to_dict() for b in field.bonds]
        return {
            "field_id": field.field_id,
            "crystal_id": field.crystal_id,
            "grammar": field.grammar,
            "scene_graph_hash": field.scene_graph_hash,
            "splat_buffer_hash": field.splat_buffer_hash,
            "atom_count": len(atoms),
            "bond_count": len(bonds),
            "atoms": atoms,
            "bonds": bonds,
            "format": format,
            "ring_gate": "r_lane_granted",
            "export_grant": self._grants[-1],
        }

    # --- audit ---------------------------------------------------------------

    def grants(self) -> List[Dict[str, Any]]:
        """Return all lane grants accumulated by this adapter, in order."""
        return list(self._grants)

    def grant_summary(self) -> Dict[str, Any]:
        """One-line summary: how many grants of each lane type."""
        from collections import Counter
        counts = Counter(g["lane"] for g in self._grants)
        return {
            "total_grants": len(self._grants),
            "by_lane": dict(counts),
            "semantic_ops_gated": sum(1 for g in self._grants
                                     if g.get("operation", "").startswith(f"{_RING_OP_PREFIX}.")
                                     and g["lane"] == "C"),
            "exports_gated": sum(1 for g in self._grants if g["lane"] == "R"),
        }

    # --- factories -----------------------------------------------------------

    @staticmethod
    def for_semantic_edits(runtime: FieldRuntime) -> "SpatialForgeAdapter":
        """Factory: C-lane + R-lane open (semantic edits + exports allowed).

        Use for trusted callers that have earned the right to fork crystals
        and export fields. The policy is explicit: center_dispatch=True and
        right_emit=True; left_io remains False (no external data reads).
        """
        from cqekernel.core.policy import Policy
        from cqekernel.lcr.typed_kernel import TypedKernel
        policy = Policy(allow_center_dispatch=True, allow_right_emit=True)
        tk = TypedKernel(kernel=None, policy=policy)
        return SpatialForgeAdapter(runtime, tk)

    @staticmethod
    def for_readonly(runtime: FieldRuntime) -> "SpatialForgeAdapter":
        """Factory: all lanes denied (renderer-safe).

        A renderer using this adapter can only call view ops (rotate, zoom,
        etc.). Any attempt to call a semantic op raises SpatialForgeError
        before the FieldRuntime is even reached; the promoted crystal is
        fully protected.
        """
        from cqekernel.core.policy import Policy
        from cqekernel.lcr.typed_kernel import TypedKernel
        policy = Policy.strict()
        tk = TypedKernel(kernel=None, policy=policy)
        return SpatialForgeAdapter(runtime, tk)


__all__ = ["SpatialForgeAdapter", "SpatialForgeError"]
