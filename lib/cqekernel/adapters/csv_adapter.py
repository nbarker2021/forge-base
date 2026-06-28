"""
CSV adapter: list-of-dicts in -> canonical frame out.

The CSV is written with sorted keys and ``\n`` line endings.
"""

from __future__ import annotations

import csv
import io
from typing import Any, Dict, List

from ..carrier.binary_boundary import BinaryBoundaryFrame, make_frame


ADAPTER_NAME = "CsvAdapter"
ADAPTER_VERSION = "0.1"


def adapt(rows: List[Dict[str, Any]]) -> BinaryBoundaryFrame:
    """Adapt a list of dicts to a binary boundary frame as CSV."""
    if not rows:
        payload = b""
        return make_frame(
            payload=payload,
            source_type="csv",
            adapter=ADAPTER_NAME,
            encoding="utf-8",
            adapter_version=ADAPTER_VERSION,
        )
    # Use a stable key order (sorted union of all keys)
    keys = sorted({k for r in rows for k in r.keys()})
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=keys, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in keys})
    payload = buf.getvalue().encode("utf-8")
    return make_frame(
        payload=payload,
        source_type="csv",
        adapter=ADAPTER_NAME,
        encoding="utf-8",
        adapter_version=ADAPTER_VERSION,
        extras={"columns": keys, "rows": len(rows)},
    )
