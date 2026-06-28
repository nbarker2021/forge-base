"""
Firmware registry.

The registry uses ``importlib`` to discover optional firmware packs.
Packs are listed as ``(pack_id, module_name)`` pairs. The registry
returns ``{"status": "EXTERNAL_REQUIRED", "reason": "..."}`` if a pack
is not installed.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class FirmwareRecord:
    pack_id: str
    available: bool
    module: Optional[str] = None
    version: Optional[str] = None
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "available": self.available,
            "module": self.module,
            "version": self.version,
            "reason": self.reason,
        }


class FirmwareRegistry:
    """Discover and query optional firmware packs."""

    # Default registry. Add packs here as they are developed.
    DEFAULT_PACKS: List[Tuple[str, str]] = [
        ("lattice_forge", "lattice_forge"),
        ("sympy_engine", "sympy"),
        ("numpy_engine", "numpy"),
        ("networkx_engine", "networkx"),
        ("oloid_geometry", "oloid"),
    ]

    def __init__(self, packs: Optional[List[Tuple[str, str]]] = None):
        self._packs = list(packs) if packs is not None else list(self.DEFAULT_PACKS)
        self._records: Dict[str, FirmwareRecord] = {}

    def discover(self) -> List[FirmwareRecord]:
        """Probe each known pack via ``importlib`` and record availability."""
        for pack_id, module_name in self._packs:
            try:
                mod = importlib.import_module(module_name)
                version = getattr(mod, "__version__", "unknown")
                self._records[pack_id] = FirmwareRecord(
                    pack_id=pack_id,
                    available=True,
                    module=module_name,
                    version=version,
                    reason="ok",
                )
            except Exception as e:
                self._records[pack_id] = FirmwareRecord(
                    pack_id=pack_id,
                    available=False,
                    module=module_name,
                    reason=f"not installed: {e!r}",
                )
        return list(self._records.values())

    def is_available(self, pack_id: str) -> bool:
        if pack_id not in self._records:
            self.discover()
        return self._records[pack_id].available

    def call(self, pack_id: str, operation: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call a firmware operation. Returns an ``EXTERNAL_REQUIRED``
        receipt if the pack is not installed.

        Kernel code MUST treat the returned dict as the only authority
        for what the firmware said.
        """
        if pack_id not in self._records:
            self.discover()
        rec = self._records.get(pack_id)
        if not rec or not rec.available:
            return {
                "status": "EXTERNAL_REQUIRED",
                "reason": f"optional firmware {pack_id!r} not installed",
                "pack_id": pack_id,
                "operation": operation,
            }
        mod = importlib.import_module(rec.module)  # type: ignore
        fn = getattr(mod, operation, None)
        if fn is None:
            return {
                "status": "EXTERNAL_REQUIRED",
                "reason": f"firmware {pack_id!r} has no operation {operation!r}",
                "pack_id": pack_id,
                "operation": operation,
            }
        try:
            result = fn(payload)
            return {"status": "OK", "pack_id": pack_id, "operation": operation, "result": result}
        except Exception as e:
            return {
                "status": "FAIL",
                "reason": repr(e),
                "pack_id": pack_id,
                "operation": operation,
            }

    def manifest(self) -> List[Dict[str, Any]]:
        if not self._records:
            self.discover()
        return [r.to_dict() for r in self._records.values()]
