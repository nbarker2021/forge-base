from __future__ import annotations
from typing import Any, Dict
from .encoder import image_receipt_to_worldforge

def to_researchcraft_payload(receipt) -> Dict[str, Any]:
    graph = image_receipt_to_worldforge(receipt)
    return {
        "journal_slug": "pixleforge",
        "source_type": "image",
        "receipt_id": receipt.receipt_id,
        "nodes": graph["nodes"],
        "edges": graph["edges"],
        "obligations": [n for n in graph["nodes"] if n.get("payload",{}).get("correction") == 1],
        "metadata": graph["metadata"],
    }
