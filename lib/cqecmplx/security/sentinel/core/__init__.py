"""Sentinel Syndrome Fingerprinting Engine.

Ported from CMPLX-R30: 8-syndrome system with 64-bit checkpoint IDs,
chart state transitions, and bonded frame observations.
"""

from .syndrome import (
    SyndromeSignature,
    SyndromeFingerprint,
    ChartState,
    ChartStateMachine,
    FingerprintEngine,
    compute_syndrome_id,
    LIE_CONJUGATES,
    ALL_TRIADS,
)
from .checkpoint import Checkpoint, CheckpointLedger, compute_64bit_id

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
