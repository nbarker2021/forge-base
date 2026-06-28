# MannyAI v3 Kernel

The v3 MannyAI kernel is the production version of what was scattered across:
- `D:/CQE_CMPLX/cqekernel/` (the 11 modules: adapters, algebra, carrier, core, cqe, firmware, lcr, ledger, projection, ribbon, storage, verification)
- `D:/CQE_CMPLX/papers_tool_solvers/tmn_tools_core.py` (the 850-line TMNToolBase)
- `D:/CQE_CMPLX/papers_tool_solvers/generated_tools/` (the 93 TMN_* stubs)
- `production/operations/crystal_library/` (the 88 named claims)
- `D:/CQE_CMPLX/forge_dbs/tmn_unified.db` (the 11-table runtime state)

## Architecture

```
+-----------------+     +-----------------+     +-----------------+
|  CQKERNEL       |     |  TMN TOOLS      |     |  CRYSTAL LIB    |
|  (11 modules)   |     |  (93 tools)     |     |  (88 claims)    |
+--------+--------+     +--------+--------+     +--------+--------+
         |                       |                       |
         +-----------------------+-----------------------+
                                 |
                      +----------v----------+
                      |     MannyAI v3       |
                      |     (this kernel)    |
                      +----------+--------+
                                 |
                      +----------v----------+
                      |   TMN_UNIFIED.DB    |
                      |  (11 tables, 103    |
                      |   brains, 268 edges)|
                      +---------------------+
```

## Usage

```python
from cqekernel.v3 import MannyKernel

kernel = MannyKernel()
print(kernel.boot())
# {'kernel_version': '3.0.0', 'tools_loaded': 93, 'tools_by_tier': {...}, ...}

# Invoke a tool by name (e.g. for a Discord message)
result = kernel.invoke("TMN-crystal", "TMN")
# or via the Discord-routing helper:
result = kernel.handle_message("user_id", "channel_id", "!crystal TMN")

# Crystal search
claims = kernel.crystals.search_claims("TMN", limit=5)
# Returns 5 named claims matching "TMN"

# Conservation state
print(kernel.runtime.global_dphi())  # current cumulative ΔΦ
```

## Routing

`handle_message(user_id, channel_id, message)` routes incoming messages:

| Pattern | Routes To |
|---------|-----------|
| `!crystal <query>` | `TMN-crystal` (smart alias for `!TMN-crystal`) |
| `!thinktank <query>` | `TMN-thinktank` (crystal search) |
| `!gateway <input>` | `TMN-gateway` (route to other tools) |
| `claim <id>` | crystal-search |
| `crystal <query>` | crystal-search |
| `what is...?` | `TMN-thinktank` (default) |

## Physical Operation

Every tool invocation follows the universal tool contract:
> "Mount crystal in LCR frame. Read state through (L,C,R) gradient. Verify ΔΦ ≤ 0. Issue receipt."

This is enforced at the kernel level: every `invoke()` call:
1. **Mounts** the tool crystal (loads its 4 atoms from the LCR DB)
2. **Reads** the input through the L→C→C→R atom flow
3. **Verifies** the conservation bound (ΔΦ ≤ 0)
4. **Issues** a receipt (logged to the runtime DB)

## Tables in tmn_unified.db

The runtime DB has 11 tables populated by `populate_tmn_unified.py`:
- `agent_brains` (103): 9 sub-agents + 93 TMN tools + 1 MannyAI-v3
- `brain_contributions` (114): 1 contribution per brain
- `coin_definitions` (8): atom, receipt, claim, theorem, falsifier, kernel, tool, agent
- `coin_ledger` (103): 1 ledger per brain
- `coin_mint_log` (103): 1 mint per brain
- `conservation_entries` (114): 1 conservation entry per brain
- `conservation_ledger` (1): global cumulative ΔΦ
- `crystals` (88): 1 per named claim
- `dag_edges` (268): 226 tool bonds + 50 claim→commit links
- `e8_nodes` (88): 1 per named claim
- `receipts` (101): 50 git commits + 50 per-paper receipts + 1 populate

## What the v3 kernel can do TODAY

- ✅ Boot from cold state in <2s
- ✅ Lookup any of 93 tools by name
- ✅ Search 88 crystal claims by substring
- ✅ Lookup any of 103 brains (sub-agents + TMN tools + MannyAI-v3)
- ✅ Track conservation (ΔΦ stays ≤ 0)
- ✅ Issue receipts (every invocation logs to runtime DB)
- ✅ Route Discord messages to the right tool via smart aliases

## What the v3 kernel CANNOT do yet (the v3.1 work)

- ❌ Real implementations of the 93 tools (each is a generic "process and return" stub)
- ❌ Lattice_forge imports (the CMPLX-R30 math library is not yet wired)
- ❌ Cross-tool bonds (the 226 declared bonds are not yet enforced)
- ❌ Subagent dispatch (the 9 sub-agents exist as brains but don't actually orchestrate work)
- ❌ Discord bot direct integration (MannyAI#2807 still uses the Hermes gateway, not v3 kernel)
- ❌ Persistent state across reboots (the runtime DB is rebuilt on every boot)

## Where to go next

- **Step 3** (wire stubs to real implementations): for each of the 93 tools, find the real `service:X:X` implementation in `lattice_forge` or `cqekernel/<module>` and replace the generic handler.
- **Step 4** (complete 3 priority tools): TMN-gateway (the 1956-line router), TMN-daemon (the 1468-line process manager), TMN-bond (the 1102-line LCR atom-bonder). These are the most-called tools in the bond graph.
- **Step 5** (wire Discord bot): point the Hermes Discord gateway at `MannyKernel.handle_message()` so that incoming messages route through v3.

## Files

- `__init__.py` (this directory): the v3 kernel code (renamed from `v3.py`)
- `../populate_tmn_unified.py`: the population script (re-runnable to rebuild the runtime DB)
- `D:/CQE_CMPLX/forge_dbs/tmn_unified.db`: the runtime state (11 tables, 1300+ rows)
- `D:/CQE_CMPLX/TMN_TOOLS_LCR.db`: the source-of-truth for 93 tools (read-only, source)
- `D:/CQE_CMPLX/cqekernel/`: the 11 modules (adapters, algebra, carrier, core, cqe, firmware, lcr, ledger, projection, ribbon, storage, verification)

## Honest boundaries

- The 93 tools' "real implementations" are the source `service:X:X` URLs in TMN_TOOLS_LCR.db. The current kernel only has default handlers for `crystal`, `brain`, `gate`, `daemon`, `gateway`, `thinktank`. The other 87 tools get generic "process and return" stubs.
- The LCR DB lists `formal_theorem` and `physical_op` columns for each tool, but the actual code that implements those operations is in the source zips (not in this kernel). Rebuilding them is the v3.1+ work.
- The crystal library is query-only. The v3 kernel reads from it; it does not write back. Adding crystal mutation (e.g., a new claim from a tool execution) is a v3.2+ feature.
- The conservation ledger is updated on every invocation, but the actual conservation check is symbolic (ΔΦ = -0.001 per call, -0.0005 per atom). Real conservation (e.g., for a market-decoder tool) requires the underlying math to be wired in.
