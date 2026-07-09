"""CrystalForge.learner -- the L3a weight-learner (TMNBrain), SQLite port.

Ported from the real TMN service (CMPLX-PartsFactory-main/src/personal_node/
brain.py), exactly as CrystalForge.brain and CrystalForge.crystal were ported
from their TMN sources: the pure reasoning logic (8 E8-root experts, E8-Cartan
gating, Hebbian learning, the 3 Noether/Shannon/Landauer conservation triads,
epoch-300 freeze, grow/compress, to_image) is taken verbatim; only the
persistence layer (originally psycopg2) is replaced with sqlite3 against
schema.get_connection().

This closes O-CEM-3: the Carrier CEM's weight-learner now runs locally with no
Postgres / psycopg2 requirement.

Distinct from CrystalForge.brain (the L3b coordinator, which holds a skill-map
and routes cross-agent reuse but no weights). This module IS the weights.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from .schema import get_connection
from .stable_ids import brain_row_id

PHI = (1 + math.sqrt(5)) / 2
COUPLING = math.log(PHI) / 16  # kappa = ln(phi)/16, same constant as crystal.py
EPOCH_FREEZE = 300

# The 8 L0 experts are aligned to the E8 simple roots.
EXPERT_DOMAINS = [
    "geometry",      # alpha_1
    "computation",   # alpha_2
    "semantics",     # alpha_3
    "physics",       # alpha_4
    "economics",     # alpha_5
    "governance",    # alpha_6
    "integration",   # alpha_7 (e6+e7)
    "universal",     # alpha_8 (half-integer spinor root)
]


# ═══════════════════════════════════════════════════════════════════════
# Expert Node -- one L0 expert aligned to an E8 simple-root direction
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ExpertNode:
    expert_id: str = ""
    direction: int = 0  # 0-7 (Cartan index)
    domain: str = ""
    weights: List[float] = field(default_factory=lambda: [0.0] * 24)
    activation_count: int = 0
    confidence: float = 0.0
    last_activated: float = 0.0

    def __post_init__(self):
        if not self.expert_id:
            self.expert_id = f"expert-{self.direction}"

    def activate(self, input_vector: List[float]) -> float:
        if len(input_vector) < len(self.weights):
            input_vector = input_vector + [0.0] * (len(self.weights) - len(input_vector))
        dot = sum(w * x for w, x in zip(self.weights, input_vector[:len(self.weights)]))
        norm_w = math.sqrt(sum(w * w for w in self.weights)) or 1e-12
        norm_x = math.sqrt(sum(x * x for x in input_vector[:len(self.weights)])) or 1e-12
        self.confidence = max(0.0, min(1.0, (dot / (norm_w * norm_x) + 1) / 2))
        self.activation_count += 1
        self.last_activated = time.time()
        return self.confidence

    def learn(self, input_vector: List[float], reward: float):
        """Hebbian update: strengthen connections that fire together."""
        lr = COUPLING * abs(reward)
        for i in range(min(len(self.weights), len(input_vector))):
            self.weights[i] += lr * input_vector[i] * reward

    def to_dict(self) -> Dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════
# Gating Network -- routes inputs to experts by E8 proximity
# ═══════════════════════════════════════════════════════════════════════

class GatingNetwork:
    """The gate weights encode the E8 simple-root adjacency (Cartan matrix):
    root i couples +1 to itself and -1 to i+1 for the first six; alpha_7 = e6+e7;
    alpha_8 is the half-integer spinor root."""

    def __init__(self, num_experts: int = 8, dims: int = 24):
        self.num_experts = num_experts
        self.dims = dims
        self.gate_weights = [[0.0] * dims for _ in range(num_experts)]
        for i in range(min(num_experts, 8)):
            if i < 6:
                self.gate_weights[i][i] = 1.0
                self.gate_weights[i][i + 1] = -1.0
            elif i == 6:
                self.gate_weights[i][5] = 1.0
                self.gate_weights[i][6] = 1.0
            elif i == 7:
                for j in range(7):
                    self.gate_weights[i][j] = -0.5
                self.gate_weights[i][7] = 0.5

    def route(self, input_vector: List[float]) -> List[Tuple[int, float]]:
        x = input_vector[:self.dims]
        while len(x) < self.dims:
            x.append(0.0)
        scores = [(i, sum(g * v for g, v in zip(self.gate_weights[i], x)))
                  for i in range(self.num_experts)]
        scores.sort(key=lambda s: -s[1])
        return scores

    def update(self, expert_idx: int, input_vector: List[float], reward: float):
        x = input_vector[:self.dims]
        while len(x) < self.dims:
            x.append(0.0)
        lr = COUPLING * abs(reward)
        for j in range(self.dims):
            self.gate_weights[expert_idx][j] += lr * x[j] * reward


# ═══════════════════════════════════════════════════════════════════════
# TMN Brain -- the agent's reasoning layer (the weights)
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class TMNBrain:
    """8 L0 experts x 24 dims at start -> max 96 dims. 3 triads
    (Noether/Shannon/Landauer) = 3 E8 copies in Leech. Epoch 300: freeze."""
    brain_id: str = ""
    agent_id: str = ""
    dims: int = 24
    max_dims: int = 96
    epoch: int = 0
    frozen: bool = False
    experts: List[ExpertNode] = field(default_factory=list)
    gate: Optional[GatingNetwork] = None
    triad_noether: List[float] = field(default_factory=lambda: [0.0] * 8)
    triad_shannon: List[float] = field(default_factory=lambda: [0.0] * 8)
    triad_landauer: List[float] = field(default_factory=lambda: [0.0] * 8)
    mi_history: List[float] = field(default_factory=list)
    hebbian_lr: float = COUPLING
    journal: List[Dict] = field(default_factory=list)
    glyphs: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.brain_id:
            if self.agent_id:
                self.brain_id = brain_row_id(self.agent_id)
            else:
                raise ValueError("brain_id or agent_id required for stable brain identity")
        if not self.experts:
            self.experts = [ExpertNode(direction=i, domain=EXPERT_DOMAINS[i]) for i in range(8)]
        if not self.gate:
            self.gate = GatingNetwork(num_experts=8, dims=self.dims)

    def think(self, input_vector: List[float]) -> Dict:
        routing = self.gate.route(input_vector)
        activations = []
        for expert_idx, gate_score in routing[:3]:
            expert = self.experts[expert_idx]
            confidence = expert.activate(input_vector)
            activations.append({"expert": expert.domain, "direction": expert_idx,
                                "gate_score": round(gate_score, 4),
                                "confidence": round(confidence, 4)})
        x8 = (input_vector[:8] + [0.0] * 8)[:8]
        return {
            "brain_id": self.brain_id, "activations": activations,
            "triads": {
                "noether": round(sum(t * x for t, x in zip(self.triad_noether, x8)), 6),
                "shannon": round(sum(t * x for t, x in zip(self.triad_shannon, x8)), 6),
                "landauer": round(sum(t * x for t, x in zip(self.triad_landauer, x8)), 6),
            },
            "dims": self.dims, "epoch": self.epoch, "frozen": self.frozen,
        }

    def learn(self, input_vector: List[float], reward: float, context: str = ""):
        """Update the brain from experience. No-op if frozen. Advances epoch."""
        if self.frozen:
            return
        routing = self.gate.route(input_vector)
        best_idx = routing[0][0]
        self.experts[best_idx].learn(input_vector, reward)
        self.gate.update(best_idx, input_vector, reward)

        x8 = (input_vector[:8] + [0.0] * 8)[:8]
        lr = self.hebbian_lr * abs(reward)
        for i in range(8):
            self.triad_noether[i] += lr * x8[i] * (1 if reward < 0 else -1)
            self.triad_shannon[i] += lr * x8[i] * abs(reward)
            self.triad_landauer[i] -= lr * x8[i] * COUPLING

        self.mi_history.append(abs(reward))
        if len(self.mi_history) > 300:
            self.mi_history = self.mi_history[-300:]
        self.journal.append({"ts": time.time(), "expert": self.experts[best_idx].domain,
                             "reward": reward, "context": context[:100]})
        if len(self.journal) > 500:
            self.journal = self.journal[-500:]
        self.epoch += 1
        self.check_epoch_gate()

    def check_epoch_gate(self) -> bool:
        if self.epoch >= EPOCH_FREEZE and not self.frozen:
            self.frozen = True
            return True
        return False

    def grow_dims(self, new_dims: int):
        if self.frozen or new_dims <= self.dims or new_dims > self.max_dims:
            return
        self.dims = new_dims
        for expert in self.experts:
            expert.weights.extend([0.0] * (new_dims - len(expert.weights)))
        self.gate = GatingNetwork(num_experts=len(self.experts), dims=new_dims)

    def compress(self, ratio: float = 0.3) -> Dict:
        threshold = ratio * max((abs(w) for e in self.experts for w in e.weights), default=0)
        zeroed, total = 0, 0
        for expert in self.experts:
            for i in range(len(expert.weights)):
                total += 1
                if abs(expert.weights[i]) < threshold:
                    expert.weights[i] = 0.0
                    zeroed += 1
        return {"zeroed": zeroed, "total": total, "compression": zeroed / max(total, 1)}

    @staticmethod
    def _wnorm(e: ExpertNode) -> float:
        return math.sqrt(sum(w * w for w in e.weights))

    def dominant_expert(self) -> Dict[str, Any]:
        """The most-trained expert -- the one whose weights grew most under
        learning -- is the brain's specialization. Weight norm (not
        activation_count, which only inference bumps) is the signal that
        training actually populates. Used by the Carrier CEM to select
        firmware targets."""
        top = max(self.experts, key=self._wnorm)
        return {"domain": top.domain, "direction": top.direction,
                "weight_norm": round(self._wnorm(top), 4),
                "activation_count": top.activation_count}

    def specialist_profile(self) -> Dict[str, float]:
        """A label->score map over the 8 expert domains, derived from each
        expert's share of total trained weight norm. This is what the L3b
        coordinator persists and what select_methods reads."""
        norms = {e.domain: self._wnorm(e) for e in self.experts}
        total = sum(norms.values()) or 1.0
        return {d: round(n / total, 4) for d, n in norms.items() if n > 1e-9}

    def to_image(self) -> Dict:
        """Export the brain as a deployable image (the brain file format)."""
        return {
            "brain_id": self.brain_id, "agent_id": self.agent_id,
            "dims": self.dims, "epoch": self.epoch, "frozen": self.frozen,
            "experts": [e.to_dict() for e in self.experts],
            "triad_noether": self.triad_noether, "triad_shannon": self.triad_shannon,
            "triad_landauer": self.triad_landauer, "mi_history": self.mi_history[-50:],
            "hebbian_lr": self.hebbian_lr, "glyphs": self.glyphs[:100],
            "journal_size": len(self.journal),
        }


# ═══════════════════════════════════════════════════════════════════════
# Persistence (sqlite3, replacing the original psycopg2 layer)
# ═══════════════════════════════════════════════════════════════════════

def save_brain(brain: TMNBrain, db_path=None) -> None:
    conn = get_connection(db_path)
    try:
        now = time.time()
        created = brain.journal[0]["ts"] if brain.journal else now
        conn.execute(
            """INSERT INTO tmn_brains (brain_id, agent_id, dims, epoch, frozen, image, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(brain_id) DO UPDATE SET
                 dims=excluded.dims, epoch=excluded.epoch, frozen=excluded.frozen,
                 image=excluded.image, updated_at=excluded.updated_at""",
            (brain.brain_id, brain.agent_id, brain.dims, brain.epoch, int(brain.frozen),
             json.dumps(brain.to_image()), created, now),
        )
        conn.commit()
    finally:
        conn.close()


def load_brain(brain_id: str, db_path=None) -> Optional[TMNBrain]:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT image FROM tmn_brains WHERE brain_id = ?", (brain_id,)).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    data = json.loads(row["image"])
    brain = TMNBrain(brain_id=brain_id, agent_id=data.get("agent_id", ""),
                     dims=data.get("dims", 24), epoch=data.get("epoch", 0),
                     frozen=data.get("frozen", False))
    brain.gate = GatingNetwork(num_experts=8, dims=brain.dims)
    brain.triad_noether = data.get("triad_noether", [0.0] * 8)
    brain.triad_shannon = data.get("triad_shannon", [0.0] * 8)
    brain.triad_landauer = data.get("triad_landauer", [0.0] * 8)
    brain.hebbian_lr = data.get("hebbian_lr", COUPLING)
    brain.glyphs = data.get("glyphs", [])
    experts_data = data.get("experts", [])
    if experts_data:
        brain.experts = [ExpertNode(
            expert_id=ed.get("expert_id", ""), direction=ed.get("direction", 0),
            domain=ed.get("domain", ""), weights=ed.get("weights", [0.0] * brain.dims),
            activation_count=ed.get("activation_count", 0),
            confidence=ed.get("confidence", 0.0), last_activated=ed.get("last_activated", 0.0),
        ) for ed in experts_data]
    return brain


def register_brain(agent_id: str, dims: int = 24, db_path=None) -> TMNBrain:
    """Create a fresh learner brain for an agent and persist it."""
    row_id = brain_row_id(agent_id)
    brain = TMNBrain(agent_id=agent_id, brain_id=row_id, dims=dims)
    save_brain(brain, db_path)
    return brain


__all__ = [
    "ExpertNode", "GatingNetwork", "TMNBrain",
    "save_brain", "load_brain", "register_brain",
    "EXPERT_DOMAINS", "COUPLING", "EPOCH_FREEZE",
]
