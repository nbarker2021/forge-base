from __future__ import annotations

import argparse
import json
from pathlib import Path

from .forge import Forge


def print_json(payload) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def forge_from_args(args: argparse.Namespace) -> Forge:
    return Forge.open(args.root)


def cmd_status(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).status())
    return 0


def cmd_verify_seed(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_seed()
    print_json(payload)
    return 0 if payload["result"].get("status") == "pass" else 1


def cmd_object(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).object(args.object_id))
    return 0


def cmd_can_close(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).can_close(args.source_id, args.target_id, args.max_depth))
    return 0


def cmd_future_cone(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).future_cone(args.object_id, args.max_depth))
    return 0


def cmd_exactness(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).exactness_dashboard(args.object_id))
    return 0


def cmd_terminal_tree(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).terminal_tree(args.terminal_id))
    return 0


def cmd_terminal_trees(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).terminal_trees())
    return 0


def cmd_verify_terminal_trees(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_terminal_trees()
    print_json(payload)
    return 0 if payload["result"].get("status") == "pass" else 1


def cmd_morphonics_model(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).morphonics_model())
    return 0


def cmd_verify_morphonics(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_morphonics()
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_morphon(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).rule30_morphon(args.max_depth, args.sample_count))
    return 0


def cmd_verify_rule30(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30(args.max_depth, args.sample_count)
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_vignettes(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).rule30_vignettes(args.max_order))
    return 0


def cmd_verify_rule30_vignettes(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_vignettes(args.max_order)
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_moving_frame(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).rule30_moving_frame(args.max_depth, args.max_order))
    return 0


def cmd_verify_rule30_moving_frame(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_moving_frame(args.max_depth, args.max_order)
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_color_chirality(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).rule30_color_chirality(args.max_depth, args.max_order))
    return 0


def cmd_verify_rule30_color_chirality(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_color_chirality(args.max_depth, args.max_order)
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_lagrangian(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).rule30_lagrangian(args.max_depth, args.max_order))
    return 0


def cmd_verify_rule30_lagrangian(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_lagrangian(args.max_depth, args.max_order)
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_lagrangian_trace(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).rule30_lagrangian_depth_trace(args.max_depth, args.max_order))
    return 0


def cmd_verify_rule30_lagrangian_trace(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_lagrangian_depth_trace(args.max_depth, args.max_order)
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_mandelbrot_scalar(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).rule30_mandelbrot_scalar(args.max_depth, args.max_order))
    return 0


def cmd_verify_rule30_mandelbrot_scalar(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_mandelbrot_scalar(args.max_depth, args.max_order)
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_reduced_alphabet(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).rule30_reduced_alphabet(args.max_depth, args.max_order))
    return 0


