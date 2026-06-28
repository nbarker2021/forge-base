"""Generate FORGE_MANIFEST.json (content-addressed) + verify the base is a
complete, self-contained single source for the forge/lib family.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def package_hash(pkg: Path):
    """Deterministic content hash + file count for a package dir."""
    items = []
    for f in sorted(pkg.rglob("*.py")):
        rel = f.relative_to(pkg).as_posix()
        items.append(rel + ":" + hashlib.sha256(f.read_bytes()).hexdigest())
    blob = "\n".join(items).encode()
    return hashlib.sha256(blob).hexdigest()[:16], len(items)


def main():
    lib = ROOT / "lib"
    packages = sorted(p for p in lib.iterdir()
                      if p.is_dir() and not p.name.startswith((".", "_", "__")))
    manifest = {"_meta": {"role": "canonical forge/lib base — the ONE location",
                          "source": "repo_harvest CQECMPLX-Production cqecmplx-forge/src + cqekernel",
                          "package_count": len(packages)},
                "packages": {}}
    for pkg in packages:
        h, n = package_hash(pkg)
        manifest["packages"][pkg.name] = {"content_hash": h, "py_files": n}
    (ROOT / "FORGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"manifest: {len(packages)} packages")

    # Verify the chain resolves from THIS base alone.
    sys.path.insert(0, str(ROOT / "lib"))
    results = {}
    for name in ("lattice_forge", "CrystalForge", "SplatForge", "PixelForge",
                 "ChromaForge", "MorphForge", "cqekernel"):
        try:
            __import__(name)
            results[name] = "ok"
        except Exception as exc:  # noqa: BLE001
            results[name] = f"{type(exc).__name__}: {exc}"
    print("import check (from forge-base only):")
    for k, v in results.items():
        print(f"  {k:16} {v}")
    # SplatForge pulling PixelForge.blotlift is the key self-containment proof.
    try:
        from SplatForge import compiler  # noqa: F401
        print("  SplatForge.compiler chain: ok (PixelForge.blotlift resolved)")
    except Exception as exc:  # noqa: BLE001
        print(f"  SplatForge.compiler chain: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
