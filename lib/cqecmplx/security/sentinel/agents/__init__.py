"""Sentinel Lightweight Monitoring Agents.

Cross-platform monitoring agents for Linux, Windows, and Kubernetes.
Collect system metrics, quantize them into syndrome triads, and stream
to the Sentinel API for real-time anomaly detection.
"""

from .linux_agent import LinuxAgent
from .k8s_agent import K8sAgent

__all__ = ["LinuxAgent", "K8sAgent"]
