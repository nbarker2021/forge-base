"""Base adapter pattern for CMPLX bootstrap port tools."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


def _get_morphon_provider(port: str) -> Any | None:
    try:
        from cmplx.morphon import MorphonController

        return MorphonController.get().get_provider(port)
    except Exception:
        return None


class PortTool(ABC):
    """Optional CMPLX port adapter with provenance metadata."""

    port: str
    part_id: str

    @classmethod
    @abstractmethod
    def available(cls) -> bool:
        """True when the CMPLX port provider is reachable."""

    @abstractmethod
    def invoke(self, **kwargs: Any) -> dict[str, Any]:
        """Call the port or return a graceful fallback payload."""

    def provenance(self) -> dict[str, str]:
        return {"port": self.port, "part_id": self.part_id}

    def unavailable(self, reason: str = "cmplx_port_not_available", **extra: Any) -> dict[str, Any]:
        return {
            "available": False,
            "reason": reason,
            "provenance": self.provenance(),
            **extra,
        }

    def _provider(self) -> Any | None:
        return _get_morphon_provider(self.port)
