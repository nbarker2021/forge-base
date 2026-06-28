"""SpeedLight cache port adapter."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from .base import PortTool


class SpeedlightTool(PortTool):
    port = "cache"
    part_id = "speedlight-cache"

    _local_cache: dict[str, Any] = {}

    @classmethod
    def available(cls) -> bool:
        return cls()._provider() is not None

    @staticmethod
    def _cache_key(namespace: str, payload: dict[str, Any]) -> str:
        blob = json.dumps(payload, sort_keys=True, default=str)
        digest = hashlib.sha256(blob.encode()).hexdigest()[:16]
        return f"{namespace}:{digest}"

    def invoke(
        self,
        *,
        namespace: str = "block_tower",
        payload: dict[str, Any] | None = None,
        value: Any = None,
        op: str = "get",
        **_: Any,
    ) -> dict[str, Any]:
        payload = payload or {}
        key = self._cache_key(namespace, payload)
        prov = self._provider()

        if op == "get":
            if prov is not None:
                fn = getattr(prov, "get", None) or getattr(prov, "lookup", None)
                if fn is not None:
                    try:
                        hit = fn(key=key, namespace=namespace)
                        if hit is not None:
                            return {
                                "available": True,
                                "provenance": self.provenance(),
                                "hit": True,
                                "key": key,
                                "value": hit,
                            }
                    except Exception:
                        pass
            local = self._local_cache.get(key)
            return {
                "available": prov is not None,
                "provenance": self.provenance(),
                "hit": local is not None,
                "key": key,
                "value": local,
            }

        if op in ("set", "put") and value is not None:
            if prov is not None:
                fn = getattr(prov, "set", None) or getattr(prov, "store", None)
                if fn is not None:
                    try:
                        fn(key=key, value=value, namespace=namespace)
                    except Exception:
                        pass
            self._local_cache[key] = value
            return {
                "available": prov is not None,
                "provenance": self.provenance(),
                "stored": True,
                "key": key,
            }

        return self.unavailable(op=op, namespace=namespace)
