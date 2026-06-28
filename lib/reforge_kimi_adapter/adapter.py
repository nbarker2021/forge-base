from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

# Kimi/Lattice Forge paths are injected by CLI or inferred from workspace .env.
def _read_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def configure_paths(workspace: str | None = None) -> dict[str, str]:
    """Add Kimi final submission source paths to sys.path and return discovered env."""
    ws = Path(workspace or os.environ.get("CQE_WORKSPACE", "/mnt/data/cqe_transport_workspace"))
    env = _read_env_file(ws / ".env")
    env.update({k: v for k, v in os.environ.items() if k.startswith(("KIMI", "CQE", "REFORGE"))})
    kimi_root = Path(env.get("KIMI_REVIEW_ROOT", ws / "02_unpacked/kimi_full_again"))
    candidates = [
        kimi_root / "CMPLX-R30-FINAL-SUBMISSION" / "PROOF" / "src",
        kimi_root / "CMPLX-R30-FINAL-SUBMISSION" / "src",
        kimi_root / "CMPLX-R30-full-checkpoint-v7" / "PROOF" / "src",
        kimi_root / "CMPLX-R30-full-checkpoint-v7" / "src",
    ]
    for p in candidates:
        if p.exists() and str(p) not in sys.path:
            sys.path.insert(0, str(p))
    return env


def _bytes_to_bits(data: bytes, limit_bits: int = 256) -> list[int]:
    bits: list[int] = []
    for b in data:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)
    return bits[-limit_bits:] if len(bits) > limit_bits else bits


def _triads(bits: list[int]) -> list[tuple[int, int, int]]:
    if not bits:
        return []
    # Pad with edge values so every bit has L/C/R context.
    ext = [bits[0]] + bits + [bits[-1]]
    return [(ext[i - 1], ext[i], ext[i + 1]) for i in range(1, len(ext) - 1)]


def _state_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


@dataclass
class WorldForgeNode:
    id: str
    label: str
    kind: str
    color_state: str
    paper_state: str
    proof_status: str
    x: float
    y: float
    payload: dict[str, Any]


@dataclass
class WorldForgeEdge:
    source: str
    target: str
    kind: str
    color_state: str
    payload: dict[str, Any]


def _color_for_state(state: tuple[int, int, int]) -> str:
    # Manual-kit color readout: center bit selects proof/obligation polarity;
    # axis-like popcount assigns quark-color surface.
    pop = sum(state)
    if pop == 0:
        return "white/vacuum"
    if pop == 3:
        return "black/full"
    if state[1] == 1 and state[2] == 0:
        return "neon/correction"
    return ["red", "green", "blue"][pop % 3]


def adapt_work_fragment(text: str, *, window: int = 64, workspace: str | None = None) -> dict[str, Any]:
    """Encode a text/work fragment into Kimi proof-machine and WorldForge receipt.

    Flow:
      text -> bytes/bits -> BinaryBoundaryAdapter -> LCR triads -> D4 -> VOA
      -> proof/obligation labels -> WorldForge nodes/edges.
    """
    configure_paths(workspace)
    from lattice_forge.binary_boundary_adapter import adapt as bba_adapt
    from lattice_forge.chart_codec_d4 import encode_d4, decode_d4
    from lattice_forge.centroid_voa import gluon, voa_weight, anneal_to_lie_conjugate
    from lattice_forge.rule90_linearization import correction

    raw = text.encode("utf-8", errors="ignore")
    bits = _bytes_to_bits(raw, limit_bits=max(window, 16))
    if len(bits) < 3:
        bits = ([0, 0, 0] + bits)[-3:]
    triad_stream = _triads(bits[-window:])

    # Kimi adapter over the same bit tail.
    bba = bba_adapt(bits, window=min(window, len(bits)))
    d4 = encode_d4(triad_stream)
    d4_roundtrip_ok = decode_d4(d4) == triad_stream

    nodes: list[WorldForgeNode] = []
    edges: list[WorldForgeEdge] = []
    previous_id: str | None = None
    carry_count = 0
    obligation_count = 0
    proof_count = 0

    for i, s in enumerate(triad_stream):
        L, C, R = s
        corr = int(correction(L, C, R))
        carry_count += corr
        weight = int(voa_weight(s))
        ann = anneal_to_lie_conjugate(s)
        color = _color_for_state(s)
        paper_state = "new_page" if corr else "continue_page"
        proof_status = "obligation" if corr else "proof_continuation"
        if corr:
            obligation_count += 1
        else:
            proof_count += 1
        nid = f"{_state_id(text)}:lcr:{i:04d}"
        nodes.append(WorldForgeNode(
            id=nid,
            label=f"LCR {i}: {s}",
            kind="lcr_block",
            color_state=color,
            paper_state=paper_state,
            proof_status=proof_status,
            x=float(i),
            y=float(sum(s)),
            payload={
                "index": i,
                "L": L,
                "C": C,
                "R": R,
                "gluon_gamma": int(gluon(s)),
                "correction": corr,
                "voa_weight": weight,
                "anneal_steps": ann.get("steps"),
                "anneal_target": ann.get("final"),
                "d4_axis": d4["labels"][i],
                "d4_sheet": d4["sheets"][i],
            },
        ))
        if previous_id is not None:
            edges.append(WorldForgeEdge(
                source=previous_id,
                target=nid,
                kind="continuous_discrete_path",
                color_state=color,
                payload={"step": i, "relation": "next_lcr_window"},
            ))
        previous_id = nid

    receipt = {
        "receipt_type": "reforge_kimi_adapter_v0_1",
        "fragment_id": _state_id(text),
        "input_preview": text[:240],
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "input_bytes": len(raw),
        "window_bits": min(window, len(bits)),
        "bit_count_total": len(bits),
        "lcr_block_count": len(triad_stream),
        "bba_summary": bba.get("summary", {}),
        "d4_roundtrip_ok": d4_roundtrip_ok,
        "d4_label_counts": {str(k): d4["labels"].count(k) for k in sorted(set(d4["labels"]))},
        "d4_sheet_counts": {str(k): d4["sheets"].count(k) for k in sorted(set(d4["sheets"]))},
        "proof_continuation_count": proof_count,
        "obligation_count": obligation_count,
        "carry_density": carry_count / len(triad_stream) if triad_stream else 0.0,
        "worldforge_graph": {
            "nodes": [asdict(n) for n in nodes],
            "edges": [asdict(e) for e in edges],
        },
        "adapter_boundary": "text-to-bit adapter; semantic parsing is deferred to GlyphForge/FuMu; proof labels are Kimi-local LCR/correction receipts, not external scientific validation",
    }
    return receipt


def batch_adapt(texts: Iterable[str], *, window: int = 64, workspace: str | None = None) -> list[dict[str, Any]]:
    return [adapt_work_fragment(t, window=window, workspace=workspace) for t in texts]


def save_receipt(receipt: dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(json.dumps(receipt, indent=2, default=str), encoding="utf-8")
