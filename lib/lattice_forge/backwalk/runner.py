"""Console entry points for Niemeier backwalk, Weyl bonds, and lattice-space jobs."""
from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from lattice_forge.algebra.o1_registry import E8_WEYL_ORDER
from lattice_forge.backwalk import (
    PILOT_TERMINAL_IDS,
    WorkStore,
    all_niemeier_terminal_ids,
    materialize_exceptional_spine,
    materialize_terminals,
)
from lattice_forge.backwalk.lattice_space_job import run_lattice_space_exhaustion
from lattice_forge.backwalk.weyl_bond_dual import (
    QUADRANT_COUNT,
    WeylBondBatchSpec,
    iter_batch_specs,
    materialize_weyl_bond_batch,
)
from lattice_forge.backwalk.weyl_bond_quadrant import concatenate_quadrant_trees
from lattice_forge.paths import resolve_work_db
from lattice_forge.seed import SeedStore


def _parse_exceptionals(raw: str) -> set[str]:
    return {x.strip() for x in raw.split(",") if x.strip()}


def _terminals_for_phase(phase: str, explicit: str | None) -> list[str]:
    if explicit:
        return [t.strip() for t in explicit.split(",") if t.strip()]
    if phase == "pilot":
        return list(PILOT_TERMINAL_IDS)
    if phase == "full24":
        return all_niemeier_terminal_ids()
    if phase == "exceptional-only":
        return []
    raise ValueError(f"unknown phase: {phase}")


def _expected_state_count(terminal_id: str) -> int | None:
    expected = {
        "Niemeier:Leech": 1,
        "Niemeier:D4^6": 7,
        "Niemeier:A2^12": 13,
        "Niemeier:A1^24": 25,
    }
    return expected.get(terminal_id)


def _sort_weyl_specs(specs: list[WeylBondBatchSpec]) -> list[WeylBondBatchSpec]:
    def key(s: WeylBondBatchSpec) -> tuple:
        depth_key = -s.dual_depth if s.direction == "construct_in" else s.dual_depth
        return (s.direction, depth_key, s.source_group, s.target_group)

    return sorted(specs, key=key)


def build_backwalk_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lattice-forge-backwalk",
        description="Niemeier backward-category builder (bundled seed, writable work DB)",
    )
    parser.add_argument("--phase", choices=("pilot", "full24", "exceptional-only"), default="pilot")
    parser.add_argument("--terminals", default=None, help="Comma-separated terminal IDs")
    parser.add_argument(
        "--work-db",
        type=Path,
        default=None,
        help="Writable SQLite (default: LATTICE_FORGE_WORK_DB or ./.lattice_forge/backwalk/backwalk_work.db)",
    )
    parser.add_argument("--progress-jsonl", type=Path, default=None)
    parser.add_argument("--baseline-report", type=Path, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--include-exceptionals",
        default=os.environ.get("BACKWALK_EXCEPTIONALS", "g2,f4,e6"),
    )
    parser.add_argument("--involution-limit", type=int, default=None)
    return parser


