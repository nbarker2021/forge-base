from __future__ import annotations

from pathlib import Path

from .forge import Forge


def create_app(root: str | Path | None = None):
    """Create the optional FastAPI app.

    FastAPI is an optional dependency. Install with: lattice-forge[server].
    """
    try:
        from fastapi import Body, FastAPI, Query
    except ImportError as exc:  # pragma: no cover - exercised by CLI smoke without extra
        raise RuntimeError("Install server dependencies with: pip install lattice-forge[server]") from exc

    forge = Forge.open(root)
    cache_root = Path(root) if root is not None else Path.cwd()
    app = FastAPI(
        title="Lattice Forge",
        version="0.1.0",
        description="Local lattice/morphism admissibility API.",
    )

    @app.get("/health")
    def health():
        return {"ok": True, "service": "lattice-forge"}

    @app.get("/status")
    def status():
        return forge.status()

    @app.get("/objects/{object_id}")
    def object_(object_id: str):
        return forge.object(object_id)

    @app.post("/can-close")
    def can_close(req: dict = Body(...)):
        return forge.can_close(
            str(req["source_id"]),
            str(req["target_id"]),
            max_depth=int(req.get("max_depth", 10)),
        )

    @app.get("/future-cone/{object_id}")
    def future_cone(object_id: str, max_depth: int = 8):
        return forge.future_cone(object_id, max_depth=max_depth)

    @app.get("/exactness/{object_id}")
    def exactness(object_id: str):
        return forge.exactness_dashboard(object_id)

    @app.get("/terminal-tree/{terminal_id}")
    def terminal_tree(terminal_id: str):
        return forge.terminal_tree(terminal_id)

    @app.get("/terminal-trees")
    def terminal_trees():
        return forge.terminal_trees()

    @app.get("/terminal-trees/verify")
    def verify_terminal_trees():
        return forge.verify_terminal_trees()

    @app.get("/morphonics/model")
    def morphonics_model():
        return forge.morphonics_model()

    @app.get("/morphonics/verify")
    def verify_morphonics():
        return forge.verify_morphonics()

    @app.get("/rule30/morphon")
    def rule30_morphon(max_depth: int = 7, sample_count: int = 512):
        return forge.rule30_morphon(max_depth=max_depth, sample_count=sample_count)

    @app.get("/rule30/verify")
    def verify_rule30(max_depth: int = 7, sample_count: int = 512):
        return forge.verify_rule30(max_depth=max_depth, sample_count=sample_count)

    @app.get("/rule30/vignettes")
    def rule30_vignettes(max_order: int = 4):
        return forge.rule30_vignettes(max_order=max_order)

    @app.get("/rule30/vignettes/verify")
    def verify_rule30_vignettes(max_order: int = 4):
        return forge.verify_rule30_vignettes(max_order=max_order)

    @app.get("/rule30/moving-frame")
    def rule30_moving_frame(max_depth: int = 12, max_order: int = 4):
        return forge.rule30_moving_frame(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/moving-frame/verify")
    def verify_rule30_moving_frame(max_depth: int = 12, max_order: int = 4):
        return forge.verify_rule30_moving_frame(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/color-chirality")
    def rule30_color_chirality(max_depth: int = 12, max_order: int = 4):
        return forge.rule30_color_chirality(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/color-chirality/verify")
    def verify_rule30_color_chirality(max_depth: int = 12, max_order: int = 4):
        return forge.verify_rule30_color_chirality(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/lagrangian")
    def rule30_lagrangian(max_depth: int = 12, max_order: int = 4):
        return forge.rule30_lagrangian(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/lagrangian/verify")
    def verify_rule30_lagrangian(max_depth: int = 12, max_order: int = 4):
        return forge.verify_rule30_lagrangian(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/lagrangian-trace")
    def rule30_lagrangian_trace(max_depth: int = 256, max_order: int = 4):
        return forge.rule30_lagrangian_depth_trace(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/lagrangian-trace/verify")
    def verify_rule30_lagrangian_trace(max_depth: int = 256, max_order: int = 4):
        return forge.verify_rule30_lagrangian_depth_trace(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/mandelbrot-scalar")
    def rule30_mandelbrot_scalar(max_depth: int = 256, max_order: int = 4):
        return forge.rule30_mandelbrot_scalar(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/mandelbrot-scalar/verify")
    def verify_rule30_mandelbrot_scalar(max_depth: int = 256, max_order: int = 4):
        return forge.verify_rule30_mandelbrot_scalar(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/reduced-alphabet")
    def rule30_reduced_alphabet(max_depth: int = 1024, max_order: int = 4):
        return forge.rule30_reduced_alphabet(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/reduced-alphabet/verify")
    def verify_rule30_reduced_alphabet(max_depth: int = 1024, max_order: int = 4):
        return forge.verify_rule30_reduced_alphabet(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/symmetry-environment")
    def rule30_symmetry_environment(max_depth: int = 1024, max_period: int = 128, max_order: int = 4):
        return forge.rule30_symmetry_environment(
            max_depth=max_depth,
            max_period=max_period,
            max_order=max_order,
        )

    @app.get("/rule30/symmetry-environment/verify")
    def verify_rule30_symmetry_environment(max_depth: int = 1024, max_period: int = 128, max_order: int = 4):
        return forge.verify_rule30_symmetry_environment(
            max_depth=max_depth,
            max_period=max_period,
            max_order=max_order,
        )

    @app.get("/rule30/physics-stack")
    def rule30_physics_method_stack(
        max_depth: int = 1024,
        max_period: int = 128,
        max_order: int = 4,
        max_block: int = 8,
    ):
        return forge.rule30_physics_method_stack(
            max_depth=max_depth,
            max_period=max_period,
            max_order=max_order,
            max_block=max_block,
        )

    @app.get("/rule30/physics-stack/verify")
    def verify_rule30_physics_method_stack(
        max_depth: int = 1024,
        max_period: int = 128,
        max_order: int = 4,
        max_block: int = 8,
    ):
        return forge.verify_rule30_physics_method_stack(
            max_depth=max_depth,
            max_period=max_period,
            max_order=max_order,
            max_block=max_block,
        )

    @app.get("/rule30/n-coverage")
    def rule30_whole_integer_n_coverage(max_depth: int = 4096, max_order: int = 4):
        return forge.rule30_whole_integer_n_coverage(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/n-coverage/verify")
    def verify_rule30_whole_integer_n_coverage(max_depth: int = 4096, max_order: int = 4):
        return forge.verify_rule30_whole_integer_n_coverage(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/readout-ribbon")
    def rule30_readout_ribbon_machine(max_depth: int = 4096, max_order: int = 4):
        return forge.rule30_readout_ribbon_machine(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/readout-ribbon/verify")
    def verify_rule30_readout_ribbon_machine(max_depth: int = 4096, max_order: int = 4):
        return forge.verify_rule30_readout_ribbon_machine(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/dihedral-hypervisor")
    def rule30_dihedral_block_hypervisor(max_depth: int = 4096, block_size: int = 8, max_order: int = 4):
        return forge.rule30_dihedral_block_hypervisor(
            max_depth=max_depth,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/dihedral-hypervisor/verify")
    def verify_rule30_dihedral_block_hypervisor(max_depth: int = 4096, block_size: int = 8, max_order: int = 4):
        return forge.verify_rule30_dihedral_block_hypervisor(
            max_depth=max_depth,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/extension-tape")
    def rule30_hypervisor_extension_tape(
        page_count: int = 2,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ):
        return forge.rule30_hypervisor_extension_tape(
            page_count=page_count,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/extension-tape/verify")
    def verify_rule30_hypervisor_extension_tape(
        page_count: int = 2,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ):
        return forge.verify_rule30_hypervisor_extension_tape(
            page_count=page_count,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/sheet-operator")
    def rule30_sheet_operator(
        page_count: int = 2,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ):
        return forge.rule30_sheet_operator(
            page_count=page_count,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/sheet-operator/verify")
    def verify_rule30_sheet_operator(
        page_count: int = 2,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ):
        return forge.verify_rule30_sheet_operator(
            page_count=page_count,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/field-address/{n}")
    def rule30_mandelbrot_field_address(n: int, page_size: int = 4096, block_size: int = 8, max_order: int = 4):
        return forge.rule30_mandelbrot_field_address(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/field-address/{n}/verify")
    def verify_rule30_mandelbrot_field_address(
        n: int,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ):
        return forge.verify_rule30_mandelbrot_field_address(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/exit-trajectory/{n}")
    def rule30_exit_trajectory(n: int, page_size: int = 4096, block_size: int = 8, max_order: int = 4):
        return forge.rule30_exit_trajectory(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/exit-trajectory/{n}/verify")
    def verify_rule30_exit_trajectory(n: int, page_size: int = 4096, block_size: int = 8, max_order: int = 4):
        return forge.verify_rule30_exit_trajectory(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/sheet-lift/{n}")
    def rule30_sheet_lift(n: int, page_size: int = 4096, block_size: int = 8, max_order: int = 4):
        return forge.rule30_sheet_lift(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/sheet-lift/{n}/verify")
    def verify_rule30_sheet_lift(n: int, page_size: int = 4096, block_size: int = 8, max_order: int = 4):
        return forge.verify_rule30_sheet_lift(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/julia-resolution/{n}")
    def rule30_julia_resolution(n: int, page_size: int = 4096, block_size: int = 8, max_order: int = 4):
        return forge.rule30_julia_resolution(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/julia-resolution/{n}/verify")
    def verify_rule30_julia_resolution(n: int, page_size: int = 4096, block_size: int = 8, max_order: int = 4):
        return forge.verify_rule30_julia_resolution(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/torsor-functor/{n}")
    def rule30_torsor_functor_term(n: int, page_size: int = 4096, block_size: int = 8, max_order: int = 4):
        return forge.rule30_torsor_functor_term(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/torsor-functor/{n}/verify")
    def verify_rule30_torsor_functor_term(n: int, page_size: int = 4096, block_size: int = 8, max_order: int = 4):
        return forge.verify_rule30_torsor_functor_term(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/spinor-oloid")
    def rule30_spinor_oloid_model(max_depth: int = 4096, max_order: int = 4):
        return forge.rule30_spinor_oloid_model(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/spinor-oloid/verify")
    def verify_rule30_spinor_oloid_model(max_depth: int = 4096, max_order: int = 4):
        return forge.verify_rule30_spinor_oloid_model(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/oloid-winding/verify")
    def verify_rule30_oloid_winding_from_n(
        max_depth: int = 256,
        axis_angle: float = 1.5707963267948966,
        pattern: str = "alternating_xy",
        shell_axis: str = "z",
        side_axis: str = "x",
        shell_offset: float = 0.0,
        side_threshold: float = 0.05,
        parameterization: str = "identity",
    ):
        return forge.verify_rule30_oloid_winding_from_n(
            max_depth=max_depth,
            config={
                "axis_angle": axis_angle,
                "pattern": pattern,
                "shell_axis": shell_axis,
                "side_axis": side_axis,
                "shell_offset": shell_offset,
                "side_threshold": side_threshold,
                "parameterization": parameterization,
            },
        )

    @app.get("/rule30/oloid-antipode/verify")
    def verify_rule30_oloid_antipodal_winding(
        max_depth: int = 256,
        axis_angle: float = 1.5707963267948966,
        pattern: str = "alternating_xy",
        shell_axis: str = "z",
        side_axis: str = "x",
        shell_offset: float = 0.0,
        side_threshold: float = 0.05,
        parameterization: str = "identity",
    ):
        return forge.verify_rule30_oloid_antipodal_winding(
            max_depth=max_depth,
            config={
                "axis_angle": axis_angle,
                "pattern": pattern,
                "shell_axis": shell_axis,
                "side_axis": side_axis,
                "shell_offset": shell_offset,
                "side_threshold": side_threshold,
                "parameterization": parameterization,
            },
        )

    @app.get("/rule30/oloid-winding/{n}")
    def rule30_oloid_winding_from_n(
        n: int,
        axis_angle: float = 1.5707963267948966,
        pattern: str = "alternating_xy",
        shell_axis: str = "z",
        side_axis: str = "x",
        shell_offset: float = 0.0,
        side_threshold: float = 0.05,
        parameterization: str = "identity",
    ):
        return forge.rule30_oloid_winding_from_n(
            n=n,
            axis_angle=axis_angle,
            pattern=pattern,
            shell_axis=shell_axis,
            side_axis=side_axis,
            shell_offset=shell_offset,
            side_threshold=side_threshold,
            parameterization=parameterization,
        )

    @app.get("/rule30/oloid-antipode/{n}")
    def rule30_oloid_antipodal_winding(
        n: int,
        axis_angle: float = 1.5707963267948966,
        pattern: str = "alternating_xy",
        shell_axis: str = "z",
        side_axis: str = "x",
        shell_offset: float = 0.0,
        side_threshold: float = 0.05,
        parameterization: str = "identity",
    ):
        return forge.rule30_oloid_antipodal_winding(
            n=n,
            axis_angle=axis_angle,
            pattern=pattern,
            shell_axis=shell_axis,
            side_axis=side_axis,
            shell_offset=shell_offset,
            side_threshold=side_threshold,
            parameterization=parameterization,
        )

    @app.get("/rule30/oloid-scan")
    def rule30_oloid_parameterization_scan(max_depth: int = 256):
        return forge.rule30_oloid_parameterization_scan(max_depth=max_depth)

    @app.get("/rule30/winding-number")
    def rule30_winding_number_proof(max_depth: int = 4096, max_order: int = 4):
        return forge.rule30_winding_number_proof(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/winding-number/verify")
    def verify_rule30_winding_number_proof(max_depth: int = 4096, max_order: int = 4):
        return forge.verify_rule30_winding_number_proof(max_depth=max_depth, max_order=max_order)

    @app.get("/rule30/nth-bit/{n}")
    def rule30_nth_bit_expression(n: int, page_size: int = 4096, block_size: int = 8, max_order: int = 4):
        return forge.rule30_nth_bit_expression(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/nth-bit/{n}/verify")
    def verify_rule30_nth_bit_expression(n: int, page_size: int = 4096, block_size: int = 8, max_order: int = 4):
        return forge.verify_rule30_nth_bit_expression(
            n=n,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    def _cqe_idempotent_cache():
        from .cqe_idempotent_cache import CQEIdempotentLibCache

        return CQEIdempotentLibCache(cache_root / ".lattice_forge" / "cqe_idempotent_cache.sqlite")

    @app.post("/cqe/idempotent-cache/seed")
    def seed_cqe_idempotent_cache(max_rule30_depth: int = Query(16, ge=1, le=4096)):
        cache = _cqe_idempotent_cache()
        try:
            return cache.seed_core(max_rule30_depth=max_rule30_depth)
        finally:
            cache.close()

    @app.get("/cqe/idempotent-cache/status")
    def cqe_idempotent_cache_status():
        cache = _cqe_idempotent_cache()
        try:
            return cache.stats()
        finally:
            cache.close()

    @app.get("/rule30/cqe-nth-bit/{n}")
    def rule30_cqe_nth_bit(n: int, max_depth: int = 4096, base_page: int = 64):
        from .rule30_cqe_tool import Rule30CQETool

        cache = _cqe_idempotent_cache()
        try:
            return Rule30CQETool(
                max_depth=max_depth,
                base_page=base_page,
                idempotent_cache=cache,
            ).analyze_nth_bit(n)
        finally:
            cache.close()

    @app.get("/rule30/proof-obligations")
    def rule30_proof_obligations(
        max_depth: int = 4096,
        page_count: int = 2,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ):
        return forge.rule30_proof_obligations(
            max_depth=max_depth,
            page_count=page_count,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/rule30/proof-obligations/verify")
    def verify_rule30_proof_obligations(
        max_depth: int = 4096,
        page_count: int = 2,
        page_size: int = 4096,
        block_size: int = 8,
        max_order: int = 4,
    ):
        return forge.verify_rule30_proof_obligations(
            max_depth=max_depth,
            page_count=page_count,
            page_size=page_size,
            block_size=block_size,
            max_order=max_order,
        )

    @app.get("/witnesses")
    def witnesses(
        source_id: str | None = None,
        target_id: str | None = None,
        morphism_id: str | None = None,
    ):
        return forge.witnesses(source_id=source_id, target_id=target_id, morphism_id=morphism_id)

    @app.get("/obstructions")
    def obstructions(source_id: str | None = None, target_id: str | None = None):
        return forge.obstructions(source_id=source_id, target_id=target_id)

    @app.get("/events")
    def events(limit: int = Query(20, ge=1, le=500)):
        return {"events": forge.latest_events(limit)}

    @app.get("/receipts")
    def receipts(limit: int = Query(20, ge=1, le=500)):
        return {"receipts": forge.latest_receipts(limit)}

    @app.get("/snapshot")
    def snapshot(limit: int = Query(100, ge=1, le=1000)):
        return forge.snapshot(limit=limit)

    try:
        from lattice_forge.witness.api import create_witness_router

        app.include_router(create_witness_router(forge, provider=None, mint_fn=None))
    except ImportError:
        pass

    return app
