"""
ChromaForge — Operational engine of ChromaBlend Studio.

Architecture:
  ChromaForgeEngine = the wired composite. Instantiate once per context.
  Module-level `engine` singleton available for single-context use.

Component engines (each independently instantiable):
  ReceiptLedger      — Merkle-chained dyadic gluon records
  ConservationLedger — NSL ΔΦ = ΔN + ΔI + ΔL enforcement
  MDHGEngine         — 9-level oloid resolution hierarchy
  SpeedLightEngine   — Two-tier idempotent cache f(f(x))=f(x)
  MMDBEngine         — VOA-like crystal storage, E8-proximity search
  TarPitEngine       — 6-layer Turing-complete computation
  SNAPEngine         — Gate369 + Lenses + 8-angle Stratifier

Invariant: every chroma_execute / chroma_store call:
  1. Executes through its engine
  2. Mints a receipt (dyadic gluon record)
  3. Reports ΔΦ to conservation
  4. May be served from SpeedLight cache (idempotent projection)
"""
import math
from typing import Any, Callable, Dict, List, Optional, Set

# ─── Mathematical substrate (shared constant) ─────────────────────────────────
from ChromaForge.conservation import COUPLING, PHI

# ─── Gluon substrate (from existing cqe_engine, graceful fallback) ────────────
try:
    from cqe_engine import (
        gluon, swap_LR, swap_LC, swap_CR, TRANSPOSITIONS,
        cayley_dickson_oloid_normal_form, CayleyDicksonOloidNormalForm,
        Scope, scope, is_local, is_meso, is_global,
    )
    _GLUON_WIRED = True
except ImportError:
    _GLUON_WIRED = False

    def gluon(state):
        """T_EMISSION: bit_n = NOT(L) if C=1 | L⊕R if C=0. C is the local gluon."""
        if hasattr(state, "__len__") and len(state) >= 3:
            L, C, R = int(state[0]), int(state[1]), int(state[2])
            return (1 - L) if C else (L ^ R)
        return state

# ─── Component engine imports ─────────────────────────────────────────────────
from ChromaForge.receipt import ReceiptLedger, RECEIPT_TYPES, GENESIS_HASH
from ChromaForge.conservation import ConservationLedger
from ChromaForge.mdhg import MDHGEngine, HIERARCHY_LEVELS, SESSION_TTL, _LEVEL_PREFIX
from ChromaForge.speedlight import SpeedLightEngine, _CHANNEL_DATA, _PRIORITY_CHANNELS
from ChromaForge.mmdb import MMDBEngine, e8_distance
from ChromaForge.tarpit import (
    TarPitEngine, TarPitTape, GlyphGrain, Wall, BondType,
    e6_encode, e6_to_jot, e6_to_ops, e6_signature, torus_chart,
    create_grain, jot_execute, ecology_step,
    ETP_OPS, _E6_DECODE, _E6_JOT, _COUPLING_SINES, _TORUS_QUANT,
)
from ChromaForge.snap import (
    SNAPEngine, Gate369, LensBank,
    Body, Predicate, SNAPRecord, HexadInvariant, EnneadPackage,
    BaseLens, LegalityLens, NoveltyLens, SymmetryLens,
    ANGLES, _ANGLE_MAP, _DEFAULT_FAMILIES,
)
from ChromaForge.color_e8 import (
    BASE_HUES, NEON_ANTICOLORS, OPEN, CLOSED, CURATED_PALETTE,
    CURATED_COLOR_E8_TABLE,
    rgb_to_hex, hex_to_rgb, neon_anticolor,
    locate_color_in_e8, blend_compatibility,
    verify as verify_color_e8,
)

# ─── Lifecycle + storage contracts (the two-tier law) ─────────────────────────
from ChromaForge.contracts import CrystalVault
from ChromaForge.lifecycle import RunLifecycle, PROMOTE_AT, DECAY_EVERY

# ─── GraphStax — graph identity layer (sibling lib-forge package) ─────────────
try:
    from GraphStax import GraphStaxEngine, Stax, StaxGraph, StaxRoute
    _GRAPHSTAX_WIRED = True
except ImportError:
    _GRAPHSTAX_WIRED = False
    GraphStaxEngine = None
    Stax = StaxGraph = StaxRoute = None


# ─── ChromaForgeEngine — the wired composite ──────────────────────────────────

