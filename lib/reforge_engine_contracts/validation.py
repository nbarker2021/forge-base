from __future__ import annotations
from typing import Any, Dict, List
from .core import LCRBlock, GraphNode, GraphEdge, Receipt


def receipt_from_dict(d: Dict[str, Any]) -> Receipt:
    blocks = [LCRBlock(**b) for b in d.get("blocks", d.get("lcr_blocks", []))]
    nodes = [GraphNode(**n) for n in d.get("nodes", [])]
    edges = [GraphEdge(**e) for e in d.get("edges", [])]
    r = Receipt(
        d.get("receipt_id", "missing"),
        source_text=d.get("source_text", ""),
        followup=d.get("followup", d.get("status", "unresolved")),
        blocks=blocks,
        nodes=nodes,
        edges=edges,
        metadata=d.get("metadata", {}),
        created_at=d.get("created_at", d.get("timestamp", 0.0)),
    )
    r.validate()
    return r


def validate_lcr(block: Dict[str, Any]) -> Dict[str, Any]:
    b = LCRBlock(**block)
    b.validate()
    return block


def validate_graph(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, int]:
    node_ids = {n.get("id") for n in nodes}
    missing = 0
    for e in edges:
        if e.get("source") not in node_ids or e.get("target") not in node_ids:
            missing += 1
    if missing:
        raise ValueError(f"graph has {missing} dangling edges")
    return {"nodes": len(nodes), "edges": len(edges)}


def validate_worldforge_graph(graph: Dict[str, Any]) -> Dict[str, int]:
    return validate_graph(graph.get("nodes", []), graph.get("edges", []))
