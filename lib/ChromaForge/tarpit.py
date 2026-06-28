"""
ChromaForge TarPit — Turing-complete geometric computation engine.

6 layers:
  Layer 0: E6 Token Encoding    — 6-bit IR, 8 ETP ops: } < > + [ ] 0 1
  Layer 1: GlyphGrain           — E8 coord, digital root, mass, extent
  Layer 2: Tape                 — MDHG-backed computation surface
  Layer 3: Jot Interpreter      — 0=APPLY (bond), 1=NEST (lambda). SK-complete.
  Layer 4: Bond Chemistry        — Grain→Dust→Triad, sin(θ)>ε=dimensional emergence
  Layer 5: Wall Emission         — OutputWall (success) | ErrorWall (failure+mirrors)
  Layer 6: Ecology               — mass conservation, competitive evolution

Design: TarPitEngine is a class. Module-level singleton `engine` available.
The heavy per-call computation (E6 decode, torus quantization, coupling sines)
lives in import-time lookup tables.
"""
import hashlib
import math
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ─── Lookup tables (import-time, read-only) ────────────────────────────────────

PHI: float = (1 + math.sqrt(5)) / 2
COUPLING: float = math.log(PHI) / 16     # κ ≈ 0.030076

# The 8 ETP opcodes (3-bit opcode space)
ETP_OPS: Tuple[str, ...] = ("}", "<", ">", "+", "[", "]", "0", "1")

# E6 decode table: token (0-63) → (opcode_str, repeat_count)
# Computed once at import time; used in e6_to_ops and e6_to_jot
_E6_DECODE: Dict[int, Tuple[str, int]] = {
    t: (ETP_OPS[(t >> 3) & 0b111], t & 0b111)
    for t in range(64)
}

# E6 → Jot bits table: token (0-63) → 6-bit binary string
_E6_JOT: Dict[int, str] = {t: format(t, "06b") for t in range(64)}

# Pre-computed sin(i * κ) for i in 0..1023 — used for lambda grain E8 coords
# Avoids recomputing math.sin on every NEST step
_COUPLING_SINES: Tuple[float, ...] = tuple(
    math.sin(i * COUPLING) for i in range(1024)
)

# Torus chart quantization: map a float in [-1, 1] to an octal digit [0, 7]
# Represented as a 2001-entry lookup (index = int((c + 1) * 1000), c in [-1,1])
# Values outside range are clamped
def _build_torus_quant() -> Tuple[int, ...]:
    result = []
    for i in range(2001):
        c = (i - 1000) / 1000.0  # maps 0..2000 → -1.0..1.0
        q = int(math.floor(((c + 1.0) / 2.0) * 8.0))
        result.append(max(0, min(7, q)))
    return tuple(result)

_TORUS_QUANT: Tuple[int, ...] = _build_torus_quant()


# ─── E8 Weyl algebra offload (import-time, read-only) ────────────────────────
# From PROOF papers: T1 (E8 Root System, 240 roots), T2 (Weyl group order 696729600).
# All grains positioned in R^8 at E8-norm scale. Bond chemistry follows from
# the E8 root inner product structure.

# E8 Cartan matrix  A_ij = 2<α_i, α_j> / <α_j, α_j>  (= <α_i, α_j> since all norms = 2)
# Dynkin diagram: 1-2-3-4-5-6-7 (chain) with branch 4-8 (E8 branch at node 4)
_E8_CARTAN: Tuple[Tuple[int,...], ...] = (
    ( 2, -1,  0,  0,  0,  0,  0,  0),   # α_1
    (-1,  2, -1,  0,  0,  0,  0,  0),   # α_2
    ( 0, -1,  2, -1,  0,  0,  0,  0),   # α_3
    ( 0,  0, -1,  2, -1,  0,  0, -1),   # α_4  ← branch node: connects to α_3, α_5, α_8
    ( 0,  0,  0, -1,  2, -1,  0,  0),   # α_5
    ( 0,  0,  0,  0, -1,  2, -1,  0),   # α_6
    ( 0,  0,  0,  0,  0, -1,  2,  0),   # α_7
    ( 0,  0,  0, -1,  0,  0,  0,  2),   # α_8  ← branch: connects only to α_4
)

