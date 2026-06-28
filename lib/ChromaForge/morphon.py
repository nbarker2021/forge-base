"""ChromaForge Morphon — the kappa = ln(phi)/16 coupling and the conserved
morphon potential delta.

Distilled from CMPLX-TMN-main (profile repo) into the forge ring, joining the
existing ChromaForge.conservation ledger. Paper binding: CQE-paper-09
(Hamiltonian Temporal Emergence). The morphon potential delta is the
per-event change in the conserved field Phi; the conservation law
cumulative(Phi) <= 0 is a Hamiltonian/Lyapunov descent, and the ordered
ledger of deltas IS the emergent timeline.

The coupling constant:

    kappa = ln(phi) / 16,    phi = (1 + sqrt 5) / 2

It scales every interaction. A content item is embedded on the unit
7-sphere from its hash, then scaled by kappa, so the E8 coordinate has
norm exactly kappa and the per-event potential magnitude is bounded by
kappa * affinity.

ADJUDICATED SIGN CORRECTION (the load-bearing finding):
CMPLX-TMN-main carries an internal sign contradiction.
  - src/conservation/conservation.py: `is_violation = delta_phi > 0`, and
    /surplus reports `spendable = cumulative_dphi < 0`. So conserved means
    delta_phi <= 0; surplus is negative.
  - src/engine/engine.py: `morphon_delta = COUPLING * e8_norm * affinity`
    is strictly POSITIVE, with the comment "Positive delta means the
    processing added structure (conserved surplus)" — backwards: a positive
    delta is exactly what the conservation service flags as a violation.
The live ChromaForge/PaneForge Event Law receipt settles it: each event
mints delta_phi = -kappa (negative). EVENT_LAW_DELTA below is that value.
The conserved morphon emits delta_phi = -(kappa * ||e8|| * affinity) <= 0.

Stdlib only.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any

from .conservation import COUPLING, PHI, ConservationLedger

# The per-event Event Law potential: one conserved emission of -kappa.
# This is the exact value minted in every ChromaForge/PaneForge receipt.
EVENT_LAW_DELTA: float = -COUPLING


def kappa() -> float:
    """The coupling constant kappa = ln(phi) / 16."""
    return COUPLING


def e8_embed(content: str | bytes) -> list[float]:
    """Embed content on the kappa-sphere in 8D from its SHA-256 hash.

    Coordinates sit on the unit 7-sphere, then scale by kappa, so the
    returned vector has norm exactly kappa (up to rounding).
    """
    if isinstance(content, str):
        content = content.encode("utf-8")
    digest = hashlib.sha256(content).digest()
    raw = [(digest[i] - 128) / 128.0 for i in range(8)]
    norm = math.sqrt(sum(x * x for x in raw)) or 1.0
    return [round(x / norm * COUPLING, 10) for x in raw]


def morphon_delta(content: str | bytes, affinity: float = 1.0) -> float:
    """The conserved per-event potential change.

    Magnitude is kappa * ||e8|| * affinity; the sign is negative (conserved
    descent), correcting the source engine's positive convention.
    """
    e8 = e8_embed(content)
    e8_norm = math.sqrt(sum(x * x for x in e8))
    return round(-(COUPLING * e8_norm * max(affinity, 0.0)), 12)


def sector_split(delta_phi: float) -> dict[str, float]:
    """Decompose a conserved delta into the three sectors in equal thirds:
    Noether (symmetry), Shannon (information), Landauer (erasure)."""
    third = delta_phi / 3.0
    return {"delta_n": third, "delta_i": third, "delta_l": third}


# ─── Finite verifier (paper-bound claims, CQE-paper-09) ─────────────────────

def verify() -> dict[str, Any]:
    """Run the 10 finite checks binding the conservation law to CQE-paper-09."""
    checks: dict[str, bool] = {}

    # 1. kappa numeric value and the source constant 0.030076 agree
    k = kappa()
    checks["kappa_is_ln_phi_over_16"] = (
        abs(k - math.log(PHI) / 16) < 1e-15
        and abs(k - 0.030075739066) < 1e-9
    )

    # 2. Golden-ratio identities: phi^2 = phi + 1 and e^(16 kappa) = phi
    checks["golden_ratio_identities"] = (
        abs(PHI * PHI - (PHI + 1)) < 1e-12
        and abs(math.exp(16 * k) - PHI) < 1e-12
    )

    # 3. E8 embedding has norm exactly kappa (deterministic, content-keyed)
    e8 = e8_embed("conservation-law-probe")
    checks["e8_embed_norm_is_kappa"] = (
        abs(math.sqrt(sum(x * x for x in e8)) - k) < 1e-8
        and e8_embed("conservation-law-probe") == e8
    )

    # 4. The morphon delta is conserved (<= 0) and bounded by kappa*affinity
    d = morphon_delta("payload-A", affinity=1.0)
    checks["morphon_delta_conserved_and_bounded"] = (
        d <= 0 and abs(d) <= k + 1e-9
    )

    # 5. Sector split is additive: delta_n + delta_i + delta_l == delta_phi
    s = sector_split(d)
    checks["sector_split_additive"] = (
        abs(s["delta_n"] + s["delta_i"] + s["delta_l"] - d) < 1e-12
    )

    # 6. Event Law constant: per-event emission is exactly -kappa, the value
    #    minted in the live ChromaForge/PaneForge receipt
    checks["event_law_delta_is_minus_kappa"] = (
        EVENT_LAW_DELTA == -k
        and abs(EVENT_LAW_DELTA - (-0.030075739066225217)) < 1e-15
    )

    # 7. Conservation ledger: a stream of conserved deltas keeps cumulative
    #    non-increasing and raises zero violations
    led = ConservationLedger()
    cumulative = [0.0]
    for i in range(200):
        d_i = morphon_delta(f"event-{i}", affinity=(i % 5 + 1) / 5.0)
        led.track(delta_phi=d_i, operation="emit", agent_id="forge")
        cumulative.append(led.cumulative)
    monotone = all(cumulative[i + 1] <= cumulative[i] + 1e-12
                   for i in range(len(cumulative) - 1))
    checks["cumulative_monotone_non_increasing"] = (
        monotone and led.violations == 0
    )

    # 8. Violation detection: a single positive delta flips the law and is
    #    flagged (and only positive deltas are)
    led2 = ConservationLedger()
    led2.track(delta_phi=-k, operation="good")
    entry = led2.track(delta_phi=+k, operation="bad")
    checks["positive_delta_flagged_violation"] = (
        entry["violation"] is True
        and led2.violations == 1
        and led2.check(-k) is True
        and led2.check(+k) is False
    )

    # 9. Audit chain: recompute matches the running cumulative with no drift
    audit = led.audit()
    checks["audit_chain_zero_drift"] = (
        audit["valid"] and audit["drift"] < 1e-8
    )

    # 10. Surplus semantics: a conserved ledger has spendable negative surplus
    checks["surplus_is_spendable_when_negative"] = (
        led.spendable() and led.surplus() > 0
        and abs(led.surplus() - abs(led.cumulative)) < 1e-12
    )

    return {
        "forge": "ChromaForge",
        "module": "morphon",
        "paper": "CQE-paper-09",
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2))
