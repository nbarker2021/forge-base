"""
EntropyCore Client-Side Verification Library
=============================================

Independent verification of entropy blocks without trusting the server.

Usage:
    from entropy_verify import verify_block, verify_stream

    # Verify a block from the API
    result = verify_block(block_dict)
    assert result["status"] == "valid"

    # Verify non-periodicity across a stream
    result = verify_stream(blocks)
    assert result["non_periodic"] is True
"""

from .verifier import verify_block, verify_stream, verify_syndrome

__version__ = "1.0.0"
__all__ = ["verify_block", "verify_stream", "verify_syndrome"]