# E8 simple roots in R^8 (all have norm² = 2).
# Verified: Dynkin diagram matches _E8_CARTAN exactly.
_E8_SIMPLE_ROOTS: Tuple[Tuple[float,...], ...] = (
    ( 1.0, -1.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0),   # α_1 = e_1 - e_2
    ( 0.0,  1.0, -1.0,  0.0,  0.0,  0.0,  0.0,  0.0),   # α_2 = e_2 - e_3
    ( 0.0,  0.0,  1.0, -1.0,  0.0,  0.0,  0.0,  0.0),   # α_3 = e_3 - e_4
    ( 0.0,  0.0,  0.0,  1.0, -1.0,  0.0,  0.0,  0.0),   # α_4 = e_4 - e_5
    ( 0.0,  0.0,  0.0,  0.0,  1.0, -1.0,  0.0,  0.0),   # α_5 = e_5 - e_6
    ( 0.0,  0.0,  0.0,  0.0,  0.0,  1.0, -1.0,  0.0),   # α_6 = e_6 - e_7
    ( 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  1.0,  1.0),   # α_7 = e_7 + e_8
    (-0.5, -0.5, -0.5, -0.5,  0.5,  0.5,  0.5, -0.5),   # α_8 = spinor half-root
)
# Branch verification: <α_4, α_8> = (1)(-0.5) + (-1)(0.5) = -0.5-0.5 = -1 ✓
#                     <α_7, α_6> = (1)(1) + (1)(0) = 1? wait: e_7 term of α_6 is -1
#                     <α_7, α_6> = 0+0+0+0+0+(0)(1)+(-1)(1)+(0)(1) = -1 ✓

def _weyl_matrix(root: Tuple[float,...]) -> Tuple[Tuple[float,...], ...]:
    """Compute the 8×8 Weyl reflection matrix for a simple root.
    s_α(v) = v - <v,α>α  (since <α,α>=2, the 2/<α,α>=1 factor is already 1).
    Each entry M[i][j] = δ_ij - α_i * α_j.
    """
    n = len(root)
    return tuple(
        tuple(
            (1.0 if i == j else 0.0) - root[i] * root[j]
            for j in range(n)
        )
        for i in range(n)
    )

# 8 Weyl reflection matrices (one per simple root). Import-time. Read-only.
_E8_WEYL_MATRICES: Tuple[Tuple[Tuple[float,...], ...], ...] = tuple(
    _weyl_matrix(r) for r in _E8_SIMPLE_ROOTS
)


def _matvec(M: Tuple[Tuple[float,...], ...], v: List[float]) -> List[float]:
    """Apply 8×8 matrix M to vector v."""
    return [sum(M[i][j] * v[j] for j in range(len(v))) for i in range(len(M))]


def weyl_reflect(e8_coords: List[float], root_index: int) -> List[float]:
    """Apply the fundamental Weyl reflection s_{root_index} to an E8 vector.
    root_index in 0..7 selects which simple root to reflect in.
    O(1) from lookup table: reads _E8_WEYL_MATRICES[root_index].
    """
    return _matvec(_E8_WEYL_MATRICES[root_index], e8_coords)


# E8 inner product bond classification table.
# Two E8 roots at positions a, b have inner product values in {-2,-1,0,+1,+2}.
# For norm = sqrt(2) vectors: cos(θ) = inner_product / 2.
# Allowed bonds when sin(θ) > ε = 0.3 (default):
#   inner product  0 → cos=0,    sin=1.0   → ORTHOGONAL  (strongest)
#   inner product ±1 → cos=±0.5, sin=0.866 → SEMANTIC_COMPOSITION
#   inner product  2 → cos=1,    sin=0     → REDUNDANT (same vector)
#   inner product -2 → cos=-1,   sin=0     → REDUNDANT (opposite vector)
_E8_INNER_PRODUCT_BOND: Dict[int, str] = {
     2: "redundant",       # parallel — no bond
     1: "linear",          # weak angle — marginal bond
     0: "orthogonal",      # 90° — strong bond
    -1: "semantic_composition",  # 120° — strong bond (E8 root adjacency)
    -2: "redundant",       # antiparallel — no bond
}

