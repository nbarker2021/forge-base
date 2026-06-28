"""Sentinel Kubernetes Monitoring Agent.

Monitors pod metrics, node health, and cluster state by reading
the Kubernetes API, then converts them into syndrome triads for
the Sentinel anomaly detector.

Usage:
    # Deploy as a DaemonSet in your cluster
    kubectl apply -f docker/k8s-agent.yaml
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class K8sMetrics:
    """Collected Kubernetes metrics for syndrome quantization."""

    # Pod metrics
    pod_cpu_percent: float
    pod_memory_percent: float
    pod_restart_count: float
    pod_ready: float  # 1.0 if ready, 0.0 if not

    # Node metrics
    node_cpu_percent: float
    node_memory_percent: float
    node_disk_percent: float
    node_pod_count: float

    # Cluster metrics
    total_pods: float
    running_pods: float
    pending_pods: float
    failed_pods: float

    def to_dict(self) -> dict[str, float]:
        return {
            "pod_cpu_percent": self.pod_cpu_percent,
            "pod_memory_percent": self.pod_memory_percent,
            "pod_restart_count": float(self.pod_restart_count),
            "pod_ready": self.pod_ready,
            "node_cpu_percent": self.node_cpu_percent,
            "node_memory_percent": self.node_memory_percent,
            "node_disk_percent": self.node_disk_percent,
            "node_pod_count": float(self.node_pod_count),
            "total_pods": float(self.total_pods),
            "running_pods": float(self.running_pods),
            "pending_pods": float(self.pending_pods),
            "failed_pods": float(self.failed_pods),
        }

    @property
    def thresholds(self) -> dict[str, tuple[float, float]]:
        return {
            "pod_cpu_percent": (0.0, 100.0),
            "pod_memory_percent": (0.0, 100.0),
            "pod_restart_count": (0.0, 10.0),
            "pod_ready": (0.0, 1.0),
            "node_cpu_percent": (0.0, 100.0),
            "node_memory_percent": (0.0, 100.0),
            "node_disk_percent": (0.0, 100.0),
            "node_pod_count": (0.0, 250.0),
            "total_pods": (0.0, 1000.0),
            "running_pods": (0.0, 1000.0),
            "pending_pods": (0.0, 100.0),
            "failed_pods": (0.0, 50.0),
        }


class K8sAgent:
    """Kubernetes monitoring agent for Sentinel.

    Reads from the Kubernetes API (via service account token) and
    converts cluster state into syndrome triads.
    """

    def __init__(
        self,
        api_url: str,
        source: str = "",
        interval: int = 30,
        k8s_host: str = "https://kubernetes.default.svc",
    ):
        self.api_url = api_url.rstrip("/")
        self.source = source or socket.gethostname()
        self.interval = interval
        self.k8s_host = k8s_host
        self._running = False
        self._token = self._get_service_account_token()
        self._namespace = self._get_namespace()

    def _get_service_account_token(self) -> str:
        token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
        try:
            return Path(token_path).read_text().strip()
        except Exception:
            return ""

    def _get_namespace(self) -> str:
        ns_path = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
        try:
            return Path(ns_path).read_text().strip()
        except Exception:
            return "default"

    def _k8s_request(self, path: str) -> dict | None:
        """Make an authenticated request to the Kubernetes API."""
        if not self._token:
            return None
        url = f"{self.k8s_host}{path}"
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/json",
                },
            )
            # Skip SSL verification for in-cluster communication
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            print(f"[WARN] K8s API request failed: {e}", file=sys.stderr)
            return None

    def collect_metrics(self) -> K8sMetrics:
        """Collect Kubernetes metrics."""
        # Pod metrics via metrics-server (optional)
        pod_cpu = 0.0
        pod_mem = 0.0
        restarts = 0.0
        ready = 1.0

        # Get pod info
        pod_data = self._k8s_request(
            f"/api/v1/namespaces/{self._namespace}/pods"
        )
        if pod_data:
            items = pod_data.get("items", [])
            my_hostname = socket.gethostname()
            for pod in items:
                name = pod.get("metadata", {}).get("name", "")
                if my_hostname in name or name.startswith(self.source):
                    status = pod.get("status", {})
                    container_statuses = status.get("containerStatuses", [])
                    for cs in container_statuses:
                        restarts = float(cs.get("restartCount", 0))
                        ready = 1.0 if cs.get("ready", False) else 0.0
                    phase = status.get("phase", "")
                    if phase == "Running":
                        pod_cpu = 50.0  # placeholder if no metrics-server
                        pod_mem = 50.0

        # Node metrics
        node_cpu = 0.0
        node_mem = 0.0
        node_disk = 0.0
        node_pods = 0.0

        node_data = self._k8s_request("/api/v1/nodes")
        if node_data:
            items = node_data.get("items", [])
            if items:
                node = items[0]
                status = node.get("status", {})
                capacity = status.get("capacity", {})
                allocatable = status.get("allocatable", {})
                conditions = status.get("conditions", [])

                # Find Ready condition
                for cond in conditions:
                    if cond.get("type") == "Ready":
                        ready = 1.0 if cond.get("status") == "True" else 0.0

                # Calculate percentages
                cpu_cap = self._parse_cpu(capacity.get("cpu", "0"))
                cpu_alloc = self._parse_cpu(allocatable.get("cpu", "0"))
                if cpu_cap > 0:
                    node_cpu = 100.0 * (1.0 - cpu_alloc / cpu_cap)

                mem_cap = self._parse_memory(capacity.get("memory", "0"))
                mem_alloc = self._parse_memory(allocatable.get("memory", "0"))
                if mem_cap > 0:
                    node_mem = 100.0 * (1.0 - mem_alloc / mem_cap)

                node_pods = float(len(pod_data.get("items", [])) if pod_data else 0)

        # Cluster-wide pod counts
        total_pods = 0.0
        running_pods = 0.0
        pending_pods = 0.0
        failed_pods = 0.0

        all_pods = self._k8s_request("/api/v1/pods")
        if all_pods:
            items = all_pods.get("items", [])
            total_pods = float(len(items))
            for pod in items:
                phase = pod.get("status", {}).get("phase", "")
                if phase == "Running":
                    running_pods += 1.0
                elif phase == "Pending":
                    pending_pods += 1.0
                elif phase in ("Failed", "Unknown"):
                    failed_pods += 1.0

        return K8sMetrics(
            pod_cpu_percent=pod_cpu,
            pod_memory_percent=pod_mem,
            pod_restart_count=restarts,
            pod_ready=ready,
            node_cpu_percent=node_cpu,
            node_memory_percent=node_mem,
            node_disk_percent=node_disk,
            node_pod_count=node_pods,
            total_pods=total_pods,
            running_pods=running_pods,
            pending_pods=pending_pods,
            failed_pods=failed_pods,
        )

    def _parse_cpu(self, val: str) -> float:
        """Parse CPU value (cores or millicores)."""
        if val.endswith("m"):
            return float(val[:-1]) / 1000.0
        try:
            return float(val)
        except ValueError:
            return 0.0

    def _parse_memory(self, val: str) -> float:
        """Parse memory value (Ki, Mi, Gi)."""
        multipliers = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4}
        for suffix, mult in multipliers.items():
            if val.endswith(suffix):
                try:
                    return float(val[:-len(suffix)]) * mult
                except ValueError:
                    return 0.0
        try:
            return float(val)
        except ValueError:
            return 0.0

    def send_to_api(self, metrics: K8sMetrics) -> dict | None:
        """Send metrics to the Sentinel API."""
        payload = json.dumps({
            "source": self.source,
            "metrics": metrics.to_dict(),
            "thresholds": {k: list(v) for k, v in metrics.thresholds.items()},
        }).encode()

        try:
            req = urllib.request.Request(
                f"{self.api_url}/monitor",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            print(f"[WARN] Failed to send to API: {e}", file=sys.stderr)
            return None

    def run(self) -> None:
        """Run the K8s agent in a loop."""
        self._running = True
        print(f"[INFO] Sentinel K8s Agent — source={self.source} "
              f"namespace={self._namespace} interval={self.interval}s")

        while self._running:
            try:
                metrics = self.collect_metrics()
                result = self.send_to_api(metrics)

                if result and result.get("alert"):
                    alert = result["alert"]
                    print(f"[ALERT] {alert['severity'].upper()}: "
                          f"{alert['voa_proof']['proof_statement'][:200]}")

                time.sleep(self.interval)
            except KeyboardInterrupt:
                print("[INFO] Shutting down...")
                self._running = False
            except Exception as e:
                print(f"[ERROR] {e}", file=sys.stderr)
                time.sleep(self.interval)

    def run_once(self) -> dict | None:
        """Run one collection cycle."""
        metrics = self.collect_metrics()
        return self.send_to_api(metrics)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sentinel Kubernetes Agent")
    parser.add_argument("--api-url", default="http://sentinel-api:8000", help="Sentinel API URL")
    parser.add_argument("--source", default="", help="Source identifier")
    parser.add_argument("--interval", type=int, default=30, help="Collection interval")
    parser.add_argument("--k8s-host", default="https://kubernetes.default.svc", help="K8s API host")
    parser.add_argument("--once", action="store_true", help="Run once")
    args = parser.parse_args()

    agent = K8sAgent(
        api_url=args.api_url,
        source=args.source,
        interval=args.interval,
        k8s_host=args.k8s_host,
    )

    if args.once:
        result = agent.run_once()
        print(json.dumps(result, indent=2) if result else "No result")
    else:
        agent.run()


if __name__ == "__main__":
    main()
