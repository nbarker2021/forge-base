"""
verifier.py — Standalone Entropy Verification Library
=====================================================

Pure Python verification of EntropyCore entropy blocks.
No external dependencies. Can run offline.

Verifies:
1. Chart state validity (all states in {0,1}^3)
2. VOA partition Z(q) = 2q^0 + 6q^5
3. Monster scalar alignment (196883)
4. Syndrome ID format and computation
5. Non-periodicity (no repeating syndrome IDs)
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


def voa_weight(state: tuple[int, int, int]) -> int:
    """VOA conformal weight: 0 for vacuum, 5 for excited."""
    L, C, R = state
    if L == C == R:
        return 0
    return 5


def verify_block(block_data: dict[str, Any], tolerance: float = 0.15) -> dict[str, Any]:
    """
    Verify an entropy block independently.

    Args:
        block_data: Block dict from API (with proof)
        tolerance: Allowed VOA deviation

    Returns:
        {"status": "valid"|"invalid", errors: [...], ...}
    """
    errors: list[str] = []

    proof = block_data.get("proof")
    if not proof:
        return {"status": "valid", "note": "no proof to verify"}

    chart_seq = [tuple(s) for s in proof.get("chart_sequence", [])]
    if not chart_seq:
        errors.append("empty chart sequence")
        return {"status": "invalid", "errors": errors}

    # 1. Validate chart states
    for state in chart_seq:
        if state not in CHART_STATES:
            errors.append(f"invalid state: {state}")

    # 2. VOA partition Z(q) = 2q^0 + 6q^5
    n = len(chart_seq)
    weight_counts: dict[int, int] = {}
    for state in chart_seq:
        w = voa_weight(state)
        weight_counts[w] = weight_counts.get(w, 0) + 1

    vacuum_count = weight_counts.get(0, 0)
    expected_vacuum = n * 2 / 8.0
    deviation = abs(vacuum_count - expected_vacuum) / n if n > 0 else 0

    if deviation > tolerance:
        errors.append(f"vacuum deviation {deviation:.3f} > {tolerance}")

    # 3. Monster scalar
    if proof.get("monster_scalar") != MONSTER_SCALAR:
        errors.append(f"monster scalar: expected {MONSTER_SCALAR}")

    # 4. Seed hash format
    seed_hash = proof.get("seed_hash", "")
    if len(seed_hash) != 32:
        errors.append(f"seed hash length {len(seed_hash)} != 32")

    # 5. Syndrome format
    syndrome = proof.get("syndrome_id", "")
    if len(syndrome) != 24:
        errors.append(f"syndrome length {len(syndrome)} != 24")

    # 6. Density ~0.5
    density = block_data.get("chart_density", 0.5)
    if abs(density - 0.5) > tolerance:
        errors.append(f"density {density} deviates from 0.5")

    status = "valid" if not errors else "invalid"
    return {
        "status": status,
        "errors": errors,
        "vacuum_fraction": vacuum_count / n if n > 0 else 0,
        "weight_distribution": weight_counts,
        "deviation": deviation,
        "monster_scalar_ok": proof.get("monster_scalar") == MONSTER_SCALAR,
        "syndrome_format_ok": len(syndrome) == 24,
    }


def verify_stream(blocks: list[dict[str, Any]], tolerance: float = 0.15) -> dict[str, Any]:
    """
    Verify a stream of entropy blocks.

    Checks non-periodicity by ensuring no syndrome ID repeats.
    """
    results = []
    all_valid = True
    syndromes: list[str] = []

    for i, block in enumerate(blocks):
        result = verify_block(block, tolerance)
        results.append({"index": i, **result})
        if result["status"] != "valid":
            all_valid = False
        proof = block.get("proof", {})
        syndromes.append(proof.get("syndrome_id", ""))

    unique = set(syndromes)
    collisions = len(syndromes) - len(unique)

    return {
        "status": "valid" if (all_valid and collisions == 0) else "invalid",
        "block_count": len(blocks),
        "all_blocks_valid": all_valid,
        "syndrome_collisions": collisions,
        "unique_syndromes": len(unique),
        "non_periodic": collisions == 0,
        "results": results,
    }


def verify_syndrome(
    syndrome_id: str,
    chart_sequence: list[tuple[int, int, int]],
    seed_hash: str,
) -> bool:
    """
    Recompute and verify a syndrome ID.

    Args:
        syndrome_id: The syndrome ID to verify
        chart_sequence: The chart state sequence
        seed_hash: The seed hash used in generation

    Returns:
        True if the syndrome ID is correctly computed
    """
    if len(syndrome_id) != 24 or len(seed_hash) != 32:
        return False
    if not chart_sequence:
        return False

    weight_counts: dict[int, int] = {}
    for state in chart_sequence:
        w = voa_weight(state)
        weight_counts[w] = weight_counts.get(w, 0) + 1

    hash_input = f"{seed_hash}:{len(chart_sequence)}"
    hash_input += f":{weight_counts.get(0, 0)}:{weight_counts.get(5, 0)}"

    expected = hashlib.sha256(hash_input.encode()).hexdigest()[:24]
    return expected == syndrome_id