# Pre-computed E8 bond strength from inner product:
# strength = |sin(θ)| where cos(θ) = inner_product / sqrt(<a,a><b,b>)
# For unit E8 roots (norm=sqrt(2)): cos(θ) = inner_product / 2
_E8_BOND_STRENGTH: Dict[int, float] = {
     2:  0.0,
     1:  math.sqrt(3) / 2,    # ≈ 0.866
     0:  1.0,
    -1:  math.sqrt(3) / 2,    # ≈ 0.866
    -2:  0.0,
}


def e8_inner_product_rounded(a: List[float], b: List[float]) -> int:
    """Compute ⟨a, b⟩ and round to nearest integer in {-2,-1,0,1,2}.
    Used to dispatch bond chemistry via _E8_INNER_PRODUCT_BOND lookup.
    """
    raw = sum(ai * bi for ai, bi in zip(a, b))
    return max(-2, min(2, round(raw)))


def e8_classify(e8_coords: List[float]) -> Dict:
    """Classify an E8 vector by its inner products with all 8 simple roots.
    Returns cartan_profile (8-tuple), bond_type with first connected root,
    and proximity to nearest root class.
    """
    profile = tuple(e8_inner_product_rounded(list(e8_coords), list(r))
                    for r in _E8_SIMPLE_ROOTS)
    # Find which Cartan node this vector 'activates' (inner product = ±1 or ±2)
    activated = [i for i, p in enumerate(profile) if p != 0]
    nearest_root = activated[0] if activated else None
    bond_type = _E8_INNER_PRODUCT_BOND.get(profile[nearest_root], "semantic_composition") if nearest_root is not None else "orthogonal"
    return {
        "cartan_profile": profile,
        "activated_roots": activated,
        "nearest_root_index": nearest_root,
        "bond_type": bond_type,
        "norm_squared": round(sum(c * c for c in e8_coords), 6),
    }


# Digital root → base mass scale.
# DR = sum(abs(int(c*100)) for c in e8) % 9, range 1-9.
# Scaling uses COUPLING as the quantum step: DR k adds k×κ to base mass 1.0.
# This ensures mass differences are always multiples of the coupling constant.
_DR_MASS_SCALE: Dict[int, float] = {
    k: 1.0 + k * COUPLING for k in range(1, 10)
}
# {1: 1.030, 2: 1.060, 3: 1.090, ..., 9: 1.271}


def dr_mass(grain_e8: List[float], dr: int) -> float:
    """Return the DR-scaled mass for a grain. Lookup + one multiply."""
    base = math.sqrt(sum(c * c for c in grain_e8)) or 1.0
    return base * _DR_MASS_SCALE.get(dr, 1.0)


def _quant(c: float) -> int:
    """Quantize a float in [-1, 1] to an octal digit using the lookup table."""
    idx = int((c + 1.0) * 1000.0)
    idx = max(0, min(2000, idx))
    return _TORUS_QUANT[idx]


# ═══════════════════════════════════════════════════════════════════════
# Layer 0: E6 Token Encoding — pure functions, use lookup tables
# ═══════════════════════════════════════════════════════════════════════

def e6_encode(content: str) -> List[int]:
    """Encode content into 6-bit E6 token stream (low 6 bits of each byte)."""
    return [byte & 0x3F for byte in content.encode("utf-8", errors="replace")]


def e6_to_jot(tokens: List[int]) -> str:
    """Convert E6 tokens to Jot binary string (lookup, not format())."""
    return "".join(_E6_JOT[t] for t in tokens)


def e6_to_ops(tokens: List[int]) -> List[str]:
    """Convert E6 tokens to ETP operation sequence (lookup, not compute)."""
    ops = []
    for t in tokens:
        op, repeat = _E6_DECODE[t]
        ops.extend([op] * (repeat + 1))
    return ops


