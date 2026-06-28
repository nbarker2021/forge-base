from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Dict, Any, Tuple

try:
    from reforge_kimi_adapter.adapter import adapt_work_fragment as adapt_fragment
except Exception:  # pragma: no cover
    adapt_fragment = None

FRAGMENT_TYPES = [
    "definition", "axiom", "lemma", "claim", "example", "method",
    "obligation", "test", "source", "paper_section", "supplement", "note"
]

TYPE_PATTERNS = {
    "definition": [r"\bis defined as\b", r"\bdefinition\b", r"\bmeans\b", r"\bcalled\b"],
    "axiom": [r"\baxiom\b", r"\bmust\b", r"\brequired\b", r"\balways\b"],
    "lemma": [r"\blemma\b", r"\bfollows\b", r"\btherefore\b", r"\bimplies\b"],
    "claim": [r"\bclaim\b", r"\bI propose\b", r"\btheory\b", r"\bthis shows\b", r"\bthis means\b"],
    "example": [r"\bexample\b", r"\bfor instance\b", r"\be\.g\.\b"],
    "method": [r"\bmethod\b", r"\bworkflow\b", r"\bprocess\b", r"\boperator\b", r"\bengine\b"],
    "obligation": [r"\bobligation\b", r"\bneeds? to\b", r"\bmust test\b", r"\bTODO\b", r"\bunresolved\b"],
    "test": [r"\btest\b", r"\bverify\b", r"\bvalidation\b", r"\bpytest\b", r"\bsolver\b"],
    "source": [r"\bcitation\b", r"\bsource\b", r"\bpaper\b", r"\bURL\b", r"https?://"],
    "supplement": [r"\bsupplement\b", r"\bappendix\b", r"\bextra\b"],
    "paper_section": [r"\bsection\b", r"\bchapter\b", r"\bPaper\s+\d+\b"],
}

COLOR_RULES = [
    ("black", ["obligation", "unresolved"]),
    ("white", ["proof", "verified", "receipt"]),
    ("red", ["claim", "action", "quark", "color"]),
    ("green", ["method", "operator", "engine", "workflow"]),
    ("blue", ["definition", "source", "document", "glyph"]),
    ("grey", ["maybe", "unclear", "draft", "note"]),
    ("neon", ["boundary", "test", "active", "urgent"]),
    ("clear", ["overlay", "comment", "meta", "review"]),
]

DEMAND_RULES = [
    ("formalize", ["definition", "axiom", "lemma"]),
    ("prove_or_receipt", ["claim", "lemma", "test"]),
    ("defer_obligation", ["obligation"]),
    ("export_paper", ["paper_section", "supplement"]),
    ("source_ground", ["source"]),
    ("demonstrate", ["example", "method"]),
]

@dataclass
class GlyphFragment:
    fragment_id: str
    order: int
    text: str
    fragment_type: str
    confidence: float
    color_state: str
    language_demand: str
    proof_state: str
    obligation_flag: bool
    receipt_id: str | None = None
    lcr_summary: Dict[str, Any] | None = None


