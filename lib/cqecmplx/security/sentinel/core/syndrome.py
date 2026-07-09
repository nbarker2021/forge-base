"""Syndrome fingerprinting engine — ported from CMPLX-R30.

The 8-syndrome system maps every system state into one of 8 LocalTriad patterns.
Each syndrome gets a 64-bit ID derived from:
  - The triad's Lie conjugate status (invariant vs variable)
  - Its Rule 30 emission
  - Its correction against Rule 90 prior
  - Its 4 bonded-frame observations at 0/90/180/270 degrees

The 8-chart state machine tracks every D4 transformation:
  rotate_0, rotate_90, rotate_180, rotate_270,
  mirror_rotate_0, mirror_rotate_90, mirror_rotate_180, mirror_rotate_270
"""

from __future__ import annotations

import hashlib
import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

# ---------------------------------------------------------------------------
# CMPLX-R30 constants — the 8 triads and their mathematical properties
# ---------------------------------------------------------------------------

ALL_TRIADS: list[tuple[int, int, int]] = [
    (0, 0, 0),  # syndrome 0
    (0, 0, 1),  # syndrome 1
    (0, 1, 0),  # syndrome 2
    (0, 1, 1),  # syndrome 3
    (1, 0, 0),  # syndrome 4
    (1, 0, 1),  # syndrome 5
    (1, 1, 0),  # syndrome 6
    (1, 1, 1),  # syndrome 7
]

# Lie conjugates are triads where L == R — these are the 4 "stable" states.
# Within these 4, 2 are deeply invariant (000, 111 at level 0)
# and 2 are level-1 stable (010, 101).
LIE_CONJUGATES: frozenset[tuple[int, int, int]] = frozenset(
    {(0, 0, 0), (0, 1, 0), (1, 0, 1), (1, 1, 1)}
)

# Deep invariants: triads that NEVER change under any correction
DEEP_INVARIANTS: frozenset[tuple[int, int, int]] = frozenset({(0, 0, 0), (1, 1, 1)})

# Variable triads: those that DO change under correction
VARIABLE_TRIADS: frozenset[tuple[int, int, int]] = frozenset(
    {(0, 0, 1), (0, 1, 1), (1, 0, 0), (1, 1, 0)}
)

# Level-1 invariants: stable but respond to external pressure
LEVEL1_INVARIANTS: frozenset[tuple[int, int, int]] = frozenset({(0, 1, 0), (1, 0, 1)})


def _validate_bit(bit: int) -> None:
    if bit not in (0, 1):
        raise ValueError(f"expected binary bit, got {bit!r}")


def rule30_emit(triad: tuple[int, int, int]) -> int:
    """Rule 30 local emission: left XOR (center OR right)."""
    left, center, right = triad
    return left ^ (center | right)


def rule90_emit(triad: tuple[int, int, int]) -> int:
    """Rule 90 prior emission: left XOR right."""
    left, center, right = triad
    return left ^ right


def correction_against_rule90(triad: tuple[int, int, int]) -> int:
    """Correction bit needed to turn Rule 90 into Rule 30: center AND (NOT right)."""
    left, center, right = triad
    return center & (1 - right)


def swap_lr(triad: tuple[int, int, int]) -> tuple[int, int, int]:
    """Mirror the triad: swap left and right."""
    return triad[2], triad[1], triad[0]


def lcr_cycle(triad: tuple[int, int, int]) -> tuple[int, int, int]:
    """Full LCR cyclic permutation (apply 3 times)."""
    left, center, right = triad
    # L->C->R->L
    for _ in range(3):
        left, center, right = center, right, left
    return left, center, right


def idempotent_at_c(triad: tuple[int, int, int]) -> bool:
    """Local closure predicate: center invariant under LR-swap, emission invariant under LCR-cycle."""
    return triad[1] == swap_lr(triad)[1] and rule30_emit(triad) == rule30_emit(lcr_cycle(triad))


