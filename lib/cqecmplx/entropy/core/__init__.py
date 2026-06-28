"""
EntropyCore — Rule 30 Cryptographic Entropy Engine
===================================================

Core engine implementing Rule 30 cellular automaton with mathematically
proven non-periodicity via the VOA partition Z(q) = 2q^0 + 6q^5.

The 8-chart state machine ensures no cycle ever repeats. Every entropy
block comes with a compact syndrome ID that clients can independently verify.

Key components:
    Rule30Engine     — Generate entropy from Rule 30 CA evolution
    VOAPartition     — VOA sector decomposition and checksums
    ChartMachine     — 8-chart state machine for non-periodicity proofs
    EntropyVerifier  — Client-side verification of entropy blocks
"""

from .rule30_engine import Rule30Engine, EntropyBlock, GenerationProof
from .voa_partition import VOAPartition, voa_checksum, voa_sector_of
from .chart_machine import ChartMachine, ChartState, EightChartStates
from .verifier import EntropyVerifier, verify_block, verify_stream

__all__ = [
    "Rule30Engine",
    "EntropyBlock",
    "GenerationProof",
    "VOAPartition",
    "voa_checksum",
    "voa_sector_of",
    "ChartMachine",
    "ChartState",
    "EightChartStates",
    "EntropyVerifier",
    "verify_block",
    "verify_stream",
]

__version__ = "1.0.0"
