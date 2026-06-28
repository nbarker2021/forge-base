"""
ChromaForge SpeedLight — Two-tier idempotent content-addressed cache.

f(f(x)) = f(x) — the quantum projection operator. Zero recomputation cost.
Channel 3/6/9 governance: permissive/strict/idempotent.
Two-tier: in-memory LRU (OrderedDict, max configurable) + optional backend.

Channel governance:
  3 = permissive  (limit 1e3)   — general use
  6 = strict      (limit 0.1)   — conservation-sensitive paths
  9 = idempotent  (limit 1e-6)  — priority cache, never evicted first

Design: SpeedLightEngine is a class. Module-level singleton `engine` available.
"""
import hashlib
import json
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

# ─── Lookup tables (import-time, read-only) ────────────────────────────────────

# Combined channel data: channel → (priority, delta_phi_limit, governance_name)
_CHANNEL_DATA: Dict[int, Tuple[int, float, str]] = {
    3: (1, 1e3,  "permissive"),
    6: (2, 0.1,  "strict"),
    9: (3, 1e-6, "idempotent"),
}

_PRIORITY_CHANNELS: frozenset = frozenset(_CHANNEL_DATA.keys())

MAX_MEMORY_SIZE: int = 10000
GENESIS_HASH: str = "0" * 64


# ─── Engine class ──────────────────────────────────────────────────────────────