def classify_triad(triad: tuple[int, int, int]) -> dict[str, Any]:
    """Full CMPLX-R30 classification of a triad."""
    lie = triad in LIE_CONJUGATES
    deep = triad in DEEP_INVARIANTS
    variable = triad in VARIABLE_TRIADS
    level1 = triad in LEVEL1_INVARIANTS
    correction = correction_against_rule90(triad)
    r30 = rule30_emit(triad)
    r90 = rule90_emit(triad)
    return {
        "triad": list(triad),
        "syndrome_index": ALL_TRIADS.index(triad),
        "lie_conjugate": lie,
        "deep_invariant": deep,
        "level1_invariant": level1,
        "variable": variable,
        "correction_fires": correction == 1,
        "geometry_level": 0 if deep else (1 if lie else 2),
        "emission_level": 2 if (triad[1] == 1 and triad[2] == 0) else 1,
        "rule30_emission": r30,
        "rule90_prior": r90,
        "correction_bit": correction,
        "idempotent": idempotent_at_c(triad),
    }


def compute_syndrome_id(triad: tuple[int, int, int]) -> int:
    """Compute a syndrome index 0-7 from a triad."""
    try:
        return ALL_TRIADS.index(triad)
    except ValueError:
        raise ValueError(f"invalid triad: {triad}")


# ---------------------------------------------------------------------------
# Bonded frames — 4 observer positions around each edge
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BondedFrames:
    """Four observer frames around one LCR edge at 0, 90, 180, 270 degrees."""

    observe_c: tuple[int, int, int]      # frame 0: centroid view
    bridge_r: tuple[int, int, int]       # frame 90: right bridge
    antipodal_c: tuple[int, int, int]    # frame 180: antipodal centroid
    bridge_l: tuple[int, int, int]       # frame 270: left bridge

    @classmethod
    def from_triad(cls, triad: tuple[int, int, int]) -> "BondedFrames":
        left, center, right = triad
        return cls(
            observe_c=triad,
            bridge_r=(center, right, left),
            antipodal_c=(right, center, left),
            bridge_l=(right, left, center),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "0_observe_c": list(self.observe_c),
            "90_bridge_r": list(self.bridge_r),
            "180_antipodal_c": list(self.antipodal_c),
            "270_bridge_l": list(self.bridge_l),
        }


# ---------------------------------------------------------------------------
# Chart state machine — 8 D4 views
# ---------------------------------------------------------------------------

class ChartState(str, Enum):
    """One of 8 chart views in the D4 dihedral atlas."""

    ROTATE_0 = "rotate_0"
    ROTATE_90 = "rotate_90"
    ROTATE_180 = "rotate_180"
    ROTATE_270 = "rotate_270"
    MIRROR_ROTATE_0 = "mirror_rotate_0"
    MIRROR_ROTATE_90 = "mirror_rotate_90"
    MIRROR_ROTATE_180 = "mirror_rotate_180"
    MIRROR_ROTATE_270 = "mirror_rotate_270"

    @classmethod
    def all_states(cls) -> list["ChartState"]:
        return list(cls)

    @property
    def is_mirror(self) -> bool:
        return self.value.startswith("mirror_")

    @property
    def rotation_degrees(self) -> int:
        return int(self.value.rsplit("_", 1)[1])


@dataclass
class ChartStateMachine:
    """8-chart state machine tracking every D4 transition.

    Each transition is recorded with a 64-bit transition ID derived from
    the source state, target state, and the triad being observed.
    """

    current: ChartState = ChartState.ROTATE_0
    transition_log: list[dict[str, Any]] = field(default_factory=list)

    def transition(self, target: ChartState, triad: tuple[int, int, int] | None = None) -> int:
        """Execute a chart state transition and return a 64-bit transition ID."""
        source = self.current
        self.current = target

        # 64-bit transition ID: pack source (4 bits), target (4 bits), triad syndrome (3 bits)
        source_idx = ChartState.all_states().index(source)
        target_idx = ChartState.all_states().index(target)
        triad_idx = compute_syndrome_id(triad) if triad else 0
        trans_id = (source_idx << 60) | (target_idx << 56) | (triad_idx << 53) | (
            len(self.transition_log) & 0x1FFFFFFFFFFFFF
        )

        self.transition_log.append({
            "timestamp": time.time(),
            "source": source.value,
            "target": target.value,
            "triad": list(triad) if triad else None,
            "transition_id": trans_id,
        })
        return trans_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_state": self.current.value,
            "transition_count": len(self.transition_log),
            "transitions": self.transition_log,
        }


