"""
ChromaForge Conservation — ΔΦ = ΔN + ΔI + ΔL enforcement.

Three color sectors:
  N = Noether  (symmetry)     → color R
  I = Shannon  (information)  → color G
  L = Landauer (erasure)      → color B

Conservation law = color confinement: cumulative ΔΦ must remain ≤ 0.
Any single operation with ΔΦ > 0 is a violation.
The stop condition IS palindromic closure IS ΔΦ ≤ 0.
COUPLING = κ = ln(φ)/16 ≈ 0.030076.

Design: ConservationLedger is a class. Module-level singleton `ledger` available.
"""
import math
import time
from typing import Dict, List

# ─── Lookup tables (import-time, read-only) ────────────────────────────────────

PHI: float = (1 + math.sqrt(5)) / 2
COUPLING: float = math.log(PHI) / 16          # κ ≈ 0.030076

# Pre-computed sector weights (R, G, B) — equal thirds summing to COUPLING
_SECTOR_WEIGHT: float = COUPLING / 3.0

# Violation severity buckets for reporting
_SEVERITY: tuple = (
    (0.0,        "clean"),
    (COUPLING,   "minor"),
    (COUPLING * 3, "moderate"),
    (float("inf"), "severe"),
)


def _severity(dphi: float) -> str:
    for threshold, label in _SEVERITY:
        if dphi <= threshold:
            return label
    return "severe"


# ─── Engine class ──────────────────────────────────────────────────────────────

class ConservationLedger:
    """Tracks ΔΦ = ΔN + ΔI + ΔL across all operations in this context."""

    __slots__ = (
        "coupling",
        "_ledger", "_cumulative", "_violations", "_total",
        "_per_agent", "_per_service", "_per_operation", "_per_agent_violations",
    )

    def __init__(self, coupling: float = COUPLING):
        self.coupling: float = coupling
        self._ledger: List[Dict] = []
        self._cumulative: float = 0.0
        self._violations: int = 0
        self._total: int = 0
        self._per_agent: Dict[str, float] = {}
        self._per_service: Dict[str, float] = {}
        self._per_operation: Dict[str, float] = {}
        self._per_agent_violations: Dict[str, int] = {}

    # ── Core ───────────────────────────────────────────────────────────────────

    def track(
        self,
        delta_phi: float = 0.0,
        delta_n: float = 0.0,
        delta_i: float = 0.0,
        delta_l: float = 0.0,
        agent_id: str = "",
        service: str = "",
        atom_id: str = "",
        operation: str = "",
        epoch: int = 0,
    ) -> Dict:
        """Record one conservation report. Returns the entry with violation flag."""
        self._total += 1
        prev = self._cumulative

        entry: Dict = {
            "agent_id":         agent_id,
            "service":          service,
            "atom_id":          atom_id,
            "delta_phi":        delta_phi,
            "delta_n":          delta_n,
            "delta_i":          delta_i,
            "delta_l":          delta_l,
            "operation":        operation,
            "epoch":            epoch,
            "timestamp":        time.time(),
            "cumulative_before": prev,
        }

        self._cumulative += delta_phi
        entry["cumulative_after"] = self._cumulative

        self._per_agent[agent_id] = self._per_agent.get(agent_id, 0.0) + delta_phi
        self._per_service[service] = self._per_service.get(service, 0.0) + delta_phi
        self._per_operation[operation] = self._per_operation.get(operation, 0.0) + delta_phi

        violation = delta_phi > 0
        entry["violation"] = violation
        entry["severity"] = _severity(delta_phi) if violation else "clean"

        if violation:
            self._violations += 1
            self._per_agent_violations[agent_id] = (
                self._per_agent_violations.get(agent_id, 0) + 1
            )

        self._ledger.append(entry)
        return entry

    def check(self, delta_phi: float) -> bool:
        """True if this delta_phi satisfies the conservation law (≤ 0)."""
        return delta_phi <= 0

    def surplus(self) -> float:
        """Accumulated conservation surplus when cumulative < 0."""
        return abs(self._cumulative) if self._cumulative < 0 else 0.0

    def spendable(self) -> bool:
        """True when there is surplus to spend (cumulative < 0)."""
        return self._cumulative < 0

    def audit(self) -> Dict:
        """Recompute the cumulative from scratch and check for drift."""
        running = 0.0
        errors = []
        for i, entry in enumerate(self._ledger):
            expected = running
            got = entry.get("cumulative_before", expected)
            if abs(got - expected) > 1e-8:
                errors.append({
                    "index": i,
                    "expected": expected,
                    "got": got,
                    "agent_id": entry.get("agent_id"),
                })
            running += entry.get("delta_phi", 0.0)

        drift = abs(running - self._cumulative)
        return {
            "valid": not errors and drift < 1e-8,
            "memory_cumulative": round(self._cumulative, 6),
            "recomputed_cumulative": round(running, 6),
            "drift": drift,
            "chain_errors": errors[:20],
            "total_entries": len(self._ledger),
        }

    def stats(self) -> Dict:
        return {
            "cumulative_dphi": round(self._cumulative, 6),
            "total_checks": self._total,
            "violations": self._violations,
            "conservation_valid": self._violations == 0,
            "coupling": self.coupling,
            "surplus": self.surplus(),
            "spendable": self.spendable(),
            "by_agent": {
                k: round(v, 6)
                for k, v in sorted(self._per_agent.items(), key=lambda x: x[1])
            },
            "by_service": {k: round(v, 6) for k, v in self._per_service.items()},
            "by_operation": {k: round(v, 6) for k, v in self._per_operation.items()},
            "agent_violations": dict(self._per_agent_violations),
        }

    def ledger(self, limit: int = 20) -> List[Dict]:
        return self._ledger[-limit:]

    @property
    def cumulative(self) -> float:
        return self._cumulative

    @property
    def violations(self) -> int:
        return self._violations


# ─── Module-level singleton + forwarding ──────────────────────────────────────

ledger = ConservationLedger()

def track(*args, **kwargs) -> Dict:
    return ledger.track(*args, **kwargs)

def check(delta_phi: float) -> bool:
    return ledger.check(delta_phi)

def surplus() -> float:
    return ledger.surplus()

def stats() -> Dict:
    return ledger.stats()

def audit() -> Dict:
    return ledger.audit()