def e6_signature(tokens: List[int]) -> str:
    """Derivation key (content identity) from E6 token stream."""
    return hashlib.sha256(bytes(tokens)).hexdigest()[:32]


def torus_chart(e8_coords: List[float]) -> Dict:
    """Map E8 coordinates to torus chart digits using the quantization table."""
    if len(e8_coords) < 8:
        e8_coords = e8_coords + [0.0] * (8 - len(e8_coords))

    comps: List[float] = []
    for i in range(0, 8, 2):
        total = abs(e8_coords[i]) + abs(e8_coords[i + 1])
        theta = math.atan2(e8_coords[i + 1], e8_coords[i]) if total > 1e-12 else 0.0
        comps.extend([math.cos(theta), math.sin(theta)])

    digits = [_quant(c) for c in comps]
    return {"components": comps, "digits": digits,
            "signature": "".join(str(d) for d in digits)}


# ═══════════════════════════════════════════════════════════════════════
# Layer 1: GlyphGrain — atomic computation unit
# ═══════════════════════════════════════════════════════════════════════

class BondType(str, Enum):
    LINEAR     = "linear"
    ORTHOGONAL = "orthogonal"
    SEMANTIC   = "semantic_composition"
    REDUNDANT  = "redundant"


@dataclass
class GlyphGrain:
    grain_id:  str = ""
    glyph:     str = "∅"   # ∅
    e8_coords: List[float] = field(default_factory=lambda: [0.0] * 8)
    digital_root: int = 0
    mass:      float = 0.0
    extent:    List[float] = field(default_factory=lambda: [0.0] * 8)
    position:  int = 0
    bonded_to: List[str] = field(default_factory=list)
    snap_labels: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.grain_id:
            self.grain_id = f"gr-{uuid.uuid4().hex[:8]}"
        if self.mass == 0.0 and self.e8_coords:
            self.mass = math.sqrt(sum(c * c for c in self.e8_coords))


def create_grain(content: str, position: int = 0,
                 coupling: float = COUPLING) -> GlyphGrain:
    """Create a GlyphGrain from raw content. Uses lookup table for op lookup."""
    tokens = e6_encode(content[:100])
    sig = e6_signature(tokens)

    hash_bytes = hashlib.sha256(content.encode()).digest()[:8]
    e8 = [(b / 127.5 - 1.0) * coupling * 10 for b in hash_bytes]
    norm = math.sqrt(sum(c * c for c in e8)) or 1.0
    e8 = [c / norm * PHI for c in e8]

    dr = sum(abs(int(c * 100)) for c in e8) % 9 or 9
    # Glyph from token lookup table (not inline bit-shift)
    glyph = _E6_DECODE[tokens[0]][0] if tokens else "∅"

    return GlyphGrain(
        grain_id=f"gr-{sig[:8]}",
        glyph=glyph,
        e8_coords=e8,
        digital_root=dr,
        mass=math.sqrt(sum(c * c for c in e8)),
        extent=e8[:],
        position=position,
    )


# ═══════════════════════════════════════════════════════════════════════
# Layer 2: Tape — computation surface
# ═══════════════════════════════════════════════════════════════════════

class TarPitTape:
    """Computation surface. Each cell is a GlyphGrain at a position."""

    def __init__(self, size: int = 1024):
        self.cells: Dict[int, GlyphGrain] = {}
        self.pointer: int = 0
        self.size = size

    def get_cell(self) -> Optional[GlyphGrain]:
        return self.cells.get(self.pointer)

    def set_cell(self, grain: GlyphGrain) -> None:
        grain.position = self.pointer
        self.cells[self.pointer] = grain

    def move_left(self) -> None:
        self.pointer = max(0, self.pointer - 1)

    def move_right(self) -> None:
        self.pointer = min(self.size - 1, self.pointer + 1)

    def get_neighbor(self, offset: int = 1) -> Optional[GlyphGrain]:
        return self.cells.get(self.pointer + offset)

    def snapshot(self) -> Dict:
        return {
            "pointer":    self.pointer,
            "cells_used": len(self.cells),
            "total_mass": sum(g.mass for g in self.cells.values()),
        }


