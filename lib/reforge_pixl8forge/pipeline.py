from __future__ import annotations
from .frames import Frame, make_demo_frame, frame_to_worldforge_nodes
from .rote8 import rote8
from .devi8 import devi8_transition
from .concat8 import concat8
from typing import Dict, Any, List
import time, json, hashlib


def pixl8_receipt(seed: str = "demo", width: int = 8, height: int = 8) -> Dict[str, Any]:
    base = make_demo_frame(width, height, phase=0, label=f"{seed}:base")
    target = rote8(make_demo_frame(width, height, phase=3, label=f"{seed}:target"), 1)
    # if orientation changes dimensions, rotate target back into same dims for Devi8 if needed
    if target.width != base.width or target.height != base.height:
        target = rote8(target, 3)
    dev = devi8_transition(base, target, steps=8, include_endpoints=True)
    cat = concat8([dev])
    graphs = [frame_to_worldforge_nodes(f, prefix="pixl8") for f in cat["frames"]]
    nodes = []
    edges = []
    prev_frame_id = None
    for idx, g in enumerate(graphs):
        frame_id = f"frame_{idx}"
        nodes.append({"id": frame_id, "kind": "frame", "label": g["frame"]["label"], "phase": g["frame"]["phase"], "digest": g["frame"]["digest"]})
        if prev_frame_id:
            edges.append({"source": prev_frame_id, "target": frame_id, "kind": "temporal_concat8"})
        prev_frame_id = frame_id
        for n in g["nodes"]:
            n2 = dict(n); n2["id"] = f"{frame_id}:{n['id']}"; nodes.append(n2)
            edges.append({"source": frame_id, "target": n2["id"], "kind": "contains_pixel_block"})
    payload = {
        "engine": "PixL8Forge",
        "operators": ["Rote8", "Devi8", "Concat8"],
        "seed": seed,
        "created_at": time.time(),
        "frame_count": cat["frame_count"],
        "boundary_receipts": cat["boundary_receipts"],
        "graph": {"nodes": nodes, "edges": edges},
        "claim": "Rote8 orients frames; Devi8 composes clean internal pixel transition; Concat8 joins eightfold segments with receipts.",
    }
    payload["receipt_id"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    return payload
