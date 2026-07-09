"""Real-time anomaly detector with syndrome-based mathematical proof.

The detector consumes a stream of system observations, computes syndrome
fingerprints, checks against the VOA partition law, and emits alerts with
mathematical proof of any deviation.

Unlike rule-based SIEMs or ML-based tools, Sentinel alerts are
mathematically proven — every alert includes the exact p-value,
standard deviation distance, and proof statement showing the VOA
partition has been violated.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Callable

from ..core.checkpoint import Checkpoint, CheckpointLedger
from ..core.syndrome import (
    ALL_TRIADS,
    SyndromeFingerprint,
    SyndromeSignature,
    classify_triad,
    compute_syndrome_id,
    rule30_emit,
)
from ..voa.checker import VOAChecker, VOADeviationSeverity, VOAResult


class AlertSeverity(str, Enum):
    """Unified alert severity combining VOA deviation + chart anomaly."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Alert:
    """One Sentinel alert with mathematical proof of anomaly."""

    alert_id: str                          # unique alert identifier
    timestamp: float                       # when detected
    source: str                            # what system/source

    # VOA deviation
    voa_result: VOAResult                  # mathematical proof

    # Chart state anomaly
    chart_anomaly: dict[str, Any]          # chart transition anomaly details

    # Severity (combined VOA + chart)
    severity: AlertSeverity

    # Proof
    proof_hash: str                        # SHA-256 of proof data

    # Context
    fingerprint_snapshot: dict[str, Any]   # the fingerprint that triggered it
    baseline_snapshot: dict[str, Any] | None  # baseline fingerprint for comparison
    recommended_action: str

    # Metadata
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp,
            "source": self.source,
            "severity": self.severity.value,
            "voa_proof": self.voa_result.to_dict(),
            "chart_anomaly": self.chart_anomaly,
            "proof_hash": self.proof_hash,
            "fingerprint_snapshot": self.fingerprint_snapshot,
            "baseline_snapshot": self.baseline_snapshot,
            "recommended_action": self.recommended_action,
            "tags": self.tags,
        }

    @property
    def summary(self) -> str:
        v = self.voa_result
        return (
            f"[{self.severity.value.upper()}] Sentinel alert from {self.source}: "
            f"VOA deviation {v.deviation:+.4f} ({v.standard_deviations:.2f} sigma), "
            f"p={v.p_value:.6f}, confidence={v.confidence_percent:.2f}%"
        )


