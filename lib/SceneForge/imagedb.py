"""
SceneForge ImageDB — the saved-pictures database.

Real images already on disk (PNG/BMP, decoded by PixelForge.images) become
indexed, content-hashed lib items: scan once, look up forever. Labels come
from path tokens; picks are deterministic by seed (same world = same cast).
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Optional

from PixelForge.images import load_image
from PixelForge.picture import Picture


class ImageDB:
    def __init__(self, index_path: "str | Path" = "imagedb.jsonl"):
        self.index_path = Path(index_path)
        self._items: Dict[str, Dict] = {}      # content_hash -> record
        self._pictures: Dict[str, Picture] = {}
        if self.index_path.is_file():
            for line in self.index_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    self._items[rec["content_hash"]] = rec

    # ── ingest ───────────────────────────────────────────────────────────────
    def scan(self, folder: "str | Path", limit: int = 64,
             min_px: int = 16) -> int:
        """Decode every supported real image under folder into the DB."""
        added = 0
        for p in sorted(Path(folder).rglob("*")):
            if added >= limit or p.suffix.lower() not in (".png", ".bmp"):
                continue
            pic = load_image(str(p))
            if pic is None or pic.width < min_px or pic.height < min_px:
                continue
            ch = pic.content_hash()
            if ch in self._items:
                continue
            rec = {"content_hash": ch, "path": str(p),
                   "width": pic.width, "height": pic.height,
                   "labels": [t.lower() for t in p.stem.replace("-", "_").split("_") if t]}
            self._items[ch] = rec
            self._pictures[ch] = pic
            with open(self.index_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
            added += 1
        return added

    # ── lookup ───────────────────────────────────────────────────────────────
    def picture(self, content_hash: str) -> Optional[Picture]:
        if content_hash in self._pictures:
            return self._pictures[content_hash]
        rec = self._items.get(content_hash)
        if rec:
            pic = load_image(rec["path"])
            if pic:
                self._pictures[content_hash] = pic
            return pic
        return None

    def pick(self, n: int, seed: int = 0,
             keywords: Optional[List[str]] = None) -> List[Picture]:
        """Deterministic cast selection: same seed = same pictures."""
        pool = list(self._items.values())
        if keywords:
            kw = [k.lower() for k in keywords]
            scored = sorted(pool, key=lambda r: -sum(
                1 for k in kw for lab in r["labels"] if k in lab))
            pool = scored
        rng = random.Random(seed)
        if len(pool) > n:
            head = pool[:max(n, 8)]
            pool = rng.sample(head, min(n, len(head)))
        out = []
        for rec in pool[:n]:
            pic = self.picture(rec["content_hash"])
            if pic:
                out.append(pic)
        return out

    @property
    def count(self) -> int:
        return len(self._items)

    def stats(self) -> Dict:
        return {"images": self.count,
                "index": str(self.index_path),
                "decoded_cached": len(self._pictures)}


def fit_to(pic: Picture, w: int, h: int) -> Picture:
    """Nearest-neighbor resample any real image onto a target sheet —
    resolution independence for the saved-picture layer."""
    out = Picture(w, h)
    for y in range(h):
        sy = y * pic.height // h
        for x in range(w):
            out.set(x, y, pic.get(x * pic.width // w, sy))
    return out
