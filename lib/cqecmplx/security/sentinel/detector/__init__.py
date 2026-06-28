"""Sentinel Real-Time Anomaly Detector.

Streaming anomaly detection using syndrome fingerprint deviations
and chart state machine transitions. Every alert includes mathematical
proof from the VOA partition checker.
"""

from .detector import AnomalyDetector, Alert, AlertManager, DetectionRule

__all__ = ["AnomalyDetector", "Alert", "AlertManager", "DetectionRule"]
