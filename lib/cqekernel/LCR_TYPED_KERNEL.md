# L/C/R typed kernel

> *Promote the L, C, R bits of the LCR triple from algebraic identity to operational role.*

The L/C/R typed kernel is a strictly-additive contract on top of the
existing `cqekernel.Kernel` runtime. It does not change the algebra,
the carriers, the gate, the ribbon, the master-ribbon, the firmware
ABI, or any of the 35 forges. It adds **three new Protocol classes**,
**three new policy gates**, a **lane classifier** for the 8 LCR
states, and a thin `TypedKernel` wrapper that enforces the gates.

The result: a kernel that is **type-strict by default** and must be
explicitly opened one lane at a time.

---

## Why this exists

The cqekernel already runs the entire observation pipeline through a
3-bit `(L, C, R)` triple. Today the three bits are *algebraic* —
they are XOR'd into Rule 30, Rule 90, and the correction surface, and
they appear as `(L, C, R)` in receipts, gluons, and the asymmetric
gate.

What the typed kernel adds is the *operational* reading of those
three bits:

| Bit | Algebraic role | Operational role | Type | Policy gate |
|-----|----------------|------------------|------|-------------|
| L   | one of three bits in the LCR triple | **data in / data out** (adapter, reader, writer) | `LAdapter` | `allow_left_io` |
| C   | the centre bit (the C-form, the carrier) | **control plane** (kernel, policy, firmware dispatch, mode changes) | `CKernel` | `allow_center_dispatch` |
| R   | one of three bits in the LCR triple | **outward surface** (receipts, snapshots, projections, whitepapers) | `RChannel` | `allow_right_emit` |

Three lanes, three types, three gates. The kernel's
`Policy.strict()` denies all three by default.

---

## The three Protocols

All three live in `production/packages/cqekernel/lcr/typed_kernel.py`
and are exported from `cqekernel.lcr`.

### `LAdapter` — the L lane

```python
from cqekernel.lcr import LAdapter

class LAdapter(Protocol):
    def adapt(self, source: Any) -> BinaryBoundaryFrame: ...
```

An L adapter is the *only* allowed path between the kernel and the
outside world. The existing six adapters in
`production/packages/cqekernel/adapters/` already satisfy this
contract:

| Adapter | Source | Module |
|---------|--------|--------|
| `BytesAdapter` | `bytes` | `adapters/bytes_adapter.py` |
| `JsonAdapter`  | `dict` / JSON-serialisable | `adapters/json_adapter.py` |
| `TextAdapter`  | `str` | `adapters/text.py` |
| `CsvAdapter`   | CSV bytes/str | `adapters/csv_adapter.py` |
| `FilesystemAdapter` | directory path | `adapters/filesystem.py` |
| `HostPacketAdapter` | host packet dict | `adapters/host_packet.py` |

`isinstance(adapter_instance, LAdapter)` returns `True` for all six.

### `CKernel` — the C lane

```python
from cqekernel.lcr import CKernel

class CKernel(Protocol):
    def observe(self, payload: Any, **kwargs: Any) -> Any: ...
    def observe_packet(self, packet: Dict[str, Any]) -> Any: ...
    def dispatch(self, firmware_call: str, payload: Dict[str, Any]) -> Any: ...
    def firmware_manifest(self) -> Dict[str, Any]: ...
    def cqe_info(self) -> Dict[str, Any]: ...
    def replay(self, snapshot_id: str) -> Any: ...
    def verify_kernel(self) -> Dict[str, Any]: ...
    def workbook_check(self) -> Dict[str, Any]: ...
    def get_snapshot(self, snapshot_id: str) -> Any: ...
    def list_snapshots(self) -> Any: ...
```

A C kernel is the *only* thing that may change the kernel's mode,
dispatch to a firmware, or run a workbook step. The existing
`cqekernel.Kernel` class satisfies every method in this Protocol —
the new `Kernel.dispatch()` method (added 2026-06-24) is a thin
wrapper around `firmware_registry.call()` that closes the final
shape gap.