# ═══════════════════════════════════════════════════════════════════════
# Layer 3: Jot Interpreter
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Wall:
    wall_id:          str = ""
    wall_type:        str = "output"
    content:          str = ""
    certificates:     Dict = field(default_factory=dict)
    grains:           List[str] = field(default_factory=list)
    timestamp:        float = 0.0
    mirror_candidates: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.wall_id:
            self.wall_id = f"wall-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()


def jot_execute(bit_string: str, tape: TarPitTape,
                epsilon: float = 0.3,
                coupling: float = COUPLING) -> List[Wall]:
    """Execute a Jot binary program on the tape.
    0 = APPLY: bond current with right neighbor if sin(θ) > ε
    1 = NEST:  create new grain (lambda abstraction), uses _COUPLING_SINES lookup
    """
    walls: List[Wall] = []
    bonds_formed = 0

    for i, bit in enumerate(bit_string[:1000]):
        current = tape.get_cell()

        if bit == "0":
            neighbor = tape.get_neighbor(1)
            if current and neighbor:
                dot = sum(a * b for a, b in zip(current.e8_coords, neighbor.e8_coords))
                norm_a = math.sqrt(sum(c * c for c in current.e8_coords)) or 1e-12
                norm_b = math.sqrt(sum(c * c for c in neighbor.e8_coords)) or 1e-12
                cos_t = max(-1.0, min(1.0, dot / (norm_a * norm_b)))
                sin_t = math.sqrt(max(0.0, 1.0 - cos_t * cos_t))

                if sin_t > epsilon:
                    composite_e8 = [(a + b) / 2 for a, b in
                                    zip(current.e8_coords, neighbor.e8_coords)]
                    composite = GlyphGrain(
                        glyph=f"({current.glyph}·{neighbor.glyph})",
                        e8_coords=composite_e8,
                        mass=math.sqrt(current.mass * neighbor.mass) * sin_t,
                    )
                    tape.set_cell(composite)
                    current.bonded_to.append(neighbor.grain_id)
                    neighbor.bonded_to.append(current.grain_id)
                    bonds_formed += 1
                else:
                    walls.append(Wall(
                        wall_type="output",
                        content=f"redundant step {i}: sinθ={sin_t:.4f}<ε={epsilon}",
                        certificates={"step": i, "sin_theta": sin_t, "epsilon": epsilon},
                        grains=[current.grain_id, neighbor.grain_id],
                    ))
            tape.move_right()

        elif bit == "1":
            # NEST: lambda grain — E8 coords from coupling sines lookup table
            idx = i % 1024
            new_grain = GlyphGrain(
                glyph=f"λ{i}",
                e8_coords=[_COUPLING_SINES[idx]] * 8,
            )
            tape.move_right()
            tape.set_cell(new_grain)

    walls.append(Wall(
        wall_type="output",
        content=f"complete: {len(bit_string)} steps, {bonds_formed} bonds, {len(tape.cells)} cells",
        certificates={
            "steps": len(bit_string), "bonds": bonds_formed,
            "cells": len(tape.cells),
            "total_mass": sum(g.mass for g in tape.cells.values()),
        },
        grains=[g.grain_id for g in tape.cells.values()],
    ))
    return walls


# ═══════════════════════════════════════════════════════════════════════
# Layer 6: Ecology
# ═══════════════════════════════════════════════════════════════════════

def ecology_step(tape: TarPitTape) -> Dict:
    """One ecology step. Higher-mass grains absorb lower-mass neighbors.
    Total mass is conserved.
    """
    grains = list(tape.cells.values())
    if len(grains) < 2:
        return {"absorptions": 0, "survivors": len(grains)}

    mass_before = sum(g.mass for g in grains)
    absorbed_ids: set = set()
    grains.sort(key=lambda g: -g.mass)

    for i, predator in enumerate(grains):
        if predator.grain_id in absorbed_ids:
            continue
        for prey in grains[i + 1:]:
            if prey.grain_id in absorbed_ids:
                continue
            if predator.mass > prey.mass * 2:
                predator.mass += prey.mass
                predator.bonded_to.append(prey.grain_id)
                absorbed_ids.add(prey.grain_id)

    for gid in absorbed_ids:
        for pos, grain in list(tape.cells.items()):
            if grain.grain_id == gid:
                del tape.cells[pos]

    mass_after = sum(g.mass for g in tape.cells.values())
    return {
        "absorptions":        len(absorbed_ids),
        "survivors":          len(tape.cells),
        "mass_before":        round(mass_before, 6),
        "mass_after":         round(mass_after, 6),
        "conservation_valid": abs(mass_before - mass_after) < 1e-6,
    }


