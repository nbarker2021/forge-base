"""
SplatForge.provenance_panel — KRR-GS-006: the provenance-inspection half
(PixelForge.overlay is the chart-overlay half).

Static, file-based, read-only: renders a render_pass frame receipt's key
fields to a small self-contained HTML file, written next to the rendered
frame. No live server, no new dependency — stdlib only, matching the rest
of this build's discipline. This is read-only receipt INSPECTION: it never
recomputes, validates, or alters anything in the receipt it's handed.
"""
from __future__ import annotations

import html
import json
from typing import Any, Dict

_FIELDS_OF_INTEREST = (
    "frame_hash", "backend", "gpu_profile", "width", "height",
    "tile_size", "splat_count", "tile_count", "max_splats_per_tile",
    "quantization", "genesis_correction_density", "tile_chart_classification",
    "parity_backend", "governance",
)


def render_provenance_html(frame_receipt: Dict[str, Any], title: str = "Render Provenance") -> str:
    """One frame receipt -> one self-contained HTML string. Fields not in
    _FIELDS_OF_INTEREST are still included, under "other", so this is a
    complete view of the receipt, not a lossy summary."""
    rows = []
    seen = set()
    for key in _FIELDS_OF_INTEREST:
        if key in frame_receipt:
            rows.append((key, frame_receipt[key]))
            seen.add(key)
    other = {k: v for k, v in frame_receipt.items() if k not in seen}

    def _row_html(key: str, value: Any) -> str:
        pretty = json.dumps(value, indent=2) if isinstance(value, (dict, list)) else str(value)
        return (
            "<tr><th>" + html.escape(key) + "</th>"
            "<td><pre>" + html.escape(pretty) + "</pre></td></tr>"
        )

    body = "\n".join(_row_html(k, v) for k, v in rows)
    if other:
        body += _row_html("other", other)

    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>"
        "body{font-family:monospace;background:#111;color:#ddd;padding:1em}"
        "table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #444;padding:6px;text-align:left;vertical-align:top}"
        "th{color:#9cf;width:220px}"
        "pre{margin:0;white-space:pre-wrap;word-break:break-all}"
        "</style></head><body>"
        f"<h2>{html.escape(title)}</h2>"
        f"<table>{body}</table>"
        "</body></html>"
    )


def write_provenance_panel(frame_receipt: Dict[str, Any], path: str,
                            title: str = "Render Provenance") -> str:
    """Render and write the HTML panel to `path`. Returns `path`."""
    html_text = render_provenance_html(frame_receipt, title=title)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_text)
    return path
