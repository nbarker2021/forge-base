"""Command line interface for Kp8.06.24."""

from __future__ import annotations
import argparse
import json
from pathlib import Path
from .compiler import MasterRibbonCompiler


def _repo() -> Path:
    return Path(__file__).resolve().parents[4]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m cqekernel.master_ribbon")
    parser.add_argument("--repo", type=Path, default=_repo())
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build"); build.add_argument("--cutoff", required=True)
    verify = commands.add_parser("verify"); verify.add_argument("epoch")
    project = commands.add_parser("project"); project.add_argument("paper_tile"); project.add_argument("--epoch")
    delta = commands.add_parser("delta"); delta.add_argument("prior_epoch"); delta.add_argument("new_cutoff")
    args = parser.parse_args(argv)
    compiler = MasterRibbonCompiler(args.repo)
    if args.command == "build": result = compiler.build(args.cutoff)
    elif args.command == "verify": result = compiler.verify(args.epoch)
    elif args.command == "project": result = compiler.project(args.paper_tile, args.epoch)
    else: result = compiler.delta(args.prior_epoch, args.new_cutoff)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("result", "PASS") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
