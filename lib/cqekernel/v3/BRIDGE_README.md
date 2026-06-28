# MannyAI v3 Bridge (HTTP)

The v3 bridge exposes the MannyKernel as an HTTP service that the
Hermes Discord gateway can call.

## What it does

The bridge has 3 endpoints:

| Method | Path | Body | Purpose |
|---|---|---|---|
| `GET` | `/health` | — | Kernel state + request count |
| `POST` | `/invoke` | `{"tool": "TMN-...", "input": ...}` | Direct tool invocation |
| `POST` | `/message` | `{"user_id": "...", "channel_id": "...", "message": "..."}` | Discord-style routing (calls `kernel.handle_message()`) |

## How to run

```bash
cd D:/CQE_CMPLX
python cqekernel/v3_bridge.py --port 7777
```

The bridge boots the MannyKernel in <2s, prints the boot state to stdout,
and serves on `http://127.0.0.1:7777` (or your chosen port).

## How to wire to Discord

The v3 bridge is the WIRE. Three more steps are needed for the gateway
to actually call it on Discord messages:

### 1. Add the bridge to the gateway's external tools

In `C:/Users/nbark/AppData/Local/hermes/config.yaml`, add:

```yaml
gateway:
  external_tools:
    - url: http://localhost:7777
      name: mannyai-v3
      tools: [invoke, message]
      timeout: 30
```

### 2. Add a slash command in the Discord adapter

The Discord adapter (`hermes-agent/plugins/platforms/discord/adapter.py`)
defines slash commands. Add a `/v3` command that calls the bridge:

```python
async def v3_callback(self, interaction, *, query: str):
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:7777/message", json={
            "user_id": str(interaction.user.id),
            "channel_id": str(interaction.channel_id),
            "message": query,
        }) as resp:
            result = await resp.json()
    await interaction.response.send_message(format_v3_result(result))
```

### 3. Restart the gateway

```bash
hermes gateway install   # if first time, needs UAC
# OR for dev:
hermes gateway run --replace
```

The gateway restart (PID 30468 → new PID) loads the new config.

## What the bridge CAN do today

- ✅ Boot the v3 kernel
- ✅ Serve `/health`, `/invoke`, `/message` endpoints
- ✅ Route 104 handlers (6 specific + 3 real + 95 smart)
- ✅ Return real crystal search hits (89 named claims)
- ✅ Execute the 3 priority tools (TMN-gateway routes, TMN-daemon manages processes, TMN-bond does vector arithmetic)
- ✅ Track conservation (ΔΦ stays ≤ 0)

## What the bridge CANNOT do yet (the v3.1 wire-up)

- ❌ Config-side wiring: the gateway doesn't know about the bridge yet
- ❌ Slash command registration: no `/v3` command on MannyAI#2807
- ❌ Auto-restart: the gateway needs a manual restart to pick up the new config
- ❌ Auth: the bridge has no API key, anyone on localhost can call it
- ❌ Persistence: the bridge state (daemon processes, bond graph) is in-memory only
- ❌ Cross-process state: the v3 kernel in this bridge and the v3 kernel in another process don't share state

## Test commands (for now, while the gateway isn't wired)

```bash
# Boot the bridge
cd D:/CQE_CMPLX && python cqekernel/v3_bridge.py --port 7777 &

# Health check
curl http://localhost:7777/health

# Direct invocation
curl -X POST http://localhost:7777/invoke \
  -H 'Content-Type: application/json' \
  -d '{"tool": "TMN-bond", "input": {"op": "add", "a": [1,2,3], "b": [4,5,6]}}'

# Discord-style message routing
curl -X POST http://localhost:7777/message \
  -H 'Content-Type: application/json' \
  -d '{"user_id": "289204964763369474", "channel_id": "1518675187074207846", "message": "!TMN-thinktank R30"}'
```

## Files

- `v3_bridge.py` — the bridge server (172 lines)
- `../v3.py` — the kernel code (MannyKernel class)
- `D:/CQE_CMPLX/forge_dbs/tmn_unified.db` — the runtime state (11 tables, 268+ rows)
- `D:/CQE_CMPLX/TMN_TOOLS_LCR.db` — the source-of-truth for 93 tools
- `C:/Users/nbark/AppData/Local/hermes/state.db` — the Discord agent's session store
- `D:/CQE_CMPLX/cqekernel/` — the local kernel copy
- `production/packages/cqekernel/v3/` — the git-tracked copy
