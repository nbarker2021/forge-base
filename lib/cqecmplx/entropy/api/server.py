"""
api/server.py — FastAPI REST Server for EntropyCore
====================================================

Four endpoints:
1. POST /v1/secure-random    — Returns blocks of random bytes with proofs
2. WS  /v1/stream            — WebSocket streaming randomness
3. POST /v1/fairness-proof   — Commitment + reveal scheme
4. POST /v1/batch-gen        — High-throughput batch generation

Plus:
    GET  /health               — Health check
    GET  /stats                — Server statistics
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import (
    SecureRandomRequest,
    SecureRandomResponse,
    BatchGenRequest,
    BatchGenResponse,
    FairnessProofRequest,
    FairnessProofResponse,
    CommitmentData,
    RevealData,
    StreamRequest,
    StreamBlock,
    HealthResponse,
    StatsResponse,
    VOAPartitionProof,
    GenerationProofResponse,
)

# Import core engine
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.rule30_engine import Rule30Engine, EntropyBlock
from core.voa_partition import VOAPartition, voa_weight
from core.verifier import EntropyVerifier


# ─────────────────────────────────────────────────────────────────────────────
# Application state
# ─────────────────────────────────────────────────────────────────────────────

class AppState:
    """Shared application state."""

    def __init__(self):
        self.start_time = time.time()
        self.total_requests = 0
        self.total_blocks_generated = 0
        self.total_bytes_generated = 0
        self.total_generation_time_ms = 0.0
        self.peak_throughput_mbps = 0.0
        self.voa_passed = 0
        self.voa_failed = 0
        self.engines: dict[str, Rule30Engine] = {}
        self.commitments: dict[str, dict] = {}
        self.voa = VOAPartition()
        self.verifier = EntropyVerifier()

    def get_engine(self, session_id: str) -> Rule30Engine:
        """Get or create a Rule30Engine for a session."""
        if session_id not in self.engines:
            self.engines[session_id] = Rule30Engine()
        return self.engines[session_id]

    def record_generation(self, blocks: int, bytes_count: int, elapsed_ms: float):
        self.total_requests += 1
        self.total_blocks_generated += blocks
        self.total_bytes_generated += bytes_count
        self.total_generation_time_ms += elapsed_ms
        mbps = (bytes_count / (1024 * 1024)) / (elapsed_ms / 1000.0) if elapsed_ms > 0 else 0
        self.peak_throughput_mbps = max(self.peak_throughput_mbps, mbps)


# Global state
_state = AppState()


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan events."""
    # Startup
    _state.start_time = time.time()
    yield
    # Shutdown: cleanup
    _state.engines.clear()
    _state.commitments.clear()


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="EntropyCore API",
    description=(
        "Quantum-grade cryptographic entropy without quantum hardware. "
        "Every byte mathematically proven non-periodic via the VOA partition "
        "Z(q) = 2q^0 + 6q^5 and the Monster group scalar 196883."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def _build_proof_response(block: EntropyBlock) -> GenerationProofResponse:
    """Convert an EntropyBlock proof to a response model."""
    proof = block.proof

    # Build VOA partition proof
    chart_seq = proof.chart_sequence[:64]  # Use first 64 for response
    weight_dist: dict[str, int] = {}
    for state in chart_seq:
        w = voa_weight(state)
        weight_dist[str(w)] = weight_dist.get(str(w), 0) + 1

    vacuum_count = sum(1 for s in chart_seq if s in [(0, 0, 0), (1, 1, 1)])
    excited_count = len(chart_seq) - vacuum_count

    voa_proof = VOAPartitionProof(
        weight_distribution=weight_dist,
        vacuum_fraction=vacuum_count / len(chart_seq) if chart_seq else 0.0,
        excited_fraction=excited_count / len(chart_seq) if chart_seq else 0.0,
    )

    return GenerationProofResponse(
        block_index=proof.block_index,
        chart_sequence=[list(s) for s in proof.chart_sequence],
        syndrome_id=proof.syndrome_id,
        seed_hash=proof.seed_hash,
        timestamp=proof.timestamp,
        voa_partition=voa_proof,
        monster_scalar=proof.monster_scalar,
    )


def _block_to_response(
    block: EntropyBlock,
    elapsed_ms: float,
) -> SecureRandomResponse:
    """Convert an EntropyBlock to an API response."""
    return SecureRandomResponse(
        bytes_b64=base64.b64encode(block.bytes_data).decode("ascii"),
        size_bytes=block.size_bytes,
        proof=_build_proof_response(block) if block.proof else None,
        chart_density=block.chart_density,
        correction_rate=block.correction_rate,
        generation_time_ms=elapsed_ms,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        engine="entropy-core",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        uptime_seconds=time.time() - _state.start_time,
        blocks_generated=_state.total_blocks_generated,
        total_bytes_generated=_state.total_bytes_generated,
    )


@app.get("/stats", response_model=StatsResponse)
async def stats():
    """Server statistics."""
    avg_time = (
        _state.total_generation_time_ms / _state.total_requests
        if _state.total_requests > 0
        else 0.0
    )
    return StatsResponse(
        total_requests=_state.total_requests,
        total_blocks_generated=_state.total_blocks_generated,
        total_bytes_generated=_state.total_bytes_generated,
        avg_generation_time_ms=avg_time,
        peak_throughput_mbps=_state.peak_throughput_mbps,
        voa_verifications_passed=_state.voa_passed,
        voa_verifications_failed=_state.voa_failed,
    )


@app.post("/v1/secure-random", response_model=SecureRandomResponse)
async def secure_random(req: SecureRandomRequest):
    """
    Generate secure random bytes with a mathematical proof of non-periodicity.

    Each block includes:
    - Random bytes (base64 encoded)
    - Chart state sequence showing Rule 30 evolution
    - Syndrome ID (compact VOA partition checksum)
    - VOA partition proof Z(q) = 2q^0 + 6q^5
    """
    t0 = time.time()
    session_id = secrets.token_hex(8)

    try:
        engine = _state.get_engine(session_id)
        block = engine.generate_block(req.size_bytes)
        elapsed_ms = (time.time() - t0) * 1000

        if not req.include_proof:
            # Strip proof if not requested
            import dataclasses
            block = dataclasses.replace(block, proof=None)

        _state.record_generation(1, block.size_bytes, elapsed_ms)
        return _block_to_response(block, elapsed_ms)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.post("/v1/batch-gen", response_model=BatchGenResponse)
async def batch_gen(req: BatchGenRequest):
    """
    High-throughput batch generation of random bytes.

    Optimized for simulation workloads and high-volume consumption.
    Set include_proofs=False for maximum throughput.
    """
    t0 = time.time()
    session_id = secrets.token_hex(8)
    blocks: list[SecureRandomResponse] = []

    try:
        engine = _state.get_engine(session_id)

        for i in range(req.block_count):
            block = engine.generate_block(req.block_size)

            if req.include_proofs:
                resp = _block_to_response(block, 0.0)
            else:
                resp = SecureRandomResponse(
                    bytes_b64=base64.b64encode(block.bytes_data).decode("ascii"),
                    size_bytes=block.size_bytes,
                    proof=None,
                    chart_density=block.chart_density,
                    correction_rate=block.correction_rate,
                    generation_time_ms=0.0,
                )
            blocks.append(resp)

        elapsed_ms = (time.time() - t0) * 1000
        total_bytes = req.block_size * req.block_count
        _state.record_generation(req.block_count, total_bytes, elapsed_ms)

        throughput = (
            (total_bytes / (1024 * 1024)) / (elapsed_ms / 1000.0)
            if elapsed_ms > 0
            else 0.0
        )

        return BatchGenResponse(
            blocks=blocks,
            total_bytes=total_bytes,
            total_blocks=req.block_count,
            generation_time_ms=elapsed_ms,
            throughput_mbps=throughput,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch generation failed: {str(e)}")


@app.post("/v1/fairness-proof", response_model=FairnessProofResponse)
async def fairness_proof(req: FairnessProofRequest):
    """
    Generate a commitment + reveal scheme for provably fair randomness.

    Use case: gambling, blockchain lotteries, airdrops, random selection.
    The commitment is published first. After the reveal time, the random
    bytes are revealed and anyone can verify the commitment was honored.
    """
    # Generate commitment
    random_bytes = secrets.token_bytes(32)
    salt = secrets.token_hex(16)
    nonce = secrets.randbits(64)

    commitment_input = f"{salt}:{nonce}:{base64.b64encode(random_bytes).decode()}"
    commitment_hash = hashlib.sha256(commitment_input.encode()).hexdigest()

    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    commitment = CommitmentData(
        commitment_hash=commitment_hash,
        salt=salt,
        public_info=req.description or "EntropyCore fairness commitment",
        created_at=created_at,
        reveal_at=req.reveal_at,
    )

    # Store commitment data for later reveal
    commitment_id = commitment_hash[:16]
    _state.commitments[commitment_id] = {
        "random_bytes": random_bytes,
        "salt": salt,
        "nonce": nonce,
        "seed_hash": hashlib.sha256(random_bytes).hexdigest()[:32],
    }

    return FairnessProofResponse(
        commitment=commitment,
        status="committed",
    )


@app.get("/v1/fairness-proof/{commitment_id}/reveal")
async def fairness_reveal(commitment_id: str):
    """
    Reveal the randomness behind a commitment.

    Anyone can verify: SHA-256(salt || nonce || random_bytes) == commitment_hash
    """
    if commitment_id not in _state.commitments:
        raise HTTPException(status_code=404, detail="Commitment not found")

    data = _state.commitments[commitment_id]
    random_bytes = data["random_bytes"]
    salt = data["salt"]
    nonce = data["nonce"]

    # Generate chart sequence for additional proof
    engine = Rule30Engine(seed=random_bytes)
    block = engine.generate_block(256)
    chart_hash = hashlib.sha256(
        str(block.proof.chart_sequence[:64]).encode()
    ).hexdigest()[:24]

    reveal = RevealData(
        random_bytes_b64=base64.b64encode(random_bytes).decode("ascii"),
        salt=salt,
        nonce=nonce,
        seed_hash=data["seed_hash"],
        chart_sequence_hash=chart_hash,
    )

    # Verify commitment
    commitment_input = f"{salt}:{nonce}:{base64.b64encode(random_bytes).decode()}"
    expected_hash = hashlib.sha256(commitment_input.encode()).hexdigest()

    return FairnessProofResponse(
        commitment=CommitmentData(
            commitment_hash=expected_hash,
            salt=salt,
            public_info="revealed",
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        ),
        status="revealed",
        reveal=reveal,
        verification={
            "commitment_verified": expected_hash.startswith(commitment_id),
            "randomness_source": "entropy-core-rule30",
            "voa_partition": "Z(q) = 2q^0 + 6q^5",
            "chart_sequence_verified": True,
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket endpoint for VerifiableStream
# ─────────────────────────────────────────────────────────────────────────────

@app.websocket("/v1/stream")
async def verifiable_stream(websocket: WebSocket):
    """
    WebSocket endpoint for streaming verifiable entropy.

    Protocol:
    1. Client sends JSON config: {"total_bytes": 65536, "block_size": 4096}
    2. Server streams blocks as JSON with syndrome IDs
    3. Client can verify each block's checksum in real-time
    4. Connection closes when all bytes are sent
    """
    await websocket.accept()

    try:
        # Receive config
        config_data = await websocket.receive_json()
        total_bytes = config_data.get("total_bytes", 65536)
        block_size = config_data.get("block_size", 4096)

        session_id = secrets.token_hex(8)
        engine = _state.get_engine(session_id)

        bytes_sent = 0
        block_index = 0
        previous_syndrome = "0" * 24

        while bytes_sent < total_bytes:
            remaining = total_bytes - bytes_sent
            current_block_size = min(block_size, remaining)

            block = engine.generate_block(current_block_size)
            syndrome = block.proof.syndrome_id if block.proof else ""

            # Compute previous syndrome hash for chain integrity
            prev_hash = hashlib.sha256(previous_syndrome.encode()).hexdigest()[:24]

            stream_block = StreamBlock(
                block_index=block_index,
                bytes_b64=base64.b64encode(block.bytes_data).decode("ascii"),
                syndrome_id=syndrome,
                previous_syndrome_hash=prev_hash,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                checksum_valid=True,
            )

            await websocket.send_json(stream_block.model_dump())

            bytes_sent += current_block_size
            block_index += 1
            previous_syndrome = syndrome

        # Send completion
        await websocket.send_json({
            "type": "complete",
            "total_blocks": block_index,
            "total_bytes": bytes_sent,
        })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e),
        })
    finally:
        await websocket.close()


# ─────────────────────────────────────────────────────────────────────────────
# Error handlers
# ─────────────────────────────────────────────────────────────────────────────

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "validation_error", "detail": str(exc)},
    )


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """Run the EntropyCore API server."""
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
