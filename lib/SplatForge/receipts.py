"""
SplatForge.receipts — Merkle-chained SplatReceipt ledger.

Schema-conformant to ecology/schemas/splat_receipt.schema.json (the
workplan's own SplatReceipt object table — a different, domain-specific
shape from ChromaForge.ReceiptLedger's generic MINT/POST/BOND/... receipts).
House style (mint/walk/verify/recent/head/length) is mirrored from
production/packages/cqecmplx-forge/src/ChromaForge/receipt.py so this forge
needs no cross-package import — every forge in this ring is self-contained
and stdlib-only (plus numpy, via tiling.py). A future product kernel (e.g.
SplatForge-Stick) is where this gets wired into ChromaForgeEngine for the
full compute->save->validate->receipt->reuse Event Law, exactly as
PaneForge-Stick's kernel wires PixelForge/FridgeForge/LinkForge today.

Honesty note: Crystal Zoo records are "registered", not externally
validated (ecology/registries/CRYSTAL_ZOO.md). A SplatReceipt minted here is
bounded_exec evidence (a deterministic CPU harness ran and reproduced a
hash) — it is not, and must not be read as, external physical validation of
the underlying crystal geometry.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from .compiler import ADAPTER_ID, GaussianSplatInstance, TileToSplatCompiler

GENESIS_HASH = "0" * 64


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SplatReceiptLedger:
    """Merkle-chained ledger. One instance = one chain context."""

    def __init__(self) -> None:
        self._chain: List[Dict] = []
        self._head: str = GENESIS_HASH
        self._by_id: Dict[str, Dict] = {}
        self._by_hash: Dict[str, Dict] = {}

    def mint(
        self,
        *,
        source_assets: List[str],
        adapter_id: str,
        input_hash: str,
        output_hash: str,
        backend: str = "cpu_reference",
        status: str = "PASS_WITH_OPEN_GAPS",
        evidence_class: str = "bounded_exec",
        parameters: Dict = None,
        render_pass: str = None,
        gpu_profile: str = None,
        output_paths: List[str] = None,
        benchmark_metrics: Dict = None,
    ) -> Dict:
        parent = self._head
        receipt_id = hashlib.sha256(
            f"{parent}:{adapter_id}:{input_hash}:{output_hash}".encode()
        ).hexdigest()[:16]
        ts = _utcnow_iso()
        receipt_hash = hashlib.sha256(
            json.dumps({
                "parent": parent,
                "adapter_id": adapter_id,
                "input_hash": input_hash,
                "output_hash": output_hash,
                "backend": backend,
                "status": status,
                "evidence_class": evidence_class,
            }, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        receipt = {
            "receipt_id": receipt_id,
            "receipt_hash": receipt_hash,
            "source_assets": list(source_assets),
            "parameters": dict(parameters or {}),
            "adapter_id": adapter_id,
            "render_pass": render_pass,
            "backend": backend,
            "gpu_profile": gpu_profile,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "output_paths": list(output_paths or []),
            "benchmark_metrics": dict(benchmark_metrics or {}),
            "status": status,
            "evidence_class": evidence_class,
            "prev_hash": parent,
            "created_at": ts,
        }
        self._chain.append(receipt)
        self._head = receipt_hash
        self._by_id[receipt_id] = receipt
        self._by_hash[receipt_hash] = receipt
        return receipt

    def walk(self, start_hash: str, max_depth: int = 100) -> List[Dict]:
        chain: List[Dict] = []
        current = start_hash
        seen: set = set()
        for _ in range(max_depth):
            if current in seen or current == GENESIS_HASH:
                break
            seen.add(current)
            receipt = self._by_hash.get(current)
            if not receipt:
                break
            chain.append(receipt)
            current = receipt.get("prev_hash", "")
        return chain

    def verify(self) -> Dict:
        prev = GENESIS_HASH
        breaks = []
        for i, r in enumerate(self._chain):
            if r["prev_hash"] != prev:
                breaks.append({"index": i, "expected": prev[:16], "got": r["prev_hash"][:16]})
            prev = r["receipt_hash"]
        return {"valid": not breaks, "length": len(self._chain), "head": self._head, "breaks": breaks[:10]}

    def recent(self, limit: int = 20) -> List[Dict]:
        return self._chain[-limit:]

    @property
    def head(self) -> str:
        return self._head

    @property
    def length(self) -> int:
        return len(self._chain)


ledger = SplatReceiptLedger()


def compile_with_receipt(
    crystal_id: str,
    extent: Tuple[int, int, int] = (2, 2, 2),
) -> Tuple[List[GaussianSplatInstance], Dict]:
    """Compile splats for crystal_id, mint exactly one SplatReceipt for the
    whole buffer, and stamp every splat with that receipt's hash — one
    receipt per compile pass, not one per splat."""
    compiler = TileToSplatCompiler()
    splats, input_hash, output_hash = compiler.compile_and_hash(crystal_id, extent)
    receipt = ledger.mint(
        source_assets=[crystal_id],
        adapter_id=ADAPTER_ID,
        input_hash=input_hash,
        output_hash=output_hash,
        parameters={"crystal_id": crystal_id, "extent": list(extent)},
    )
    stamped = [dataclasses.replace(s, receipt_id=receipt["receipt_hash"]) for s in splats]
    return stamped, receipt
