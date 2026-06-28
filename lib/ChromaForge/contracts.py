"""
ChromaForge Contracts — the storage law made contractual.

THE STORAGE LAW:
  Nothing is ever saved that is not (a) a live run item, or (b) a crystal.
  Raw receipts, cache entries, sessions, lanes — all live-run scaffolding.
  At process end the receipt chain compresses to its bare active spine and
  crystallizes; everything else evaporates (its information is either in
  the crystal or was not load-bearing).

This module adds NO new engine. It defines the contracts the existing
engines adapt through:

  CrystalVault   — the BACKEND lib database. Crystal-form records only,
                   append-only on disk, loadable as lookup tables at boot.
                   This is the "optional backend" slot SpeedLight's design
                   always declared.

Adapters bind engines to contracts; engines stay untouched.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional


class CrystalVault:
    """The backend lib database. Crystals in, lookups out. Append-only JSONL
    (one crystal per line) so the vault is diff-able, git-able, and replayable.
    """

    def __init__(self, path: "Path | str"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._by_hash: Dict[str, Dict[str, Any]] = {}
        self._by_id: Dict[str, Dict[str, Any]] = {}
        if self.path.is_file():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        self._index(json.loads(line))
                    except json.JSONDecodeError:
                        continue   # a torn line is data loss already logged upstream

    # ── contract surface ─────────────────────────────────────────────────────
    def crystallize(self, crystal: Dict[str, Any]) -> Dict[str, Any]:
        """Persist one crystal. Idempotent by content_hash (re-crystallizing
        the same content is a free no-op — the lib never duplicates)."""
        ch = crystal.get("content_hash", "")
        with self._lock:
            if ch and ch in self._by_hash:
                return self._by_hash[ch]
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(crystal, separators=(",", ":")) + "\n")
            self._index(crystal)
        return crystal

    def lookup(self, content_hash: str) -> Optional[Dict[str, Any]]:
        return self._by_hash.get(content_hash)

    def get(self, crystal_id: str) -> Optional[Dict[str, Any]]:
        return self._by_id.get(crystal_id)

    def all(self) -> List[Dict[str, Any]]:
        return list(self._by_id.values())

    def rehydrate(self, mmdb_engine) -> int:
        """Boot adapter: load every vault crystal into a live MMDB engine so
        the backend lib is queryable through the normal frontend surface."""
        n = 0
        for c in self._by_id.values():
            mmdb_engine.store(
                content=c.get("content", ""),
                snap_labels=c.get("snap_labels", []),
                e8_coords=c.get("e8_coords"),
                domain=c.get("domain", "lib.vault"),
                metadata=c.get("metadata", {}),
            )
            n += 1
        return n

    # ── internals ────────────────────────────────────────────────────────────
    def _index(self, crystal: Dict[str, Any]) -> None:
        ch = crystal.get("content_hash")
        cid = crystal.get("crystal_id")
        if ch:
            self._by_hash[ch] = crystal
        if cid:
            self._by_id[cid] = crystal

    # ── consolidation: the lib reorganizes as it grows ───────────────────────
    # AI-context-compression with full provenance: when a domain accumulates
    # enough crystals at one resolution level, they consolidate into ONE
    # meta-crystal — a compressed summary whose provenance field carries every
    # child content_hash. Children remain in the vault (append-only; lineage
    # is never erased); the meta-crystal becomes the preferred lookup. Meta-
    # crystals themselves consolidate at the next level: the vault climbs the
    # MDHG ladder (grain -> dust -> triad -> ...) as the database grows.

    CONSOLIDATE_AT: int = 8     # children per meta-crystal (one rung's worth)

    def consolidate(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """One consolidation pass. Returns the meta-crystals generated."""
        import hashlib as _h
        made: List[Dict[str, Any]] = []
        with self._lock:
            # group unconsolidated crystals by (domain, level)
            groups: Dict[tuple, List[Dict[str, Any]]] = {}
            absorbed = {h for c in self._by_id.values()
                        for h in c.get("provenance", [])}
            for c in self._by_id.values():
                if c.get("content_hash") in absorbed:
                    continue                       # already inside a meta-crystal
                d = c.get("domain", "lib.vault")
                if domain and d != domain:
                    continue
                lvl = int(c.get("level", 0))
                groups.setdefault((d, lvl), []).append(c)

        for (d, lvl), members in groups.items():
            while len(members) >= self.CONSOLIDATE_AT:
                batch = members[:self.CONSOLIDATE_AT]
                members = members[self.CONSOLIDATE_AT:]
                prov = [c["content_hash"] for c in batch]
                # merged label histogram = the compressed semantic summary
                labels: Dict[str, int] = {}
                for c in batch:
                    for lab in c.get("snap_labels", []):
                        labels[lab] = labels.get(lab, 0) + 1
                body = json.dumps({"domain": d, "level": lvl + 1,
                                   "children": prov,
                                   "labels": labels}, sort_keys=True,
                                  separators=(",", ":"))
                ch = _h.sha256(body.encode()).hexdigest()[:16]
                meta = {
                    "crystal_id": f"meta-{ch}",
                    "content": body,
                    "content_hash": ch,
                    "snap_labels": sorted(labels, key=labels.get, reverse=True)[:12],
                    "domain": d,
                    "level": lvl + 1,                       # one MDHG rung up
                    "provenance": prov,                     # full lineage, walkable
                    "metadata": {"children": len(prov),
                                 "compression": f"{len(prov)}:1"},
                }
                self.crystallize(meta)
                made.append(meta)
        return made

    def lineage(self, content_hash: str) -> List[str]:
        """Walk a meta-crystal's provenance down to leaf crystals."""
        out: List[str] = []
        stack = [content_hash]
        seen = set()
        while stack:
            h = stack.pop()
            if h in seen:
                continue
            seen.add(h)
            c = self._by_hash.get(h)
            if not c:
                continue
            kids = c.get("provenance", [])
            if kids:
                stack.extend(kids)
            else:
                out.append(h)
        return out

    @property
    def count(self) -> int:
        return len(self._by_id)

    def stats(self) -> Dict[str, Any]:
        domains: Dict[str, int] = {}
        levels: Dict[int, int] = {}
        for c in self._by_id.values():
            d = c.get("domain", "lib.vault")
            domains[d] = domains.get(d, 0) + 1
            lv = int(c.get("level", 0))
            levels[lv] = levels.get(lv, 0) + 1
        return {"crystals": self.count, "path": str(self.path),
                "domains": domains, "levels": levels}
