# forge-base — the ONE forge/lib location

Canonical, content-addressed home for **every** CQE/CMPLX forge + lib package.
There is no other authoritative copy. The forges used to be scattered across
`cqecmplx-forge/src`, `lib-forge/engines`, `archive/stale-review/...`,
`products/*/lib-forge`, and multiple repo clones — with version drift that kept
breaking dependents (e.g. a `stale-review` PixelForge missing `blotlift.py`, a
working-tree CrystalForge reorganized into `archive/` mid-build). That division
is retired here.

## Layout

```
forge-base/
  lib/                 # the import root — add THIS to sys.path
    lattice_forge/ CrystalForge/ SplatForge/ SplatForgeField/ PixelForge/
    ChromaForge/ MorphForge/ cqekernel/ ... (50 packages)
  FORGE_MANIFEST.json  # per-package content_hash + py_files
  make_manifest.py     # regenerate the manifest + verify self-containment
```

## Use it (the single source)

```python
import sys
sys.path.insert(0, r"D:/forge-base/lib")
import lattice_forge, CrystalForge, SplatForge, cqekernel
```

Every consumer (MannyAI, the products, the kernels) resolves forges from
`D:/forge-base/lib` — never from a scattered tree. Set `FORGE_BASE` to override.

## Provenance

Assembled from the one complete clean source
(`repo_harvest/CQECMPLX-Production/production/packages/cqecmplx-forge/src` +
`cqekernel`), then verified: all 50 packages import from this base alone and the
SplatForge → PixelForge.blotlift chain resolves with no external path.

Note: packages live under `lib/` (not the base root) because some forges hard-code
a nesting depth (`Path.parents[3]`) to find their `DATA` dir; `lib/` puts them at
the depth that assumption needs. A real fix belongs in those forges
(robust data-root discovery), tracked as an obligation.