@dataclass
class DetectionRule:
    """A configurable detection rule for Sentinel."""

    name: str
    description: str
    # VOA deviation thresholds
    min_sigma: float = 2.0                 # minimum sigma to trigger
    min_p_value: float = 0.01              # maximum p-value to trigger
    # Required severity
    min_voa_severity: VOADeviationSeverity = VOADeviationSeverity.WARNING
    # Chart state monitoring
    monitor_chart_transitions: bool = True
    max_transitions_per_window: int = 100  # excessive transitions = anomaly
    window_seconds: int = 60               # observation window
    # Source filter (empty = all)
    sources: list[str] = field(default_factory=list)
    # Actions
    actions: list[str] = field(default_factory=lambda: ["log", "webhook"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "min_sigma": self.min_sigma,
            "min_p_value": self.min_p_value,
            "min_voa_severity": self.min_voa_severity.value,
            "monitor_chart_transitions": self.monitor_chart_transitions,
            "max_transitions_per_window": self.max_transitions_per_window,
            "window_seconds": self.window_seconds,
            "sources": self.sources,
            "actions": self.actions,
        }


class AlertManager:
    """Persistent alert manager with deduplication and escalation."""

    def __init__(self, path: Path | None = None, max_alerts: int = 10000):
        self.path = path
        self.max_alerts = max_alerts
        self.alerts: list[Alert] = []
        self._dedup_window: dict[str, float] = {}  # hash -> last_seen
        self._dedup_ttl = 300  # 5-minute dedup window

    def add(self, alert: Alert) -> bool:
        """Add an alert, returning False if deduplicated."""
        now = time.time()

        # Deduplication: skip if same proof hash seen recently
        dedup_key = f"{alert.source}:{alert.proof_hash}"
        last_seen = self._dedup_window.get(dedup_key)
        if last_seen and (now - last_seen) < self._dedup_ttl:
            return False
        self._dedup_window[dedup_key] = now

        self.alerts.append(alert)

        # Trim if needed
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]

        if self.path is not None:
            self._persist()

        return True

    def get_alerts(
        self,
        severity: AlertSeverity | None = None,
        source: str | None = None,
        since: float | None = None,
        limit: int = 100,
    ) -> list[Alert]:
        results = self.alerts
        if severity:
            results = [a for a in results if a.severity == severity]
        if source:
            results = [a for a in results if a.source == source]
        if since:
            results = [a for a in results if a.timestamp >= since]
        return results[-limit:]

    def get_stats(self) -> dict[str, Any]:
        counts = {s.value: 0 for s in AlertSeverity}
        for a in self.alerts:
            counts[a.severity.value] = counts.get(a.severity.value, 0) + 1
        return {
            "total_alerts": len(self.alerts),
            "severity_counts": counts,
            "dedup_window_size": len(self._dedup_window),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "alerts": [a.to_dict() for a in self.alerts[-200:]],
            "stats": self.get_stats(),
        }

    def _persist(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "alerts": [a.to_dict() for a in self.alerts],
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


class AnomalyDetector:
    """Production real-time anomaly detector.

    Consumes observations, maintains rolling fingerprints, checks against
the VOA partition law, and emits mathematically-proven alerts.
    """

    def __init__(
        self,
        source: str = "default",
        baseline_fingerprint: SyndromeFingerprint | None = None,
        checkpoint_path: Path | None = None,
        alert_path: Path | None = None,
        rule: DetectionRule | None = None,
    ):
        self.source = source
        self.baseline = baseline_fingerprint
        self.checker = VOAChecker()
        self.ledger = CheckpointLedger(path=checkpoint_path)
        self.alert_manager = AlertManager(path=alert_path)
        self.rule = rule or DetectionRule(
            name="default",
            description="Default detection: sigma > 2 or WARNING+ VOA severity",
        )

        # Rolling observation window
        self._observations: list[tuple[int, int, int]] = []
        self._window_size = 1024  # observations per fingerprint
        self._transition_count = 0
        self._transition_window_start = time.time()

    def observe(self, triad: tuple[int, int, int], chart_state: str = "rotate_0") -> Alert | None:
        """Process one observation. Returns an Alert if anomaly detected."""
        self._observations.append(triad)

        # Compute syndrome properties
        classification = classify_triad(triad)
        syndrome_idx = compute_syndrome_id(triad)

        # Record checkpoint
        self.ledger.append(
            syndrome_index=syndrome_idx,
            triad=triad,
            chart_state=chart_state,
            emission=classification["rule30_emission"],
            correction=classification["correction_bit"],
            lie_conjugate=classification["lie_conjugate"],
            geometry_level=classification["geometry_level"],
            metadata={"source": self.source},
        )

        # Check if window is full
        if len(self._observations) >= self._window_size:
            return self._evaluate_window()
        return None

    def observe_metrics(
        self, metrics: dict[str, float], thresholds: dict[str, tuple[float, float]] | None = None
    ) -> Alert | None:
        """Process a metrics dict. Returns Alert if anomaly detected."""
        from ..core.syndrome import FingerprintEngine

        engine = FingerprintEngine(source=self.source)
        fp = engine.fingerprint_metrics(metrics, thresholds)

        # Extract triads from fingerprint
        triads = []
        for i, count in fp.syndrome_counts.items():
            triads.extend([ALL_TRIADS[i]] * count)

        for triad in triads:
            result = self.observe(triad)
            if result is not None:
                return result

        return self._evaluate_window() if len(self._observations) > 0 else None

    def observe_batch(self, triads: list[tuple[int, int, int]], chart_state: str = "rotate_0") -> Alert | None:
        """Process a batch of observations."""
        for triad in triads:
            result = self.observe(triad, chart_state)
            if result is not None:
                return result
        return None

    def _evaluate_window(self) -> Alert | None:
        """Evaluate the current observation window."""
        if not self._observations:
            return None

        fp = SyndromeFingerprint.from_observations(self._observations, source=self.source)
        voa_result = self.checker.check(fp)

        # Check chart transition anomaly
        chart_anomaly = self._check_chart_anomaly()

        # Determine combined severity
        severity = self._compute_alert_severity(voa_result, chart_anomaly)

        # Check rule thresholds
        if severity == AlertSeverity.INFO:
            self._observations = self._observations[self._window_size // 2:]  # slide window
            return None

        if voa_result.standard_deviations < self.rule.min_sigma:
            if voa_result.severity.value in ["nominal", "elevated"]:
                self._observations = self._observations[self._window_size // 2:]
                return None

        # Build and emit alert
        alert = self._create_alert(fp, voa_result, chart_anomaly, severity)
        self.alert_manager.add(alert)

        # Slide the window
        self._observations = self._observations[self._window_size // 2:]

        return alert

    def _check_chart_anomaly(self) -> dict[str, Any]:
        """Check for chart transition anomalies."""
        now = time.time()
        window_elapsed = now - self._transition_window_start

        if window_elapsed >= self.rule.window_seconds:
            excess = self._transition_count > self.rule.max_transitions_per_window
            result = {
                "transitions_in_window": self._transition_count,
                "window_seconds": self.rule.window_seconds,
                "max_allowed": self.rule.max_transitions_per_window,
                "anomalous": excess,
            }
            self._transition_count = 0
            self._transition_window_start = now
            return result

        return {
            "transitions_in_window": self._transition_count,
            "window_seconds": self.rule.window_seconds,
            "max_allowed": self.rule.max_transitions_per_window,
            "anomalous": False,
        }

    def _compute_alert_severity(
        self, voa: VOAResult, chart: dict[str, Any]
    ) -> AlertSeverity:
        """Compute combined alert severity from VOA + chart anomalies."""
        severity_map = {
            VOADeviationSeverity.NOMINAL: AlertSeverity.INFO,
            VOADeviationSeverity.ELEVATED: AlertSeverity.LOW,
            VOADeviationSeverity.WARNING: AlertSeverity.MEDIUM,
            VOADeviationSeverity.CRITICAL: AlertSeverity.HIGH,
            VOADeviationSeverity.EMERGENCY: AlertSeverity.CRITICAL,
        }
        voa_alert = severity_map.get(voa.severity, AlertSeverity.INFO)

        # Upgrade severity if chart transitions are anomalous
        if chart.get("anomalous", False):
            severity_levels = [AlertSeverity.INFO, AlertSeverity.LOW, AlertSeverity.MEDIUM,
                              AlertSeverity.HIGH, AlertSeverity.CRITICAL]
            voa_idx = severity_levels.index(voa_alert)
            return severity_levels[min(voa_idx + 1, len(severity_levels) - 1)]

        return voa_alert

    def _create_alert(
        self,
        fp: SyndromeFingerprint,
        voa: VOAResult,
        chart: dict[str, Any],
        severity: AlertSeverity,
    ) -> Alert:
        """Create a fully documented alert."""
        proof_body = {
            "voa": voa.to_dict(),
            "chart": chart,
            "fingerprint": fp.to_dict(),
            "source": self.source,
        }
        proof_hash = hashlib.sha256(
            json.dumps(proof_body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:32]
        alert_id = f"SNTL-{proof_hash[:16].upper()}"

        # Recommended action
        action_map = {
            AlertSeverity.INFO: "No action required.",
            AlertSeverity.LOW: "Monitor closely. Review recent system changes.",
            AlertSeverity.MEDIUM: "Investigate within 1 hour. Check logs and access patterns.",
            AlertSeverity.HIGH: "Immediate investigation required. Consider isolating affected systems.",
            AlertSeverity.CRITICAL: "EMERGENCY: Isolate compromised systems immediately. Initiate incident response.",
        }

        return Alert(
            alert_id=alert_id,
            timestamp=time.time(),
            source=self.source,
            voa_result=voa,
            chart_anomaly=chart,
            severity=severity,
            proof_hash=proof_hash,
            fingerprint_snapshot=fp.to_dict(),
            baseline_snapshot=self.baseline.to_dict() if self.baseline else None,
            recommended_action=action_map.get(severity, "Review and investigate."),
            tags=["syndrome_anomaly", f"voa_{voa.severity.value}"],
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "observations_buffered": len(self._observations),
            "window_size": self._window_size,
            "checkpoints": len(self.ledger.checkpoints),
            "chain_integrity": self.ledger.verify_chain(),
            "alerts": self.alert_manager.get_stats(),
            "rule": self.rule.to_dict(),
        }
