"""SplatForgeField — the SplatForge Field Runtime v0.1.

A governed, datum-to-field spatial compiler: any admitted crystal becomes a
persistent, manipulable application field. Built as a deterministic loop, not a
hologram demo:

    Crystal -> SpatialField -> Interaction -> Receipt -> Child Crystal | View Reset

Three separated objects (operator's §3):
  A. Crystal graph (CrystalForge)  -- source of truth
  B. SpatialField (field.py)       -- reversible, regenerable projection
  C. ApplicationField (Phase B)    -- physical placement (projector/AR; not in v0.1)

Splats are a rendering carrier, never the meaning store. Nothing semantic
changes through visual manipulation alone; nothing persists without a receipt.
"""
from __future__ import annotations

from .field import (
    Atom, Bond, SpatialField, compile_field,
    FIELD_ADAPTER_ID, FIELD_ADAPTER_VERSION,
)
from .runtime import FieldRuntime, classify_op, VIEW_OPS, SEMANTIC_OPS
from .render import render_field, screen_layout, pick
from .adapter import SpatialForgeAdapter, SpatialForgeError
from .grammar import (
    SpatialGrammar, get_grammar, GRAMMAR_TABLE, GRAMMAR_NAMES,
    CLAIM_GRAPH, MOLECULE, ENGINEERING_PART, RULE30_STRIP,
)
from .reconstruct import (
    ReconstructForge, ReconstructReceipt, AtomReconstruction,
    build_view_layouts, VIEW_FRONT, VIEW_SIDE, VIEW_TOP, TOLERANCE,
)

__version__ = "0.1.0"

__all__ = [
    "Atom", "Bond", "SpatialField", "compile_field",
    "FieldRuntime", "classify_op", "VIEW_OPS", "SEMANTIC_OPS",
    "render_field", "screen_layout", "pick",
    "SpatialForgeAdapter", "SpatialForgeError",
    "SpatialGrammar", "get_grammar", "GRAMMAR_TABLE", "GRAMMAR_NAMES",
    "CLAIM_GRAPH", "MOLECULE", "ENGINEERING_PART", "RULE30_STRIP",
    "ReconstructForge", "ReconstructReceipt", "AtomReconstruction",
    "build_view_layouts", "VIEW_FRONT", "VIEW_SIDE", "VIEW_TOP", "TOLERANCE",
    "FIELD_ADAPTER_ID", "FIELD_ADAPTER_VERSION", "verify",
]


def verify(db_path=None) -> dict:
    """Smoke-verify the WP-01 exit gate (determinism) and the §7 interaction
    separation (view changes no model; semantic forks a child crystal)."""
    import tempfile, os
    from CrystalForge import crystal as _crystal

    if db_path is None:
        db_path = os.path.join(tempfile.gettempdir(), "splatforge_field_verify.db")
        if os.path.exists(db_path):
            os.remove(db_path)

    # a tiny crystal with three labeled atoms
    cr = _crystal.create_crystal("verify-field", crystal_type="cem", db_path=db_path)
    for i, (content, labels) in enumerate([
        ("thesis", ["claim"]), ("evidence-A", ["claim", "evidence"]),
        ("open-obligation", ["claim", "residue"]),
    ]):
        _crystal.add_node(cr.crystal_id, content=content, labels=labels, db_path=db_path)

    rt = FieldRuntime(db_path=db_path)
    f1 = rt.compile(cr.crystal_id)
    f2 = compile_field(cr.crystal_id, db_path=db_path)
    deterministic = (f1.scene_graph_hash == f2.scene_graph_hash
                     and f1.splat_buffer_hash == f2.splat_buffer_hash)

    view = rt.interact(f1, "rotate", rotation=(0.1, 0.2, 0.0))
    sem = rt.interact(f1, "add_datum", content="new-evidence", labels=["claim", "evidence"])

    return {
        "forge": "SplatForgeField",
        "status": "pass" if (deterministic and not view["created_child"]
                             and sem["created_child"]) else "fail",
        "deterministic_compile": deterministic,
        "scene_graph_hash": f1.scene_graph_hash[:16],
        "atoms": len(f1.atoms), "bonds": len(f1.bonds), "splats": len(f1.splats),
        "view_created_child": view["created_child"],
        "semantic_created_child": sem["created_child"],
        "child_crystal": sem.get("child_crystal"),
        "lineage_edges": len(rt.lineage_of(cr.crystal_id)),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2))
