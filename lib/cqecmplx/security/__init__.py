"""cqecmplx.security — Zero-Trust Security Monitor (Sentinel).

Mathematically proven anomaly detection using the CMPLX-R30 syndrome framework.
8 syndromes, 64-bit checkpointing, and VOA partition ratio validation.

Key components:
    SyndromeSignature / SyndromeFingerprint — Anomaly fingerprints
    ChartState / ChartStateMachine          — 8-chart state machine
    FingerprintEngine                       — Syndrome computation
    Checkpoint / CheckpointLedger           — 64-bit checkpoint IDs
    compute_syndrome_id / compute_64bit_id  — Core operations

Usage:
    from cqecmplx.security import SyndromeFingerprint, FingerprintEngine
    engine = FingerprintEngine()
    fp = engine.compute(data)
"""

from .sentinel.core import (
    SyndromeSignature,
    SyndromeFingerprint,
    ChartState,
    ChartStateMachine,
    FingerprintEngine,
    compute_syndrome_id,
    Checkpoint,
    CheckpointLedger,
    compute_64bit_id,
    LIE_CONJUGATES,
    ALL_TRIADS,
)

__version__ = "1.0.0"
__all__ = [
    "SyndromeSignature",
    "SyndromeFingerprint",
    "ChartState",
    "ChartStateMachine",
    "FingerprintEngine",
    "compute_syndrome_id",
    "Checkpoint",
    "CheckpointLedger",
    "compute_64bit_id",
    "LIE_CONJUGATES",
    "ALL_TRIADS",
]