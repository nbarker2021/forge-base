"""
Bytes adapter: raw bytes in -> canonical frame out.
"""

from __future__ import annotations

from ..carrier.binary_boundary import BinaryBoundaryFrame, make_frame


ADAPTER_NAME = "BytesAdapter"
ADAPTER_VERSION = "0.1"


def adapt(data: bytes) -> BinaryBoundaryFrame:
    """Adapt raw bytes to a binary boundary frame."""
    return make_frame(
        payload=data,
        source_type="bytes",
        adapter=ADAPTER_NAME,
        encoding="raw",
        adapter_version=ADAPTER_VERSION,
    )
