# cqe-kernel

**stdlib-only CQE/CMPLX source-bound C-form runtime.** Zero external
runtime dependencies.

This is the kernel from `D:\CQE_CMPLX\cqekernel\` — a 64-file, ~150KB
Python package that implements the full CQE/CMPLX kernel spec
without importing `numpy`, `pandas`, `pydantic`, `fastapi`,
`sympy`, `networkx`, `lattice_forge`, or any other external math
library. Optional firmware may attach higher lattice, Jordan, F4,
D12, oloid, or Moonshine receipts, but the kernel itself remains
dependency-free and never promotes those layers without explicit
evidence status.

## Install

```
pip install cqe-kernel
```

Or editable from this directory:
```
pip install -e .
```

## Use

```python
from cqekernel import Kernel, RequestMode

k = Kernel()                      # strict policy, default workspace
res = k.observe("hello world", mode=RequestMode.AUDIT)
print(res.arity)                  # 8 (full 8-slot ribbon)
print(res.ribbon_hash[:16])       # deterministic per-input hash
print(res.extras)                 # aperture_count, frame_governance_ok, ...

# CLI
# python -m cqekernel observe input.txt --mode AUDIT
# python -m cqekernel verify
# python -m cqekernel packet '{"op":"observe","payload":"x","mode":"AUDIT"}'
```

## Architecture

The kernel has 11 layers, all stdlib:

```
core/         request, kernel, policy, status, errors
carrier/      binary_boundary, fourbit, lcr, cform, correction
ribbon/       slot, ribbon, arity, hydrate, transport
projection/   observer_frame, light_cone, boundary_aperture, closure, eversion
ledger/       event, receipt, store, snapshot, replay
verification/ verifier, falsifier, honesty, socratic
firmware/     abi, registry, manifest          (optional, importlib-discovered)
adapters/     text, bytes, json, csv, filesystem, host_packet
workbook/     analog_schema, workbook_engine, token_map
storage/      json_store, sqlite_store, paths
tests/        26 unit + 19 integration tests, all stdlib
```

## Determinism

The ribbon hash is a deterministic function of the request: same
input → same `ribbon_hash`. Frame IDs, ribbon IDs, and carrier IDs
are derived from request hashes, not `uuid4()`. The slot identity
hash covers `(name, source_kind, provenance, status)` only — the
slot `value` may contain runtime UUIDs and is content, not identity.

## License

Proprietary / research prototype.
