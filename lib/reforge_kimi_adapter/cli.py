from __future__ import annotations
import argparse, json
from pathlib import Path
from .adapter import adapt_work_fragment


def main() -> None:
    ap = argparse.ArgumentParser(description="ReForge ↔ Kimi adapter v0.1")
    ap.add_argument("input", help="Text input or path to a text file")
    ap.add_argument("--file", action="store_true", help="Treat input as file path")
    ap.add_argument("--window", type=int, default=64)
    ap.add_argument("--workspace", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    text = Path(args.input).read_text(errors="ignore") if args.file else args.input
    receipt = adapt_work_fragment(text, window=args.window, workspace=args.workspace)
    payload = json.dumps(receipt, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    else:
        print(payload)

if __name__ == "__main__":
    main()
