"""SentinelForge — correction-surface monitoring with exact deviation proofs.

Distilled from product_sentinel (historical_pastworks) into the forge ring.
Paper binding: CQE-paper-02 (Correction Surface). A sentinel alert is a
correction-surface receipt: a measured deviation from the VOA partition law
logged as data with an exact proof, never a silent guess (Axiom 00.3,
Boundary Positivity).

The partition law over the 8 LCR triads:
  deep invariants   {000, 111}            geometry level 0   (2 states)
  level-1 invariants{010, 101}            geometry level 1   (2 states)
  variable          {001, 011, 100, 110}  geometry level 2   (4 states)
Expected deep-invariant fraction in an unbiased stream: 2/8 = 0.25.

Adjudicated divergences from the source product:
  1. product_sentinel switched to a normal approximation for n > 100;
     SentinelForge computes the exact two-tailed binomial tail with
     math.comb for every n.
  2. The async/API/agent layers stay product-side; the forge carries only
     the proven monitoring core.

Stdlib only.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any, Iterable

ALL_TRIADS: list[tuple[int, int, int]] = [
    (L, C, R) for L in (0, 1) for C in (0, 1) for R in (0, 1)
]

DEEP_INVARIANTS = frozenset({(0, 0, 0), (1, 1, 1)})
LEVEL1_INVARIANTS = frozenset({(0, 1, 0), (1, 0, 1)})
LIE_CONJUGATES = frozenset(s for s in ALL_TRIADS if s[0] == s[2])
VARIABLE_TRIADS = frozenset(s for s in ALL_TRIADS if s not in LIE_CONJUGATES)

EXPECTED_INVARIANT_RATIO = 0.25  # 2/8 deep invariants

SEVERITY_LADDER = ["nominal", "elevated", "warning", "critical", "emergency"]


def rule30_emit(triad: tuple[int, int, int]) -> int:
    L, C, R = triad
    return L ^ (C | R)


def rule90_emit(triad: tuple[int, int, int]) -> int:
    L, _, R = triad
    return L ^ R


def correction_bit(triad: tuple[int, int, int]) -> int:
    """The Paper 2 correction surface bit: C AND (NOT R)."""
    _, C, R = triad
    return C & (1 - R)


def geometry_level(triad: tuple[int, int, int]) -> int:
    if triad in DEEP_INVARIANTS:
        return 0
    if triad in LIE_CONJUGATES:
        return 1
    return 2


def classify_triad(triad: tuple[int, int, int]) -> dict[str, Any]:
    return {
        "triad": list(triad),
        "syndrome_index": ALL_TRIADS.index(triad),
        "deep_invariant": triad in DEEP_INVARIANTS,
        "level1_invariant": triad in LEVEL1_INVARIANTS,
        "lie_conjugate": triad in LIE_CONJUGATES,
        "variable": triad in VARIABLE_TRIADS,
        "geometry_level": geometry_level(triad),
        "rule30_emission": rule30_emit(triad),
        "rule90_prior": rule90_emit(triad),
        "correction_bit": correction_bit(triad),
    }


@dataclass(frozen=True)
class BondedFrames:
    """Four observer frames around one LCR edge: identity, the two cyclic
    rotations, and the LR mirror (antipodal)."""
    observe_c: tuple[int, int, int]
    bridge_r: tuple[int, int, int]
    antipodal_c: tuple[int, int, int]
    bridge_l: tuple[int, int, int]

    @classmethod
    def from_triad(cls, triad: tuple[int, int, int]) -> "BondedFrames":
        L, C, R = triad
        return cls(
            observe_c=triad,
            bridge_r=(C, R, L),
            antipodal_c=(R, C, L),
            bridge_l=(R, L, C),
        )


@dataclass
class SyndromeFingerprint:
    """Frequency distribution of the 8 syndromes in an observation stream."""
    syndrome_counts: dict[int, int] = field(
        default_factory=lambda: {i: 0 for i in range(8)}
    )
    source: str = ""

    @classmethod
    def from_observations(cls, observations: Iterable[tuple[int, int, int]],
                          source: str = "") -> "SyndromeFingerprint":
        fp = cls(source=source)
        for triad in observations:
            fp.syndrome_counts[ALL_TRIADS.index(triad)] += 1
        return fp

    @classmethod
    def from_bytes(cls, data: bytes, source: str = "") -> "SyndromeFingerprint":
        """3 bits per triad over the bit stream of the data."""
        bits = [(byte >> shift) & 1 for byte in data for shift in range(7, -1, -1)]
        triads = [
            (bits[i], bits[i + 1], bits[i + 2])
            for i in range(0, len(bits) - 2, 3)
        ]
        return cls.from_observations(triads, source=source)

    @property
    def total(self) -> int:
        return sum(self.syndrome_counts.values())

    @property
    def invariant_count(self) -> int:
        return self.syndrome_counts[0] + self.syndrome_counts[7]

    @property
    def invariant_ratio(self) -> float:
        return self.invariant_count / self.total if self.total else 0.0


def binomial_p_value(k: int, n: int, p: float) -> float:
    """Exact two-tailed binomial p-value via math.comb (no approximation).

    Two-tailed by the point-probability method: sum the probability of every
    outcome at most as likely as the observed one.
    """
    if n == 0:
        return 1.0
    def pmf(i: int) -> float:
        return math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
    observed = pmf(k)
    total = sum(pr for i in range(n + 1)
                if (pr := pmf(i)) <= observed * (1 + 1e-12))
    return min(1.0, total)


def classify_severity(sigma: float) -> str:
    if sigma < 1.0:
        return "nominal"
    if sigma < 2.0:
        return "elevated"
    if sigma < 3.0:
        return "warning"
    if sigma < 4.0:
        return "critical"
    return "emergency"


@dataclass(frozen=True)
class DeviationProof:
    """Exact proof that a fingerprint deviates (or not) from the partition law."""
    invariant_observed: int
    total_observations: int
    invariant_ratio: float
    deviation: float
    standard_deviations: float
    p_value: float
    severity: str
    proof_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "invariant_observed": self.invariant_observed,
            "total_observations": self.total_observations,
            "invariant_ratio": round(self.invariant_ratio, 6),
            "expected_ratio": EXPECTED_INVARIANT_RATIO,
            "deviation": round(self.deviation, 6),
            "standard_deviations": round(self.standard_deviations, 4),
            "p_value": self.p_value,
            "severity": self.severity,
            "proof_hash": self.proof_hash,
        }


def check_partition(fp: SyndromeFingerprint) -> DeviationProof:
    """Check a fingerprint against the 0.25 deep-invariant partition law."""
    n = fp.total
    k = fp.invariant_count
    ratio = k / n if n else 0.0
    deviation = ratio - EXPECTED_INVARIANT_RATIO
    std = math.sqrt(EXPECTED_INVARIANT_RATIO * (1 - EXPECTED_INVARIANT_RATIO) / n) if n else 0.0
    sigma = abs(deviation) / std if std > 0 else 0.0
    p = binomial_p_value(k, n, EXPECTED_INVARIANT_RATIO)
    payload = f"{fp.source}:{k}:{n}:{ratio:.9f}:{p:.12g}"
    return DeviationProof(
        invariant_observed=k,
        total_observations=n,
        invariant_ratio=ratio,
        deviation=deviation,
        standard_deviations=sigma,
        p_value=p,
        severity=classify_severity(sigma),
        proof_hash=hashlib.sha256(payload.encode()).hexdigest()[:24],
    )


# ─── Finite verifier (paper-bound claims, CQE-paper-02) ─────────────────────

def _cycle(t: tuple[int, int, int]) -> tuple[int, int, int]:
    return (t[1], t[2], t[0])


def verify() -> dict[str, Any]:
    """Run the 10 finite checks that bind SentinelForge to CQE-paper-02."""
    checks: dict[str, bool] = {}

    # 1. Partition law sizes: 2 deep + 2 level-1 + 4 variable = 8
    checks["partition_sizes_2_2_4"] = (
        len(DEEP_INVARIANTS) == 2
        and len(LEVEL1_INVARIANTS) == 2
        and len(VARIABLE_TRIADS) == 4
        and DEEP_INVARIANTS | LEVEL1_INVARIANTS | VARIABLE_TRIADS == set(ALL_TRIADS)
    )

    # 2. Lie conjugates are exactly the L=R states and equal deep + level-1
    checks["lie_conjugates_are_deep_union_level1"] = (
        LIE_CONJUGATES == DEEP_INVARIANTS | LEVEL1_INVARIANTS
        and all(s[0] == s[2] for s in LIE_CONJUGATES)
    )

    # 3. Correction identity: rule30 = rule90 XOR correction, on all 8 states
    checks["rule30_equals_rule90_xor_correction"] = all(
        rule30_emit(s) == (rule90_emit(s) ^ correction_bit(s)) for s in ALL_TRIADS
    )

    # 4. Correction fires on exactly 2 of 8 states: (0,1,0) and (1,1,0)
    firing = {s for s in ALL_TRIADS if correction_bit(s) == 1}
    checks["correction_fires_on_exactly_2_states"] = firing == {(0, 1, 0), (1, 1, 0)}

    # 5. Geometry levels partition as 2/2/4 over levels 0/1/2
    levels: dict[int, int] = {}
    for s in ALL_TRIADS:
        levels[geometry_level(s)] = levels.get(geometry_level(s), 0) + 1
    checks["geometry_levels_partition_2_2_4"] = levels == {0: 2, 1: 2, 2: 4}

    # 6. Bonded frames: bridge frames are the cyclic rotations, antipodal is
    #    the LR mirror and an involution
    ok6 = True
    for s in ALL_TRIADS:
        f = BondedFrames.from_triad(s)
        ok6 &= f.bridge_r == _cycle(s)
        ok6 &= f.bridge_l == _cycle(_cycle(s))
        ok6 &= f.antipodal_c == (s[2], s[1], s[0])
        ok6 &= BondedFrames.from_triad(f.antipodal_c).antipodal_c == s
    checks["bonded_frames_cyclic_and_antipodal_involution"] = ok6

    # 7. Exact-balance stream: each triad once -> ratio 0.25, sigma 0, nominal
    balanced = check_partition(SyndromeFingerprint.from_observations(ALL_TRIADS * 16))
    checks["balanced_stream_is_nominal_sigma_zero"] = (
        balanced.invariant_ratio == 0.25
        and balanced.standard_deviations == 0.0
        and balanced.severity == "nominal"
    )

    # 8. Frozen stream (all vacuum) is an emergency with vanishing p-value
    frozen = check_partition(
        SyndromeFingerprint.from_observations([(0, 0, 0)] * 128)
    )
    checks["frozen_stream_is_emergency"] = (
        frozen.invariant_ratio == 1.0
        and frozen.severity == "emergency"
        and frozen.p_value < 1e-9
    )

    # 9. Exact binomial sanity: pmf sums to 1; symmetric two-tail at the mean
    n, p = 16, 0.25
    total_mass = sum(math.comb(n, i) * p**i * (1 - p)**(n - i) for i in range(n + 1))
    checks["binomial_exact_mass_and_mean_p"] = (
        abs(total_mass - 1.0) < 1e-12
        and binomial_p_value(4, 16, 0.25) == 1.0  # k = np exactly
    )

    # 10. Severity ladder is monotone in sigma
    sigmas = [0.5, 1.5, 2.5, 3.5, 4.5]
    checks["severity_ladder_monotone"] = [classify_severity(s) for s in sigmas] == SEVERITY_LADDER

    return {
        "forge": "SentinelForge",
        "paper": "CQE-paper-02",
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2))