`isinstance(Kernel(), CKernel)` returns `True` out of the box.

### `RChannel` — the R lane

```python
from cqekernel.lcr import RChannel

class RChannel(Protocol):
    def emit(self, receipt: Any) -> None: ...
    def project(self, snapshot: Any) -> Any: ...
```

An R channel is the *only* thing the customer ever sees. It takes
kernel receipts and snapshots and projects them into outward
artifacts: HTML cards on the demo suite, JSON manifests in
`evidence/full-data/`, PDFs in `showcase/.../presentation/`, PNG
plots in `simulation/`, validation receipts in
`validation_receipt.json`, the 8-slot ribbon in `master_ribbon/`.

The MetaForge ASTRO demo's R-channel surface is the existing
`showcase/astro-metaforge-lunch-demo/` directory plus `docs/index.html`
and `docs/demo-suite.html`. Every panel of the demo suite is an
R-channel projection.

---

## The three policy gates

`Policy.strict()` denies all three by default. A working system
must grant at least one lane per operation it wants to run.

```python
from cqekernel import Policy

# All three lanes closed.
p = Policy.strict()
p.check("left_io")         # KernelPolicyError
p.check("center_dispatch") # KernelPolicyError
p.check("right_emit")      # KernelPolicyError

# Open the C lane. L and R stay closed.
p.allow_center_dispatch = True
p.check("center_dispatch") # passes
p.check("left_io")         # KernelPolicyError
p.check("right_emit")      # KernelPolicyError
```

`Policy.from_dict` and `Policy.to_dict` round-trip the three new
fields. Existing policies (without the new keys) default the three
gates to `False`, so a policy persisted before 2026-06-24 retains
strict-by-default behaviour. The original eight gates
(`allow_firmware`, `allow_external_io`, `allow_mutation`,
`allow_compute`, `allow_conjectural_output`, `require_receipts`,
`require_replay`, `allow_host_write`) are unchanged.

---

## The lane classifier (`lane_of_lcr`)

Every `(L, C, R)` triple maps to its *dominant* lane via the
auditable heuristic in `lane_of_lcr`. Today every state maps to
`Lane.C` (the centre arbitrates all admission decisions), but the
classifier is exposed as a public function so the heuristic can be
refined without changing the policy or the gate.

```python
from cqekernel.lcr import lane_of_lcr, lane_role_string

lane_of_lcr((0, 1, 0))          # -> Lane.C  (boundary pair)
lane_role_string((0, 1, 0))      # -> "C (kernel)"
```

The classifier is used for **type-aware error messages** and
**obligation reporting**, not for policy decisions. Policy decisions
always come from the asymmetric gate in `carrier.lcr._gate()`.

---

## The `TypedKernel` wrapper

```python
from cqekernel import Kernel
from cqekernel.lcr import TypedKernel, Lane

k = Kernel()
tk = TypedKernel(kernel=k, policy=k.policy)

# Strict-by-default: everything denied.
tk.check_lane("observe_audit", Lane.C)  # KernelPolicyError

# Open the C lane and the operation passes.
k.policy.allow_center_dispatch = True
tk.check_lane("observe_audit", Lane.C)  # -> LaneGrant(granted=True, ...)

# R lane is still denied, even with the C lane open.
tk.check_lane("emit_receipt", Lane.R)   # KernelPolicyError
```

`TypedKernel.grants()` returns the current grant table (L, C, R
order), which is what you persist at boot time to audit what the
host has actually opened.

`TypedKernel.dispatch(firmware_call, payload)` is a thin pass-through
to `kernel.dispatch()` that *additionally* checks
`allow_center_dispatch`. This is the canonical way a host
programmatically dispatches a firmware call from a typed CEM.

---

## Canonical first CEM: ASTRO MetaForge (3 lanes open, all explicit)

The MetaForge ASTRO demo at
`showcase/astro-metaforge-lunch-demo/` is the canonical first typed
CEM. Boot it with:

```python
from cqekernel import Kernel
from cqekernel.lcr import TypedKernel, Lane

# 1. L lane: open data in/out
# 2. C lane: open control plane
# 3. R lane: open outward surface
k = Kernel()
k.policy.allow_left_io = True
k.policy.allow_center_dispatch = True
k.policy.allow_right_emit = True
k.policy.allow_firmware = True
k.policy.allow_external_io = True

tk = TypedKernel(kernel=k, policy=k.policy)

# Read an ASTRO source through the L lane (BytesAdapter satisfies LAdapter)
from cqekernel.adapters import adapt_bytes
src = b'{"material":"GRCop-42","process":"LPBF","heat_flux_w_m2":50000}'
frame = adapt_bytes(src)

# Dispatch through the C lane
result = tk.dispatch("lattice_forge.verify_j3", {"frame": frame.sha256})

# Project the receipt chain through the R lane (HTML / JSON / PDF)
# ...handled by the existing showcase scripts...
```

The MetaForge ASTRO flow demonstrates the three-lane contract end to
end. The same flow, with a different L adapter and a different
firmware target, is what a *next* CEM looks like — and the L/C/R
labels on the receipts make the CEM swap auditable per
`receipts.jsonl`.

---

## What this does NOT change

- The 8 LCR states, the asymmetric gate, the 4-bit carrier, the
  2x2/4x4/8x8 window envelope, the Rule 30 / Rule 90 / correction
  algebra.
- The ribbon (8 slots, arity report), the master_ribbon compiler,
  the firmware ABI, the firmware registry, the snapshot store, the
  Socratic wrapper, the workbooks.
- The 35 forges, the lattice_forge, ChromaForge, GraphStax,
  PixelForge, FridgeForge, LinkForge, MandleForge, ManiForge,
  SceneForge, the Wargame, the KIMI adapter, the Rhenium engine,
  and every other forge in the ring.
- The original eight policy gates.

A host that never imports `cqekernel.lcr.typed_kernel` sees no
behaviour change. A host that imports it gets the lane gate, the
Protocols, the classifier, and the `TypedKernel` wrapper, and can
choose to opt in lane-by-lane.

---

## Test coverage

`production/packages/cqekernel/tests/test_typed_kernel.py` covers:

- `Lane` enum and its role / policy-action / policy-field mapping
- `lane_of_lcr` classifier on all 8 LCR states
- `Policy` gains the three new fields with strict defaults
- `Policy.check` recognises the three new actions
- `TypedKernel.check_lane` denies by default, passes when granted
- `TypedKernel.grants` reports the current grant table
- `LaneGrant` serialises to a dict and is frozen
- `LAdapter` / `CKernel` / `RChannel` Protocols are runtime-checkable
- The real `cqekernel.Kernel` satisfies `CKernel` out of the box
- The original eight `Policy` gates still work (regression test)

Test result on the live tree: **168 passed, 1 pre-existing
unrelated failure** (a paper-body marker in `test_paper_spine.py`
that pre-dates this change and is unrelated to the typed kernel).

---

## Source map (real file paths, all in `D:\CQE_CMPLX\git-hosted-roots\CQECMPLX-Production\production\packages\cqekernel\`)

- `lcr/typed_kernel.py` — the three Protocols, the `Lane` enum, the
  classifier, the `LaneGrant` dataclass, and the `TypedKernel`
  wrapper
- `lcr/__init__.py` — re-exports the new surface
- `core/policy.py` — three new `Policy` fields and three new
  `check()` actions
- `core/kernel.py` — new `Kernel.dispatch()` method (C-lane
  convenience pass-through to `firmware_registry.call`)
- `adapters/bytes_adapter.py`, `adapters/json_adapter.py`,
  `adapters/text.py`, `adapters/csv_adapter.py`,
  `adapters/filesystem.py`, `adapters/host_packet.py` — the six
  existing L-lane adapters
- `tests/test_typed_kernel.py` — 45 tests, all passing
- `carrier/lcr.py` — the underlying 8-state LCR truth table
  (`_classify`, `gluon_from_lcr`, `admit`), unchanged