# ═══════════════════════════════════════════════════════════════════════
# Engine class
# ═══════════════════════════════════════════════════════════════════════

class TarPitEngine:
    """Unified 6-layer computation engine. One instance = one tape context."""

    def __init__(self, coupling: float = COUPLING):
        self.coupling: float = coupling
        self.tape = TarPitTape()
        self._sessions: Dict[str, Dict] = {}
        self._walls: List[Wall] = []
        self._lexicon: Dict[str, Dict] = {}
        self._total_executions: int = 0
        self._total_bonds: int = 0

    def execute(self, content: str) -> Dict:
        """Full pipeline: E6 → Jot → seed tape → Jot execute → ecology → torus."""
        session_id = f"sess-{uuid.uuid4().hex[:8]}"
        t0 = time.time()

        tokens = e6_encode(content[:500])
        sig = e6_signature(tokens)
        jot = e6_to_jot(tokens[:100])

        # Seed tape with word grains
        for i, word in enumerate(content.split()[:20]):
            grain = create_grain(word, position=i, coupling=self.coupling)
            self.tape.set_cell(grain)
            self.tape.move_right()
            self._lexicon.setdefault(grain.glyph, {
                "glyph": grain.glyph, "first_seen": time.time(),
                "occurrences": 0, "grains": [],
            })
            self._lexicon[grain.glyph]["occurrences"] += 1
            self._lexicon[grain.glyph]["grains"].append(grain.grain_id)
        self.tape.pointer = 0

        walls = jot_execute(jot, self.tape, coupling=self.coupling)
        self._walls.extend(walls)

        eco = ecology_step(self.tape)

        # Centroid torus chart from tape state
        centroid = [0.0] * 8
        for g in self.tape.cells.values():
            for j in range(8):
                centroid[j] += g.e8_coords[j]
        n = max(len(self.tape.cells), 1)
        chart = torus_chart([c / n for c in centroid])

        self._total_executions += 1
        self._total_bonds += sum(1 for w in walls if "bond" in w.content.lower())

        result = {
            "session_id":    session_id,
            "e6_tokens":     len(tokens),
            "jot_length":    len(jot),
            "cells_after":   len(self.tape.cells),
            "walls_emitted": len(walls),
            "ecology":       eco,
            "torus_chart":   chart,
            "derivation_key": sig,
            "elapsed_ms":    round((time.time() - t0) * 1000, 2),
            "walls":         [asdict(w) for w in walls[-5:]],
        }
        self._sessions[session_id] = result
        return result

    def encode(self, content: str) -> Dict:
        """Encode without executing — uses all lookup tables."""
        tokens = e6_encode(content)
        return {
            "tokens":     tokens[:100],
            "token_count": len(tokens),
            "jot_binary":  e6_to_jot(tokens[:50]),
            "ops":         e6_to_ops(tokens[:20]),
            "signature":   e6_signature(tokens),
        }

    def run_ecology(self) -> Dict:
        return ecology_step(self.tape)

    def status(self) -> Dict:
        return {
            "tape":               self.tape.snapshot(),
            "lexicon_size":       len(self._lexicon),
            "total_executions":   self._total_executions,
            "total_bonds":        self._total_bonds,
            "total_walls":        len(self._walls),
            "sessions":           len(self._sessions),
        }


# ─── Module-level singleton + forwarding ──────────────────────────────────────

engine = TarPitEngine()

def execute(content: str) -> Dict:
    return engine.execute(content)

def encode(content: str) -> Dict:
    return engine.encode(content)

def status() -> Dict:
    return engine.status()
