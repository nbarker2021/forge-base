"""
Host packet adapter: a JSON packet in -> canonical frame out.

The host packet is a small dict::

    {
      "op": "observe",
      "payload": "...",
      "mode": "AUDIT",
      "policy": {"allow_firmware": false, ...}
    }
"""

from __future__ import annotations

import json
from typing import Any, Dict

from ..carrier.binary_boundary import BinaryBoundaryFrame, make_frame


ADAPTER_NAME = "HostPacketAdapter"
ADAPTER_VERSION = "0.1"


def adapt(packet: Dict[str, Any]) -> BinaryBoundaryFrame:
    """Adapt a host packet to a binary boundary frame."""
    payload = json.dumps(packet, sort_keys=True, separators=(",", ":")).encode("utf-8")
    op = packet.get("op", "unknown")
    return make_frame(
        payload=payload,
        source_type="host_packet",
        adapter=ADAPTER_NAME,
        encoding="utf-8",
        adapter_version=ADAPTER_VERSION,
        extras={"op": op, "mode": packet.get("mode", "READ_ONLY")},
    )
