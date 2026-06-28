"""Command-line interface for CMPLX-R30."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .cache import (
    ContinuationLedger,
    ExtendedMemoryManifest,
    FormulaicBillionAddressLibrary,
    InMemorySheetCache,
    RootPlacementTemplateStore,
)
from .atlas import BinaryRule, open_binary_atlas
from .bridge_lab import ImmutableReverseAtlasBackend
from .canonical import build_canonical_witness, promote_canonical_window
from .hierarchy import HierarchicalAtlasGeometry
from .library import ReverseAtlasChain, ReverseAtlasLibrary
from .proof_shell import ProofShell
from .request_codec import RequestTailCodec
from .solver import CmplxR30Solver
from .verify import verify_product


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cmplx-r30")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("verify")

    cache = commands.add_parser("cache")
    cache_commands = cache.add_subparsers(dest="cache_command", required=True)
    cache_commands.add_parser("status")
    hydrate = cache_commands.add_parser("hydrate")
    hydrate.add_argument("--layer", required=True)
    hydrate.add_argument("--source", required=True, type=Path)
    plan = cache_commands.add_parser("plan")
    plan.add_argument("--n", required=True, type=int)
    validate = cache_commands.add_parser("validate-canonical")
    validate.add_argument("--max-depth", required=True, type=int)
    validate.add_argument("--sheet-width", type=int, default=4096)
    promote = cache_commands.add_parser("promote")
    promote.add_argument("--witness", required=True, type=Path)
    promote.add_argument("--sheet-width", type=int, default=4096)

    solve = commands.add_parser("solve")
    solve.add_argument("--n", required=True, type=int)
    solve.add_argument("--bits", required=True)

    atlas = commands.add_parser("atlas")
    atlas_commands = atlas.add_subparsers(dest="atlas_command", required=True)
    atlas_read = atlas_commands.add_parser("read")
    atlas_read.add_argument("--source", required=True, type=Path)
    atlas_read.add_argument("--bit-count", type=int)
    atlas_read.add_argument("--n", required=True, type=int)
    atlas_read.add_argument("--rule-number", required=True, type=int)
    atlas_read.add_argument("--prior-rule-number", type=int, default=90)
    atlas_project = atlas_commands.add_parser("project")
    atlas_project.add_argument("--source", required=True, type=Path)
    atlas_project.add_argument("--output", required=True, type=Path)
    atlas_project.add_argument("--bit-count", type=int)
    atlas_project.add_argument("--start", type=int, default=0)
    atlas_project.add_argument("--stop", type=int)
    atlas_project.add_argument("--rule-number", required=True, type=int)
    atlas_project.add_argument("--prior-rule-number", type=int, default=90)
    atlas_address = atlas_commands.add_parser("address")
    atlas_address.add_argument("--n", required=True, type=int)

    library = commands.add_parser("library")
    library_commands = library.add_subparsers(dest="library_command", required=True)
    library_compile = library_commands.add_parser("compile")
    library_compile.add_argument("--source", required=True, type=Path)
    library_compile.add_argument("--output", required=True, type=Path)
    library_compile.add_argument("--bit-count", type=int)
    library_compile.add_argument("--rule-number", required=True, type=int)
    library_compile.add_argument("--prior-rule-number", type=int, default=90)
    library_lookup = library_commands.add_parser("lookup")
    library_lookup.add_argument("--library", required=True, type=Path)
    library_lookup.add_argument("--n", required=True, type=int)
    library_backtrack = library_commands.add_parser("backtrack")
    library_backtrack.add_argument("--chain", required=True, type=Path)
    library_backtrack.add_argument("--n", required=True, type=int)
    library_backtrack.add_argument("--depth", type=int)
    library_address = library_commands.add_parser("address")
    library_address.add_argument("--n", required=True, type=int)

    codec = commands.add_parser("codec")
    codec_commands = codec.add_subparsers(dest="codec_command", required=True)
    codec_decode = codec_commands.add_parser("decode")
    codec_decode.add_argument("--n", required=True, type=int)

    claims = commands.add_parser("claims")
    claims_commands = claims.add_subparsers(dest="claims_command", required=True)
    claims_commands.add_parser("verify-shell")
    claims_show = claims_commands.add_parser("show")
    claims_show.add_argument("claim_id")
    claims_commands.add_parser("frontier")

    bridge = commands.add_parser("bridge")
    bridge_commands = bridge.add_subparsers(dest="bridge_command", required=True)
    bridge_predict = bridge_commands.add_parser("predict")
    bridge_predict.add_argument("--library", required=True, type=Path)
    bridge_predict.add_argument("--n", required=True, type=int)
    return parser


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CMPLX-R30 CLI."""
    args = _parser().parse_args(argv)
    if args.command == "verify":
        payload = verify_product()
        _print(payload)
        return 0 if payload["status"] == "pass" else 1
    if args.command == "cache":
        if args.cache_command == "promote":
            payload = promote_canonical_window(
                witness_path=args.witness,
                ledger=ContinuationLedger(
                    Path("extended_memory/hot/continuations.json")
                ),
                sheet_width=args.sheet_width,
            )
            _print(payload)
            return 0
        if args.cache_command == "validate-canonical":
            witness_path = Path(
                f"extended_memory/hot/canonical_rule30_depth_{args.max_depth}.json"
            )
            build_canonical_witness(args.max_depth, witness_path)
            payload = promote_canonical_window(
                witness_path=witness_path,
                ledger=ContinuationLedger(
                    Path("extended_memory/hot/continuations.json")
                ),
                sheet_width=args.sheet_width,
            )
            _print(payload)
            return 0
        if args.cache_command == "plan":
            ledger = ContinuationLedger(
                Path("extended_memory/hot/continuations.json")
            )
            instruction = ledger.instructions.get(f"N{args.n}")
            if instruction is None:
                _print({"N": args.n, "status": "missing"})
                return 2
            _print(instruction.to_dict())
            return 0
        manifest = ExtendedMemoryManifest.load(
            Path("extended_memory/manifest.json")
        )
        if args.cache_command == "hydrate":
            target = manifest.hydrate(args.layer, args.source)
            payload = {
                "hydrated": True,
                "layer": args.layer,
                "target": str(target),
            }
        else:
            payload = manifest.status()
        _print(payload)
        return 0
    if args.command == "atlas":
        if args.atlas_command == "address":
            _print(HierarchicalAtlasGeometry().route(args.n))
            return 0
        atlas = open_binary_atlas(args.source, bit_count=args.bit_count)
        projector = BinaryRule.from_rule_number(args.rule_number)
        prior = BinaryRule.from_rule_number(args.prior_rule_number)
        if args.atlas_command == "project":
            payload = atlas.project_to_packed(
                args.output,
                start=args.start,
                stop=args.stop,
                projector=projector,
                prior=prior,
            )
            _print(payload)
            return 0
        cell = atlas.cell(
            args.n,
            projector=projector,
            prior=prior,
        )
        _print(cell.to_dict())
        return 0
    if args.command == "library":
        if args.library_command == "address":
            payload = FormulaicBillionAddressLibrary().compile(args.n)
        elif args.library_command == "compile":
            payload = ReverseAtlasLibrary.compile(
                source=args.source,
                output=args.output,
                bit_count=args.bit_count,
                projector=BinaryRule.from_rule_number(args.rule_number),
                prior=BinaryRule.from_rule_number(args.prior_rule_number),
            ).manifest
        elif args.library_command == "lookup":
            payload = ReverseAtlasLibrary.open(args.library).lookup(args.n)
        else:
            payload = ReverseAtlasChain.open(args.chain).backtrack(
                args.n,
                depth=args.depth,
            )
        _print(payload)
        return 0
    if args.command == "codec":
        _print(RequestTailCodec().decode(args.n))
        return 0
    if args.command == "claims":
        shell = ProofShell.default()
        if args.claims_command == "verify-shell":
            payload = shell.verify()
            _print(payload)
            return 0 if payload["status"] == "pass_with_frontier" else 1
        if args.claims_command == "frontier":
            _print(shell.frontier())
            return 0
        payload = shell.show(args.claim_id)
        if payload is None:
            _print({"claim_id": args.claim_id, "status": "missing"})
            return 2
        _print(payload)
        return 0
    if args.command == "bridge":
        payload = ImmutableReverseAtlasBackend.open(args.library).predict(args.n)
        _print(payload)
        return 0 if payload["bit"] is not None else 2
    solver = CmplxR30Solver(
        InMemorySheetCache.from_bits(args.bits),
        template_store=RootPlacementTemplateStore(
            Path("extended_memory/hot/root_templates.json")
        ),
        continuation_ledger=ContinuationLedger(
            Path("extended_memory/hot/continuations.json")
        ),
    )
    receipt = solver.solve(args.n)
    _print(receipt.to_dict())
    return 0 if receipt.bit is not None else 2


if __name__ == "__main__":
    raise SystemExit(main())
