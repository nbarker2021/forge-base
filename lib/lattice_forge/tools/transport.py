"""Transport layer port adapter."""
from __future__ import annotations

from typing import Any

from .base import PortTool


class TransportTool(PortTool):
    port = "transport"
    part_id = "transport-layer"

    @classmethod
    def available(cls) -> bool:
        return cls()._provider() is not None

    def invoke(
        self,
        *,
        step: str = "",
        from_regime: str = "",
        to_regime: str = "",
        payload: dict[str, Any] | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        payload = payload or {}
        record = {
            "step": step,
            "from_regime": from_regime,
            "to_regime": to_regime,
            "payload": payload,
            "doctrine": "failure implies need k+1 projection",
        }
        prov = self._provider()
        if prov is None:
            return {
                "available": False,
                "provenance": self.provenance(),
                "local_record": record,
            }

        fn = getattr(prov, "record", None) or getattr(prov, "transport", None)
        if fn is None:
            return self.unavailable(**record)

        try:
            result = fn(**record)
            return {
                "available": True,
                "provenance": self.provenance(),
                "record": result,
            }
        except Exception as exc:
            return self.unavailable(reason=str(exc), **record)