def run_backwalk(argv: list[str] | None = None) -> int:
    args = build_backwalk_parser().parse_args(argv)

    inv_limit = args.involution_limit
    if inv_limit is None and os.environ.get("BACKWALK_INVOLUTION_LIMIT"):
        inv_limit = int(os.environ["BACKWALK_INVOLUTION_LIMIT"])
    if args.phase == "full24" and inv_limit is None:
        inv_limit = 50

    work_db = resolve_work_db(args.work_db)
    progress_path = args.progress_jsonl or work_db.parent / "progress.jsonl"
    baseline_path = args.baseline_report or work_db.parent / "baseline_report.json"

    seed_verify_before = SeedStore.packaged().verify()
    run_id = str(uuid.uuid4())
    config = {
        "phase": args.phase,
        "terminals": args.terminals,
        "involution_limit": inv_limit,
        "include_exceptionals": args.include_exceptionals,
        "resume": args.resume,
    }

    t0 = time.perf_counter()
    errors: list[str] = []
    stats_list = []
    ex_summary: dict = {}

    with WorkStore(work_db) as store:
        store.start_run(run_id, args.phase, config)
        terminal_ids = _terminals_for_phase(args.phase, args.terminals)

        if terminal_ids:
            stats_list = materialize_terminals(
                store,
                terminal_ids,
                involution_limit=inv_limit,
                resume=args.resume,
            )

        ex_summary = materialize_exceptional_spine(
            store,
            include=_parse_exceptionals(args.include_exceptionals),
        )

        for st in stats_list:
            exp = _expected_state_count(st.terminal_id)
            if exp is not None and st.state_count != exp:
                errors.append(f"{st.terminal_id}: expected {exp} states, got {st.state_count}")
            peel_exp = max(0, st.state_count - 1)
            if st.peel_morphism_count != peel_exp:
                errors.append(
                    f"{st.terminal_id}: expected {peel_exp} peel morphisms, got {st.peel_morphism_count}"
                )

        if "g2" in args.include_exceptionals.lower() and "f4" in args.include_exceptionals.lower():
            if not ex_summary.get("g2_f4_path"):
                errors.append("exceptional spine missing G2->F4 path")

        if "e6" in args.include_exceptionals.lower():
            if (
                store.count_exceptional_morphisms("cartan_extension") < 1
                and "e7" in args.include_exceptionals.lower()
            ):
                errors.append("expected E6->E7 cartan_extension when e6,e7 enabled")

    seed_verify_after = SeedStore.packaged().verify()

    report = {
        "run_id": run_id,
        "phase": args.phase,
        "work_db": str(work_db),
        "work_db_bytes": work_db.stat().st_size if work_db.exists() else 0,
        "wall_seconds": time.perf_counter() - t0,
        "seed_verify_before": seed_verify_before,
        "seed_verify_after": seed_verify_after,
        "terminals": [asdict(s) for s in stats_list],
        "exceptional": ex_summary,
        "errors": errors,
        "status": "fail" if errors else "pass",
    }

    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    with progress_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "run_complete", **report}, default=str) + "\n")

    print(json.dumps(report, indent=2))
    return 1 if errors else 0


