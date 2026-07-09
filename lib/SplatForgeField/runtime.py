"""SplatForgeField.runtime — the governed field loop.

Implements the operator's non-negotiable interaction separation (§7):

  * READOUT manipulation (view) changes only the view. No child crystal.
  * SEMANTIC manipulation changes the model. ALWAYS creates a child crystal
    with parent linkage and a persisted field receipt.

And the contract (§1):
  * Nothing semantic changes through visual manipulation alone.
  * Nothing becomes persistent until it has a receipt.

The SpatialField is regenerable (field.py) and is therefore not persisted;
only field receipts and parent->child crystal lineage are written to SQLite
(CrystalForge schema: field_receipts, field_lineage).
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

from CrystalForge import crystal as _crystal
from CrystalForge.schema import get_connection
from .field import SpatialField, compile_field, FIELD_ADAPTER_ID

GENESIS = "0" * 64

VIEW_OPS = {"rotate", "zoom", "hide", "isolate", "expand_shell", "change_grammar", "reset"}
SEMANTIC_OPS = {"add_datum", "change_bond", "approve_relation", "alter_constraint",
                "run_forge", "change_validator"}


def classify_op(op: str) -> str:
    if op in VIEW_OPS:
        return "view"
    if op in SEMANTIC_OPS:
        return "semantic"
    raise ValueError(f"unknown op {op!r}; not in VIEW_OPS or SEMANTIC_OPS")


class FieldRuntime:
    """One runtime == one governed crystal->field->interaction->receipt loop."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path
        self._head: str = GENESIS
        self.view_state: Dict[str, Any] = {"rotation": (0.0, 0.0, 0.0), "zoom": 1.0,
                                            "isolated": None, "grammar": None}

    # --- compile + receipt -------------------------------------------------
    def compile(self, crystal_id: str, grammar: str = "claim_graph") -> SpatialField:
        field = compile_field(crystal_id, grammar=grammar, db_path=self.db_path)
        self.view_state["grammar"] = grammar
        self._mint_field_receipt(field, op="compile")
        return field

    def _mint_field_receipt(self, field: SpatialField, op: str,
                            application_frame_hash: str = "") -> Dict[str, Any]:
        ts = time.time()
        crystal = _crystal.get_crystal(field.crystal_id, self.db_path)
        revision = crystal.receipt_chain if crystal else ""
        receipt_hash = hashlib.sha256(
            f"{self._head}:{field.field_id}:{field.scene_graph_hash}:"
            f"{field.splat_buffer_hash}:{op}:{ts}".encode()
        ).hexdigest()
        payload = {
            "field_id": field.field_id, "crystal_id": field.crystal_id,
            "crystal_revision": revision, "grammar": field.grammar,
            "scene_graph_hash": field.scene_graph_hash,
            "splat_buffer_hash": field.splat_buffer_hash,
            "application_frame_hash": application_frame_hash,
            "render_backend": "cpu_reference", "visibility_policy": "default",
            "adapter_id": FIELD_ADAPTER_ID, "op": op,
            "prev_hash": self._head, "receipt_head": receipt_hash,
        }
        conn = get_connection(self.db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO field_receipts
                   (receipt_hash, field_id, crystal_id, crystal_revision, grammar,
                    scene_graph_hash, splat_buffer_hash, application_frame_hash,
                    render_backend, visibility_policy, prev_hash, payload, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (receipt_hash, field.field_id, field.crystal_id, revision, field.grammar,
                 field.scene_graph_hash, field.splat_buffer_hash, application_frame_hash,
                 "cpu_reference", "default", self._head, json.dumps(payload), ts),
            )
            conn.commit()
        finally:
            conn.close()
        self._head = receipt_hash
        return payload

    # --- interaction -------------------------------------------------------
    def interact(self, field: SpatialField, op: str, **payload: Any) -> Dict[str, Any]:
        """Apply one interaction. View ops mutate only self.view_state and
        return no child. Semantic ops fork a child crystal + persist a
        receipt + record lineage."""
        op_class = classify_op(op)
        if op_class == "view":
            return self._apply_view(op, payload)
        return self._apply_semantic(field, op, payload)

    def _apply_view(self, op: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if op == "rotate":
            self.view_state["rotation"] = tuple(payload.get("rotation", (0, 0, 0)))
        elif op == "zoom":
            self.view_state["zoom"] = float(payload.get("zoom", 1.0))
        elif op == "isolate":
            self.view_state["isolated"] = payload.get("lineage")
        elif op == "change_grammar":
            self.view_state["grammar"] = payload.get("grammar")
        elif op == "reset":
            self.view_state = {"rotation": (0, 0, 0), "zoom": 1.0, "isolated": None,
                               "grammar": self.view_state.get("grammar")}
        return {"class": "view", "op": op, "created_child": False,
                "view_state": dict(self.view_state)}

    def _apply_semantic(self, field: SpatialField, op: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        child_id = self._fork_crystal(field.crystal_id, op, payload)
        child_field = compile_field(child_id, grammar=field.grammar, db_path=self.db_path)
        receipt = self._mint_field_receipt(child_field, op=op)
        self._record_lineage(field.crystal_id, child_id, op, receipt["receipt_head"])
        return {"class": "semantic", "op": op, "created_child": True,
                "parent_crystal": field.crystal_id, "child_crystal": child_id,
                "child_field": child_field.summary(), "receipt_hash": receipt["receipt_head"]}

    def _fork_crystal(self, parent_id: str, op: str, payload: Dict[str, Any]) -> str:
        from SplatForgeField.stable_ids import field_child_name

        parent_nodes = _crystal.get_nodes(parent_id, self.db_path)
        child = _crystal.create_crystal(
            name=field_child_name(parent_id, op, payload),
            crystal_type="field_child", owner="field_runtime", db_path=self.db_path)
        # copy parent atoms verbatim (the child is a branch, not a fresh datum)
        for n in parent_nodes:
            _crystal.add_node(child.crystal_id, content=n.content, content_type=n.content_type,
                              e8_coords=n.e8_coords, labels=n.snap_labels, db_path=self.db_path)
        # apply the semantic edit as a new, recorded atom (v0.1: edits are atoms;
        # a typed bond-edit model is the documented next step)
        if op == "add_datum":
            _crystal.add_node(child.crystal_id, content=str(payload.get("content", "")),
                              content_type="atom", labels=payload.get("labels", []),
                              db_path=self.db_path)
        else:
            _crystal.add_node(child.crystal_id, content=json.dumps({"op": op, **payload}, default=str),
                              content_type="edit", labels=[op], db_path=self.db_path)
        # promote so other systems can pull it (growing -> committed -> active)
        _crystal.commit_crystal(child.crystal_id, self.db_path)
        _crystal.activate_crystal(child.crystal_id, self.db_path)
        return child.crystal_id

    def _record_lineage(self, parent: str, child: str, op: str, receipt_hash: str) -> None:
        conn = get_connection(self.db_path)
        try:
            conn.execute(
                """INSERT INTO field_lineage (parent_crystal, child_crystal, relation, op,
                    receipt_hash, created_at) VALUES (?,?,?,?,?,?)""",
                (parent, child, "semantic_edit", op, receipt_hash, time.time()),
            )
            conn.commit()
        finally:
            conn.close()

    def lineage_of(self, crystal_id: str) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        try:
            rows = conn.execute(
                "SELECT parent_crystal, child_crystal, op, receipt_hash FROM field_lineage "
                "WHERE parent_crystal = ? OR child_crystal = ? ORDER BY edge_id",
                (crystal_id, crystal_id)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
