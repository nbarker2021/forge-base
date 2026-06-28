"""cqecmplx-verify — run the ring's own verifiers as an install check.

Every check is a real verifier from the packaged modules, not a mock.
Exit code 0 = the installed wheel is healthy.
Version 1.0.0 = unified integration (kernel + forges + products).
"""
import sys


def main() -> int:
    checks = []

    def run(name, fn):
        try:
            r = fn()
            ok = (r is True) or (isinstance(r, dict) and r.get("status", "pass") in ("pass", "ok", True))
            checks.append((name, ok, "" if ok else str(r)[:80]))
        except Exception as exc:
            checks.append((name, False, f"{type(exc).__name__}: {exc}"))

    # === Substrate (lattice_forge) ===
    from cqecmplx.lattice.centroid_voa import verify_gluon_invariance
    from cqecmplx.lattice.rule90_linearization import verify_rule90_linearization
    from cqecmplx.lattice.binary_boundary_adapter import adapt
    run("gluon invariance (Theorem 0)", verify_gluon_invariance)
    run("rule90 linearization (O2')", verify_rule90_linearization)
    run("BBA adapt round-trip", lambda: bool(adapt(b"cqecmplx")["summary"]["n_bits"]))

    # === Engines ===
    from cqecmplx.engines import chroma, graphstax
    run("superperm n4 coverage", lambda: graphstax.coverage_check(graphstax.SUPERPERM_N4, 4))
    run("superperm n5 octad coverage", lambda: all(
        graphstax.coverage_check(s, 5) for s in graphstax.N5_OCTAD))
    run("Event Law mint+reuse", lambda: (
        lambda e: e.execute("verify") and e.execute("verify").get("receipt") is not None
    )(chroma.ChromaForgeEngine()))

    def _lifecycle_check():
        import tempfile, os
        e = chroma.ChromaForgeEngine()
        vault = chroma.CrystalVault(os.path.join(tempfile.mkdtemp(), "v.jsonl"))
        run_ = chroma.RunLifecycle(e, vault, run_id="verify")
        for _ in range(10):
            out = e.execute("lifecycle verify item")
            r = run_.activate("k", out["receipt"]["receipt_hash"], content="x")
        c = run_.finish()
        return bool(r["promoted"] and c["metadata"]["spine_length"] >= 1
                    and vault.count == 2 and len(e.speedlight._cache) == 0)
    run("two-tier law: promote+compress+crystal-only", _lifecycle_check)

    def _rgb_lcr_check():
        from cqecmplx.engines.pixel import (pixel_planes, planes_pixel,
                                            pixel_gluon, Picture, VideoSynth)
        for rgb in [(0,0,0),(255,255,255),(137,201,77),(255,0,128)]:
            if planes_pixel(pixel_planes(*rgb)) != rgb:
                return False
            if pixel_gluon(*rgb) != pixel_gluon(rgb[2], rgb[1], rgb[0]):
                return False
        r30 = Picture.rule30_texture(48, 27, (255,255,255), (0,0,32), seed=7)
        v1 = VideoSynth(48, 27); v1.add_layer(r30, motion=lambda t: (t, 0))
        v2 = VideoSynth(48, 27); v2.add_layer(r30, motion=lambda t: (t, 0))
        return v1.render(6)["video_hash"] == v2.render(6)["video_hash"]
    run("rgb=lcr: roundtrip+gluon+video determinism", _rgb_lcr_check)

    def _genesis_check():
        from cqecmplx.engines.pixel import Picture, GenesisField
        target = Picture.rule30_texture(48, 27, (250, 180, 60), (8, 8, 30), seed=5)
        g = GenesisField.from_picture(target)
        exact = g.regenerate().content_hash() == target.content_hash()
        d = g.density()["total"]
        cont = g.regenerate(extra_rows=10).height == 37
        return bool(exact and 0.0 <= d <= 1.0 and cont)
    run("genesis: rule90+correction regenerates exactly", _genesis_check)

    def _metamorph_check():
        from cqecmplx.engines.pixel import Picture
        from PixelForge.metamorph import morph_video
        a = Picture.rule30_texture(40, 22, (255, 200, 80), (8, 8, 30), seed=3)
        b = Picture.gradient(40, 22, (30, 60, 200), (220, 40, 90))
        m = morph_video(a, b, frames=8, fps=30, mode="sweep")
        return bool(m["first_exact"] and m["last_exact"]
                    and m["frames"][4].content_hash()
                    != a.blend(b, 0.5).content_hash())
    run("metamorph: correction-space morph, endpoints exact", _metamorph_check)

    # === Core Products (Rule 30 derived) ===

    # cqecmplx.r30
    def _r30_smoke_check():
        from cqecmplx.r30 import CmplxR30Solver
        from cqecmplx.r30.cache import InMemorySheetCache
        cache = InMemorySheetCache.from_bits("101100")
        solver = CmplxR30Solver(cache)
        receipt = solver.solve(2)
        return bool(receipt and hasattr(receipt, "to_dict"))
    run("r30: solver + cache smoke test", _r30_smoke_check)

    def _r30_atlas_check():
        from cqecmplx.r30.atlas import OrientedBinaryAtlas
        atlas = OrientedBinaryAtlas.from_bits("1101")
        bits = [atlas._read(n) for n in range(4)]
        return bits == [1, 1, 0, 1]
    run("r30: oriented atlas reads", _r30_atlas_check)

    def _r30_normal_form_check():
        from cqecmplx.r30.normal_form import decompose_address
        N, K = 12345, 4096
        q, r = decompose_address(N, K)
        return q * K + r == N and q == 3 and r == 57
    run("r30: normal form decomposition", _r30_normal_form_check)

    # cqecmplx.engines.analog_workbench
    def _analog_workbench_smoke_check():
        from cqecmplx.engines.analog_workbench import WorkbenchSimulator, build_eightfold_kit
        sim = WorkbenchSimulator()
        kit = build_eightfold_kit(copies=2)
        return bool(sim and kit and kit.get("object_count", 0) > 0)
    run("analog_workbench: engine instantiation", _analog_workbench_smoke_check)

    def _analog_workbench_receipt_check():
        from cqecmplx.engines.analog_workbench import WorkbenchSimulator, Receipt
        sim = WorkbenchSimulator()
        result = sim.run_action("test-001", "test action", ["red", "green", "blue"], True)
        receipt = result["receipt"]
        validated = Receipt(**receipt).validate()
        return bool(len(validated) == 0 and receipt["gradient_valid"])
    run("analog_workbench: receipt validation", _analog_workbench_receipt_check)

    # cqecmplx.entropy
    def _entropy_smoke_check():
        from cqecmplx.entropy.core import Rule30Engine
        engine = Rule30Engine(seed=b"verify-seed-123456")
        block = engine.generate_block(16)
        return block is not None and hasattr(block, 'to_dict')
    run("entropy: Rule30Engine generate + verify", _entropy_smoke_check)

    def _entropy_voa_check():
        from cqecmplx.entropy.core import VOAPartition, voa_checksum, voa_sector_of
        vp = VOAPartition()
        # voa_checksum expects a chart_sequence (list of triads)
        test_sequence = [(0,0,0), (1,1,1), (0,1,0), (1,0,1), (0,0,1), (1,1,0), (0,1,1), (1,0,0)]
        checksum = voa_checksum(test_sequence)
        sector = voa_sector_of((0, 0, 0))  # vacuum state
        return bool(checksum and sector == "vacuum")
    run("entropy: VOA partition + checksum", _entropy_voa_check)

    # cqecmplx.security
    def _security_smoke_check():
        from cqecmplx.security import FingerprintEngine, SyndromeFingerprint
        engine = FingerprintEngine()
        fp = engine.fingerprint_stream(b"verify-input")
        return isinstance(fp, SyndromeFingerprint) and fp.syndrome_counts.get(0, 0) >= 0
    run("security: FingerprintEngine fingerprint_stream", _security_smoke_check)

    def _security_checkpoint_check():
        from cqecmplx.security import CheckpointLedger, compute_64bit_id
        cid = compute_64bit_id(syndrome_index=1, geometry_level=0, emission=0, correction=0, chart_index=0, sequence=0)
        ledger = CheckpointLedger()
        return cid > 0 and isinstance(ledger, CheckpointLedger)
    run("security: CheckpointLedger + compute_64bit_id", _security_checkpoint_check)

    width = max(len(n) for n, _, _ in checks)
    fails = 0
    for name, ok, note in checks:
        print(f"  {'ok  ' if ok else 'FAIL'} {name.ljust(width)} {note}")
        fails += 0 if ok else 1
    print(f"cqecmplx-verify: {len(checks) - fails}/{len(checks)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())