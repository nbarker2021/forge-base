"""
Host adapters: text, bytes, json, csv, filesystem, host packet.

The ``adapter_for`` function routes to the correct adapter based on
source type. Each adapter produces a ``BinaryBoundaryFrame``.
"""

from __future__ import annotations

from .bytes_adapter import adapt as adapt_bytes
from .csv_adapter import adapt as adapt_csv
from .filesystem import adapt as adapt_fs
from .host_packet import adapt as adapt_packet
from .json_adapter import adapt as adapt_json
from .text import adapt as adapt_text

from ..carrier.binary_boundary import BinaryBoundaryFrame


ADAPTER_REGISTRY = {
    "text": adapt_text,
    "bytes": adapt_bytes,
    "json": adapt_json,
    "csv": adapt_csv,
    "filesystem": adapt_fs,
    "host_packet": adapt_packet,
    "auto": None,  # will be resolved at call time
}


def adapter_for(source_type: str) -> "adapter_for.__annotations__['return']":
    """Return the adapter function for the given source type.

    If ``source_type`` is ``"auto"``, the caller must handle the
    dispatch manually (usually by checking ``isinstance(payload, bytes)``).
    """
    if source_type == "auto":
        raise ValueError("adapter_for('auto') is not supported; handle dispatch at call site")
    try:
        return ADAPTER_REGISTRY[source_type]
    except KeyError:
        raise ValueError(f"unknown source_type: {source_type}")


__all__ = [
    "ADAPTER_REGISTRY",
    "adapter_for",
    "adapt_text",
    "adapt_bytes",
    "adapt_json",
    "adapt_csv",
    "adapt_fs",
    "adapt_packet",
]