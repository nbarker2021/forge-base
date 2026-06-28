"""
Text adapter: utf-8 text in -> canonical bytes out.
"""

from __future__ import annotations

from ..carrier.binary_boundary import BinaryBoundaryFrame, make_frame


ADAPTER_NAME = "TextAdapter"
ADAPTER_VERSION = "0.1"


def adapt(text: str) -> BinaryBoundaryFrame:
    """Adapt text to a binary boundary frame."""
    return make_frame(
        payload=text.encode("utf-8"),
        source_type="text",
        adapter=ADAPTER_NAME,
        encoding="utf-8",
        adapter_version=ADAPTER_VERSION,
    )
