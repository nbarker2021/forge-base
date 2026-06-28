from __future__ import annotations
import argparse, json
from pathlib import Path

from .kit import build_eightfold_kit
from .simulation import WorkbenchSimulator
from .pdf_reports import build_all_pdfs


def main(argv=None):
    parser = argparse.ArgumentParser(prog="analog-workbench", description="Analog Forge Workbook simulation and PDF tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_kit = sub.add_parser("kit", help="export eightfold kit manifest")
    p_kit.add_argument("--out", default="kit_manifest.json")
    p_kit.add_argument("--copies", type=int, default=8)

    p_demo = sub.add_parser("demo", help="run demo simulation")
    p_demo.add_argument("--out", default="exports/demo_run")

    p_pdf = sub.add_parser("pdf", help="generate workbench PDFs")
    p_pdf.add_argument("--out", default="exports/pdfs")

    args = parser.parse_args(argv)

    if args.cmd == "kit":
        manifest = build_eightfold_kit(copies=args.copies)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(manifest, indent=2))
        print(str(out))
    elif args.cmd == "demo":
        sim = WorkbenchSimulator()
        demo = sim.demo()
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "demo_summary.json").write_text(json.dumps(demo, indent=2))
        sim.export(out)
        build_all_pdfs(out / "pdf", demo)
        print(str(out))
    elif args.cmd == "pdf":
        sim = WorkbenchSimulator()
        demo = sim.demo()
        paths = build_all_pdfs(args.out, demo)
        print("\n".join(paths))

if __name__ == "__main__":
    main()
