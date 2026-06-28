"""
PixelForge Frame — pixel-to-video creation layer (stripped donor stream model).

Frame: one rendered moment — an E8 state, its projected screen points, and
governance metadata (digital root, parity, entropy). Pixel buffers are
OPTIONAL: a frame is primarily its geometric record, realized to pixels by
whatever Surface displays it ("e8lossless": same state = same frame at any
resolution, deterministic, replayable).

FrameStream: an ordered frame sequence with legality checking between
neighbors (parity channel alternation and entropy non-increase, the donor's
DeltaPhi <= 0 discipline) and a serializable artifact form — the seed of the
video path we grow as we work (SceneForge shot graphs compose on top).

Stdlib only; pixel rasterization stays in the display layer by design.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PixelForge.projection import project_state, entropy as _entropy


@dataclass
class Frame:
    """One geometric frame: E8 state + projected record. Resolution-free."""
    frame_number: int
    e8_state: List[float]
    projection: str = "standard"
    record: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.record:
            self.record = project_state(self.e8_state, self.projection)

    def content_hash(self) -> str:
        canon = json.dumps({"n": self.frame_number, "e8": self.record["e8"],
                            "proj": self.projection}, sort_keys=True)
        return hashlib.sha256(canon.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {"frame": self.frame_number, "projection": self.projection,
                "record": self.record, "hash": self.content_hash(),
                "metadata": self.metadata}


class FrameStream:
    """Ordered frames with transition legality (donor governance):
       - parity channel must alternate or hold per `parity_rule`
       - entropy must not increase by more than `entropy_slack` per step
    Illegal transitions are not dropped — they are recorded as obligations,
    Event-Law style (failures are data)."""

    def __init__(self, fps: float = 30.0, projection: str = "standard",
                 parity_rule: str = "free",     # free | alternate | hold
                 entropy_slack: float = 0.0):
        self.stream_id = f"fs-{uuid.uuid4().hex[:10]}"
        self.fps = fps
        self.projection = projection
        self.parity_rule = parity_rule
        self.entropy_slack = entropy_slack
        self.frames: List[Frame] = []
        self.obligations: List[Dict[str, Any]] = []
        self.created = time.time()

    # ── building ─────────────────────────────────────────────────────────────
    def add_state(self, e8: Sequence[float],
                  metadata: Optional[Dict[str, Any]] = None) -> Frame:
        f = Frame(len(self.frames), list(e8[:8]), self.projection,
                  metadata=metadata or {})
        if self.frames:
            self._check_transition(self.frames[-1], f)
        self.frames.append(f)
        return f

    def add_trajectory(self, states: Sequence[Sequence[float]]) -> int:
        for s in states:
            self.add_state(s)
        return len(self.frames)

    # ── governance ───────────────────────────────────────────────────────────
    def _check_transition(self, a: Frame, b: Frame) -> None:
        pa, pb = a.record["parity"], b.record["parity"]
        if self.parity_rule == "alternate" and pa == pb:
            self.obligations.append({"frame": b.frame_number,
                                     "type": "parity_alternation_violated",
                                     "a": pa, "b": pb})
        elif self.parity_rule == "hold" and pa != pb:
            self.obligations.append({"frame": b.frame_number,
                                     "type": "parity_hold_violated",
                                     "a": pa, "b": pb})
        de = b.record["entropy"] - a.record["entropy"]
        if de > self.entropy_slack:
            self.obligations.append({"frame": b.frame_number,
                                     "type": "entropy_increase",
                                     "delta": round(de, 6)})

    # ── artifact ─────────────────────────────────────────────────────────────
    @property
    def duration(self) -> float:
        return len(self.frames) / self.fps if self.fps else 0.0

    def legal(self) -> bool:
        return not self.obligations

    def artifact(self) -> Dict[str, Any]:
        """The e8lossless-style stream artifact: fully deterministic replay."""
        return {
            "stream_id": self.stream_id,
            "codec": "e8lossless",
            "fps": self.fps,
            "projection": self.projection,
            "frame_count": len(self.frames),
            "duration_s": round(self.duration, 4),
            "parity_rule": self.parity_rule,
            "legal": self.legal(),
            "obligations": list(self.obligations),
            "frames": [f.to_dict() for f in self.frames],
        }

    def content_hash(self) -> str:
        h = hashlib.sha256()
        for f in self.frames:
            h.update(f.content_hash().encode())
        return h.hexdigest()[:16]

    def stats(self) -> Dict[str, Any]:
        if not self.frames:
            return {"frames": 0}
        ents = [f.record["entropy"] for f in self.frames]
        return {
            "frames": len(self.frames), "fps": self.fps,
            "duration_s": round(self.duration, 3),
            "entropy_first": ents[0], "entropy_last": ents[-1],
            "entropy_monotone_nonincreasing":
                all(b <= a + self.entropy_slack for a, b in zip(ents, ents[1:])),
            "obligations": len(self.obligations),
            "hash": self.content_hash(),
        }
