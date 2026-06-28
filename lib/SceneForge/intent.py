"""
SceneForge Intent — the Scene8 prompt-understanding layer, stdlib-stripped.

Donor: the generative-video engine's MiniAletheia intent system.
Intent-as-Slice: a prompt generates THREE trajectory candidates (one per
action lattice), each is scored by the system's own principles (entropy
non-increase, digital-root attractor, parity), and the best slice wins.

Action lattices (DR 1, 3, 7 — donor-faithful, numpy removed):
    UNITY      identity walk
    TERNARY    120-degree rotation in the first plane
    ATTRACTOR  spiral toward the DR=7 attractor

Trajectories live on the 240-root E8 lattice (enumerated once at import,
pure python); every state is snapped to its nearest root — the walk is ON
the lattice, not near it. Deterministic: same prompt = same intent forever.
"""
from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from PixelForge.projection import entropy, parity as _parity, digital_root

# ─── the 240 E8 roots (import-time, pure python) ─────────────────────────────

def _e8_roots() -> List[Tuple[float, ...]]:
    roots: List[Tuple[float, ...]] = []
    # type 1: (+-1, +-1, 0^6) in all position pairs — 112 roots
    for i in range(8):
        for j in range(i + 1, 8):
            for si in (-1.0, 1.0):
                for sj in (-1.0, 1.0):
                    v = [0.0] * 8
                    v[i], v[j] = si, sj
                    roots.append(tuple(v))
    # type 2: (+-1/2)^8 with even minus count — 128 roots
    for mask in range(256):
        signs = [1.0 if (mask >> k) & 1 else -1.0 for k in range(8)]
        if signs.count(-1.0) % 2 == 0:
            roots.append(tuple(s / 2.0 for s in signs))
    return roots

E8_ROOTS: List[Tuple[float, ...]] = _e8_roots()


def nearest_root(v: List[float]) -> Tuple[float, ...]:
    best, bd = E8_ROOTS[0], float("inf")
    for r in E8_ROOTS:
        d = sum((a - b) * (a - b) for a, b in zip(v, r))
        if d < bd:
            best, bd = r, d
    return best


# ─── action lattices (donor-faithful) ─────────────────────────────────────────

UNITY, TERNARY, ATTRACTOR = "unity", "ternary", "attractor"
ACTIONS = (UNITY, TERNARY, ATTRACTOR)
_ANG = 2.0 * math.pi / 3.0


def apply_action(v: List[float], action: str) -> List[float]:
    if action == TERNARY:
        c, s = math.cos(_ANG), math.sin(_ANG)
        out = list(v)
        out[0] = c * v[0] - s * v[1]
        out[1] = s * v[0] + c * v[1]
        return out
    if action == ATTRACTOR:
        return [v[0] * 0.7 + 0.7] + [x * 0.7 for x in v[1:]]
    return list(v)


# ─── intent ───────────────────────────────────────────────────────────────────

@dataclass
class Intent:
    text: str
    trajectory: List[Tuple[float, ...]]
    action: str
    projection_type: str
    score: float
    digital_root: int
    parity: int


_PROJ_KEYWORDS = {
    "hopf": ("swirl", "spiral", "orbit", "spin", "flow"),
    "coxeter": ("crystal", "lattice", "symmetry", "golden", "star"),
    "orthographic": ("flat", "map", "plan", "grid"),
}


def _infer_projection(prompt: str) -> str:
    p = prompt.lower()
    for proj, words in _PROJ_KEYWORDS.items():
        if any(w in p for w in words):
            return proj
    return "standard"


def _trajectory(prompt: str, n: int, action: str) -> List[Tuple[float, ...]]:
    seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    state = nearest_root([rng.gauss(0, 1) for _ in range(8)])
    out = [state]
    for _ in range(n - 1):
        state = nearest_root(apply_action(list(state), action))
        out.append(state)
    return out


def _score(traj: List[Tuple[float, ...]]) -> float:
    s = 0.0
    ents = [entropy(f) for f in traj]
    if ents[-1] <= ents[0]:
        s += 0.3                                   # DeltaPhi <= 0
    total = sum(sum(f) for f in traj)
    if digital_root(total) == 7:
        s += 0.4                                   # the DR=7 attractor
    flat = [x for f in traj for x in f]
    if _parity(flat) == 0:
        s += 0.1                                   # even channel
    s += 0.2 * (len({f for f in traj}) / len(traj))  # coverage of distinct roots
    return round(s, 4)


def understand(prompt: str, num_frames: int = 30) -> Intent:
    """Intent-as-Slice: three candidates, system-scored, best wins."""
    cands: List[Intent] = []
    for action in ACTIONS:
        traj = _trajectory(prompt, num_frames, action)
        cands.append(Intent(
            text=prompt, trajectory=traj, action=action,
            projection_type=_infer_projection(prompt),
            score=_score(traj),
            digital_root=digital_root(sum(sum(f) for f in traj)),
            parity=_parity([x for f in traj for x in f]),
        ))
    return max(cands, key=lambda c: c.score)
