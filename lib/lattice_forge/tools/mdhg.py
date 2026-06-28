"""MDHG addressing port adapter."""
from __future__ import annotations

from typing import Any

from .base import PortTool


class MDHGTool(PortTool):
    port = "addressing"
    part_id = "mdhg-addressing"

    @classmethod
    def available(cls) -> bool:
        return cls()._provider() is not None

    def invoke(
        self,
        *,
        key: str = "",
        page: int = 0,
        block: int = 0,
        metadata: dict[str, Any] | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        prov = self._provider()
        if prov is None:
            local = {
                "homonym_safe_key": key or f"lf/page/{page}/block/{block}",
                "page": page,
                "block": block,
                "metadata": metadata or {},
            }
            return {
                "available": False,
                "provenance": self.provenance(),
                "local_address": local,
            }

        fn = getattr(prov, "resolve", None) or getattr(prov, "address", None)
        if fn is None:
            return self.unavailable(key=key, page=page, block=block)

        try:
            result = fn(key=key or f"lf/page/{page}/block/{block}", **params)
            return {
                "available": True,
                "provenance": self.provenance(),
                "key": key,
                "result": result,
            }
        except Exception as exc:
            return self.unavailable(reason=str(exc), key=key)
