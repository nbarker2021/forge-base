"""
Firmware manifest.

A firmware pack is described by a small JSON manifest. The kernel
queries the registry for available packs and returns
``{"status": "EXTERNAL_REQUIRED", "reason": "..."}`` when a pack is
not installed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class FirmwarePack:
    """A discovered firmware pack."""

    pack_id: str
    version: str
    entrypoint: str
    capabilities: List[str] = field(default_factory=list)
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "version": self.version,
            "entrypoint": self.entrypoint,
            "capabilities": list(self.capabilities),
            "extras": dict(self.extras),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FirmwarePack":
        return cls(
            pack_id=data["pack_id"],
            version=data["version"],
            entrypoint=data["entrypoint"],
            capabilities=list(data.get("capabilities", [])),
            extras=dict(data.get("extras", {})),
        )


def load_manifest(path: Path) -> FirmwarePack:
    """Load a firmware manifest from a JSON file."""
    return FirmwarePack.from_dict(json.loads(path.read_text(encoding="utf-8")))
