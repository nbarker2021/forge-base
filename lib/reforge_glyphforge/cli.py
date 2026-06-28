from __future__ import annotations
import argparse, json
from pathlib import Path
from .fumu import analyze_work, export_markdown_bundle

def main(argv=None):
    ap = argparse.ArgumentParser(description="GlyphForge/FuMu semantic fragment analyzer")
    ap.add_argument("input", help="Text file to analyze")
    ap.add_argument("--out", default="exports/glyphforge_run", help="Output directory")
    ap.add_argument("--no-adapter", action="store_true", help="Skip Kimi/LCR adapter receipts")
    ns = ap.parse_args(argv)
    text = Path(ns.input).read_text(encoding="utf-8")
    analysis = analyze_work(text, run_adapter=not ns.no_adapter)
    out = Path(ns.out); out.mkdir(parents=True, exist_ok=True)
    (out / "glyphforge_analysis.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    written = export_markdown_bundle(analysis, out)
    print(json.dumps({"summary": analysis["summary"], "written": written}, indent=2))

if __name__ == "__main__":
    main()
