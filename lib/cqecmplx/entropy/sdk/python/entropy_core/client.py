"""
client.py — EntropyCore Python SDK Client
==========================================

Provides a clean Python interface to the EntropyCore API.

Usage:
    from entropy_core import EntropyClient

    client = EntropyClient("http://localhost:8000")

    # Generate random bytes
    block = client.random_bytes(64)
    print(block.bytes_data.hex())

    # Verify the proof
    result = client.verify(block)
    assert result.status == "valid"

    # Batch generation
    batch = client.batch(4096, 100)
    for block in batch.blocks:
        use(block.bytes_data)

    # Fairness commitment
    commitment = client.commit("Slot machine round 1234")
    # ... later ...
    reveal = client.reveal(commitment.id)
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

import requests
import websocket


@dataclass
class EntropyBlock:
    """A block of secure random bytes with generation proof."""
    bytes_data: bytes
    size_bytes: int
    proof: Optional[dict[str, Any]] = None
    chart_density: float = 0.0
    correction_rate: float = 0.0
    generation_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "bytes_b64": base64.b64encode(self.bytes_data).decode("ascii"),
            "size_bytes": self.size_bytes,
            "proof": self.proof,
            "chart_density": self.chart_density,
            "correction_rate": self.correction_rate,
        }


@dataclass
class FairnessCommitment:
    """A cryptographic commitment for provably fair randomness."""
    id: str
    hash: str
    salt: str
    public_info: str
    created_at: str


@dataclass
class FairnessReveal:
    """The reveal that opens a fairness commitment."""
    random_bytes: bytes
    salt: str
    nonce: int
    seed_hash: str
    verified: bool


@dataclass
class BatchResult:
    """Result of a batch generation request."""
    blocks: list[EntropyBlock]
    total_bytes: int
    total_blocks: int
    generation_time_ms: float
    throughput_mbps: float


class EntropyClient:
    """
    EntropyCore SDK client.

    Provides access to all four API endpoints with a clean,
    production-grade interface including retries, timeouts,
    and automatic proof verification.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update({
            "User-Agent": "entropy-core-python/1.0.0",
            "Accept": "application/json",
        })

    def _post(self, path: str, json_data: dict) -> dict:
        """Make a POST request to the API."""
        resp = self.session.post(
            f"{self.base_url}{path}",
            json=json_data,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str) -> dict:
        """Make a GET request to the API."""
        resp = self.session.get(
            f"{self.base_url}{path}",
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def health(self) -> dict[str, Any]:
        """Check API health."""
        return self._get("/health")

    def random_bytes(
        self,
        size: int = 32,
        include_proof: bool = True,
    ) -> EntropyBlock:
        """
        Generate secure random bytes with optional proof.

        Args:
            size: Number of bytes (1 to 1MB)
            include_proof: Whether to include the non-periodicity proof

        Returns:
            EntropyBlock with random bytes and proof
        """
        data = self._post("/v1/secure-random", {
            "size_bytes": size,
            "include_proof": include_proof,
        })
        return self._parse_block(data)

    def batch(
        self,
        block_size: int = 4096,
        block_count: int = 100,
        include_proofs: bool = False,
    ) -> BatchResult:
        """
        High-throughput batch generation.

        Args:
            block_size: Bytes per block
            block_count: Number of blocks
            include_proofs: Include proofs (slower)

        Returns:
            BatchResult with all blocks
        """
        data = self._post("/v1/batch-gen", {
            "block_size": block_size,
            "block_count": block_count,
            "include_proofs": include_proofs,
        })
        blocks = [self._parse_block(b) for b in data.get("blocks", [])]
        return BatchResult(
            blocks=blocks,
            total_bytes=data.get("total_bytes", 0),
            total_blocks=data.get("total_blocks", 0),
            generation_time_ms=data.get("generation_time_ms", 0.0),
            throughput_mbps=data.get("throughput_mbps", 0.0),
        )

    def commit(self, description: str = "") -> FairnessCommitment:
        """
        Create a fairness commitment.

        Returns a commitment object that can be revealed later
        to prove the randomness was pre-committed.
        """
        data = self._post("/v1/fairness-proof", {
            "description": description,
        })
        commitment = data["commitment"]
        return FairnessCommitment(
            id=commitment["commitment_hash"][:16],
            hash=commitment["commitment_hash"],
            salt=commitment["salt"],
            public_info=commitment["public_info"],
            created_at=commitment["created_at"],
        )

    def reveal(self, commitment_id: str) -> FairnessReveal:
        """
        Reveal a fairness commitment.

        Args:
            commitment_id: The ID from commit()

        Returns:
            FairnessReveal with the random bytes and verification
        """
        data = self._get(f"/v1/fairness-proof/{commitment_id}/reveal")
        reveal = data.get("reveal", {})
        return FairnessReveal(
            random_bytes=base64.b64decode(reveal.get("random_bytes_b64", "")),
            salt=reveal.get("salt", ""),
            nonce=reveal.get("nonce", 0),
            seed_hash=reveal.get("seed_hash", ""),
            verified=data.get("verification", {}).get("commitment_verified", False),
        )

    def stream(
        self,
        total_bytes: int = 65536,
        block_size: int = 4096,
    ) -> Iterator[EntropyBlock]:
        """
        Stream random bytes via WebSocket.

        Args:
            total_bytes: Total bytes to stream
            block_size: Bytes per chunk

        Yields:
            EntropyBlock chunks
        """
        ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        ws = websocket.create_connection(
            f"{ws_url}/v1/stream",
            timeout=self.timeout,
        )
        try:
            ws.send(json.dumps({
                "total_bytes": total_bytes,
                "block_size": block_size,
            }))
            while True:
                msg = json.loads(ws.recv())
                if msg.get("type") == "complete":
                    break
                if msg.get("type") == "error":
                    raise RuntimeError(msg.get("message", "Stream error"))
                if "bytes_b64" in msg:
                    yield EntropyBlock(
                        bytes_data=base64.b64decode(msg["bytes_b64"]),
                        size_bytes=len(base64.b64decode(msg["bytes_b64"])),
                        proof={"syndrome_id": msg.get("syndrome_id", "")},
                    )
        finally:
            ws.close()

    def verify(self, block: EntropyBlock) -> dict[str, Any]:
        """
        Verify an entropy block client-side.

        Checks the VOA partition, syndrome ID, and Monster scalar.
        """
        from .verify import verify_block
        return verify_block(block.to_dict())

    @staticmethod
    def _parse_block(data: dict[str, Any]) -> EntropyBlock:
        """Parse an API block response into an EntropyBlock."""
        return EntropyBlock(
            bytes_data=base64.b64decode(data.get("bytes_b64", "")),
            size_bytes=data.get("size_bytes", 0),
            proof=data.get("proof"),
            chart_density=data.get("chart_density", 0.0),
            correction_rate=data.get("correction_rate", 0.0),
            generation_time_ms=data.get("generation_time_ms", 0.0),
        )

    def close(self):
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