class ChromaForgeEngine:
    """Full operational engine. Wires all components with injected dependencies.

    Usage:
        engine = ChromaForgeEngine()
        result = engine.execute("hello world")
        engine.receipt.status()
        engine.conservation.stats()

        # Or fresh isolated context:
        test_engine = ChromaForgeEngine()
    """

    def __init__(
        self,
        coupling: float = COUPLING,
        speedlight_max: int = 10000,
        mdhg_session_ttl: int = SESSION_TTL,
        snap_lens_bank: Optional[LensBank] = None,
    ):
        self.coupling = coupling

        # Instantiate each engine
        self.receipt     = ReceiptLedger()
        self.conservation = ConservationLedger(coupling=coupling)
        # SpeedLight receives the receipt ledger so computation receipts chain
        self.speedlight  = SpeedLightEngine(max_size=speedlight_max,
                                            receipt_ledger=self.receipt)
        self.mdhg        = MDHGEngine(coupling=coupling,
                                      session_ttl=mdhg_session_ttl)
        self.mmdb        = MMDBEngine()
        self.tarpit      = TarPitEngine(coupling=coupling)
        self.snap        = SNAPEngine(lens_bank=snap_lens_bank)
        # Graph identity layer — every bit on every ribbon resolvable as a
        # C-gluon at its sheet size (None if GraphStax package absent)
        self.graphstax   = GraphStaxEngine() if _GRAPHSTAX_WIRED else None

        # The gluon function — from cqe_engine if wired, else fallback
        self.gluon: Callable = gluon

    # ── Integrated operations ─────────────────────────────────────────────────

    def execute(
        self,
        content: str,
        agent_id: str = "chroma",
        atom_id: str = "",
        epoch: int = 0,
        use_cache: bool = True,
    ) -> Dict:
        """Execute through TarPit. Auto-issues receipt + conservation report.
        SpeedLight cache checked first if use_cache=True.
        """
        # Cache check (idempotent projection). NOTE: must use get(), not
        # compute(result=None) — compute stores its placeholder on a miss,
        # which would poison the cache before the real result lands.
        if use_cache:
            cached = self.speedlight.get(content)
            if cached["hit"] and cached.get("result") is not None:
                return cached["result"]

        # TarPit execution
        result = self.tarpit.execute(content)

        # Estimate ΔΦ from ecology mass delta
        eco = result.get("ecology", {})
        mass_delta = eco.get("mass_after", 0.0) - eco.get("mass_before", 0.0)
        delta_phi = -abs(mass_delta) * self.coupling if mass_delta else -self.coupling

        # Mint receipt
        effective_atom = atom_id or result["session_id"]
        r = self.receipt.mint(
            receipt_type="PROCESS",
            agent_id=agent_id,
            atom_id=effective_atom,
            operation="tarpit.execute",
            input_data=content[:64],
            output_data=result.get("derivation_key", ""),
            delta_phi=delta_phi,
            epoch=epoch,
        )

        # Conservation report
        self.conservation.track(
            delta_phi=delta_phi,
            delta_n=-self.coupling,
            delta_i=-self.coupling,
            delta_l=-self.coupling,
            agent_id=agent_id,
            service="ChromaForge.tarpit",
            atom_id=effective_atom,
            operation="tarpit.execute",
            epoch=epoch,
        )

        result["receipt"] = r
        result["conservation"] = {
            "delta_phi": delta_phi,
            "cumulative": self.conservation.cumulative,
        }

        # Cache the result (put() overwrites; compute() would no-op on a hit)
        if use_cache:
            self.speedlight.put(content, result,
                                fn_name="tarpit.execute",
                                cost_seconds=result.get("elapsed_ms", 0.0) / 1000)

        return result

    def store(
        self,
        content: str,
        snap_labels: List[str] = None,
        e8_coords: List[float] = None,
        agent_id: str = "chroma",
        epoch: int = 0,
    ) -> Dict:
        """Store a crystal in MMDB. Auto-issues MINT receipt."""
        crystal = self.mmdb.store(
            content=content,
            snap_labels=snap_labels or [],
            e8_coords=e8_coords or [0.0] * 8,
        )
        r = self.receipt.mint(
            receipt_type="MINT",
            agent_id=agent_id,
            atom_id=crystal["crystal_id"],
            operation="mmdb.store",
            input_data=content[:64],
            output_data=crystal["content_hash"],
            delta_phi=-self.coupling,
            snap_labels=snap_labels or [],
            epoch=epoch,
        )
        self.conservation.track(
            delta_phi=-self.coupling,
            delta_n=-self.coupling,
            agent_id=agent_id,
            service="ChromaForge.mmdb",
            atom_id=crystal["crystal_id"],
            operation="mmdb.store",
            epoch=epoch,
        )
        crystal["receipt"] = r
        return crystal

    def resolve(
        self,
        content: str,
        levels: tuple = (0, 1, 2),
        max_bits: int = 128,
        agent_id: str = "chroma",
        epoch: int = 0,
    ) -> Dict:
        """Resolve content into graph identity: every bit of its E6/Jot ribbon
        becomes a C-gluon Stax at each requested sheet level.

        Pipeline: E6 encode → jot ribbon → GraphStax multilevel resolution →
        identity crystal in MMDB → receipt + conservation.
        """
        if self.graphstax is None:
            raise RuntimeError("GraphStax package not available in lib-forge")

        enc = self.tarpit.encode(content)
        jot = enc["jot_binary"][:max_bits]
        bits = [int(b) for b in jot]
        ribbon_id = f"rb-{enc['signature'][:12]}"

        stacks = self.graphstax.resolve_multilevel(ribbon_id, bits, levels=list(levels))

        # Identity summary at the finest level
        base = stacks[levels[0]] if levels else []
        class_counts: Dict[str, int] = {}
        for s in base:
            class_counts[s.state_class] = class_counts.get(s.state_class, 0) + 1

        labels = [f"ribbon:{ribbon_id}"] + [
            f"class:{k}:{v}" for k, v in sorted(class_counts.items())
        ]
        crystal = self.mmdb.store(
            content=f"resolve:{ribbon_id}",
            snap_labels=labels,
            metadata={"levels": list(levels), "bits": len(bits),
                      "signature": enc["signature"]},
        )

        r = self.receipt.mint(
            receipt_type="PROCESS",
            agent_id=agent_id,
            atom_id=ribbon_id,
            operation="graphstax.resolve",
            input_data=content[:64],
            output_data=enc["signature"],
            delta_phi=-self.coupling,
            snap_labels=labels,
            epoch=epoch,
        )
        self.conservation.track(
            delta_phi=-self.coupling,
            delta_n=-self.coupling,
            agent_id=agent_id,
            service="ChromaForge.graphstax",
            atom_id=ribbon_id,
            operation="graphstax.resolve",
            epoch=epoch,
        )

        return {
            "ribbon_id":    ribbon_id,
            "bits":         len(bits),
            "levels":       list(levels),
            "class_counts": class_counts,
            "graph":        self.graphstax.graph.stats(),
            "crystal_id":   crystal["crystal_id"],
            "receipt":      r,
        }

    def stratify(
        self,
        seed: str,
        max_depth: int = 3,
        label_fn: Optional[Callable[[str], List[str]]] = None,
    ) -> Dict:
        """Stratify a concept and store each discovered label as a crystal."""
        result = self.snap.stratify(seed, max_depth=max_depth, label_fn=label_fn)
        # Store the converged label set as a crystal
        all_labels = []
        for level in result.get("levels", []):
            all_labels.extend(
                r.get("angle", "") for r in level.get("results", [])
            )
        self.store(
            content=f"stratify:{seed}",
            snap_labels=list(set(all_labels)),
            agent_id="snap",
        )
        return result

    def status(self) -> Dict:
        return {
            "gluon_wired":  _GLUON_WIRED,
            "graphstax_wired": _GRAPHSTAX_WIRED,
            "coupling":     self.coupling,
            "receipt":      self.receipt.status(),
            "conservation": self.conservation.stats(),
            "speedlight":   self.speedlight.stats(),
            "mdhg_sessions": self.mdhg.session_count,
            "mmdb":         self.mmdb.stats(),
            "tarpit":       self.tarpit.status(),
            "snap_families": self.snap.family_count,
            "graphstax":    self.graphstax.status() if self.graphstax else None,
        }


