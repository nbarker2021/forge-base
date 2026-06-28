"""
Firmware ABI.

A thin abstract interface for the higher-level operations the kernel
may delegate to external firmware. The kernel never imports the math
libraries directly; it routes through this ABI and the
``FirmwareRegistry``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from .registry import FirmwareRegistry


class FirmwareABI(ABC):
    """Abstract firmware ABI. The default implementation is the
    ``DefaultFirmwareABI`` below; hosts may subclass and inject their
    own."""

    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def manifest(self) -> Dict[str, Any]: ...

    @abstractmethod
    def verify_j3(self, payload: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def verify_su3_n3(self, payload: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def verify_d12(self, payload: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def route_g2_f4_t5(self, payload: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def resolve_oloid(self, payload: Dict[str, Any]) -> Dict[str, Any]: ...


class DefaultFirmwareABI(FirmwareABI):
    """Default ABI: uses the ``FirmwareRegistry`` to route calls.

    All operations return ``{"status": "EXTERNAL_REQUIRED", ...}`` if
    the relevant firmware is not installed.
    """

    def __init__(self, registry: FirmwareRegistry):
        self._registry = registry

    def available(self) -> bool:
        return any(r.available for r in self._registry.discover())

    def manifest(self) -> Dict[str, Any]:
        return {"packs": self._registry.manifest()}

    def verify_j3(self, payload):
        return self._registry.call("lattice_forge", "verify_j3", payload)

    def verify_su3_n3(self, payload):
        return self._registry.call("lattice_forge", "verify_su3_n3", payload)

    def verify_d12(self, payload):
        return self._registry.call("lattice_forge", "verify_d12", payload)

    def route_g2_f4_t5(self, payload):
        return self._registry.call("lattice_forge", "route_g2_f4_t5", payload)

    def resolve_oloid(self, payload):
        return self._registry.call("oloid_geometry", "resolve_oloid", payload)