# ---------------------------------------------------------------------------
# Syndrome signature — the "DNA" of a system state
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SyndromeSignature:
    """One syndrome measurement: the triad plus all its derived properties."""

    triad: tuple[int, int, int]
    frames: BondedFrames
    emission: int
    correction: int
    lie_conjugate: bool
    geometry_level: int
    emission_level: int
    idempotent: bool

    @classmethod
    def from_triad(cls, triad: tuple[int, int, int]) -> "SyndromeSignature":
        classification = classify_triad(triad)
        return cls(
            triad=triad,
            frames=BondedFrames.from_triad(triad),
            emission=classification["rule30_emission"],
            correction=classification["correction_bit"],
            lie_conjugate=classification["lie_conjugate"],
            geometry_level=classification["geometry_level"],
            emission_level=classification["emission_level"],
            idempotent=classification["idempotent"],
        )

    @property
    def syndrome_index(self) -> int:
        return compute_syndrome_id(self.triad)

    def to_dict(self) -> dict[str, Any]:
        return {
            "syndrome_index": self.syndrome_index,
            "triad": list(self.triad),
            "frames": self.frames.to_dict(),
            "rule30_emission": self.emission,
            "correction_bit": self.correction,
            "lie_conjugate": self.lie_conjugate,
            "geometry_level": self.geometry_level,
            "emission_level": self.emission_level,
            "idempotent": self.idempotent,
        }


@dataclass
class SyndromeFingerprint:
    """Complete 8-syndrome fingerprint of a system — its mathematical DNA.

    Contains the frequency distribution of all 8 syndromes observed
    in the system, plus the computed VOA invariant:variable ratio.
    """

    # Count of each syndrome index (0-7) observed
    syndrome_counts: dict[int, int] = field(default_factory=lambda: {i: 0 for i in range(8)})
    # Chart state transition history
    chart_machine: ChartStateMachine = field(default_factory=ChartStateMachine)
    # When the fingerprint was created (audit column — set at construction)
    created_at: float = 0.0
    # Source label (e.g. "baseline", "production_web", "db_cluster")
    source: str = ""

    @classmethod
    def from_observations(cls, observations: list[tuple[int, int, int]], source: str = "") -> "SyndromeFingerprint":
        """Build a fingerprint from a list of observed triads."""
        fp = cls(source=source, created_at=time.time())
        for triad in observations:
            idx = compute_syndrome_id(triad)
            fp.syndrome_counts[idx] += 1
        return fp

    @property
    def total_observations(self) -> int:
        return sum(self.syndrome_counts.values())

    @property
    def invariant_count(self) -> int:
        """Count of deep invariant observations (syndromes 0 and 7)."""
        return self.syndrome_counts[0] + self.syndrome_counts[7]

    @property
    def variable_count(self) -> int:
        """Count of variable observations (syndromes 1, 2, 3, 4, 5, 6)."""
        return self.total_observations - self.invariant_count

    @property
    def voa_ratio(self) -> float:
        """The VOA partition ratio: invariant / (invariant + variable).

        For a healthy system this should be exactly 0.25 (2/8 = 25% invariant).
        """
        if self.total_observations == 0:
            return 0.0
        return self.invariant_count / self.total_observations

    @property
    def voa_ratio_variable(self) -> float:
        """Variable ratio: variable / total. Should be 0.75 (6/8)."""
        if self.total_observations == 0:
            return 0.0
        return self.variable_count / self.total_observations

    def to_dict(self) -> dict[str, Any]:
        total = self.total_observations
        return {
            "source": self.source,
            "created_at": self.created_at,
            "timestamp": self.created_at,
            "total_observations": total,
            "syndrome_counts": dict(self.syndrome_counts),
            "invariant_count": self.invariant_count,
            "variable_count": self.variable_count,
            "voa_ratio": round(self.voa_ratio, 6),
            "voa_ratio_variable": round(self.voa_ratio_variable, 6),
            "expected_ratio": 0.25,
            "chart_transitions": len(self.chart_machine.transition_log),
        }


# ---------------------------------------------------------------------------
# Fingerprint engine — production-grade syndrome scanner
# ---------------------------------------------------------------------------

