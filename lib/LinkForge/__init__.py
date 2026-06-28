"""
LinkForge — link any external database into the lib as a receipted lib item.

The collapse of "integration work": every outside data source — a weather
API, a calendar feed, a recipe database, a product catalog, a vision
service's output — enters the system the SAME way, exactly once:

    link(name, source) -> fetch/read -> parse -> canonical record
                        -> (host kernel: BBA compute -> crystal -> validate
                            -> receipt w/ 2 links) -> saved lookup table
                        -> reused forever for nearly free

After that, the linked data IS a lib item: engines consume it as a lookup
table, refreshes are new receipted events, and identical content re-links
as pure cache hits.

Connectivity honors the host's mode toggle via the injected fetcher:
    LOCAL   - no fetcher injected: url sources are refused (file/inline ok)
    HYBRID  - fetcher injected ONLY for calendar-kind links
    CLOUD   - fetcher injected for everything

Stdlib only. Parsers: json, csv, ics (minimal VEVENT), text.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

Fetcher = Callable[[str], str]     # url -> text (host injects per mode)

FORMATS = ("json", "csv", "ics", "text")
KINDS = ("data", "calendar", "weather", "recipes", "catalog", "vision")


# ─── Parsers (pure, stdlib) ───────────────────────────────────────────────────

def parse_json(text: str) -> Any:
    return json.loads(text)


def parse_csv(text: str) -> List[Dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def parse_ics(text: str) -> List[Dict[str, str]]:
    """Minimal VEVENT parser: DTSTART/DTEND/SUMMARY/LOCATION/UID.
    Handles line unfolding; recurrence rules are carried raw (v1)."""
    # unfold continuation lines (RFC 5545: lines starting with space/tab)
    lines: List[str] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    events: List[Dict[str, str]] = []
    cur: Optional[Dict[str, str]] = None
    for ln in lines:
        u = ln.strip()
        if u == "BEGIN:VEVENT":
            cur = {}
        elif u == "END:VEVENT":
            if cur is not None:
                events.append(cur)
            cur = None
        elif cur is not None and ":" in u:
            key, val = u.split(":", 1)
            key = key.split(";", 1)[0].upper()        # strip params
            if key in ("DTSTART", "DTEND", "SUMMARY", "LOCATION", "UID", "RRULE"):
                cur[key.lower()] = val
    out = []
    for e in events:
        dt = e.get("dtstart", "")
        date = (f"{dt[0:4]}-{dt[4:6]}-{dt[6:8]}" if len(dt) >= 8 and dt[:8].isdigit()
                else dt[:10])
        t = ""
        if "T" in dt and len(dt) >= 13:
            hh, mm = int(dt[9:11]), dt[11:13]
            t = f"{hh % 12 or 12}{':' + mm if mm != '00' else ''}{'p' if hh >= 12 else 'a'}"
        out.append({"date": date, "time": t, "text": e.get("summary", ""),
                    "uid": e.get("uid", ""), "rrule": e.get("rrule", "")})
    return out


_PARSERS: Dict[str, Callable[[str], Any]] = {
    "json": parse_json, "csv": parse_csv, "ics": parse_ics,
    "text": lambda t: t,
}


# ─── The linker ───────────────────────────────────────────────────────────────

class LinkForgeEngine:
    """Named links to external databases, each one a canonical lib item."""

    def __init__(self):
        self._links: Dict[str, Dict[str, Any]] = {}

    def link(self, name: str, source: str, fmt: str = "json",
             kind: str = "data",
             fetcher: Optional[Fetcher] = None,
             inline: Optional[str] = None) -> Dict[str, Any]:
        """Link a source into the lib.

        source: a URL (needs fetcher — mode-gated by host), a file path,
                or "inline" with the raw text in `inline`.
        Returns the canonical record the host kernel receipts.
        """
        if fmt not in _PARSERS:
            return {"ok": False, "name": name, "error": f"format must be one of {FORMATS}"}

        # acquire text
        if inline is not None:
            text, via = inline, "inline"
        elif source.startswith(("http://", "https://")):
            if fetcher is None:
                return {"ok": False, "name": name, "kind": kind,
                        "error": "url source refused: no fetcher for current "
                                 "connectivity mode (LOCAL blocks urls; HYBRID "
                                 "allows calendar links only)"}
            try:
                text, via = fetcher(source), "url"
            except Exception as exc:
                return {"ok": False, "name": name, "error": f"fetch failed: {exc}"}
        else:
            p = Path(source)
            if not p.is_file():
                return {"ok": False, "name": name, "error": f"file not found: {source}"}
            text, via = p.read_text(encoding="utf-8", errors="replace"), "file"

        # parse
        try:
            data = _PARSERS[fmt](text)
        except Exception as exc:
            return {"ok": False, "name": name, "error": f"parse failed ({fmt}): {exc}"}

        rec = {
            "ok": True,
            "name": name,
            "kind": kind,
            "format": fmt,
            "source": source if via != "inline" else "inline",
            "via": via,
            "content_hash": hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16],
            "bytes": len(text),
            "records": (len(data) if isinstance(data, (list, dict)) else 1),
            "linked_at": time.time(),
            "data": data,
        }
        self._links[name] = rec
        return rec

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        return self._links.get(name)

    def data(self, name: str, default: Any = None) -> Any:
        rec = self._links.get(name)
        return rec["data"] if rec else default

    def names(self) -> List[str]:
        return sorted(self._links)

    def status(self) -> Dict[str, Any]:
        return {n: {k: v for k, v in r.items() if k != "data"}
                for n, r in self._links.items()}


engine = LinkForgeEngine()

__version__ = "0.1.0"


# ─── Verify (forge-family contract) ───────────────────────────────────────────

def verify() -> dict:
    """Finite checks binding LinkForge to its docstring claims.

    Exercises each of the four documented formats (json, csv, ics, text)
    via inline text — the LOCAL-mode path that needs no fetcher — and
    confirms the canonical record shape. Pure additive.
    """
    checks = {}

    # 1. JSON inline link
    try:
        rec = engine.link("v-json", source="inline-not-used", fmt="json",
                          kind="data",
                          inline='[{"a": 1, "b": 2}, {"a": 3, "b": 4}]')
        checks["json_inline_link"] = bool(
            rec.get("ok") and rec.get("format") == "json"
            and rec.get("records") == 2 and rec.get("via") == "inline"
        )
    except Exception:
        checks["json_inline_link"] = False

    # 2. CSV inline link
    try:
        rec = engine.link("v-csv", source="inline", fmt="csv", kind="catalog",
                          inline="name,qty\napple,3\npear,2\n")
        checks["csv_inline_link"] = bool(
            rec.get("ok") and rec.get("format") == "csv"
            and rec.get("records") == 2
        )
    except Exception:
        checks["csv_inline_link"] = False

    # 3. ICS inline link
    try:
        ics = (
            "BEGIN:VCALENDAR\n"
            "BEGIN:VEVENT\n"
            "UID:v1@x\nDTSTART:20260622T090000\nDTEND:20260622T100000\n"
            "SUMMARY:verify event\nLOCATION:home\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        )
        rec = engine.link("v-ics", source="inline", fmt="ics",
                          kind="calendar", inline=ics)
        events = rec.get("data") or []
        checks["ics_inline_link"] = bool(
            rec.get("ok") and len(events) == 1
            and events[0].get("text") == "verify event"
            and events[0].get("date", "").startswith("2026-06-22")
        )
    except Exception:
        checks["ics_inline_link"] = False

    # 4. Text inline link (with same content twice, content_hash must match)
    try:
        engine.link("v-text", source="inline", fmt="text", kind="data",
                    inline="hello world")
        rec2 = engine.link("v-text", source="inline", fmt="text", kind="data",
                           inline="hello world")
        checks["text_link_idempotent_hash"] = bool(
            rec2.get("ok") and rec2.get("content_hash")
            and engine.get("v-text", {}).get("content_hash") == rec2.get("content_hash")
        )
    except Exception:
        checks["text_link_idempotent_hash"] = False

    # 5. URL without fetcher is refused (LOCAL-mode contract)
    try:
        refused = engine.link("v-url", source="https://example.com/x.json",
                              fmt="json", kind="data")
        checks["url_without_fetcher_refused"] = (
            refused.get("ok") is False and "refused" in refused.get("error", "").lower()
        )
    except Exception:
        checks["url_without_fetcher_refused"] = False

    # 6. Unknown format is refused cleanly
    try:
        bad = engine.link("v-bad", source="inline", fmt="yaml", kind="data",
                          inline="x: 1")
        checks["unknown_format_refused"] = (
            bad.get("ok") is False and "format" in bad.get("error", "").lower()
        )
    except Exception:
        checks["unknown_format_refused"] = False

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    if passed == total:
        status = "pass"
    elif passed >= max(1, total // 2):
        status = "partial"
    else:
        status = "fail"

    return {
        "forge": "LinkForge",
        "status": status,
        "checks": checks,
        "passed": passed,
        "total": total,
        "paper": "CQE-paper-11 (Family OS: lib item admission contract)",
    }


__all__ = ["LinkForgeEngine", "engine", "parse_ics", "parse_csv", "parse_json",
           "FORMATS", "KINDS"]