def build_weyl_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lattice-forge-weyl-bond",
        description="Quadrant-sharded dual Weyl-bond orchestrator (middle-in / middle-out)",
    )
    parser.add_argument("--work-db", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-rows-per-batch", type=int, default=None)
    parser.add_argument("--sleep-ms", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--quadrant", type=int, default=None, help="Single quadrant 0..3")
    parser.add_argument("--all-quadrants", action="store_true")
    parser.add_argument("--concat-only", action="store_true")
    return parser


def run_weyl_orchestrate(argv: list[str] | None = None) -> int:
    args = build_weyl_parser().parse_args(argv)

    max_rows = args.max_rows_per_batch
    if max_rows is None:
        max_rows = int(os.environ.get("WEYL_BOND_MAX_ROWS_PER_BATCH", "64"))
    sleep_ms = args.sleep_ms
    if sleep_ms is None:
        sleep_ms = int(os.environ.get("WEYL_BOND_BATCH_SLEEP_MS", "50"))
    mirror = os.environ.get("WEYL_BOND_MIRROR_OLOID", "1") != "0"

    work_db = resolve_work_db(args.work_db)
    manifest_path = args.manifest or work_db.parent / "weyl_bond_manifest.jsonl"
    report_path = work_db.parent / "weyl_bond_orchestrator_report.json"

    seed_before = SeedStore.packaged().verify()
    run_id = str(uuid.uuid4())

    if args.quadrant is not None and args.all_quadrants:
        print("Use either --quadrant N or --all-quadrants, not both", file=sys.stderr)
        return 2
    if args.quadrant is None and not args.all_quadrants and not args.concat_only:
        args.all_quadrants = True

    quadrant_plan: list[int]
    if args.concat_only:
        quadrant_plan = []
    elif args.quadrant is not None:
        quadrant_plan = [args.quadrant]
    else:
        quadrant_plan = list(range(QUADRANT_COUNT))

    specs: list[WeylBondBatchSpec] = []
    for q in quadrant_plan:
        specs.extend(list(iter_batch_specs(include_read_out=True, quadrant=q)))
    specs = _sort_weyl_specs(specs)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "run_id": run_id,
                    "quadrant_plan": quadrant_plan,
                    "batch_count": len(specs),
                    "dry_run": True,
                },
                indent=2,
            )
        )
        return 0

    if args.concat_only:
        with WorkStore(work_db) as store:
            root = concatenate_quadrant_trees(store, tree_path="weyl_bond_result_tree.json")
        print(json.dumps({"run_id": run_id, "concat_only": True, "total_bonds": root["total_bonds"]}, indent=2))
        return 0

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as mf:
        for spec in specs:
            mf.write(
                json.dumps(
                    {
                        "batch_id": spec.batch_id,
                        "wave_id": spec.wave_id,
                        "direction": spec.direction,
                        "dual_depth": spec.dual_depth,
                        "source_group": spec.source_group,
                        "target_group": spec.target_group,
                    }
                )
                + "\n"
            )

    t0 = time.perf_counter()
    errors: list[str] = []
    completed = 0
    skipped = 0
    total_rows = 0
    bonds_in_db = 0
    tree_root: dict[str, Any] | None = None

    with WorkStore(work_db) as store:
        for spec in specs:
            if args.resume and store.is_weyl_batch_done(spec.batch_id):
                skipped += 1
                continue
            try:
                stats = materialize_weyl_bond_batch(
                    store,
                    spec,
                    max_rows=max_rows,
                    mirror_oloid=mirror,
                )
                store.weyl_batch_done(spec.batch_id, spec.wave_id, stats["rows_written"])
                completed += 1
                total_rows += stats["rows_written"]
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{spec.batch_id}: {exc}")
            if sleep_ms > 0:
                time.sleep(sleep_ms / 1000.0)
            if completed % 10 == 0:
                gc.collect()
        bonds_in_db = store.count_weyl_bonds()
        if args.all_quadrants or len(quadrant_plan) == QUADRANT_COUNT:
            tree_root = concatenate_quadrant_trees(store, tree_path="weyl_bond_result_tree.json")

    seed_after = SeedStore.packaged().verify()
    report = {
        "run_id": run_id,
        "work_db": str(work_db),
        "work_db_bytes": work_db.stat().st_size if work_db.exists() else 0,
        "wall_seconds": time.perf_counter() - t0,
        "batch_total": len(specs),
        "batch_completed": completed,
        "batch_skipped": skipped,
        "weyl_bond_rows": total_rows,
        "weyl_bonds_in_db": bonds_in_db,
        "seed_verify_before": seed_before,
        "seed_verify_after": seed_after,
        "errors": errors,
        "status": "fail" if errors else "pass",
        "resource_limits": {
            "max_rows_per_batch": max_rows,
            "sleep_ms": sleep_ms,
            "mirror_oloid": mirror,
        },
        "quadrant_plan": quadrant_plan,
        "result_tree": tree_root,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


def build_lattice_space_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lattice-forge-lattice-space",
        description="Lattice-space exhaustion (catalog, quadrant Weyl, E8 pod index, proof capture)",
    )
    parser.add_argument("--work-db", type=Path, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def run_lattice_space(argv: list[str] | None = None) -> int:
    args = build_lattice_space_parser().parse_args(argv)

    work_db = resolve_work_db(args.work_db)
    report_path = work_db.parent / "lattice_space_exhaustion_report.json"

    if args.dry_run:
        print(
            json.dumps(
                {
                    "work_db": str(work_db),
                    "phases": [
                        "lattice_catalog",
                        "weyl_quadrant_shards",
                        "e8_pod_assign",
                        "proof_capture",
                    ],
                    "weyl_batches": 200,
                    "e8_weyl_order": E8_WEYL_ORDER,
                },
                indent=2,
            )
        )
        return 0

    seed_before = SeedStore.packaged().verify()
    run_id = str(uuid.uuid4())

    with WorkStore(work_db) as store:
        result = run_lattice_space_exhaustion(
            store,
            resume=args.resume,
            max_rows_per_weyl_batch=int(os.environ.get("WEYL_BOND_MAX_ROWS_PER_BATCH", "64")),
            weyl_sleep_ms=int(os.environ.get("WEYL_BOND_BATCH_SLEEP_MS", "50")),
            mirror_oloid=os.environ.get("WEYL_BOND_MIRROR_OLOID", "1") != "0",
            max_library_needs=int(os.environ.get("LATTICE_SPACE_MAX_LIBRARY_NEEDS", "200")),
            max_pod_per_lattice=int(os.environ["LATTICE_SPACE_MAX_POD_PER_LATTICE"])
            if os.environ.get("LATTICE_SPACE_MAX_POD_PER_LATTICE")
            else None,
        )

    seed_after = SeedStore.packaged().verify()
    report = {
        "run_id": run_id,
        "status": "pass",
        "work_db": str(work_db),
        "work_db_bytes": work_db.stat().st_size if work_db.exists() else 0,
        "seed_verify_before": seed_before,
        "seed_verify_after": seed_after,
        **result,
    }
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))
    return 0


def main_backwalk() -> int:
    return run_backwalk()


def main_weyl_orchestrate() -> int:
    return run_weyl_orchestrate()


def main_lattice_space() -> int:
    return run_lattice_space()