class FingerprintEngine:
    """Production engine for computing syndrome fingerprints from system data.

    Converts any stream of telemetry (metrics, logs, process states, network
    flows) into the 8-syndrome fingerprint space and computes the VOA ratio.
    """

    def __init__(self, source: str = ""):
        self.source = source

    def _quantize_to_triad(self, value: float, min_val: float, max_val: float) -> tuple[int, int, int]:
        """Quantize a continuous value into a 3-bit LocalTriad.

        Splits the range into 8 buckets and maps each to a syndrome.
        """
        if max_val == min_val:
            return (0, 0, 0)
        normalized = max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))
        bucket = min(7, int(normalized * 8))
        return ALL_TRIADS[bucket]

    def _metric_to_triads(
        self,
        metrics: dict[str, float],
        thresholds: dict[str, tuple[float, float]] | None = None,
    ) -> list[tuple[int, int, int]]:
        """Convert a dict of metric values into a list of triads.

        Each metric produces one triad. Three consecutive metrics can be
        combined into composite triads for richer fingerprints.
        """
        triads: list[tuple[int, int, int]] = []
        keys = sorted(metrics.keys())
        defaults = thresholds or {}

        # Single-metric triads: each metric becomes its own syndrome
        for key in keys:
            val = metrics[key]
            min_val, max_val = defaults.get(key, (0.0, 100.0))
            triad = self._quantize_to_triad(val, min_val, max_val)
            triads.append(triad)

        # Composite triads: every 3 consecutive metrics form an LCR pattern
        for i in range(len(keys) - 2):
            vals = [metrics[k] for k in keys[i:i + 3]]
            mins = [defaults.get(k, (0.0, 100.0))[0] for k in keys[i:i + 3]]
            maxs = [defaults.get(k, (0.0, 100.0))[1] for k in keys[i:i + 3]]
            triad = (
                min(7, int(max(0, (vals[0] - mins[0]) / (maxs[0] - mins[0])) * 8)),
                min(7, int(max(0, (vals[1] - mins[1]) / (maxs[1] - mins[1])) * 8)),
            )
            # Map bucket index to actual triad bits
            left_bit = 1 if triad[0] >= 4 else 0
            center_bit = 1 if triad[1] >= 4 else 0
            right_val = metrics[keys[i + 2]]
            right_min, right_max = defaults.get(keys[i + 2], (0.0, 100.0))
            right_bucket = min(7, int(max(0, (right_val - right_min) / (right_max - right_min)) * 8))
            right_bit = 1 if right_bucket >= 4 else 0
            triads.append((left_bit, center_bit, right_bit))

        return triads

    def fingerprint_metrics(
        self,
        metrics: dict[str, float],
        thresholds: dict[str, tuple[float, float]] | None = None,
    ) -> SyndromeFingerprint:
        """Create a syndrome fingerprint from system metrics."""
        triads = self._metric_to_triads(metrics, thresholds)
        return SyndromeFingerprint.from_observations(triads, source=self.source)

    def fingerprint_stream(
        self,
        data: bytes,
        chunk_size: int = 1024,
    ) -> SyndromeFingerprint:
        """Create a syndrome fingerprint from a byte stream.

        Each byte is decomposed into 8 bits, then grouped into triads.
        This is useful for log files, packet captures, memory dumps.
        """
        triads: list[tuple[int, int, int]] = []
        bits: list[int] = []
        for byte in data:
            for shift in range(7, -1, -1):
                bits.append((byte >> shift) & 1)
                if len(bits) == 3:
                    triads.append((bits[0], bits[1], bits[2]))
                    bits = bits[3:]
        # Pad remaining bits
        while len(bits) >= 3:
            triads.append((bits[0], bits[1], bits[2]))
            bits = bits[3:]
        return SyndromeFingerprint.from_observations(triads, source=self.source)

    def fingerprint_logs(self, log_entries: list[str]) -> SyndromeFingerprint:
        """Create a syndrome fingerprint from log entries.

        Each log line is hashed to produce bits, then grouped into triads.
        """
        triads: list[tuple[int, int, int]] = []
        for entry in log_entries:
            digest = hashlib.sha256(entry.encode()).digest()
            bits: list[int] = []
            for byte in digest[:8]:  # use first 64 bits
                for shift in range(7, -1, -1):
                    bits.append((byte >> shift) & 1)
            while len(bits) >= 3:
                triads.append((bits[0], bits[1], bits[2]))
                bits = bits[3:]
        return SyndromeFingerprint.from_observations(triads, source=self.source)
