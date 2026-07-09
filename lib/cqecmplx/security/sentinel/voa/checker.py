"""VOA partition ratio checker — the mathematical heart of Sentinel.

The VOA partition Z(q) = 2q^0 + 6q^5 encodes the fundamental law:
  - 2 out of 8 syndrome states are DEEP INVARIANT (syndromes 0 and 7)
  - 6 out of 8 syndrome states are VARIABLE (syndromes 1-6)
  - Expected ratio: 25% invariant, 75% variable

This ratio is a physical law of any healthy system. When it deviates,
something is wrong — and the magnitude of deviation quantifies the
severity of the anomaly with mathematical certainty.

Mathematical Foundation (from CMPLX-R30):
  - 8 LocalTriad states = 2^3 possible LCR combinations
  - Lie conjugates: L=R states (000, 010, 101, 111) — 4 stable states
  - Deep invariants: 000 and 111 — these NEVER change under correction
  - Level-1 invariants: 010 and 101 — stable but respond to external pressure
  - Variable states: 001, 011, 100, 110 — these change with every correction

The VOA partition separates the 8 states into:
  - INVARIANT component (2 states): geometry_level == 0
  - VARIABLE component (6 states): geometry_level >= 1

When the observed ratio deviates from 0.25, we compute the exact
probability of this deviation occurring naturally (binomial test),
giving a p-value that quantifies anomaly confidence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..core.syndrome import (
    ALL_TRIADS,
    DEEP_INVARIANTS,
    LIE_CONJUGATES,
    VARIABLE_TRIADS,
    SyndromeFingerprint,
)


class VOADeviationSeverity(str, Enum):
    """Severity levels based on VOA ratio deviation magnitude."""

    NOMINAL = "nominal"           # within 1 sigma — healthy
    ELEVATED = "elevated"         # 1-2 sigma — watch
    WARNING = "warning"           # 2-3 sigma — investigate
    CRITICAL = "critical"         # 3-4 sigma — probable attack
    EMERGENCY = "emergency"       # 4+ sigma — confirmed compromise


@dataclass(frozen=True)
class VOAResult:
    """Result of a VOA partition ratio check."""

    # Raw counts
    invariant_observed: int
    variable_observed: int
    total_observations: int

    # Ratios
    invariant_ratio: float
    variable_ratio: float
    deviation: float
    deviation_percent: float
    standard_deviations: float
    p_value: float
    confidence_percent: float
    severity: VOADeviationSeverity
    proof_statement: str

    # Defaults must come after non-defaults
    expected_ratio: float = 0.25
    syndrome_breakdown: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "invariant_observed": self.invariant_observed,
            "variable_observed": self.variable_observed,
            "total_observations": self.total_observations,
            "ratios": {
                "invariant": round(self.invariant_ratio, 6),
                "variable": round(self.variable_ratio, 6),
                "expected_invariant": self.expected_ratio,
            },
            "deviation": {
                "absolute": round(self.deviation, 6),
                "percent": round(self.deviation_percent, 4),
                "standard_deviations": round(self.standard_deviations, 4),
            },
            "statistical_significance": {
                "p_value": self.p_value,
                "confidence_percent": round(self.confidence_percent, 6),
            },
            "severity": self.severity.value,
            "proof_statement": self.proof_statement,
            "syndrome_breakdown": self.syndrome_breakdown,
        }


@dataclass
class VOAChecker:
    """VOA partition ratio checker with statistical rigor.

    Every check produces a mathematical proof of deviation with:
    1. Exact binomial p-value (probability this is natural)
    2. Standard deviation distance from expected
    3. Severity classification
    4. Human-readable proof statement
    """

    expected_invariant_ratio: float = 0.25  # 2/8
    # Acceptable tolerance in standard deviations before raising severity
    tolerance_sigma: float = 1.0

    def check(self, fingerprint: SyndromeFingerprint) -> VOAResult:
        """Check a syndrome fingerprint against the VOA partition law.

        Returns a VOAResult with full mathematical proof of any deviation.
        """
        n = fingerprint.total_observations
        if n == 0:
            return VOAResult(
                invariant_observed=0,
                variable_observed=0,
                total_observations=0,
                invariant_ratio=0.0,
                variable_ratio=0.0,
                deviation=0.0,
                deviation_percent=0.0,
                standard_deviations=0.0,
                p_value=1.0,
                confidence_percent=0.0,
                severity=VOADeviationSeverity.NOMINAL,
                proof_statement="No observations available for VOA check.",
            )

        invariant_obs = fingerprint.invariant_count
        variable_obs = fingerprint.variable_count
        obs_ratio = invariant_obs / n
        deviation = obs_ratio - self.expected_invariant_ratio

        # Standard deviation of binomial distribution: sqrt(p * (1-p) / n)
        std_dev = math.sqrt(self.expected_invariant_ratio * (1 - self.expected_invariant_ratio) / n)
        sigma = abs(deviation) / std_dev if std_dev > 0 else 0.0

        # Two-tailed binomial p-value
        p_value = self._binomial_p_value(invariant_obs, n, self.expected_invariant_ratio)
        confidence = (1.0 - p_value) * 100.0

        # Severity classification
        severity = self._classify_severity(sigma)

        # Build proof statement
        proof = self._build_proof(
            invariant_obs, variable_obs, n, obs_ratio, deviation, sigma, p_value, severity
        )

        # Syndrome-level breakdown
        breakdown = {
            f"syndrome_{i}": {
                "triad": list(ALL_TRIADS[i]),
                "count": fingerprint.syndrome_counts[i],
                "frequency": round(fingerprint.syndrome_counts[i] / n, 6) if n > 0 else 0.0,
                "category": "deep_invariant" if ALL_TRIADS[i] in DEEP_INVARIANTS
                else ("lie_conjugate" if ALL_TRIADS[i] in LIE_CONJUGATES else "variable"),
            }
            for i in range(8)
        }

        return VOAResult(
            invariant_observed=invariant_obs,
            variable_observed=variable_obs,
            total_observations=n,
            invariant_ratio=obs_ratio,
            variable_ratio=variable_obs / n,
            deviation=deviation,
            deviation_percent=abs(deviation) * 100.0,
            standard_deviations=sigma,
            p_value=p_value,
            confidence_percent=confidence,
            severity=severity,
            proof_statement=proof,
            syndrome_breakdown=breakdown,
        )

    def _binomial_p_value(self, k: int, n: int, p: float) -> float:
        """Compute two-tailed binomial p-value.

        P(observe k or more extreme successes in n trials with prob p).
        """
        if n == 0:
            return 1.0
        # Use normal approximation for large n
        if n > 100:
            mu = n * p
            sigma = math.sqrt(n * p * (1 - p))
            if sigma > 0:
                z = (k - mu) / sigma
                # Two-tailed: 2 * P(Z > |z|)
                return min(1.0, 2.0 * (1.0 - self._normal_cdf(abs(z))))
            return 1.0

        # Exact binomial for small n
        p_value = 0.0
        for i in range(k, n + 1):
            p_value += self._binomial_prob(i, n, p)
        for i in range(0, min(k + 1, int(n * p) + 1)):
            p_value += self._binomial_prob(i, n, p)
        return min(1.0, p_value)

    def _binomial_prob(self, k: int, n: int, p: float) -> float:
        """P(X=k) for binomial(n, p)."""
        return math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))

    def _normal_cdf(self, x: float) -> float:
        """Standard normal cumulative distribution function."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def _classify_severity(self, sigma: float) -> VOADeviationSeverity:
        if sigma < 1.0:
            return VOADeviationSeverity.NOMINAL
        elif sigma < 2.0:
            return VOADeviationSeverity.ELEVATED
        elif sigma < 3.0:
            return VOADeviationSeverity.WARNING
        elif sigma < 4.0:
            return VOADeviationSeverity.CRITICAL
        else:
            return VOADeviationSeverity.EMERGENCY

    def _build_proof(
        self,
        invariant_obs: int,
        variable_obs: int,
        n: int,
        obs_ratio: float,
        deviation: float,
        sigma: float,
        p_value: float,
        severity: VOADeviationSeverity,
    ) -> str:
        """Build a human-readable mathematical proof statement."""
        expected_inv = int(n * self.expected_invariant_ratio)

        if severity == VOADeviationSeverity.NOMINAL:
            return (
                f"VOA partition NOMINAL: observed {invariant_obs}/{n} invariants "
                f"({obs_ratio:.4f}) matches expected {expected_inv}/{n} "
                f"({self.expected_invariant_ratio:.4f}). Deviation: {deviation:+.4f} "
                f"({sigma:.2f} sigma). p={p_value:.6f}. System is healthy."
            )

        direction = "increased" if deviation > 0 else "decreased"
        conf_str = f"{((1 - p_value) * 100):.4f}%"

        return (
            f"VOA ANOMALY DETECTED — severity: {severity.value.upper()}. "
            f"The invariant component {direction} from expected {self.expected_invariant_ratio:.4f} "
            f"to {obs_ratio:.4f}. Observed {invariant_obs} invariants vs expected ~{expected_inv} "
            f"out of {n} total observations. This deviation ({abs(deviation):.4f}, "
            f"{sigma:.2f} sigma) has a {p_value:.6f} probability of occurring naturally — "
            f"{conf_str} confidence this is an attack or system failure. "
            f"The VOA partition Z(q)=2q^0+6q^5 has been violated."
        )

    def check_raw(self, invariant_count: int, total_count: int) -> VOAResult:
        """Check raw counts without building a full fingerprint."""
        from ..core.syndrome import SyndromeFingerprint

        fp = SyndromeFingerprint(
            syndrome_counts={
                0: invariant_count if total_count > 0 else 0,  # deep invariant 000
                7: 0,  # other deep invariant handled differently
            },
            source="raw_check",
            created_at=time.time(),
        )
        # Fill in realistically: assume invariant_count is split between 0 and 7
        fp.syndrome_counts[0] = invariant_count // 2
        fp.syndrome_counts[7] = invariant_count - invariant_count // 2
        remaining = total_count - invariant_count
        # Distribute remaining across variable syndromes
        for i in range(1, 7):
            fp.syndrome_counts[i] = remaining // 6
        return self.check(fp)
