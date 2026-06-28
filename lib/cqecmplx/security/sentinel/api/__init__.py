"""Sentinel FastAPI Server.

4 endpoints + WebSocket streaming:
  POST /baseline     — Learn the normal syndrome fingerprint
  POST /monitor      — Real-time streaming anomaly detection
  GET  /alerts       — Query alerts with mathematical proof
  GET  /audit        — Immutable syndrome checkpoint log
  WS   /stream       — WebSocket streaming for real-time alerts
"""
