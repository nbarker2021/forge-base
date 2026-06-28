"""
EntropyCore Python SDK
=======================

pip install entropy-core

Usage:
    import entropy_core

    # Generate secure random bytes with proof
    block = entropy_core.random_bytes(32)
    print(block.bytes_data)
    print(block.proof.syndrome_id)  # non-periodicity proof

    # Client-side verification
    result = entropy_core.verify_block(block.to_dict())
    print(result["status"])  # "valid"

    # Fairness commitment for gambling/blockchain
    commitment = entropy_core.commit_randomness("Lottery #42")
    # Later...
    reveal = entropy_core.reveal_commitment(commitment.id)

    # Stream randomness
    for chunk in entropy_core.stream_bytes(total_bytes=1_000_000):
        process(chunk.bytes_data)
"""

from .client import EntropyClient
from .verify import verify_block, verify_stream

__version__ = "1.0.0"
__all__ = [
    "EntropyClient",
    "verify_block",
    "verify_stream",
]

# Convenience functions for direct usage
def random_bytes(size: int = 32, include_proof: bool = True):
    """Generate secure random bytes with proof."""
    client = EntropyClient()
    return client.random_bytes(size, include_proof=include_proof)


def commit_randomness(description: str = ""):
    """Create a fairness commitment."""
    client = EntropyClient()
    return client.commit(description)


def reveal_commitment(commitment_id: str):
    """Reveal a commitment."""
    client = EntropyClient()
    return client.reveal(commitment_id)


def stream_bytes(total_bytes: int = 65536, block_size: int = 4096):
    """Stream random bytes as an iterator."""
    client = EntropyClient()
    return client.stream(total_bytes, block_size)