def cmd_verify_rule30_reduced_alphabet(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_reduced_alphabet(args.max_depth, args.max_order)
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_symmetry_environment(args: argparse.Namespace) -> int:
    print_json(
        forge_from_args(args).rule30_symmetry_environment(
            args.max_depth,
            args.max_period,
            args.max_order,
        )
    )
    return 0


def cmd_verify_rule30_symmetry_environment(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_symmetry_environment(
        args.max_depth,
        args.max_period,
        args.max_order,
    )
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_physics_method_stack(args: argparse.Namespace) -> int:
    print_json(
        forge_from_args(args).rule30_physics_method_stack(
            args.max_depth,
            args.max_period,
            args.max_order,
            args.max_block,
        )
    )
    return 0


def cmd_verify_rule30_physics_method_stack(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_physics_method_stack(
        args.max_depth,
        args.max_period,
        args.max_order,
        args.max_block,
    )
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_whole_integer_n_coverage(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).rule30_whole_integer_n_coverage(args.max_depth, args.max_order))
    return 0


def cmd_verify_rule30_whole_integer_n_coverage(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_whole_integer_n_coverage(args.max_depth, args.max_order)
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_readout_ribbon_machine(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).rule30_readout_ribbon_machine(args.max_depth, args.max_order))
    return 0


def cmd_verify_rule30_readout_ribbon_machine(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_readout_ribbon_machine(args.max_depth, args.max_order)
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_dihedral_block_hypervisor(args: argparse.Namespace) -> int:
    print_json(
        forge_from_args(args).rule30_dihedral_block_hypervisor(
            args.max_depth,
            args.block_size,
            args.max_order,
        )
    )
    return 0


def cmd_verify_rule30_dihedral_block_hypervisor(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_dihedral_block_hypervisor(
        args.max_depth,
        args.block_size,
        args.max_order,
    )
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_hypervisor_extension_tape(args: argparse.Namespace) -> int:
    print_json(
        forge_from_args(args).rule30_hypervisor_extension_tape(
            args.page_count,
            args.page_size,
            args.block_size,
            args.max_order,
        )
    )
    return 0


def cmd_verify_rule30_hypervisor_extension_tape(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_hypervisor_extension_tape(
        args.page_count,
        args.page_size,
        args.block_size,
        args.max_order,
    )
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_sheet_operator(args: argparse.Namespace) -> int:
    print_json(
        forge_from_args(args).rule30_sheet_operator(
            args.page_count,
            args.page_size,
            args.block_size,
            args.max_order,
        )
    )
    return 0


def cmd_verify_rule30_sheet_operator(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_sheet_operator(
        args.page_count,
        args.page_size,
        args.block_size,
        args.max_order,
    )
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_mandelbrot_field_address(args: argparse.Namespace) -> int:
    print_json(
        forge_from_args(args).rule30_mandelbrot_field_address(
            args.n,
            args.page_size,
            args.block_size,
            args.max_order,
        )
    )
    return 0


def cmd_verify_rule30_mandelbrot_field_address(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_mandelbrot_field_address(
        args.n,
        args.page_size,
        args.block_size,
        args.max_order,
    )
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_exit_trajectory(args: argparse.Namespace) -> int:
    print_json(
        forge_from_args(args).rule30_exit_trajectory(
            args.n,
            args.page_size,
            args.block_size,
            args.max_order,
        )
    )
    return 0


def cmd_verify_rule30_exit_trajectory(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_exit_trajectory(
        args.n,
        args.page_size,
        args.block_size,
        args.max_order,
    )
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_sheet_lift(args: argparse.Namespace) -> int:
    print_json(
        forge_from_args(args).rule30_sheet_lift(
            args.n,
            args.page_size,
            args.block_size,
            args.max_order,
        )
    )
    return 0


def cmd_verify_rule30_sheet_lift(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_sheet_lift(
        args.n,
        args.page_size,
        args.block_size,
        args.max_order,
    )
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_julia_resolution(args: argparse.Namespace) -> int:
    print_json(
        forge_from_args(args).rule30_julia_resolution(
            args.n,
            args.page_size,
            args.block_size,
            args.max_order,
        )
    )
    return 0


def cmd_verify_rule30_julia_resolution(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_julia_resolution(
        args.n,
        args.page_size,
        args.block_size,
        args.max_order,
    )
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_torsor_functor_term(args: argparse.Namespace) -> int:
    print_json(
        forge_from_args(args).rule30_torsor_functor_term(
            args.n,
            args.page_size,
            args.block_size,
            args.max_order,
        )
    )
    return 0


def cmd_verify_rule30_torsor_functor_term(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_torsor_functor_term(
        args.n,
        args.page_size,
        args.block_size,
        args.max_order,
    )
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def _oloid_config_from_args(args: argparse.Namespace) -> dict[str, object]:
    return {
        "axis_angle": args.axis_angle,
        "pattern": args.pattern,
        "shell_axis": args.shell_axis,
        "side_axis": args.side_axis,
        "shell_offset": args.shell_offset,
        "side_threshold": args.side_threshold,
        "parameterization": args.parameterization,
    }


def cmd_rule30_spinor_oloid(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).rule30_spinor_oloid_model(args.max_depth, args.max_order))
    return 0


def cmd_verify_rule30_spinor_oloid(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_spinor_oloid_model(args.max_depth, args.max_order)
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_oloid_winding(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).rule30_oloid_winding_from_n(args.n, **_oloid_config_from_args(args)))
    return 0


def cmd_rule30_oloid_antipode(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).rule30_oloid_antipodal_winding(args.n, **_oloid_config_from_args(args)))
    return 0


def cmd_rule30_oloid_scan(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).rule30_oloid_parameterization_scan(args.max_depth))
    return 0


def cmd_verify_rule30_oloid_winding(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_oloid_winding_from_n(
        args.max_depth,
        config=_oloid_config_from_args(args),
    )
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_verify_rule30_oloid_antipode(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_oloid_antipodal_winding(
        args.max_depth,
        config=_oloid_config_from_args(args),
    )
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_winding_number(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).rule30_winding_number_proof(args.max_depth, args.max_order))
    return 0


def cmd_verify_rule30_winding_number(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_winding_number_proof(args.max_depth, args.max_order)
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_nth_bit_expression(args: argparse.Namespace) -> int:
    print_json(
        forge_from_args(args).rule30_nth_bit_expression(
            args.n,
            args.page_size,
            args.block_size,
            args.max_order,
        )
    )
    return 0


def cmd_verify_rule30_nth_bit_expression(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_nth_bit_expression(
        args.n,
        args.page_size,
        args.block_size,
        args.max_order,
    )
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_rule30_proof_obligations(args: argparse.Namespace) -> int:
    print_json(
        forge_from_args(args).rule30_proof_obligations(
            args.max_depth,
            args.page_count,
            args.page_size,
            args.block_size,
            args.max_order,
        )
    )
    return 0


def cmd_verify_rule30_proof_obligations(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).verify_rule30_proof_obligations(
        args.max_depth,
        args.page_count,
        args.page_size,
        args.block_size,
        args.max_order,
    )
    print_json(payload)
    return 0 if str(payload["result"].get("status", "")).startswith("pass") else 1


def cmd_witnesses(args: argparse.Namespace) -> int:
    print_json(
        forge_from_args(args).witnesses(
            source_id=args.source_id,
            target_id=args.target_id,
            morphism_id=args.morphism_id,
        )
    )
    return 0


def cmd_obstructions(args: argparse.Namespace) -> int:
    print_json(forge_from_args(args).obstructions(source_id=args.source_id, target_id=args.target_id))
    return 0


def cmd_export_object(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).export_object(args.object_id, vector_limit=args.vector_limit)
    if args.out:
        Path(args.out).write_text(json.dumps(payload["result"], indent=2, sort_keys=True), encoding="utf-8")
        print_json({k: payload[k] for k in ["event_id", "query_id", "receipt_id", "answer", "evidence_level"]} | {"out": args.out})
    else:
        print_json(payload)
    return 0


def cmd_events(args: argparse.Namespace) -> int:
    print_json({"events": forge_from_args(args).latest_events(args.limit)})
    return 0


def cmd_receipts(args: argparse.Namespace) -> int:
    print_json({"receipts": forge_from_args(args).latest_receipts(args.limit)})
    return 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    payload = forge_from_args(args).snapshot(limit=args.limit)
    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print_json({"out": args.out})
    else:
        print_json(payload)
    return 0


def cmd_decomposition_verify(args: argparse.Namespace) -> int:
    from lattice_forge.decomposition import verify_all_theorems, verify_checkpoint_store

    theorems = verify_all_theorems(decomposition_depths=range(1, 129))
    checkpoints = verify_checkpoint_store(max_depth=args.max_depth)
    payload = {"theorems": theorems, "checkpoints": checkpoints}
    print_json(payload)
    ok = theorems.get("status") == "pass" and checkpoints.get("status") == "pass"
    return 0 if ok else 1


def cmd_ring2_run(args: argparse.Namespace) -> int:
    import subprocess
    import sys
    from pathlib import Path

    script = Path(__file__).resolve().parents[2] / "scripts" / "run_ring2_bundle.py"
    cmd = [sys.executable, str(script)]
    if args.quick:
        cmd.append("--quick")
    if args.include_monster:
        cmd.append("--include-monster")
    if getattr(args, "max_depth", 0) and args.max_depth > 0:
        cmd.extend(["--max-depth", str(args.max_depth)])
    if args.output:
        cmd.extend(["--output", args.output])
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


def cmd_ring1_ring2_pipeline(args: argparse.Namespace) -> int:
    import subprocess
    import sys
    from pathlib import Path

    script = Path(__file__).resolve().parents[2] / "scripts" / "run_ring1_ring2_pipeline.py"
    cmd = [sys.executable, str(script)]
    if args.quick:
        cmd.append("--quick")
    if args.skip_ring2:
        cmd.append("--skip-ring2")
    if args.include_monster:
        cmd.append("--include-monster")
    if args.output:
        cmd.extend(["--output", args.output])
    return subprocess.run(cmd, check=False).returncode


def cmd_ring2_status(_args: argparse.Namespace) -> int:
    from pathlib import Path

    pkg = Path(__file__).resolve().parents[2]
    paths = {
        "ring2_bundle": pkg / "proofs_report_ring2.json",
        "regimes": pkg / "proofs_report_regimes.json",
        "transport": pkg / "proofs_report_transport.json",
    }
    payload = {"reports": {}}
    for key, path in paths.items():
        if path.is_file():
            import json

            payload["reports"][key] = json.loads(path.read_text(encoding="utf-8"))
        else:
            payload["reports"][key] = {"missing": str(path)}
    print_json(payload)
    return 0


def cmd_empirical_materialize(_args: argparse.Namespace) -> int:
    import subprocess
    import sys
    from pathlib import Path

    script = Path(__file__).resolve().parents[2] / "scripts" / "materialize_empirical_platforms.py"
    proc = subprocess.run([sys.executable, str(script)], check=False)
    return proc.returncode


def cmd_empirical_run(args: argparse.Namespace) -> int:
    from lattice_forge.empirical.runner import run_claim_platform, run_empirical_matrix

    mode = "quick" if args.quick else ("exhaustive" if args.exhaustive else "standard")
    if args.claim:
        row = run_claim_platform(args.claim, exhaustion_mode=mode)
        print_json(row)
        return 0 if row.get("status") != "fail" else 1
    out = Path(args.output) if args.output else None
    report = run_empirical_matrix(exhaustion_mode=mode, output=out)
    print_json(report)
    return 0 if report.get("overall_status") == "pass" else 1


def _cmd_mckay_matrices(print_json_fn, *, verify_only: bool = False) -> int:
    from lattice_forge.mckay_matrix_tables import verify_mckay_matrix_bootstrap

    payload = verify_mckay_matrix_bootstrap()
    print_json_fn(payload)
    return 0 if payload.get("status") == "pass" else 1


def _cmd_mckay_export(args: argparse.Namespace) -> int:
    from lattice_forge.mckay_matrix_tables import export_matrix_catalog
    from lattice_forge.paths import backwalk_data_dir

    out = args.out or (backwalk_data_dir() / "mckay_matrix_catalog.json")
    path = export_matrix_catalog(out)
    print_json({"out": str(path), "status": "ok"})
    return 0


def cmd_falsify(args: argparse.Namespace) -> int:
    if args.tier_a:
        from lattice_forge.falsify import run_tier_a

        payload = run_tier_a(max_depth=args.max_depth, quick=args.quick)
        print_json(payload)
        return 0 if payload.get("overall_status") == "pass" else 1
    if args.tier_b:
        from lattice_forge.falsify import run_tier_b

        payload = run_tier_b(
            max_period=args.max_period,
            sample_depth=args.sample_depth,
            density_max_depth=args.density_max_depth,
        )
        print_json(payload)
        return 0
    raise SystemExit("Specify a falsification tier: --tier-a or --tier-b")


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
        from .server import create_app
    except ImportError as exc:
        raise SystemExit("Install server dependencies with: pip install lattice-forge[server]") from exc
    uvicorn.run(create_app(args.root), host=args.host, port=args.port)
    return 0


def add_oloid_config_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--axis-angle", type=float, default=1.5707963267948966)
    parser.add_argument("--pattern", default="alternating_xy")
    parser.add_argument("--shell-axis", default="z")
    parser.add_argument("--side-axis", default="x")
    parser.add_argument("--shell-offset", type=float, default=0.0)
    parser.add_argument("--side-threshold", type=float, default=0.05)
    parser.add_argument("--parameterization", default="identity")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lattice-forge", description="Lattice Forge admissibility engine")
    parser.add_argument("--root", help="Project root for .lattice_forge overlay state")
    sub = parser.add_subparsers(required=True, dest="command")

    p = sub.add_parser("status", help="Show seed and overlay status")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("verify-seed", help="Verify bundled seed database")
    p.set_defaults(func=cmd_verify_seed)

    p = sub.add_parser("object", help="Inspect one lattice/morphism object")
    p.add_argument("object_id")
    p.set_defaults(func=cmd_object)

    p = sub.add_parser("can-close", help="Ask whether source can close into target")
    p.add_argument("source_id")
    p.add_argument("target_id")
    p.add_argument("--max-depth", type=int, default=10)
    p.set_defaults(func=cmd_can_close)

    p = sub.add_parser("future-cone", help="Query reachable futures for an object")
    p.add_argument("object_id")
    p.add_argument("--max-depth", type=int, default=8)
    p.set_defaults(func=cmd_future_cone)

    p = sub.add_parser("exactness", help="Show exact/computed/template/conceptual support")
    p.add_argument("object_id")
    p.set_defaults(func=cmd_exactness)

    p = sub.add_parser("terminal-tree", help="Generate a terminal form's canonical composition tree")
    p.add_argument("terminal_id")
    p.set_defaults(func=cmd_terminal_tree)

    p = sub.add_parser("terminal-trees", help="List canonical terminal tree summaries for all 24 terminals")
    p.set_defaults(func=cmd_terminal_trees)

    p = sub.add_parser("verify-terminal-trees", help="Verify all 24 terminal composition trees")
    p.set_defaults(func=cmd_verify_terminal_trees)

    p = sub.add_parser("morphonics-model", help="Show the executable Morphonics v0.2 schema ledger")
    p.set_defaults(func=cmd_morphonics_model)

    p = sub.add_parser("verify-morphonics", help="Validate the Morphonics v0.2 schema ledger")
    p.set_defaults(func=cmd_verify_morphonics)

    p = sub.add_parser("rule30-morphon", help="Run the hardened Rule 30 Morphon harness")
    p.add_argument("--max-depth", type=int, default=7)
    p.add_argument("--sample-count", type=int, default=512)
    p.set_defaults(func=cmd_rule30_morphon)

    p = sub.add_parser("verify-rule30", help="Verify the hardened Rule 30 Morphon harness")
    p.add_argument("--max-depth", type=int, default=7)
    p.add_argument("--sample-count", type=int, default=512)
    p.set_defaults(func=cmd_verify_rule30)

    p = sub.add_parser("rule30-vignettes", help="Generate the Rule 30 rotated-cone vignette composition algebra")
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_vignettes)

    p = sub.add_parser("verify-rule30-vignettes", help="Verify the Rule 30 vignette composition algebra")
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_vignettes)

    p = sub.add_parser("rule30-moving-frame", help="Run the Rule 30 moving beam-frame admissibility filter")
    p.add_argument("--max-depth", type=int, default=12)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_moving_frame)

    p = sub.add_parser("verify-rule30-moving-frame", help="Verify the Rule 30 moving beam-frame filter")
    p.add_argument("--max-depth", type=int, default=12)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_moving_frame)

    p = sub.add_parser("rule30-color-chirality", help="Generate the Rule 30 color/chirality codeword cipher")
    p.add_argument("--max-depth", type=int, default=12)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_color_chirality)

    p = sub.add_parser("verify-rule30-color-chirality", help="Verify the Rule 30 color/chirality codeword cipher")
    p.add_argument("--max-depth", type=int, default=12)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_color_chirality)

    p = sub.add_parser("rule30-lagrangian", help="Generate the Rule 30 discrete Lagrangian/NSL action ledger")
    p.add_argument("--max-depth", type=int, default=12)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_lagrangian)

    p = sub.add_parser("verify-rule30-lagrangian", help="Verify the Rule 30 discrete Lagrangian/NSL action ledger")
    p.add_argument("--max-depth", type=int, default=12)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_lagrangian)

    p = sub.add_parser("rule30-lagrangian-trace", help="Run the Rule 30 center-column Lagrangian depth trace")
    p.add_argument("--max-depth", type=int, default=256)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_lagrangian_trace)

    p = sub.add_parser("verify-rule30-lagrangian-trace", help="Verify the Rule 30 center-column Lagrangian depth trace")
    p.add_argument("--max-depth", type=int, default=256)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_lagrangian_trace)

    p = sub.add_parser("rule30-mandelbrot-scalar", help="Run the Rule 30 Mandelbrot/Julia boundary scalar map")
    p.add_argument("--max-depth", type=int, default=256)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_mandelbrot_scalar)

    p = sub.add_parser("verify-rule30-mandelbrot-scalar", help="Verify the Rule 30 Mandelbrot/Julia boundary scalar map")
    p.add_argument("--max-depth", type=int, default=256)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_mandelbrot_scalar)

    p = sub.add_parser("rule30-reduced-alphabet", help="Run the Rule 30 reduced alphabet rule catalog")
    p.add_argument("--max-depth", type=int, default=1024)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_reduced_alphabet)

    p = sub.add_parser("verify-rule30-reduced-alphabet", help="Verify the Rule 30 reduced alphabet rule catalog")
    p.add_argument("--max-depth", type=int, default=1024)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_reduced_alphabet)

    p = sub.add_parser("rule30-symmetry-environment", help="Run the Rule 30 U1/SU2/SU3 finite symmetry environment")
    p.add_argument("--max-depth", type=int, default=1024)
    p.add_argument("--max-period", type=int, default=128)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_symmetry_environment)

    p = sub.add_parser(
        "verify-rule30-symmetry-environment",
        help="Verify the Rule 30 U1/SU2/SU3 finite symmetry environment",
    )
    p.add_argument("--max-depth", type=int, default=1024)
    p.add_argument("--max-period", type=int, default=128)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_symmetry_environment)

    p = sub.add_parser("rule30-physics-stack", help="Run six finite physics/method diagnostics over Rule 30")
    p.add_argument("--max-depth", type=int, default=1024)
    p.add_argument("--max-period", type=int, default=128)
    p.add_argument("--max-order", type=int, default=4)
    p.add_argument("--max-block", type=int, default=8)
    p.set_defaults(func=cmd_rule30_physics_method_stack)

    p = sub.add_parser("verify-rule30-physics-stack", help="Verify the six-method Rule 30 physics stack")
    p.add_argument("--max-depth", type=int, default=1024)
    p.add_argument("--max-period", type=int, default=128)
    p.add_argument("--max-order", type=int, default=4)
    p.add_argument("--max-block", type=int, default=8)
    p.set_defaults(func=cmd_verify_rule30_physics_method_stack)

    p = sub.add_parser("rule30-n-coverage", help="Test whole-integer N scalar coverage for Rule 30")
    p.add_argument("--max-depth", type=int, default=4096)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_whole_integer_n_coverage)

    p = sub.add_parser("verify-rule30-n-coverage", help="Verify whole-integer N scalar coverage for Rule 30")
    p.add_argument("--max-depth", type=int, default=4096)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_whole_integer_n_coverage)

    p = sub.add_parser("rule30-readout-ribbon", help="Run the Rule 30 finite readout-ribbon machine")
    p.add_argument("--max-depth", type=int, default=4096)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_readout_ribbon_machine)

    p = sub.add_parser("verify-rule30-readout-ribbon", help="Verify the Rule 30 finite readout-ribbon machine")
    p.add_argument("--max-depth", type=int, default=4096)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_readout_ribbon_machine)

    p = sub.add_parser("rule30-dihedral-hypervisor", help="Run the Rule 30 8-step dihedral block hypervisor")
    p.add_argument("--max-depth", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_dihedral_block_hypervisor)

    p = sub.add_parser(
        "verify-rule30-dihedral-hypervisor",
        help="Verify the Rule 30 8-step dihedral block hypervisor",
    )
    p.add_argument("--max-depth", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_dihedral_block_hypervisor)

    p = sub.add_parser("rule30-extension-tape", help="Run hypervisor page-extension tape over Rule 30")
    p.add_argument("--page-count", type=int, default=2)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_hypervisor_extension_tape)

    p = sub.add_parser("verify-rule30-extension-tape", help="Verify hypervisor page-extension tape over Rule 30")
    p.add_argument("--page-count", type=int, default=2)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_hypervisor_extension_tape)

    p = sub.add_parser("rule30-sheet-operator", help="Run the finite Rule 30 relative sheet operator")
    p.add_argument("--page-count", type=int, default=2)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_sheet_operator)

    p = sub.add_parser("verify-rule30-sheet-operator", help="Verify the finite Rule 30 relative sheet operator")
    p.add_argument("--page-count", type=int, default=2)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_sheet_operator)

    p = sub.add_parser("rule30-field-address", help="Resolve N into the CA-induced Mandelbrot field address")
    p.add_argument("n", type=int)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_mandelbrot_field_address)

    p = sub.add_parser("verify-rule30-field-address", help="Verify the CA-induced Mandelbrot field address")
    p.add_argument("n", type=int)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_mandelbrot_field_address)

    p = sub.add_parser("rule30-exit-trajectory", help="Resolve N to its Julia exit trajectory")
    p.add_argument("n", type=int)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_exit_trajectory)

    p = sub.add_parser("verify-rule30-exit-trajectory", help="Verify the Julia exit trajectory")
    p.add_argument("n", type=int)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_exit_trajectory)

    p = sub.add_parser("rule30-sheet-lift", help="Lift N onto its k-th sheet in the Julia sheet tower")
    p.add_argument("n", type=int)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_sheet_lift)

    p = sub.add_parser("verify-rule30-sheet-lift", help="Verify N's k->k+1 sheet lift")
    p.add_argument("n", type=int)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_sheet_lift)

    p = sub.add_parser("rule30-julia-resolution", help="Resolve N through field address, exit trajectory, and sheet lift")
    p.add_argument("n", type=int)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_julia_resolution)

    p = sub.add_parser("verify-rule30-julia-resolution", help="Verify N's Julia sheet resolution")
    p.add_argument("n", type=int)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_julia_resolution)

    p = sub.add_parser("rule30-torsor-functor", help="Resolve N with the Rule 30 torsor/functor term")
    p.add_argument("n", type=int)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_torsor_functor_term)

    p = sub.add_parser("verify-rule30-torsor-functor", help="Verify N's torsor/functor coherence")
    p.add_argument("n", type=int)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_torsor_functor_term)

    p = sub.add_parser("rule30-spinor-oloid", help="Run the Rule 30 spinor/Oloid bridge ledger")
    p.add_argument("--max-depth", type=int, default=4096)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_spinor_oloid)

    p = sub.add_parser("verify-rule30-spinor-oloid", help="Verify the Rule 30 spinor/Oloid bridge ledger")
    p.add_argument("--max-depth", type=int, default=4096)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_spinor_oloid)

    p = sub.add_parser("rule30-oloid-winding", help="Emit one Rule 30 Oloid winding witness for N")
    p.add_argument("n", type=int)
    add_oloid_config_args(p)
    p.set_defaults(func=cmd_rule30_oloid_winding)

    p = sub.add_parser("rule30-oloid-antipode", help="Emit one Rule 30 +N/-N counter-sheet Oloid witness")
    p.add_argument("n", type=int)
    add_oloid_config_args(p)
    p.set_defaults(func=cmd_rule30_oloid_antipode)

    p = sub.add_parser("rule30-oloid-scan", help="Scan compact Oloid parameterizations against the center bar")
    p.add_argument("--max-depth", type=int, default=256)
    p.set_defaults(func=cmd_rule30_oloid_scan)

    p = sub.add_parser("verify-rule30-oloid-winding", help="Verify an Oloid winding parameterization")
    p.add_argument("--max-depth", type=int, default=256)
    add_oloid_config_args(p)
    p.set_defaults(func=cmd_verify_rule30_oloid_winding)

    p = sub.add_parser("verify-rule30-oloid-antipode", help="Verify the +N/-N counter-sheet Oloid selector")
    p.add_argument("--max-depth", type=int, default=256)
    add_oloid_config_args(p)
    p.set_defaults(func=cmd_verify_rule30_oloid_antipode)

    p = sub.add_parser("rule30-winding-number", help="Build the bounded Rule 30 winding-number witness")
    p.add_argument("--max-depth", type=int, default=4096)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_winding_number)

    p = sub.add_parser("verify-rule30-winding-number", help="Verify the bounded Rule 30 winding-number witness")
    p.add_argument("--max-depth", type=int, default=4096)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_winding_number)

    p = sub.add_parser("rule30-nth-bit", help="Emit the Rule 30 nth-bit reduced scalar expression")
    p.add_argument("n", type=int)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_nth_bit_expression)

    p = sub.add_parser("verify-rule30-nth-bit", help="Verify a Rule 30 nth-bit reduced scalar expression")
    p.add_argument("n", type=int)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_nth_bit_expression)

    p = sub.add_parser("rule30-proof-obligations", help="Build the Rule 30 submission proof-obligation ledger")
    p.add_argument("--max-depth", type=int, default=4096)
    p.add_argument("--page-count", type=int, default=2)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_rule30_proof_obligations)

    p = sub.add_parser("verify-rule30-proof-obligations", help="Verify the Rule 30 proof-obligation ledger")
    p.add_argument("--max-depth", type=int, default=4096)
    p.add_argument("--page-count", type=int, default=2)
    p.add_argument("--page-size", type=int, default=4096)
    p.add_argument("--block-size", type=int, default=8)
    p.add_argument("--max-order", type=int, default=4)
    p.set_defaults(func=cmd_verify_rule30_proof_obligations)

    p = sub.add_parser("witnesses", help="Query morphism witnesses")
    p.add_argument("--source-id")
    p.add_argument("--target-id")
    p.add_argument("--morphism-id")
    p.set_defaults(func=cmd_witnesses)

    p = sub.add_parser("obstructions", help="Query closure obstructions")
    p.add_argument("--source-id")
    p.add_argument("--target-id")
    p.set_defaults(func=cmd_obstructions)

    p = sub.add_parser("export-object", help="Export an object bundle")
    p.add_argument("object_id")
    p.add_argument("--vector-limit", type=int, default=12)
    p.add_argument("--out")
    p.set_defaults(func=cmd_export_object)

    p = sub.add_parser("events", help="List overlay events")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_events)

    p = sub.add_parser("receipts", help="List overlay receipts")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_receipts)

    p = sub.add_parser("snapshot", help="Export seed/overlay snapshot")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--out")
    p.set_defaults(func=cmd_snapshot)

    dec = sub.add_parser("decomposition", help="Rule 30 decomposition paper commands")
    dec_sub = dec.add_subparsers(required=True, dest="decomposition_command")
    dv = dec_sub.add_parser("verify", help="Verify vendored decomposition paper claims")
    dv.add_argument("--max-depth", type=int, default=512)
    dv.set_defaults(func=cmd_decomposition_verify)

    r2 = sub.add_parser("ring2", help="Ring 2 bundle (regimes + decomposition + transport)")
    r2_sub = r2.add_subparsers(required=True, dest="ring2_command")
    r2_run = r2_sub.add_parser("run", help="Run full Ring 2 proof bundle")
    r2_run.add_argument("--quick", action="store_true")
    r2_run.add_argument("--include-monster", action="store_true")
    r2_run.add_argument("--max-depth", type=int, default=0, help="0 = script default 4096")
    r2_run.add_argument("--output", help="Bundle JSON path")
    r2_run.set_defaults(func=cmd_ring2_run)
    r2_st = r2_sub.add_parser("status", help="Print latest Ring 2 report files if present")
    r2_st.set_defaults(func=cmd_ring2_status)

    r12 = sub.add_parser("pipeline", help="Ring 1 then Ring 2 (prize-core gate first)")
    r12_sub = r12.add_subparsers(required=True, dest="pipeline_command")
    r12_run = r12_sub.add_parser("ring1-ring2", help="Run run_all_proofs, audit, falsify tier-A, ring2 bundle")
    r12_run.add_argument("--quick", action="store_true")
    r12_run.add_argument("--skip-ring2", action="store_true")
    r12_run.add_argument("--include-monster", action="store_true")
    r12_run.add_argument("--output", default="proofs_report_ring1_ring2.json")
    r12_run.set_defaults(func=cmd_ring1_ring2_pipeline)

    emp = sub.add_parser("empirical", help="Per-claim empirical testing platforms")
    emp_sub = emp.add_subparsers(required=True, dest="empirical_command")
    em_m = emp_sub.add_parser("materialize", help="Rebuild platforms.manifest.jsonl from claims registry")
    em_m.set_defaults(func=cmd_empirical_materialize)
    em_r = emp_sub.add_parser("run", help="Run empirical matrix or single claim")
    em_r.add_argument("--claim", help="Single claim_id")
    em_r.add_argument("--quick", action="store_true")
    em_r.add_argument("--exhaustive", action="store_true")
    em_r.add_argument("--output", help="JSON report path (default empirical_matrix_report.json)")
    em_r.set_defaults(func=cmd_empirical_run)

    fal = sub.add_parser("falsify", help="Machine falsification for prize-core claims")
    fal.add_argument("--tier-a", action="store_true", help="Run Tier A breaks B-T1..B-decomp + B-WITNESS")
    fal.add_argument("--tier-b", action="store_true", help="Optional Tier B JSON report (non-blocking)")
    fal.add_argument("--quick", action="store_true", help="Use reduced depth windows (default for CI)")
    fal.add_argument("--max-depth", type=int, default=256, help="Depth for chart/decomposition checks")
    fal.add_argument("--max-period", type=int, default=128, help="Tier B period search cap")
    fal.add_argument("--sample-depth", type=int, default=512, help="Tier B period sample depth")
    fal.add_argument("--density-max-depth", type=int, default=256, help="Tier B density window depth")
    fal.set_defaults(func=cmd_falsify)

    bw = sub.add_parser("backwalk", help="Niemeier backward-category builder")
    bw_sub = bw.add_subparsers(required=True, dest="backwalk_command")
    bw_run = bw_sub.add_parser("run", help="Pilot, full24, or exceptional-only phase")
    bw_run.add_argument("--phase", choices=("pilot", "full24", "exceptional-only"), default="pilot")
    bw_run.add_argument("--terminals", default=None)
    bw_run.add_argument("--work-db", type=Path, default=None)
    bw_run.add_argument("--resume", action="store_true")
    bw_run.add_argument("--include-exceptionals", default=None)
    bw_run.add_argument("--involution-limit", type=int, default=None)

    def _cmd_backwalk_run(args: argparse.Namespace) -> int:
        from lattice_forge.backwalk.runner import run_backwalk

        argv = ["--phase", args.phase]
        if args.terminals:
            argv.extend(["--terminals", args.terminals])
        if args.work_db:
            argv.extend(["--work-db", str(args.work_db)])
        if args.resume:
            argv.append("--resume")
        if args.include_exceptionals:
            argv.extend(["--include-exceptionals", args.include_exceptionals])
        if args.involution_limit is not None:
            argv.extend(["--involution-limit", str(args.involution_limit)])
        return run_backwalk(argv)

    bw_run.set_defaults(func=_cmd_backwalk_run)

    wb = sub.add_parser("weyl-bond", help="Quadrant-sharded dual Weyl-bond orchestrator")
    wb_sub = wb.add_subparsers(required=True, dest="weyl_command")
    wb_run = wb_sub.add_parser("run", help="Run Weyl bond batches (default: all quadrants)")
    wb_run.add_argument("--work-db", type=Path, default=None)
    wb_run.add_argument("--resume", action="store_true")
    wb_run.add_argument("--quadrant", type=int, default=None)
    wb_run.add_argument("--all-quadrants", action="store_true")
    wb_run.add_argument("--concat-only", action="store_true")
    wb_run.add_argument("--dry-run", action="store_true")

    def _cmd_weyl_run(args: argparse.Namespace) -> int:
        from lattice_forge.backwalk.runner import run_weyl_orchestrate

        argv: list[str] = []
        if args.work_db:
            argv.extend(["--work-db", str(args.work_db)])
        if args.resume:
            argv.append("--resume")
        if args.quadrant is not None:
            argv.extend(["--quadrant", str(args.quadrant)])
        if args.all_quadrants:
            argv.append("--all-quadrants")
        if args.concat_only:
            argv.append("--concat-only")
        if args.dry_run:
            argv.append("--dry-run")
        return run_weyl_orchestrate(argv)

    wb_run.set_defaults(func=_cmd_weyl_run)

    ls = sub.add_parser("lattice-space", help="Lattice-space exhaustion job")
    ls_sub = ls.add_subparsers(required=True, dest="lattice_space_command")
    ls_run = ls_sub.add_parser("run", help="Catalog, Weyl shards, E8 pod index, proof capture")
    ls_run.add_argument("--work-db", type=Path, default=None)
    ls_run.add_argument("--resume", action="store_true")
    ls_run.add_argument("--dry-run", action="store_true")

    def _cmd_lattice_space_run(args: argparse.Namespace) -> int:
        from lattice_forge.backwalk.runner import run_lattice_space

        argv: list[str] = []
        if args.work_db:
            argv.extend(["--work-db", str(args.work_db)])
        if args.resume:
            argv.append("--resume")
        if args.dry_run:
            argv.append("--dry-run")
        return run_lattice_space(argv)

    ls_run.set_defaults(func=_cmd_lattice_space_run)

    mck = sub.add_parser("mckay-matrices", help="McKay-Thompson j-matrix bootstrap tables (5/7/9)")
    mck_sub = mck.add_subparsers(required=True, dest="mckay_command")
    mck_verify = mck_sub.add_parser("verify", help="Run bootstrap matrix proof harness")
    mck_verify.set_defaults(
        func=lambda _a: _cmd_mckay_matrices(print_json, verify_only=True),
    )
    mck_export = mck_sub.add_parser("export", help="Write global JSON catalog")
    mck_export.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default: ./mckay_matrix_catalog.json)",
    )
    mck_export.set_defaults(func=_cmd_mckay_export)

    p = sub.add_parser("serve", help="Start optional FastAPI server")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
