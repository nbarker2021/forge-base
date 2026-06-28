"""MORSR diagnostic port adapter."""
from __future__ import annotations

from typing import Any

from .base import PortTool


class MORSRTool(PortTool):
    port = "diagnostic"
    part_id = "morsr-diagnostic"

    @classmethod
    def available(cls) -> bool:
        return cls()._provider() is not None

    def invoke(
        self,
        *,
        failure_kind: str = "verify",
        context: dict[str, Any] | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        context = context or {}
        prov = self._provider()
        report = {
            "failure_kind": failure_kind,
            "context": context,
            "service": "lattice-forge",
        }

        if prov is None:
            return {
                "available": False,
                "provenance": self.provenance(),
                "local_report": report,
            }

        fn = getattr(prov, "report", None) or getattr(prov, "emit", None)
        if fn is None:
            return self.unavailable(failure_kind=failure_kind, context=context)

        try:
            result = fn(**report)
            return {
                "available": True,
                "provenance": self.provenance(),
                "report": result,
            }
        except Exception as exc:
            return self.unavailable(reason=str(exc), failure_kind=failure_kind)
