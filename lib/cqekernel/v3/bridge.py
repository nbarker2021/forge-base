"""
v3_bridge.py: a small HTTP bridge that exposes the MannyAI v3 kernel
as a tool for the Hermes Discord gateway.

The Discord gateway runs as a service in `/c/Users/nbark/AppData/Local/hermes/`.
By default it routes messages through the Hermes main agent (which has the
HuggingFace/GitHub/browser tools). To add the v3 kernel as a tool the gateway
can call, this bridge provides an HTTP endpoint that:

  POST /invoke
    body: {"tool": "TMN-crystal", "input": "..."}
    returns: the kernel's invoke() result

  POST /message
    body: {"user_id": "...", "channel_id": "...", "message": "..."}
    returns: the kernel's handle_message() result (for direct Discord routing)

  GET /health
    returns: kernel boot state

Run this in a background terminal:
    cd /d/CQE_CMPLX
    python cqekernel/v3_bridge.py --port 7777

Then add to /c/Users/nbark/AppData/Local/hermes/config.yaml:
    gateway:
      external_tools:
        - url: http://localhost:7777
          name: mannyai-v3
          tools: [invoke, message]

This is a v3.1 wire-up — full integration with the gateway config is
the next step. For now, the bridge is callable and self-documenting.

HONEST BOUNDARY: this is the WIRE — the bridge. The CONFIG (telling
the gateway to actually use the bridge) is in a separate file. The
GATEWAY RESTART (so the config takes effect) is the final step.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Add the cqekernel to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cqekernel.v3 import MannyKernel  # noqa: E402

logger = logging.getLogger("v3_bridge")


class V3KernelBridge:
    """Wraps the MannyKernel in an HTTP service."""

    def __init__(self):
        print("[v3_bridge] Booting MannyAI v3 kernel...", flush=True)
        self.kernel = MannyKernel()
        boot = self.kernel.boot()
        print(f"[v3_bridge] Booted: {self.kernel.summary()}", flush=True)
        self.boot_state = boot
        self.request_count = 0

    def invoke(self, tool: str, input_data):
        """POST /invoke"""
        self.request_count += 1
        return self.kernel.invoke(tool, input_data)

    def message(self, user_id: str, channel_id: str, message: str):
        """POST /message (the Discord routing path)"""
        self.request_count += 1
        return self.kernel.handle_message(user_id, channel_id, message)

    def health(self):
        """GET /health"""
        return {
            "status": "ok",
            "kernel": self.kernel.summary(),
            "request_count": self.request_count,
            "boot": self.boot_state,
        }


class V3Handler(BaseHTTPRequestHandler):
    """HTTP request handler for the bridge."""

    bridge = None  # set by main()

    def log_message(self, format, *args):
        # Suppress default logging; we log via the logger
        logger.info(format, *args)

    def do_POST(self):
        if self.bridge is None:
            self._respond(503, {"error": "bridge not initialized"})
            return
        # Read body
        length = int(self.headers.get("Content-Length", 0))
        body_raw = self.rfile.read(length).decode("utf-8")
        try:
            body = json.loads(body_raw) if body_raw else {}
        except json.JSONDecodeError:
            self._respond(400, {"error": "invalid JSON"})
            return

        if self.path == "/invoke":
            tool = body.get("tool")
            input_data = body.get("input", body.get("payload", ""))
            if not tool:
                self._respond(400, {"error": "missing 'tool' field"})
                return
            result = self.bridge.invoke(tool, input_data)
            self._respond(200, result)
        elif self.path == "/message":
            user_id = body.get("user_id", "anon")
            channel_id = body.get("channel_id", "anon")
            message = body.get("message", "")
            result = self.bridge.message(user_id, channel_id, message)
            self._respond(200, result)
        else:
            self._respond(404, {"error": f"unknown endpoint {self.path!r}"})

    def do_GET(self):
        if self.bridge is None:
            self._respond(503, {"error": "bridge not initialized"})
            return
        if self.path == "/health":
            self._respond(200, self.bridge.health())
        elif self.path == "/":
            # Index page: a help message
            self._respond(200, {
                "service": "MannyAI v3 bridge",
                "kernel": self.bridge.kernel.summary(),
                "endpoints": {
                    "GET /health": "kernel state + request count",
                    "POST /invoke": '{"tool": "TMN-...", "input": ...}',
                    "POST /message": '{"user_id": "...", "channel_id": "...", "message": "..."}',
                },
            })
        else:
            self._respond(404, {"error": f"unknown endpoint {self.path!r}"})

    def _respond(self, status: int, payload):
        body = json.dumps(payload, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description="MannyAI v3 kernel HTTP bridge")
    parser.add_argument("--port", type=int, default=7777, help="port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="host to bind to")
    args = parser.parse_args()

    bridge = V3KernelBridge()
    V3Handler.bridge = bridge

    server = HTTPServer((args.host, args.port), V3Handler)
    print(f"[v3_bridge] Listening on http://{args.host}:{args.port}", flush=True)
    print(f"[v3_bridge] Try: curl http://{args.host}:{args.port}/health", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[v3_bridge] Shutting down...", flush=True)
        server.shutdown()


if __name__ == "__main__":
    main()
