from __future__ import annotations
import json, hashlib
from pathlib import Path
from typing import Any
from .registry import list_engines, layer_map


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def compose(text: str) -> dict[str, Any]:
    """Compose work through the curated Rhenium path, falling back to local wrappers."""
    try:
        from rhenium_engine.orchestrator import compose_work
        result = compose_work(text)
    except Exception as exc:
        try:
            from reforge_kimi_adapter.adapter import adapt_fragment
            receipt = adapt_fragment(text)
        except Exception as inner:
            receipt = {"receipt_id":"forgefactory_fallback_"+_sha(text), "adapter_error":repr(inner), "blocks":[]}
        result = {
            "product":"ReForge",
            "engine":"ForgeFactory fallback",
            "input_sha":_sha(text),
            "engines":list_engines(),
            "layers":layer_map(),
            "receipt":receipt,
            "world_graph":{"nodes":[],"edges":[]},
            "summary":{"node_count":0,"edge_count":0,"proof_count":0,"obligation_count":0,"fragment_count":0},
            "warning":repr(exc),
        }
    result["factory"] = {"name":"ForgeFactory", "version":"0.1.0", "engines":list_engines(), "layers":layer_map()}
    return result


def export_project(result: dict[str, Any], outdir: str | Path) -> dict[str, str]:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for key, payload in {
        "composition": result,
        "receipt": result.get("receipt", {}),
        "world_graph": result.get("world_graph", {}),
        "glyph_analysis": result.get("glyph_analysis", {}),
        "factory_registry": {"engines":list_engines(), "layers":layer_map()},
    }.items():
        p = out / f"{key}.json"
        p.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        paths[key] = str(p)
    md = out / "README_EXPORT.md"
    s = result.get("summary", {})
    md.write_text(
        "# ForgeFactory Export\n\n"
        f"- Nodes: {s.get('node_count', 0)}\n"
        f"- Edges: {s.get('edge_count', 0)}\n"
        f"- Proofs: {s.get('proof_count', 0)}\n"
        f"- Obligations: {s.get('obligation_count', 0)}\n"
        f"- Fragments: {s.get('fragment_count', 0)}\n",
        encoding="utf-8",
    )
    paths["readme"] = str(md)
    return paths
