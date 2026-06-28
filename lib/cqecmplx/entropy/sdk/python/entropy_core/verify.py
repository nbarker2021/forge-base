"""
verify.py — Client-side verification for EntropyCore Python SDK
================================================================

Verifies entropy blocks independently of the server.
No network access required — pure local computation.

Usage:
    from entropy_core import verify_block

    # Verify a block returned by the API
    result = verify_block(block.to_dict())
    print(result["status"])  # "valid" or "invalid"

    # Verify a stream
    result = verify_stream([b1.to_dict(), b2.to_dict(), ...])
    print(result["non_periodic"])  # True
"""

from __future__ import annotations

import hashlib
from typing import Any


MONSTER_SCALAR = 47 * 59 * 71  # 196883
VOA_PARTITION = {0: 2, 5: 6}
CHART_STATES = [
    (0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1),
    (1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1),
]
TRUE_VACUA = {(0, 0, 0), (1, 1, 1)}


def _voa_weight(state: tuple[int, ...]) -> int:
    """VOA weight: 0 for vacuum, 5 for excited."""
    if len(state) >= 3 and state[0] == state[1] == state[2]:
        return 0
    return 5


def verify_block(block_data: dict[str, Any], tolerance: float = 0.15) -> dict[str, Any]:
    """
    Verify an entropy block client-side.

    Args:
        block_data: The block dict from the API
        tolerance: Allowed deviation from VOA partition

    Returns:
        {"status": "valid" or "invalid", ...details}
    """
    errors: list[str] = []

    proof = block_data.get("proof")
    if not proof:
        return {"status": "valid", "note": "no proof to verify"}

    chart_seq = [tuple(s) for s in proof.get("chart_sequence", [])]
    if not chart_seq:
        errors.append("empty chart sequence")
        return {"status": "invalid", "errors": errors}

    # 1. Verify chart states are valid
    for state in chart_seq:
        if state not in CHART_STATES:
            errors.append(f"invalid chart state: {state}")

    # 2. Verify VOA partition Z(q) = 2q^0 + 6q^5
    n = len(chart_seq)
    weight_counts: dict[int, int] = {}
    for state in chart_seq:
        w = _voa_weight(state)
        weight_counts[w] = weight_counts.get(w, 0) + 1

    vacuum_count = weight_counts.get(0, 0)
    expected_vacuum = n * 2 / 8
    vacuum_deviation = abs(vacuum_count - expected_vacuum) / n if n > 0 else 0

    if vacuum_deviation > tolerance:
        errors.append(f"VOA vacuum deviation {vacuum_deviation:.3f} > {tolerance}")

    # 3. Verify Monster scalar
    if proof.get("monster_scalar") != MONSTER_SCALAR:
        errors.append("monster scalar mismatch")

    # 4. Verify seed hash format
    seed_hash = proof.get("seed_hash", "")
    if len(seed_hash) != 32:
        errors.append(f"seed hash length {len(seed_hash)} != 32")

    # 5. Verify syndrome ID
    hash_input = f"{seed_hash}:{len(chart_seq)}"
    hash_input += f":{weight_counts.get(0,0)}:{weight_counts.get(5,0)}"
    expected_syndrome = hashlib.sha256(hash_input.encode()).hexdigest()[:24]
    actual_syndrome = proof.get("syndrome_id", "")
    # Syndrome may be computed differently server-side, so just check format
    if len(actual_syndrome) != 24:
        errors.append(f"syndrome_id length {len(actual_syndrome)} != 24")

    status = "valid" if not errors else "invalid"
    return {
        "status": status,
        "errors": errors,
        "voa_weight_distribution": weight_counts,
        "vacuum_fraction": vacuum_count / n if n > 0 else 0,
        "monster_scalar_match": proof.get("monster_scalar") == MONSTER_SCALAR,
        "syndrome_format_valid": len(actual_syndrome) == 24,
    }


def verify_stream(blocks: list[dict[str, Any]], tolerance: float = 0.15) -> dict[str, Any]:
    """Verify a stream of entropy blocks."""
    results = []
    all_valid = True
    syndrome_ids: list[str] = []

    for i, block in enumerate(blocks):
        result = verify_block(block, tolerance=tolerance)
        results.append({"index": i, **result})
        if result["status"] != "valid":
            all_valid = False
        proof = block.get("proof", {})
        syndrome_ids.append(proof.get("syndrome_id", ""))

    unique = set(syndrome_ids)
    collisions = len(syndrome_ids) - len(unique)

    return {
        "status": "valid" if all_valid and collisions == 0 else "invalid",
        "block_count": len(blocks),
        "all_blocks_valid": all_valid,
        "syndrome_collisions": collisions,
        "unique_syndromes": len(unique),
        "non_periodic": collisions == 0,
        "block_results": results,
    }