class SpeedLightEngine:
    """Two-tier idempotent cache. One instance = one cache context.

    receipt_ledger: optional ReceiptLedger to chain computation receipts.
    """

    def __init__(self, max_size: int = MAX_MEMORY_SIZE, receipt_ledger=None):
        self.max_size: int = max_size
        self._receipts = receipt_ledger       # injected dependency (optional)
        self._cache: OrderedDict = OrderedDict()
        self._ledger: List[Dict] = []
        self._head: str = GENESIS_HASH
        self._stats: Dict = {
            "hits": 0, "misses": 0, "time_saved": 0.0, "puts": 0,
            "memory_hits": 0, "gc_runs": 0, "gc_evicted": 0,
        }

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _hash(data: str) -> str:
        return hashlib.sha256(data.encode("utf-8", errors="replace")).hexdigest()[:32]

    def _receipt(self, fn_name: str, task_hash: str,
                 result_hash: str, hit: bool, channel: int) -> Dict:
        ts = time.time()
        entry = {
            "fn_name": fn_name, "task_hash": task_hash,
            "result_hash": result_hash, "hit": hit,
            "channel": channel, "prev": self._head, "ts": ts,
        }
        rh = hashlib.sha256(
            json.dumps(entry, sort_keys=True).encode()
        ).hexdigest()[:32]
        entry["receipt_hash"] = rh
        self._head = rh
        self._ledger.append(entry)
        return entry

    def _put_memory(self, key: str, result: Any, cost: float,
                    content_hash: str, channel: int, fn_name: str) -> None:
        self._cache[key] = {
            "result": result, "cost_seconds": cost,
            "content_hash": content_hash, "channel": channel,
            "fn_name": fn_name, "cached_at": time.time(), "hits": 0,
        }
        self._cache.move_to_end(key)
        # Evict LRU; preserve priority-channel entries longer
        while len(self._cache) > self.max_size:
            evicted = False
            for k in list(self._cache.keys()):
                if self._cache[k].get("channel", 3) not in _PRIORITY_CHANNELS:
                    self._cache.pop(k)
                    evicted = True
                    break
            if not evicted:
                self._cache.popitem(last=False)

    # ── Public API ─────────────────────────────────────────────────────────────

    def get(self, key: str) -> Dict:
        """Look up a cached result."""
        if key in self._cache:
            self._stats["hits"] += 1
            self._stats["memory_hits"] += 1
            entry = self._cache[key]
            entry["hits"] += 1
            self._stats["time_saved"] += entry.get("cost_seconds", 0.0)
            self._cache.move_to_end(key)
            self._receipt(entry.get("fn_name", ""), key,
                         entry.get("content_hash", ""), True,
                         entry.get("channel", 3))
            return {"hit": True, "key": key, "result": entry["result"],
                    "cost_saved": entry.get("cost_seconds", 0.0),
                    "hits": entry["hits"]}

        self._stats["misses"] += 1
        self._receipt("", key, "", False, 3)
        return {"hit": False, "key": key}

    def put(self, key: str, result: Any, cost_seconds: float = 0.0,
            content_hash: str = "", channel: int = 3,
            fn_name: str = "") -> Dict:
        """Store a result."""
        actual_key = key or self._hash(json.dumps(result, default=str))
        task_hash = content_hash or self._hash(actual_key)
        result_hash = self._hash(json.dumps(result, default=str))
        self._put_memory(actual_key, result, cost_seconds, task_hash, channel, fn_name)
        self._stats["puts"] += 1
        self._receipt(fn_name, task_hash, result_hash, False, channel)
        return {"cached": True, "key": actual_key, "memory_entries": len(self._cache)}

    def compute(self, task_id: str, result: Any = None, fn_name: str = "",
                cost_seconds: float = 0.0, channel: int = 3) -> Dict:
        """f(f(x)) = f(x). Check cache first; store and return on miss."""
        if task_id in self._cache:
            self._stats["hits"] += 1
            self._stats["memory_hits"] += 1
            entry = self._cache[task_id]
            entry["hits"] += 1
            saved = entry.get("cost_seconds", 0.0)
            self._stats["time_saved"] += saved
            self._cache.move_to_end(task_id)
            self._receipt(fn_name, task_id, entry.get("content_hash", ""),
                         True, channel)
            return {"hit": True, "task_id": task_id, "result": entry["result"],
                    "cost": 0.0, "cost_saved": saved, "idempotent": True}

        self._stats["misses"] += 1
        result_hash = self._hash(json.dumps(result, default=str))
        self._put_memory(task_id, result, cost_seconds, result_hash, channel, fn_name)
        self._receipt(fn_name, task_id, result_hash, False, channel)
        return {"hit": False, "task_id": task_id, "result": result,
                "cost": cost_seconds, "idempotent": False}

    def gate(self, channel: int, dphi: float = 0.0) -> Dict:
        """Check if a delta_phi passes the channel governance limit."""
        data = _CHANNEL_DATA.get(channel, (0, 1e3, "standard"))
        priority, limit, gov = data
        return {
            "channel": channel, "dphi": dphi, "limit": limit,
            "allowed": dphi <= limit, "priority": priority, "governance": gov,
        }

    def gc(self, stale_hours: int = 72) -> Dict:
        """Evict memory-tier entries not accessed recently."""
        cutoff = time.time() - stale_hours * 3600
        evicted = 0
        for k in list(self._cache.keys()):
            e = self._cache[k]
            if (e.get("cached_at", 0) < cutoff
                    and e.get("hits", 0) < 2
                    and e.get("channel", 3) not in _PRIORITY_CHANNELS):
                self._cache.pop(k)
                evicted += 1
        self._stats["gc_runs"] += 1
        self._stats["gc_evicted"] += evicted
        return {"evicted": evicted, "remaining": len(self._cache)}

    def stats(self) -> Dict:
        total = self._stats["hits"] + self._stats["misses"]
        by_channel = {
            ch: sum(1 for e in self._cache.values() if e.get("channel") == ch)
            for ch in (3, 6, 9)
        }
        return {
            **self._stats,
            "total_requests": total,
            "hit_rate": round(self._stats["hits"] / total * 100, 2) if total else 0.0,
            "memory_size": len(self._cache),
            "memory_max": self.max_size,
            "ledger_length": len(self._ledger),
            "ledger_head": self._head,
            "channel_breakdown": by_channel,
        }

    def ledger(self, limit: int = 20) -> List[Dict]:
        return self._ledger[-limit:]

    @property
    def head(self) -> str:
        return self._head


# ─── Module-level singleton + forwarding ──────────────────────────────────────

engine = SpeedLightEngine()

def compute(task_id: str, result: Any = None, fn_name: str = "",
            cost_seconds: float = 0.0, channel: int = 3) -> Dict:
    return engine.compute(task_id, result, fn_name, cost_seconds, channel)

def get(key: str) -> Dict:
    return engine.get(key)

def put(key: str, result: Any, **kwargs) -> Dict:
    return engine.put(key, result, **kwargs)

def stats() -> Dict:
    return engine.stats()
