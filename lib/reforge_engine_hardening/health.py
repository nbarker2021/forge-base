from __future__ import annotations
import json, subprocess, time
from pathlib import Path

ENGINES = [
    "reforge_kimi_adapter_v0_1",
    "reforge_worldforge_ui_adapter_v0_1",
    "reforge_researchcraft_module_v0_1",
    "reforge_glyphforge_fumu_v0_1",
]

def run_health(workspace: str | Path) -> list[dict]:
    root = Path(workspace) / "08_runs"
    rows = []
    for e in ENGINES:
        p = root / e
        row = {"engine": e, "path": str(p), "exists": p.exists()}
        if p.exists():
            t0=time.time()
            proc=subprocess.run(["python3","-m","pytest","-q"], cwd=p, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
            row.update({"pytest_returncode": proc.returncode, "pytest_output": proc.stdout.strip(), "seconds": round(time.time()-t0,3)})
        rows.append(row)
    return rows

if __name__ == "__main__":
    import os
    ws = os.environ.get("CQE_WORKSPACE", "/mnt/data/cqe_transport_workspace")
    print(json.dumps(run_health(ws), indent=2))