def _stable_id(prefix: str, text: str, order: int = 0) -> str:
    h = hashlib.sha256(f"{order}\n{text}".encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{h}"


def split_fragments(text: str) -> List[str]:
    """Split work into fragments using headings, bullets, and sentence boundaries.

    This is deliberately deterministic and stdlib-only. It treats short lines
    as their own cards, while long paragraphs are split into sentence-like cards.
    """
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []
    raw: List[str] = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        lines = [ln.strip(" -\t") for ln in block.split("\n") if ln.strip()]
        if len(lines) > 1:
            raw.extend(lines)
        else:
            # keep headings/short statements whole; split long prose
            one = lines[0] if lines else block
            if len(one) > 280:
                parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", one)
                raw.extend([p.strip() for p in parts if p.strip()])
            else:
                raw.append(one)
    return raw


def classify_fragment(text: str) -> Tuple[str, float]:
    lowered = text.lower()
    scores: Dict[str, int] = {k: 0 for k in FRAGMENT_TYPES}
    for typ, pats in TYPE_PATTERNS.items():
        for pat in pats:
            if re.search(pat, text, flags=re.IGNORECASE):
                scores[typ] += 2
    if text.strip().endswith("?"):
        scores["obligation"] += 1
    if re.match(r"^(paper|section|appendix|supplement)\b", lowered):
        scores["paper_section"] += 2
    if any(sym in text for sym in ["→", "=", "::", "=>"]):
        scores["method"] += 1
        scores["lemma"] += 1
    best = max(scores.items(), key=lambda kv: kv[1])
    if best[1] == 0:
        return "note", 0.45
    conf = min(0.95, 0.45 + 0.12 * best[1])
    return best[0], conf


def assign_color(text: str, typ: str) -> str:
    hay = f"{text.lower()} {typ}"
    for color, keys in COLOR_RULES:
        if any(k in hay for k in keys):
            return color
    return "grey"


def assign_language_demand(typ: str) -> str:
    for demand, types in DEMAND_RULES:
        if typ in types:
            return demand
    return "record"


def proof_state_for(typ: str, text: str) -> Tuple[str, bool]:
    low = text.lower()
    if typ == "obligation" or any(k in low for k in ["need", "todo", "unresolved", "must test"]):
        return "obligation", True
    if any(k in low for k in ["verified", "proven", "receipt", "pass", "closure"]):
        return "proof", False
    if typ in ["claim", "lemma", "test"]:
        return "candidate", False
    return "context", False


def analyze_work(text: str, run_adapter: bool = True) -> Dict[str, Any]:
    fragments = split_fragments(text)
    out: List[GlyphFragment] = []
    edges: List[Dict[str, Any]] = []
    for i, frag in enumerate(fragments):
        typ, conf = classify_fragment(frag)
        color = assign_color(frag, typ)
        demand = assign_language_demand(typ)
        proof_state, obligation = proof_state_for(typ, frag)
        fid = _stable_id("glyph", frag, i)
        receipt_id = None
        lcr = None
        if run_adapter and adapt_fragment is not None:
            try:
                receipt = adapt_fragment(frag)
                receipt_id = receipt.get("fragment_id") or receipt.get("receipt_id") or receipt.get("id")
                lcr = {
                    "blocks": receipt.get("lcr_block_count", len(receipt.get("blocks", []))),
                    "summary": receipt.get("summary", {}),
                    "graph": receipt.get("worldforge_graph", {}).get("summary", {}) if isinstance(receipt.get("worldforge_graph"), dict) else {},
                }
            except Exception as exc:
                lcr = {"adapter_error": str(exc)}
        out.append(GlyphFragment(fid, i, frag, typ, conf, color, demand, proof_state, obligation, receipt_id, lcr))
        if i > 0:
            edges.append({"source": out[i-1].fragment_id, "target": fid, "edge_type": "sequence"})
    # add type grouping edges to synthetic hubs
    hubs = sorted(set(f.fragment_type for f in out))
    hub_nodes = [{"id": f"hub_{h}", "label": h, "kind": "type_hub"} for h in hubs]
    for f in out:
        edges.append({"source": f"hub_{f.fragment_type}", "target": f.fragment_id, "edge_type": "classifies"})
    return {
        "summary": {
            "fragment_count": len(out),
            "obligation_count": sum(1 for f in out if f.obligation_flag),
            "type_counts": {t: sum(1 for f in out if f.fragment_type == t) for t in sorted(set(f.fragment_type for f in out))},
            "color_counts": {c: sum(1 for f in out if f.color_state == c) for c in sorted(set(f.color_state for f in out))},
        },
        "fragments": [asdict(f) for f in out],
        "hub_nodes": hub_nodes,
        "edges": edges,
    }


def export_markdown_bundle(analysis: Dict[str, Any], out_dir: str | Path) -> Dict[str, str]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    fragments = analysis.get("fragments", [])
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for f in fragments:
        by_type.setdefault(f["fragment_type"], []).append(f)
    written: Dict[str, str] = {}
    for typ, items in by_type.items():
        fp = out_path / f"{typ}_fragments.md"
        lines = [f"# {typ.title()} Fragments", ""]
        for f in items:
            lines += [f"## {f['fragment_id']}", "", f["text"], "", f"- color: `{f['color_state']}`", f"- demand: `{f['language_demand']}`", f"- proof_state: `{f['proof_state']}`", f"- receipt: `{f.get('receipt_id')}`", ""]
        fp.write_text("\n".join(lines), encoding="utf-8")
        written[typ] = str(fp)
    # paper skeleton
    skel = out_path / "paper_skeleton.md"
    lines = ["# Generated Paper / Supplement Skeleton", "", "## Definitions", ""]
    for typ in ["definition", "axiom", "lemma", "claim", "method", "example", "test", "obligation"]:
        lines.append(f"## {typ.title()}s")
        for f in by_type.get(typ, []):
            lines.append(f"- ({f['color_state']}/{f['proof_state']}) {f['text']}")
        lines.append("")
    skel.write_text("\n".join(lines), encoding="utf-8")
    written["paper_skeleton"] = str(skel)
    return written
