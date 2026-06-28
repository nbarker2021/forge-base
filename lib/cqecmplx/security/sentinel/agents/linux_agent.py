"""Sentinel Linux Monitoring Agent.

Collects system metrics (CPU, memory, disk, network, process counts)
and converts them into syndrome triads for the Sentinel API.

Usage:
    python -m sentinel.agents.linux_agent --api-url http://sentinel:8000 --source web-server-01
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import urllib.request
import urllib.error


@dataclass
class SystemMetrics:
    """Collected system metrics for syndrome quantization."""

    cpu_percent: float
    memory_percent: float
    disk_percent: float
    load_avg_1m: float
    process_count: int
    open_files: int
    network_connections: int
    swap_percent: float
    io_wait: float

    def to_dict(self) -> dict[str, float]:
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_percent": self.disk_percent,
            "load_avg_1m": self.load_avg_1m,
            "process_count": float(self.process_count),
            "open_files": float(self.open_files),
            "network_connections": float(self.network_connections),
            "swap_percent": self.swap_percent,
            "io_wait": self.io_wait,
        }

    @property
    def thresholds(self) -> dict[str, tuple[float, float]]:
        """Default thresholds for metric quantization."""
        return {
            "cpu_percent": (0.0, 100.0),
            "memory_percent": (0.0, 100.0),
            "disk_percent": (0.0, 100.0),
            "load_avg_1m": (0.0, 10.0),
            "process_count": (0.0, 500.0),
            "open_files": (0.0, 10000.0),
            "network_connections": (0.0, 500.0),
            "swap_percent": (0.0, 100.0),
            "io_wait": (0.0, 100.0),
        }


class LinuxAgent:
    """Lightweight Linux monitoring agent for Sentinel.

    Collects metrics, quantizes them into syndrome triads, and sends
them to the Sentinel API for real-time anomaly detection.
    """

    def __init__(self, api_url: str, source: str = "", interval: int = 30):
        self.api_url = api_url.rstrip("/")
        self.source = source or socket.gethostname()
        self.interval = interval
        self._running = False
        self._session = None

    def _read_proc(self, path: str) -> str:
        try:
            return Path(path).read_text().strip()
        except Exception:
            return ""

    def _read_cmd(self, cmd: list[str]) -> str:
        try:
            return subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            ).stdout.strip()
        except Exception:
            return ""

    def collect_metrics(self) -> SystemMetrics:
        """Collect system metrics from /proc and system calls."""
        # CPU usage
        cpu_stat = self._read_proc("/proc/stat")
        cpu_percent = 0.0
        if cpu_stat:
            parts = cpu_stat.splitlines()[0].split()
            if len(parts) >= 5:
                total = sum(int(p) for p in parts[1:])
                idle = int(parts[4])
                cpu_percent = 100.0 * (1.0 - idle / total) if total > 0 else 0.0

        # Memory
        mem_info = self._read_proc("/proc/meminfo")
        memory_percent = 0.0
        swap_percent = 0.0
        if mem_info:
            mem_data = {}
            for line in mem_info.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    mem_data[key.strip()] = int(val.strip().split()[0])
            total_mem = mem_data.get("MemTotal", 1)
            free_mem = mem_data.get("MemAvailable", mem_data.get("MemFree", 0))
            memory_percent = 100.0 * (1.0 - free_mem / total_mem) if total_mem > 0 else 0.0
            total_swap = mem_data.get("SwapTotal", 1)
            free_swap = mem_data.get("SwapFree", 0)
            swap_percent = 100.0 * (1.0 - free_swap / total_swap) if total_swap > 0 else 0.0

        # Load average
        load_str = self._read_proc("/proc/loadavg")
        load_avg = 0.0
        if load_str:
            load_avg = float(load_str.split()[0])

        # Process count
        process_count = 0
        try:
            process_count = len([
                p for p in Path("/proc").iterdir()
                if p.name.isdigit()
            ])
        except Exception:
            pass

        # Open file descriptors
        open_files = 0
        try:
            open_files = len(list(Path("/proc/self/fd").iterdir()))
        except Exception:
            pass

        # Network connections
        net_connections = 0
        tcp_stat = self._read_proc("/proc/net/tcp")
        if tcp_stat:
            net_connections = len(tcp_stat.splitlines()) - 1

        # Disk usage
        disk_percent = 0.0
        try:
            st = os.statvfs("/")
            disk_percent = 100.0 * (1.0 - st.f_bavail / st.f_blocks) if st.f_blocks > 0 else 0.0
        except Exception:
            pass

        # IO wait (from iostat or /proc/stat)
        io_wait = 0.0
        if cpu_stat:
            parts = cpu_stat.splitlines()[0].split()
            if len(parts) >= 6:
                total_jiffies = sum(int(p) for p in parts[1:])
                io_wait = 100.0 * int(parts[5]) / total_jiffies if total_jiffies > 0 else 0.0

        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent,
            load_avg_1m=load_avg,
            process_count=process_count,
            open_files=open_files,
            network_connections=net_connections,
            swap_percent=swap_percent,
            io_wait=io_wait,
        )

    def send_to_api(self, metrics: SystemMetrics, endpoint: str = "/monitor") -> dict | None:
        """Send metrics to the Sentinel API."""
        payload = json.dumps({
            "source": self.source,
            "metrics": metrics.to_dict(),
            "thresholds": {k: list(v) for k, v in metrics.thresholds.items()},
        }).encode()

        try:
            req = urllib.request.Request(
                f"{self.api_url}{endpoint}",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            print(f"[WARN] Failed to send metrics: {e}", file=sys.stderr)
            return None

    def run(self) -> None:
        """Run the agent in a loop."""
        self._running = True
        print(f"[INFO] Sentinel Linux Agent starting — source={self.source} "
              f"api={self.api_url} interval={self.interval}s")

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
    parser = argparse.ArgumentParser(description="Sentinel Linux Monitoring Agent")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Sentinel API URL")
    parser.add_argument("--source", default="", help="Source identifier")
    parser.add_argument("--interval", type=int, default=30, help="Collection interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    agent = LinuxAgent(api_url=args.api_url, source=args.source, interval=args.interval)

    if args.once:
        result = agent.run_once()
        print(json.dumps(result, indent=2) if result else "No result")
    else:
        agent.run()


if __name__ == "__main__":
    main()
