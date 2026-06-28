"""
ChromaForge Receipt — Merkle-chained dyadic gluon records.

Every operation produces a receipt. The receipt IS the dyadic gluon record:
  input_hash  = circle A of the oloid (what entered)
  output_hash = circle B of the oloid (what emerged)
  prev_hash   = the chain link (oloid rolls without slipping)

Receipt types: MINT POST BOND PROCESS ASSIGN VOTE BIRTH DEATH GATE CROSSING

Design: ReceiptLedger is a class — instantiate one per context, chain, or scope.
Module-level singleton `ledger` available for single-context use.
"""
import hashlib
import json
import time
import uuid
from typing import Dict, List, Optional

# ─── Lookup tables (import-time, read-only) ────────────────────────────────────

RECEIPT_TYPES: tuple = (
    "MINT", "POST", "BOND", "PROCESS", "ASSIGN",
    "VOTE", "BIRTH", "DEATH", "GATE", "CROSSING",
)
_RECEIPT_TYPE_SET: frozenset = frozenset(RECEIPT_TYPES)

GENESIS_HASH: str = "0" * 64


# ─── Engine class ──────────────────────────────────────────────────────────────

class ReceiptLedger:
    """Merkle-chained receipt ledger. One instance = one chain context."""

    __slots__ = (
        "_chain", "_head",
        "_by_id", "_by_hash", "_by_agent", "_by_type", "_by_atom",
    )

    def __init__(self):
        self._chain: List[Dict] = []
        self._head: str = GENESIS_HASH
        self._by_id: Dict[str, Dict] = {}
        self._by_hash: Dict[str, Dict] = {}
        self._by_agent: Dict[str, List[str]] = {}
        self._by_type: Dict[str, List[str]] = {}
        self._by_atom: Dict[str, List[str]] = {}

    # ── Core ───────────────────────────────────────────────────────────────────

    def mint(
        self,
        receipt_type: str = "PROCESS",
        agent_id: str = "",
        atom_id: str = "",
        operation: str = "",
        input_data: str = "",
        output_data: str = "",
        delta_phi: float = 0.0,
        snap_labels: List[str] = None,
        epoch: int = 0,
        parent_hash: str = "",
    ) -> Dict:
        """Create and append a receipt to the chain. Returns the receipt dict."""
        if receipt_type not in _RECEIPT_TYPE_SET:
            raise ValueError(f"receipt_type must be one of {RECEIPT_TYPES}")

        receipt_id = uuid.uuid4().hex[:16]
        ts = time.time()
        parent = parent_hash if parent_hash else self._head

        # The dyadic gluon pair: two hashes = two circles of the oloid
        input_hash = hashlib.sha256(input_data.encode()).hexdigest()[:16]
        output_hash = hashlib.sha256(output_data.encode()).hexdigest()[:16]

        # Chain hash: SHA256(parent:operation:atom:ts)
        receipt_hash = hashlib.sha256(
            f"{parent}:{operation}:{atom_id}:{ts}".encode()
        ).hexdigest()

        receipt: Dict = {
            "receipt_id":   receipt_id,
            "receipt_hash": receipt_hash,
            "receipt_type": receipt_type,
            "agent_id":     agent_id,
            "atom_id":      atom_id,
            "operation":    operation,
            "input_hash":   input_hash,
            "output_hash":  output_hash,
            "delta_phi":    delta_phi,
            "snap_labels":  snap_labels or [],
            "epoch":        epoch,
            "prev_hash":    parent,
            "created_at":   ts,
            "chain_index":  len(self._chain),
        }

        self._chain.append(receipt)
        self._head = receipt_hash
        self._by_id[receipt_id] = receipt
        self._by_hash[receipt_hash] = receipt
        self._by_agent.setdefault(agent_id, []).append(receipt_id)
        self._by_type.setdefault(receipt_type, []).append(receipt_id)
        if atom_id:
            self._by_atom.setdefault(atom_id, []).append(receipt_id)

        return receipt

    def walk(self, start_hash: str, max_depth: int = 100) -> List[Dict]:
        """Walk the chain backwards from start_hash to genesis."""
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

    def verify(self, receipt_hash: str = "", max_depth: int = 100) -> Dict:
        """Verify chain integrity. Empty hash = verify entire in-memory chain."""
        if not receipt_hash:
            prev = GENESIS_HASH
            breaks = []
            for i, r in enumerate(self._chain):
                if r["prev_hash"] != prev:
                    breaks.append({
                        "index": i,
                        "expected": prev[:16],
                        "got": r["prev_hash"][:16],
                    })
                prev = r["receipt_hash"]
            return {
                "valid": not breaks,
                "length": len(self._chain),
                "head": self._head,
                "breaks": breaks[:10],
            }

        chain = self.walk(receipt_hash, max_depth)
        return {
            "receipt_hash": receipt_hash,
            "chain_depth": len(chain),
            "reaches_genesis": bool(chain) and chain[-1].get("prev_hash", "") == GENESIS_HASH,
            "path": [
                {"hash": r["receipt_hash"][:16], "op": r.get("operation"), "atom": r.get("atom_id")}
                for r in chain
            ],
        }

    def atom_chain(self, atom_id: str) -> List[Dict]:
        """All receipts for a given atom."""
        ids = self._by_atom.get(atom_id, [])
        return [self._by_id[rid] for rid in ids if rid in self._by_id]

    def recent(self, limit: int = 20) -> List[Dict]:
        return self._chain[-limit:]

    @property
    def head(self) -> str:
        return self._head

    @property
    def length(self) -> int:
        return len(self._chain)

    def status(self) -> Dict:
        return {
            "chain_length": len(self._chain),
            "head": self._head,
            "agents": len(self._by_agent),
            "atoms_tracked": len(self._by_atom),
            "by_type": {t: len(self._by_type.get(t, [])) for t in RECEIPT_TYPES},
        }


# ─── Module-level singleton + forwarding ──────────────────────────────────────

ledger = ReceiptLedger()

def mint(*args, **kwargs) -> Dict:
    return ledger.mint(*args, **kwargs)

def walk(start_hash: str, max_depth: int = 100) -> List[Dict]:
    return ledger.walk(start_hash, max_depth)

def verify(receipt_hash: str = "", max_depth: int = 100) -> Dict:
    return ledger.verify(receipt_hash, max_depth)

def atom_chain(atom_id: str) -> List[Dict]:
    return ledger.atom_chain(atom_id)

def status() -> Dict:
    return ledger.status()
