"""
api/models.py — Pydantic models for EntropyCore API
====================================================

Request and response models for the four core endpoints:
1. SecureRandom — returns blocks of random bytes with proofs
2. VerifiableStream — WebSocket streaming randomness
3. FairnessProof — commitment + reveal for provably fair randomness
4. BatchGen — high-throughput batch generation
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Request Models
# ─────────────────────────────────────────────────────────────────────────────

class SecureRandomRequest(BaseModel):
    """Request for secure random bytes with generation proof."""
    size_bytes: int = Field(default=32, ge=1, le=1048576,
                           description="Number of random bytes (1 to 1MB)")
    include_proof: bool = Field(default=True,
                                description="Include mathematical proof")


class BatchGenRequest(BaseModel):
    """Request for high-throughput batch generation."""
    block_size: int = Field(default=4096, ge=64, le=65536)
    block_count: int = Field(default=100, ge=1, le=10000)
    include_proofs: bool = Field(default=False,
                                 description="Include proofs (slower)")


class FairnessProofRequest(BaseModel):
    """Request for a provably fair commitment + reveal scheme."""
    description: str = Field(default="",
                             description="Description of the fairness use case")
    reveal_at: Optional[str] = Field(default=None,
                                     description="ISO-8601 timestamp for reveal")


class StreamRequest(BaseModel):
    """Request to start a verifiable entropy stream."""
    total_bytes: int = Field(default=65536, ge=256, le=104857600)
    block_size: int = Field(default=4096, ge=256, le=65536)
    verify_checksum: bool = Field(default=True)


# ─────────────────────────────────────────────────────────────────────────────
# Response Models
# ─────────────────────────────────────────────────────────────────────────────

class VOAPartitionProof(BaseModel):
    """VOA partition proof Z(q) = 2q^0 + 6q^5."""
    weight_distribution: dict[str, int]
    vacuum_fraction: float
    excited_fraction: float
    seed_partition_function: str = "Z(q) = 2q^0 + 6q^5"
    monster_scalar: int = 196883


class GenerationProofResponse(BaseModel):
    """Mathematical proof of non-periodicity for an entropy block."""
    block_index: int
    chart_sequence: list[list[int]] = Field(..., description="First 256 (L,C,R) chart states")
    syndrome_id: str = Field(..., description="Compact VOA checksum")
    seed_hash: str
    timestamp: str
    voa_partition: VOAPartitionProof
    monster_scalar: int = 196883


class SecureRandomResponse(BaseModel):
    """Response with secure random bytes and generation proof."""
    bytes_b64: str = Field(..., description="Base64-encoded random bytes")
    size_bytes: int
    proof: Optional[GenerationProofResponse] = None
    chart_density: float = Field(..., description="Fraction of 1-bits in chart states")
    correction_rate: float = Field(..., description="Fraction where correction fires")
    generation_time_ms: float


class BatchGenResponse(BaseModel):
    """Response for high-throughput batch generation."""
    blocks: list[SecureRandomResponse]
    total_bytes: int
    total_blocks: int
    generation_time_ms: float
    throughput_mbps: float


class CommitmentData(BaseModel):
    """A cryptographic commitment for provably fair randomness."""
    commitment_hash: str = Field(..., description="SHA-256 commitment hash")
    salt: str = Field(..., description="Random salt used in commitment")
    public_info: str = Field(..., description="Public description of the use case")
    created_at: str
    reveal_at: Optional[str] = None


class RevealData(BaseModel):
    """The reveal data that opens a commitment."""
    random_bytes_b64: str
    salt: str
    nonce: int
    seed_hash: str
    chart_sequence_hash: str


class FairnessProofResponse(BaseModel):
    """Response for provably fair commitment + reveal scheme."""
    commitment: CommitmentData
    status: str = Field(..., description="'committed' or 'revealed'")
    reveal: Optional[RevealData] = None
    verification: Optional[dict[str, Any]] = None


class StreamBlock(BaseModel):
    """A single block in a verifiable entropy stream."""
    block_index: int
    bytes_b64: str
    syndrome_id: str
    previous_syndrome_hash: str
    timestamp: str
    checksum_valid: bool


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "1.0.0"
    engine: str = "entropy-core"
    timestamp: str
    uptime_seconds: float
    blocks_generated: int
    total_bytes_generated: int


class StatsResponse(BaseModel):
    """Statistics response."""
    total_requests: int
    total_blocks_generated: int
    total_bytes_generated: int
    avg_generation_time_ms: float
    peak_throughput_mbps: float
    voa_verifications_passed: int
    voa_verifications_failed: int