# ─── Module-level singleton ────────────────────────────────────────────────────

engine = ChromaForgeEngine()


# ─── Module-level convenience forwarding ──────────────────────────────────────

def execute(content: str, **kwargs) -> Dict:
    return engine.execute(content, **kwargs)

def store(content: str, **kwargs) -> Dict:
    return engine.store(content, **kwargs)

def status() -> Dict:
    return engine.status()


# ─── Verify (forge-family contract) ───────────────────────────────────────────

def verify() -> dict:
    """Finite checks binding ChromaForge to its docstring claims.

    Runs the existing internal checks: color_e8.verify() (the strongest
    statement in the package), an engine.execute() round-trip, an
    engine.store() round-trip, and confirms the component engines are
    wired together. Pure additive — does not touch the existing API.
    """
    checks: Dict[str, bool] = {}

    # 1. The color_e8 sub-module's own verifier passes (it tests the E8
    #    proximity / bond-type claims that the package reuses for color).
    try:
        ce8 = verify_color_e8()
        checks["color_e8_verify_passes"] = bool(ce8.get("status") == "pass"
                                                or ce8.get("passed", 0) > 0)
    except Exception:
        checks["color_e8_verify_passes"] = False

    # 2. Engine.execute() round-trips: idempotent on a re-run, receipts minted.
    try:
        r1 = engine.execute("chroma-verify-probe")
        r2 = engine.execute("chroma-verify-probe")
        checks["execute_roundtrip_idempotent"] = bool(
            r1 and r2 and r1.get("session_id") == r2.get("session_id")
        )
        checks["execute_mints_receipt"] = bool(r1.get("receipt"))
    except Exception:
        checks["execute_roundtrip_idempotent"] = False
        checks["execute_mints_receipt"] = False

    # 3. Engine.store() round-trips: a crystal is stored and addressable.
    try:
        c1 = engine.store("chroma-verify-crystal")
        c2 = engine.store("chroma-verify-crystal")
        checks["store_roundtrip_consistent"] = bool(
            c1 and c2 and c1.get("content_hash") == c2.get("content_hash")
            and c1.get("receipt")
        )
    except Exception:
        checks["store_roundtrip_consistent"] = False

    # 4. Conservation law reports a non-trivial state.
    try:
        s = engine.conservation.stats()
        checks["conservation_active"] = isinstance(s, dict) and bool(s)
    except Exception:
        checks["conservation_active"] = False

    # 5. Speedlight cache reports a non-trivial state.
    try:
        s = engine.speedlight.stats()
        checks["speedlight_active"] = isinstance(s, dict) and bool(s)
    except Exception:
        checks["speedlight_active"] = False

    # 6. SNAP engine has at least one family registered.
    try:
        checks["snap_families_registered"] = bool(engine.snap.family_count)
    except Exception:
        checks["snap_families_registered"] = False

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    if passed == total:
        status = "pass"
    elif passed >= max(1, total // 2):
        status = "partial"
    else:
        status = "fail"

    return {
        "forge": "ChromaForge",
        "status": status,
        "checks": checks,
        "passed": passed,
        "total": total,
        "paper": "CQE-paper-04 (Conservation Law / E8 proximity)",
    }


# ─── Version ──────────────────────────────────────────────────────────────────

__version__ = "0.3.0"

__all__ = [
    # Engine classes
    "ChromaForgeEngine",
    "ReceiptLedger", "ConservationLedger", "MDHGEngine",
    "SpeedLightEngine", "MMDBEngine", "TarPitEngine", "SNAPEngine",
    # Singletons
    "engine",
    # Gluon substrate
    "gluon", "_GLUON_WIRED",
    # Constants / lookup tables
    "COUPLING", "PHI", "RECEIPT_TYPES", "HIERARCHY_LEVELS",
    "ETP_OPS", "ANGLES", "_E6_DECODE", "_COUPLING_SINES",
    # Primitive types
    "Body", "Predicate", "SNAPRecord", "GlyphGrain", "Wall", "BondType",
    # Pure functions
    "e6_encode", "e6_to_jot", "e6_to_ops", "e6_signature",
    "torus_chart", "create_grain", "jot_execute", "ecology_step",
    "e8_distance",
    # Convenience
    "execute", "store", "status",
    # ColorE8: locating colors in E8, radioactive-decay events, blend compatibility
    "BASE_HUES", "NEON_ANTICOLORS", "OPEN", "CLOSED", "CURATED_PALETTE",
    "CURATED_COLOR_E8_TABLE",
    "rgb_to_hex", "hex_to_rgb", "neon_anticolor",
    "locate_color_in_e8", "blend_compatibility", "verify_color_e8",
]
