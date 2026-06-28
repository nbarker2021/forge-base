"""
JSON adapter: object in -> canonical frame out.

The object is serialized with sorted keys and tight separators so the
kernel observes a deterministic payload.
"""

from __future__ import annotations

import json
from typing import Any

from ..carrier.binary_boundary import BinaryBoundaryFrame, make_frame


ADAPTER_NAME = "JsonAdapter"
ADAPTER_VERSION = "0.1"


def adapt(obj: Any) -> BinaryBoundaryFrame:
    """Adapt a JSON-serializable object to a binary boundary frame."""
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return make_frame(
        payload=payload,
        source_type="json",
        adapter=ADAPTER_NAME,
        encoding="utf-8",
        adapter_version=ADAPTER_VERSION,
        extras={"schema": type(obj).__name__},
    )
