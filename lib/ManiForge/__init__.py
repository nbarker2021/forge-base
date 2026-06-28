"""ManiForge — Braid, Knot, Seam, Crease Algebra

Public surface for the string topology engine underlying workbook operations.
All workbook strings map to these primitives.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional

# ---------------------------------------------------------------------------
# Braid Group B₃ (3 strands = L, C, R / 3 frames = C/R/L-centroid)
# ---------------------------------------------------------------------------

class BraidGenerator(Enum):
    """Generators of B₃ = ⟨σ₁, σ₂, σ₃ | σ₁σ₂σ₁=σ₂σ₁σ₂, σ₁σ₃=σ₃σ₁, ...⟩"""
    SIGMA_1 = "σ₁"   # swap_LR (antipodal) — red string, side-flip
    SIGMA_2 = "σ₂"   # swap_LC — blue string, frame transition C→L
    SIGMA_3 = "σ₃"   # swap_CR — gold string, frame transition C→R


@dataclass(frozen=True)
class BraidWord:
    """A word in B₃ generators."""
    generators: Tuple[BraidGenerator, ...]
    
    def __mul__(self, other: "BraidWord") -> "BraidWord":
        return BraidWord(self.generators + other.generators)
    
    def inverse(self) -> "BraidWord":
        return BraidWord(tuple(reversed(self.generators)))
    
    def __str__(self) -> str:
        return "".join(g.value for g in self.generators)

# Important braid words
Z4_CYCLE = BraidWord((BraidGenerator.SIGMA_1, BraidGenerator.SIGMA_2, 
                       BraidGenerator.SIGMA_3, BraidGenerator.SIGMA_2))  # σ₁σ₂σ₃σ₂
TRIALITY_ROTATION = BraidWord((BraidGenerator.SIGMA_1, BraidGenerator.SIGMA_2, 
                                BraidGenerator.SIGMA_3))  # σ₁σ₂σ₃

# ---------------------------------------------------------------------------
# Knot Invariants
# ---------------------------------------------------------------------------

class KnotType(Enum):
    UNKNOT = "unknot"                    # Period-1 true vacuum
    TORUS_2_5 = "torus(2,5)"             # Period-4 excited state
    TORUS_3_4 = "torus(3,4)"             # Higher excitation
    COMPOSITE = "composite"              # Decay product knot

@dataclass(frozen=True)
class KnotInvariant:
    """Knot invariant bundle for a closed braid word."""
    knot_type: KnotType
    alexander_poly: str                  # e.g., "1", "t-1+t^-1"
    jones_poly: str                      # e.g., "1", "q+q^-1-q^2"
    homfly_pt: str                       # Full HOMFLY-PT
    
    @classmethod
    def from_period(cls, z4_period: int) -> "KnotInvariant":
        if z4_period == 1:
            return cls(KnotType.UNKNOT, "1", "1", "1")
        elif z4_period == 4:
            return cls(KnotType.TORUS_2_5, "t-1+t^-1", "q+q^-1-q^2", "...")
        return cls(KnotType.COMPOSITE, "...", "...", "...")


# ---------------------------------------------------------------------------
# Seams (frame boundaries where Gluon crosses)
# ---------------------------------------------------------------------------

class SeamType(Enum):
    C_TO_R = "C→R"        # Frame 0→1
    R_TO_CFLIP = "R→C'"   # Frame 1→2  
    CFLIP_TO_L = "C'→L"   # Frame 2→3
    L_TO_C = "L→C"        # Frame 3→0


@dataclass(frozen=True)
class Seam:
    """A frame boundary crossing with Gluon transport."""
    seam_type: SeamType
    gluon_before: int        # C value before crossing
    gluon_after: int         # C value after crossing (invariant)
    certificate: str         # "C invariant across seam"
    
    @classmethod
    def from_transition(cls, frame_from: int, frame_to: int, C: int) -> "Seam":
        seam_map = {
            (0, 1): SeamType.C_TO_R,
            (1, 2): SeamType.R_TO_CFLIP,
            (2, 3): SeamType.CFLIP_TO_L,
            (3, 0): SeamType.L_TO_C,
        }
        return cls(seam_map[(frame_from, frame_to)], C, C, "Gluon invariant")


# ---------------------------------------------------------------------------
# Creases (sharp topological transitions)
# ---------------------------------------------------------------------------

class CreaseType(Enum):
    OLOID_FOLD = "oloid_fold"          # N|-N midpoint formation
    CHAMBER_REFLECTION = "reflection"  # L=R boundary reflection
    ANTIPODE_FLIP = "antipode_flip"    # LR swap
    K_WINDOW_BREACH = "k_breach"       # K>9 boundary


@dataclass(frozen=True)
class Crease:
    """A non-smooth topological transition with certificates."""
    crease_type: CreaseType
    location: str                    # "oloid_midpoint", "L=R_plane", etc.
    gluon_invariant: bool            # C preserved?
    certificate: str

    @classmethod
    def oloid_fold(cls, C: int) -> "Crease":
        return cls(CreaseType.OLOID_FOLD, "s* = (N+-N)/2", True, f"C={C} mediator invariant")
    
    @classmethod
    def chamber_reflection(cls, C: int) -> "Crease":
        return cls(CreaseType.CHAMBER_REFLECTION, "L=R plane", True, f"C={C} invariant under LR swap")


# ---------------------------------------------------------------------------
# Workbook String → ManiForge Primitive Map
# ---------------------------------------------------------------------------

WORKBOOK_TO_MANIFORGE = {
    "red_string": BraidGenerator.SIGMA_1,      # side-flip / antipodal
    "blue_string": BraidGenerator.SIGMA_2,     # C↔L frame transition
    "gold_string": BraidGenerator.SIGMA_3,     # C↔R frame transition / repair
    "white_string": Z4_CYCLE,                  # Z4 period template
    "knot_true_vacuum": KnotType.UNKNOT,       # period-1
    "knot_excited": KnotType.TORUS_2_5,        # period-4
    "seam_C_R": SeamType.C_TO_R,
    "seam_R_Cflip": SeamType.R_TO_CFLIP,
    "seam_Cflip_L": SeamType.CFLIP_TO_L,
    "seam_L_C": SeamType.L_TO_C,
    "crease_oloid": CreaseType.OLOID_FOLD,
    "crease_reflection": CreaseType.CHAMBER_REFLECTION,
    "crease_antipode": CreaseType.ANTIPODE_FLIP,
    "crease_k_breach": CreaseType.K_WINDOW_BREACH,
}


# ---------------------------------------------------------------------------
# Public Surface
# ---------------------------------------------------------------------------

__all__ = [
    "BraidGenerator",
    "BraidWord",
    "Z4_CYCLE",
    "TRIALITY_ROTATION",
    "KnotType",
    "KnotInvariant",
    "SeamType",
    "Seam",
    "CreaseType",
    "Crease",
    "WORKBOOK_TO_MANIFORGE",
]


# ─── Verify (forge-family contract) ───────────────────────────────────────────

def verify() -> dict:
    """Finite checks binding ManiForge to its docstring claims.

    Tests the B3 braid algebra (concatenation, inverse), the knot
    invariant factory, the seam map (frame transitions 0->1->2->3->0),
    and the workbook-string -> ManiForge-primitive map. Pure additive.
    """
    checks = {}

    # 1. BraidWord concatenation and inverse
    try:
        s1 = BraidWord((BraidGenerator.SIGMA_1,))
        s2 = BraidWord((BraidGenerator.SIGMA_2,))
        prod = s1 * s2
        inv = prod.inverse()
        checks["braid_concat_inverse"] = (
            len(prod.generators) == 2
            and prod.generators[0] is BraidGenerator.SIGMA_1
            and prod.generators[1] is BraidGenerator.SIGMA_2
            and inv.generators == (BraidGenerator.SIGMA_2, BraidGenerator.SIGMA_1)
            and str(prod) == "σ₁σ₂"
        )
    except Exception:
        checks["braid_concat_inverse"] = False

    # 2. Z4_CYCLE is the documented 4-letter word, TRIALITY_ROTATION is 3
    try:
        checks["z4_cycle_is_4_letters"] = (
            len(Z4_CYCLE.generators) == 4
            and Z4_CYCLE.generators[0] is BraidGenerator.SIGMA_1
            and Z4_CYCLE.generators[-1] is BraidGenerator.SIGMA_2
        )
        checks["triality_rotation_is_3_letters"] = (
            len(TRIALITY_ROTATION.generators) == 3
            and all(g is BraidGenerator(i + 1) for i, g in
                    enumerate(TRIALITY_ROTATION.generators))
        )
    except Exception:
        checks["z4_cycle_is_4_letters"] = False
        checks["triality_rotation_is_3_letters"] = False

    # 3. Knot invariant factory: period 1 -> UNKNOT, period 4 -> TORUS_2_5
    try:
        k1 = KnotInvariant.from_period(1)
        k4 = KnotInvariant.from_period(4)
        checks["knot_invariant_factory"] = (
            k1.knot_type is KnotType.UNKNOT
            and k4.knot_type is KnotType.TORUS_2_5
            and k4.alexander_poly == "t-1+t^-1"
        )
    except Exception:
        checks["knot_invariant_factory"] = False

    # 4. Seam map: every (frame_from, frame_to) pair in {0,1,2,3} maps
    #    to a distinct SeamType, and C is invariant under the seam.
    try:
        s01 = Seam.from_transition(0, 1, C=1)
        s12 = Seam.from_transition(1, 2, C=1)
        s23 = Seam.from_transition(2, 3, C=1)
        s30 = Seam.from_transition(3, 0, C=1)
        seam_types = {s01.seam_type, s12.seam_type, s23.seam_type, s30.seam_type}
        checks["seam_map_complete"] = (
            len(seam_types) == 4
            and s01.gluon_before == s01.gluon_after == 1
        )
    except Exception:
        checks["seam_map_complete"] = False

    # 5. Crease factory: oloid_fold and chamber_reflection both
    #    preserve C (gluon_invariant=True)
    try:
        co = Crease.oloid_fold(C=1)
        cr = Crease.chamber_reflection(C=1)
        checks["crease_factories_preserve_c"] = (
            co.gluon_invariant and cr.gluon_invariant
            and co.crease_type is CreaseType.OLOID_FOLD
            and cr.crease_type is CreaseType.CHAMBER_REFLECTION
        )
    except Exception:
        checks["crease_factories_preserve_c"] = False

    # 6. Workbook-to-ManiForge map: every documented workbook string
    #    resolves to a known primitive (or to Z4_CYCLE for the period
    #    template), and red/blue/gold strings map to sigma_1/2/3.
    try:
        checks["workbook_red_string_is_sigma1"] = (
            WORKBOOK_TO_MANIFORGE["red_string"] is BraidGenerator.SIGMA_1
        )
        checks["workbook_blue_string_is_sigma2"] = (
            WORKBOOK_TO_MANIFORGE["blue_string"] is BraidGenerator.SIGMA_2
        )
        checks["workbook_gold_string_is_sigma3"] = (
            WORKBOOK_TO_MANIFORGE["gold_string"] is BraidGenerator.SIGMA_3
        )
        checks["workbook_white_string_is_z4"] = (
            WORKBOOK_TO_MANIFORGE["white_string"] is Z4_CYCLE
        )
    except Exception:
        checks["workbook_red_string_is_sigma1"] = False
        checks["workbook_blue_string_is_sigma2"] = False
        checks["workbook_gold_string_is_sigma3"] = False
        checks["workbook_white_string_is_z4"] = False

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    if passed == total:
        status = "pass"
    elif passed >= max(1, total // 2):
        status = "partial"
    else:
        status = "fail"

    return {
        "forge": "ManiForge",
        "status": status,
        "checks": checks,
        "passed": passed,
        "total": total,
        "paper": "CQE-paper-03 (D4/J3 triality surface: braid group B3)",
    }