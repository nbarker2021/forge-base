from __future__ import annotations
from .frames import Frame
from typing import Iterable, List, Dict, Any


def concat8(segments: Iterable[List[Frame]], trim_duplicate_boundaries: bool = True) -> Dict[str, Any]:
    """Concat8: concatenate up to 8 transition segments with boundary receipts."""
    out: List[Frame] = []
    receipts = []
    for i, seg in enumerate(segments):
        if not seg:
            continue
        for f in seg:
            f.validate()
        start_digest = seg[0].digest()
        end_digest = seg[-1].digest()
        added = seg
        if trim_duplicate_boundaries and out and out[-1].digest() == start_digest:
            added = seg[1:]
        out.extend(added)
        receipts.append({"segment": i, "frames": len(seg), "start_digest": start_digest, "end_digest": end_digest, "added": len(added)})
    return {"frames": out, "boundary_receipts": receipts, "frame_count": len(out)}
