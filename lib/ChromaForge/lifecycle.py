"""
ChromaForge Lifecycle — dual-lane memory, decay, promotion, and the
process-end compression event. Contractual adaptation of the existing
engines; no engine is modified.

THE MEMORY LAW (frontend):
  Valid receipts enter dual-lane live memory:
    fermionic lane — the item's IDENTITY. Pauli exclusion: one stable
                     occupant per key. A duplicate arrival is not an error,
                     it is the reuse path (activation).
    bosonic lane   — the item's ACTIVATION ENERGY. Occupancy stacks freely;
                     this stack IS the activation counter.
  DECAY ticks on global event count (not wall clock — the whole memory is
  deterministically replayable from the receipt chain). Each tick drains
  bosonic occupancy by a kappa-scaled amount. Decay that empties an item's
  stack RESETS its chain: only sustained, unbroken use accumulates.

THE PROMOTION LAW:
  An item whose bosonic chain reaches PROMOTE_AT (default 10) unbroken
  activations is PROMOTED: crystallized into the backend lib (CrystalVault),
  receipted as BIRTH with 2 links (its crystal + its final activation
  receipt), and its cache slot cleared. From then on it is a lib lookup —
  reuse forever for nearly free.

THE COMPRESSION EVENT (process end):
  finish() walks the receipt chain head -> genesis (ReceiptLedger.walk —
  the existing primitive) extracting the BARE ACTIVE CHAIN: the load-bearing
  spine only. That spine + run summary crystallizes as ONE crystal. All live
  scaffolding (cache entries not promoted, lanes, raw chain) evaporates.
  Nothing not in crystal form survives a finished process.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

from ChromaForge.conservation import COUPLING
from ChromaForge.contracts import CrystalVault

PROMOTE_AT: int = 10          # ennead + closure; channel-9 items promote at 9
DECAY_EVERY: int = 16         # one decay tick per N global events
DECAY_DRAIN: float = 1.0      # bosonic occupancy drained per tick (kappa-weighted)


class RunLifecycle:
    """One live run over a ChromaForgeEngine, bound to a CrystalVault backend.

    Usage:
        run = RunLifecycle(engine, vault, run_id="...")
        run.activate(key, receipt_hash)     # on every valid receipt / reuse
        ...
        crystal = run.finish()              # the compression event
    """

    def __init__(self, engine, vault: CrystalVault, run_id: str = "",
                 promote_at: int = PROMOTE_AT,
                 decay_every: int = DECAY_EVERY):
        self.engine = engine
        self.vault = vault
        self.run_id = run_id or f"run-{hashlib.sha256(str(time.time()).encode()).hexdigest()[:10]}"
        self.promote_at = promote_at
        self.decay_every = decay_every

        # dual lanes (live-run scaffolding — never persisted)
        self._fermionic: Dict[str, Dict[str, Any]] = {}   # key -> identity occupant
        self._bosonic: Dict[str, float] = {}              # key -> stacked occupancy
        self._chain: Dict[str, int] = {}                  # key -> unbroken activation chain
        self._last_receipt: Dict[str, str] = {}           # key -> latest activation receipt
        self._events: int = 0
        self._promoted: List[str] = []
        self._decay_log: List[Dict[str, Any]] = []
        self.finished = False

    # ── the activation path ──────────────────────────────────────────────────
    def activate(self, key: str, receipt_hash: str = "",
                 content: str = "", channel: int = 3,
                 snap_labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """One valid receipt arrives for `key`. Fermionic identity occupies
        once; bosonic occupancy stacks; chains promote at the threshold."""
        if self.finished:
            raise RuntimeError("run already finished — start a new RunLifecycle")
        self._events += 1

        # fermionic lane: Pauli exclusion — duplicate arrival = reuse path
        occ = self._fermionic.get(key)
        if occ is None:
            self._fermionic[key] = {"key": key, "content": content,
                                    "channel": channel,
                                    "snap_labels": snap_labels or [],
                                    "born_event": self._events}
        # bosonic lane: stack + chain
        self._bosonic[key] = self._bosonic.get(key, 0.0) + 1.0
        self._chain[key] = self._chain.get(key, 0) + 1
        if receipt_hash:
            self._last_receipt[key] = receipt_hash

        # event-count decay tick (deterministic, kappa-weighted)
        if self._events % self.decay_every == 0:
            self._decay_tick()

        # promotion check (channel-9 idempotent items promote one early)
        threshold = self.promote_at - 1 if channel == 9 else self.promote_at
        promoted = None
        if self._chain.get(key, 0) >= threshold:
            promoted = self._promote(key)

        return {"key": key, "chain": self._chain.get(key, 0),
                "occupancy": round(self._bosonic.get(key, 0.0), 3),
                "promoted": promoted is not None,
                "crystal": promoted}

    def _decay_tick(self) -> None:
        """Drain every bosonic stack; an emptied stack resets its chain.
        Decay products are data (logged), never silent deletions."""
        drain = DECAY_DRAIN * (1.0 + COUPLING)
        for key in list(self._bosonic):
            self._bosonic[key] -= drain
            if self._bosonic[key] <= 0.0:
                self._decay_log.append({"key": key, "event": self._events,
                                        "chain_broken_at": self._chain.get(key, 0)})
                self._bosonic.pop(key)
                self._chain[key] = 0          # decay resets the chain
                self._fermionic.pop(key, None)

    def _promote(self, key: str) -> Dict[str, Any]:
        """Crystallize a sustained item into the backend lib; clear its slot."""
        occ = self._fermionic.get(key, {"key": key})
        content = occ.get("content") or key
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # the crystal (idempotent in the vault by content_hash)
        crystal = {
            "crystal_id": f"lib-{content_hash}",
            "content": content,
            "content_hash": content_hash,
            "snap_labels": list(occ.get("snap_labels", [])) + ["lib.promoted"],
            "domain": "lib.promoted",
            "metadata": {"run_id": self.run_id, "chain": self._chain.get(key, 0),
                         "channel": occ.get("channel", 3),
                         "final_activation": self._last_receipt.get(key, "")},
        }
        self.vault.crystallize(crystal)
        self.engine.mmdb.store(content=content,
                               snap_labels=crystal["snap_labels"],
                               domain="lib.promoted",
                               metadata=crystal["metadata"])

        # BIRTH receipt, tied to 2 things: the crystal + the final activation
        self.engine.receipt.mint(
            receipt_type="BIRTH", agent_id="lifecycle",
            atom_id=crystal["crystal_id"], operation="lib.promote",
            input_data=key[:64], output_data=content_hash,
            delta_phi=-COUPLING,
            snap_labels=[f"link:{crystal['crystal_id']}",
                         f"link:{self._last_receipt.get(key, 'genesis')}"],
        )

        # clear the cache slot + lanes (it lives in the lib now)
        self._bosonic.pop(key, None)
        self._chain.pop(key, None)
        self._fermionic.pop(key, None)
        if hasattr(self.engine.speedlight, "_cache"):
            self.engine.speedlight._cache.pop(key, None)
        self._promoted.append(crystal["crystal_id"])
        return crystal

    # ── the compression event ────────────────────────────────────────────────
    def finish(self) -> Dict[str, Any]:
        """Process end: compress the receipt chain to its bare active spine,
        crystallize the spine, evaporate all live scaffolding."""
        if self.finished:
            raise RuntimeError("already finished")
        self.finished = True

        # 1. BARE ACTIVE CHAIN: walk head -> genesis (existing primitive).
        #    Only the load-bearing spine survives; side receipts do not.
        spine = self.engine.receipt.walk(self.engine.receipt.head,
                                         max_depth=10_000)
        bare = [{"h": r["receipt_hash"], "op": r["operation"],
                 "atom": r.get("atom_id", ""), "links": [
                     s[5:] for s in r.get("snap_labels", [])
                     if isinstance(s, str) and s.startswith("link:")]}
                for r in spine]

        # 2. THE RUN CRYSTAL: spine + conservation + promotions, one record.
        body = json.dumps({"run_id": self.run_id, "spine": bare}, sort_keys=True,
                          separators=(",", ":"))
        content_hash = hashlib.sha256(body.encode()).hexdigest()[:16]
        crystal = {
            "crystal_id": f"run-{content_hash}",
            "content": body,
            "content_hash": content_hash,
            "snap_labels": ["run.spine", f"run:{self.run_id}"],
            "domain": "lib.runs",
            "metadata": {
                "run_id": self.run_id,
                "spine_length": len(bare),
                "events": self._events,
                "promoted": list(self._promoted),
                "decays": len(self._decay_log),
                "conservation_cumulative": self.engine.conservation.cumulative,
                "head": self.engine.receipt.head,
            },
        }
        self.vault.crystallize(crystal)

        # 3. EVAPORATE the scaffolding: nothing non-crystal survives.
        self._fermionic.clear()
        self._bosonic.clear()
        self._chain.clear()
        self._last_receipt.clear()
        if hasattr(self.engine.speedlight, "_cache"):
            # promoted items are already in the lib; the rest were live-run only
            self.engine.speedlight._cache.clear()

        return crystal

    def stats(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id, "events": self._events,
            "live_identities": len(self._fermionic),
            "hot_keys": {k: round(v, 2) for k, v in
                         sorted(self._bosonic.items(), key=lambda x: -x[1])[:8]},
            "promoted": list(self._promoted),
            "decays": len(self._decay_log),
            "finished": self.finished,
        }
