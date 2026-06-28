"""
SceneForge WorldForge — the historical world-composition pipeline, ported.

Donor: the original worldforge.compose operator chain. A request becomes a
world context by passing through the fixed operator sequence:

    P5_startcap -> B_obs(3 bits) -> residue_endcap(harmonics 24)
                -> B_soft -> B_higgs(odd-first) -> B_ward -> Bridge(E8->Niemeier)

Each operator is a pure ctx transform that records itself in ctx["ops"] —
the world's receipt trail. compose() then attaches per-mode render plans.
Stdlib, faithful to the donor shapes.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List


# ─── operators (ported donor bodies) ─────────────────────────────────────────

def P5_startcap(ctx: Dict[str, Any]) -> Dict[str, Any]:
    ctx = dict(ctx); ctx.setdefault("ops", []).append("P5_startcap"); return ctx


def residue_endcap(ctx: Dict[str, Any], harmonics=(24,)) -> Dict[str, Any]:
    ctx = dict(ctx); ctx.setdefault("ops", []).append("Rrho_endcap")
    ctx["harmonics"] = list(harmonics); return ctx


def B_obs(ctx: Dict[str, Any], obs_bits: int = 3) -> Dict[str, Any]:
    ctx = dict(ctx); ctx.setdefault("ops", []).append("B_obs")
    ctx.setdefault("ledger", {}).setdefault("info_bits", 0)
    ctx["ledger"]["info_bits"] += int(obs_bits); return ctx


def B_soft(ctx: Dict[str, Any]) -> Dict[str, Any]:
    ctx = dict(ctx); ctx.setdefault("ops", []).append("B_soft"); return ctx


def B_higgs(ctx: Dict[str, Any], parity_order: str = "odd-first") -> Dict[str, Any]:
    ctx = dict(ctx); ctx.setdefault("ops", []).append("B_higgs")
    ctx["parity_order"] = parity_order; return ctx


def B_ward(ctx: Dict[str, Any]) -> Dict[str, Any]:
    ctx = dict(ctx); ctx.setdefault("ops", []).append("B_ward"); return ctx


def Bridge(ctx: Dict[str, Any], src="E8", dst="Niemeier") -> Dict[str, Any]:
    ctx = dict(ctx); ctx.setdefault("ops", []).append("Bridge")
    ctx["bridge"] = {"src": src, "dst": dst}; return ctx


# ─── render plans ─────────────────────────────────────────────────────────────

def plan_image(ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {"mode": "image", "seed": ctx["seed"], "lenses": ctx["lenses"]}


def plan_video(ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {"mode": "video", "seed": ctx["seed"], "lenses": ctx["lenses"],
            "harmonics": ctx.get("harmonics", [24])}


def plan_text(ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {"mode": "text", "seed": ctx["seed"]}


def plan_audio(ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {"mode": "audio", "seed": ctx["seed"]}


def stamp(ctx: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(ctx); out.update(extra)
    out["stamp"] = {
        "ts": time.time(),
        "world_id": hashlib.sha256(
            f"{ctx.get('seed')}:{ctx.get('prompt')}".encode()).hexdigest()[:16],
        "ops": list(ctx.get("ops", [])),
    }
    return out


# ─── compose (the donor pipeline, verbatim shape) ─────────────────────────────

def compose(seed: int, prompt: str, modes: List[str],
            lenses: List[str]) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {"seed": int(seed), "prompt": prompt,
                           "lenses": lenses, "ops": []}
    for op in (P5_startcap, B_obs, residue_endcap, B_soft, B_higgs, B_ward, Bridge):
        if op is B_obs:
            ctx = op(ctx, obs_bits=3)
        elif op is residue_endcap:
            ctx = op(ctx, harmonics=(24,))
        else:
            ctx = op(ctx)
    plans = []
    for m in modes:
        if m == "image":
            plans.append(plan_image(ctx))
        elif m == "video":
            plans.append(plan_video(ctx))
        elif m == "text":
            plans.append(plan_text(ctx))
        elif m == "audio":
            plans.append(plan_audio(ctx))
    return stamp(ctx, {"render_plan": {"plans": plans}})
