"""Geometry (E8/Leech) port adapter."""
from __future__ import annotations

from typing import Any

from .base import PortTool


class GeometryTool(PortTool):
    port = "geometry"
    part_id = "geometry-e8"

    @classmethod
    def available(cls) -> bool:
        return cls()._provider() is not None

    def invoke(self, *, method: str = "health", **params: Any) -> dict[str, Any]:
        prov = self._provider()
        if prov is None:
            return self.unavailable(method=method, **params)

        fn = getattr(prov, method, None)
        if fn is None:
            return self.unavailable(reason=f"unknown_method:{method}", method=method, **params)
        try:
            result = fn(**params) if params else fn()
            return {"available": True, "provenance": self.provenance(), "method": method, "result": result}
        except Exception as exc:
            return self.unavailable(reason=str(exc), method=method, **params)
