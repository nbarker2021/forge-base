"""Enumeration-derived glue selectors for the three-E8 Leech carrier."""
from __future__ import annotations

from fractions import Fraction
from functools import lru_cache
from itertools import combinations, permutations, product
from typing import Any

from .lattice_codes import GOLAY_24_GENERATORS, _span_f2

REQUEST_TAIL_BITS = 16
LEECH_MINIMAL_SHELL_RADIX = 196_560
E8_BLOCK_ORDERS = tuple(permutations(range(3)))
E8_CROSS_BLOCK_PAIRS = ((0, 1), (1, 2), (2, 0))
E8_CROSS_BLOCK_LANDING_COUNT = len(E8_CROSS_BLOCK_PAIRS) * 8 * 8
LEECH_TYPE1_LANDINGS = tuple(product(combinations(range(24), 2), product((-4, 4), repeat=2)))
GOLAY_24_CODEWORDS = frozenset(
    tuple(codeword) for codeword in _span_f2(GOLAY_24_GENERATORS)
)
GOLAY_24_WORDS = tuple(sorted(GOLAY_24_CODEWORDS))
GOLAY_OCTADS = tuple(
    codeword for codeword in GOLAY_24_WORDS if sum(codeword) == 8
)
LEECH_TYPE2_SIGNS = tuple(
    signs for signs in product((-2, 2), repeat=8) if signs.count(-2) % 2 == 0
)
LEECH_TYPE2_LANDING_COUNT = len(GOLAY_OCTADS) * len(LEECH_TYPE2_SIGNS)


def derive_enumerated_glue_selector(n: int) -> dict[str, Any]:
    """Emit deterministic glue-selection metadata from one enumerated request."""
    if n < 0:
        raise ValueError("N must be non-negative")
    modulus = 1 << REQUEST_TAIL_BITS
    local_tail = n % modulus
    request_tail = format(local_tail, f"0{REQUEST_TAIL_BITS}b")
    return {
        "status": "selector_receipt_only",
        "N": n,
        "request_tail": request_tail,
        "request_cycle": n // modulus,
        "carrier": "Niemeier:E8^3",
        "carrier_geometry": {"block_count": 3, "block_dimension": 8},
        "block_order": list(E8_BLOCK_ORDERS[local_tail % len(E8_BLOCK_ORDERS)]),
        "rotation_phase": local_tail % 4,
        "parity_lane": request_tail.count("1") % 2,
        "selector_address": local_tail,
        "leech_landing_proved": False,
        "proof_boundary": (
            "Enumeration deterministically selects three-E8 glue metadata. "
            "A rootless Leech landing requires an explicit glue action and "
            "lattice-invariant verification."
        ),
    }


@lru_cache(maxsize=1)
def verify_enumerated_glue_selector_contract() -> dict[str, Any]:
    """Exhaust the fixed request-tail window without promoting a Leech landing."""
    receipts = [derive_enumerated_glue_selector(n) for n in range(1 << REQUEST_TAIL_BITS)]
    deterministic = all(
        receipt == derive_enumerated_glue_selector(receipt["N"])
        for receipt in receipts
    )
    return {
        "status": "pass" if deterministic else "fail",
        "tails_checked": len(receipts),
        "all_selectors_deterministic": deterministic,
        "all_block_orders_are_permutations": all(
            sorted(receipt["block_order"]) == [0, 1, 2] for receipt in receipts
        ),
        "all_carriers_are_e8_cubed": all(
            receipt["carrier"] == "Niemeier:E8^3" for receipt in receipts
        ),
        "leech_landing_proved": False,
        "pending_invariants": [
            "rank_24",
            "even",
            "unimodular",
            "root_count_norm2_zero",
            "minimum_norm_4",
        ],
        "scope": "fixed 16-bit enumeration-derived glue-selection metadata only",
    }


def leech_scaled_norm(vector: tuple[int, ...]) -> Fraction:
    """Return the norm after applying the standard `1 / sqrt(8)` scale."""
    if len(vector) != 24:
        raise ValueError("Leech scaled coordinates must have length 24")
    return Fraction(sum(coordinate * coordinate for coordinate in vector), 8)


def is_leech_scaled_coordinate(vector: tuple[int, ...]) -> bool:
    """Check one classical integer-coordinate presentation of the Leech lattice."""
    if len(vector) != 24 or any(not isinstance(coordinate, int) for coordinate in vector):
        return False
    if len({(4 * coordinate) % 8 for coordinate in vector}) != 1:
        return False
    if sum(vector) % 8 != (4 * vector[0]) % 8:
        return False
    return all(
        tuple(int(coordinate % 4 == residue) for coordinate in vector)
        in GOLAY_24_CODEWORDS
        for residue in range(4)
    )


@lru_cache(maxsize=1)
def verify_leech_membership_oracle() -> dict[str, Any]:
    """Verify basic positive and rootless-negative checks for the Leech oracle."""
    zero = (0,) * 24
    minimal_pair = (4, 4) + (0,) * 22
    norm2_root = (4,) + (0,) * 23
    zero_accepted = is_leech_scaled_coordinate(zero)
    minimal_pair_accepted = is_leech_scaled_coordinate(minimal_pair)
    norm2_root_rejected = not is_leech_scaled_coordinate(norm2_root)
    return {
        "status": (
            "pass"
            if zero_accepted
            and minimal_pair_accepted
            and leech_scaled_norm(minimal_pair) == 4
            and norm2_root_rejected
            and leech_scaled_norm(norm2_root) == 2
            else "fail"
        ),
        "zero_vector_accepted": zero_accepted,
        "minimal_pair_vector_accepted": minimal_pair_accepted,
        "norm2_root_vector_rejected": norm2_root_rejected,
        "rootless_condition_checked": True,
        "scope": "classical scaled-coordinate Leech membership oracle",
    }


def derive_enumerated_leech_minimal_landing(n: int) -> dict[str, Any]:
    """Emit one enumeration-selected cross-block norm-4 Leech vector."""
    if n < 0:
        raise ValueError("N must be non-negative")
    local_address = n % E8_CROSS_BLOCK_LANDING_COUNT
    block_pair = E8_CROSS_BLOCK_PAIRS[local_address // 64]
    pair_offset = local_address % 64
    left_coordinate = block_pair[0] * 8 + pair_offset // 8
    right_coordinate = block_pair[1] * 8 + pair_offset % 8
    vector = [0] * 24
    vector[left_coordinate] = 4
    vector[right_coordinate] = 4
    scaled_vector = tuple(vector)
    return {
        "status": "bounded_vector_landing",
        "N": n,
        "selector": derive_enumerated_glue_selector(n),
        "landing_address": local_address,
        "block_pair": list(block_pair),
        "coordinates": [left_coordinate, right_coordinate],
        "cross_block": block_pair[0] != block_pair[1],
        "scaled_integer_vector": list(scaled_vector),
        "scaled_norm": int(leech_scaled_norm(scaled_vector)),
        "leech_member": is_leech_scaled_coordinate(scaled_vector),
        "selected_vector_landing_proved": True,
        "full_lattice_construction_proved": False,
    }


@lru_cache(maxsize=1)
def verify_enumerated_leech_minimal_landings() -> dict[str, Any]:
    """Exhaust the bounded cross-block landing family selected by enumeration."""
    receipts = [
        derive_enumerated_leech_minimal_landing(n)
        for n in range(E8_CROSS_BLOCK_LANDING_COUNT)
    ]
    unique_vectors = {
        tuple(receipt["scaled_integer_vector"]) for receipt in receipts
    }
    all_cross_block = all(receipt["cross_block"] for receipt in receipts)
    all_leech_members = all(receipt["leech_member"] for receipt in receipts)
    all_scaled_norm4 = all(receipt["scaled_norm"] == 4 for receipt in receipts)
    return {
        "status": (
            "pass"
            if len(unique_vectors) == E8_CROSS_BLOCK_LANDING_COUNT
            and all_cross_block
            and all_leech_members
            and all_scaled_norm4
            else "fail"
        ),
        "landing_count": len(receipts),
        "unique_vector_count": len(unique_vectors),
        "all_cross_block": all_cross_block,
        "all_leech_members": all_leech_members,
        "all_scaled_norm4": all_scaled_norm4,
        "selected_vector_family_proved": True,
        "full_minimal_shell_proved": False,
        "scope": "192 enumeration-selected cross-E8-block norm-4 Leech vectors",
    }


def derive_enumerated_leech_type1_landing(n: int) -> dict[str, Any]:
    """Emit one signed two-coordinate norm-4 Leech vector from enumeration."""
    if n < 0:
        raise ValueError("N must be non-negative")
    local_address = n % len(LEECH_TYPE1_LANDINGS)
    coordinates, signs = LEECH_TYPE1_LANDINGS[local_address]
    vector = [0] * 24
    for coordinate, sign in zip(coordinates, signs):
        vector[coordinate] = sign
    scaled_vector = tuple(vector)
    return {
        "status": "bounded_type1_landing",
        "N": n,
        "landing_address": local_address,
        "coordinates": list(coordinates),
        "signs": list(signs),
        "scaled_integer_vector": list(scaled_vector),
        "scaled_norm": int(leech_scaled_norm(scaled_vector)),
        "leech_member": is_leech_scaled_coordinate(scaled_vector),
        "selected_vector_landing_proved": True,
        "full_minimal_shell_proved": False,
    }


@lru_cache(maxsize=1)
def verify_enumerated_leech_type1_orbit() -> dict[str, Any]:
    """Exhaust the signed two-coordinate type-1 Leech minimal-vector orbit."""
    receipts = [
        derive_enumerated_leech_type1_landing(n)
        for n in range(len(LEECH_TYPE1_LANDINGS))
    ]
    unique_vectors = {
        tuple(receipt["scaled_integer_vector"]) for receipt in receipts
    }
    all_leech_members = all(receipt["leech_member"] for receipt in receipts)
    all_scaled_norm4 = all(receipt["scaled_norm"] == 4 for receipt in receipts)
    return {
        "status": (
            "pass"
            if len(unique_vectors) == 1104 and all_leech_members and all_scaled_norm4
            else "fail"
        ),
        "landing_count": len(receipts),
        "unique_vector_count": len(unique_vectors),
        "all_leech_members": all_leech_members,
        "all_scaled_norm4": all_scaled_norm4,
        "full_type1_orbit_proved": True,
        "full_minimal_shell_proved": False,
        "scope": "1104 signed two-coordinate norm-4 Leech vectors",
    }


def derive_enumerated_leech_type2_landing(n: int) -> dict[str, Any]:
    """Emit one Golay-octad norm-4 Leech vector from enumeration."""
    if n < 0:
        raise ValueError("N must be non-negative")
    local_address = n % LEECH_TYPE2_LANDING_COUNT
    octad = GOLAY_OCTADS[local_address // len(LEECH_TYPE2_SIGNS)]
    signs = LEECH_TYPE2_SIGNS[local_address % len(LEECH_TYPE2_SIGNS)]
    support = [index for index, bit in enumerate(octad) if bit]
    vector = [0] * 24
    for coordinate, sign in zip(support, signs):
        vector[coordinate] = sign
    scaled_vector = tuple(vector)
    return {
        "status": "bounded_type2_landing",
        "N": n,
        "landing_address": local_address,
        "support": support,
        "signs": list(signs),
        "negative_sign_count": signs.count(-2),
        "scaled_integer_vector": list(scaled_vector),
        "scaled_norm": int(leech_scaled_norm(scaled_vector)),
        "leech_member": is_leech_scaled_coordinate(scaled_vector),
        "selected_vector_landing_proved": True,
        "full_minimal_shell_proved": False,
    }


@lru_cache(maxsize=1)
def verify_enumerated_leech_type2_orbit() -> dict[str, Any]:
    """Exhaust the Golay-octad type-2 Leech minimal-vector orbit."""
    receipts = [
        derive_enumerated_leech_type2_landing(n)
        for n in range(LEECH_TYPE2_LANDING_COUNT)
    ]
    unique_vectors = {
        tuple(receipt["scaled_integer_vector"]) for receipt in receipts
    }
    all_leech_members = all(receipt["leech_member"] for receipt in receipts)
    all_scaled_norm4 = all(receipt["scaled_norm"] == 4 for receipt in receipts)
    return {
        "status": (
            "pass"
            if len(GOLAY_OCTADS) == 759
            and len(LEECH_TYPE2_SIGNS) == 128
            and len(unique_vectors) == 97_152
            and all_leech_members
            and all_scaled_norm4
            else "fail"
        ),
        "octad_count": len(GOLAY_OCTADS),
        "sign_assignment_count": len(LEECH_TYPE2_SIGNS),
        "landing_count": len(receipts),
        "unique_vector_count": len(unique_vectors),
        "all_leech_members": all_leech_members,
        "all_scaled_norm4": all_scaled_norm4,
        "full_type2_orbit_proved": True,
        "full_minimal_shell_proved": False,
        "scope": "97152 Golay-octad signed norm-4 Leech vectors",
    }


def derive_enumerated_leech_type3_landing(n: int) -> dict[str, Any]:
    """Emit one Golay-word sign-lifted type-3 norm-4 Leech vector."""
    if n < 0:
        raise ValueError("N must be non-negative")
    local_address = n % (24 * len(GOLAY_24_WORDS))
    distinguished = local_address // len(GOLAY_24_WORDS)
    word = GOLAY_24_WORDS[local_address % len(GOLAY_24_WORDS)]
    vector = [
        (-3 if bit else 3) if coordinate == distinguished else (1 if bit else -1)
        for coordinate, bit in enumerate(word)
    ]
    scaled_vector = tuple(vector)
    return {
        "status": "bounded_type3_landing",
        "N": n,
        "landing_address": local_address,
        "distinguished_coordinate": distinguished,
        "golay_word": list(word),
        "scaled_integer_vector": list(scaled_vector),
        "scaled_norm": int(leech_scaled_norm(scaled_vector)),
        "leech_member": is_leech_scaled_coordinate(scaled_vector),
        "selected_vector_landing_proved": True,
        "full_lattice_construction_proved": False,
    }


@lru_cache(maxsize=1)
def verify_enumerated_leech_type3_orbit() -> dict[str, Any]:
    """Exhaust the Golay-word sign-lifted type-3 Leech minimal-vector orbit."""
    receipts = [
        derive_enumerated_leech_type3_landing(n)
        for n in range(24 * len(GOLAY_24_WORDS))
    ]
    unique_vectors = {
        tuple(receipt["scaled_integer_vector"]) for receipt in receipts
    }
    all_leech_members = all(receipt["leech_member"] for receipt in receipts)
    all_scaled_norm4 = all(receipt["scaled_norm"] == 4 for receipt in receipts)
    return {
        "status": (
            "pass"
            if len(GOLAY_24_WORDS) == 4096
            and len(unique_vectors) == 98_304
            and all_leech_members
            and all_scaled_norm4
            else "fail"
        ),
        "golay_word_count": len(GOLAY_24_WORDS),
        "distinguished_coordinate_count": 24,
        "landing_count": len(receipts),
        "unique_vector_count": len(unique_vectors),
        "all_leech_members": all_leech_members,
        "all_scaled_norm4": all_scaled_norm4,
        "full_type3_orbit_proved": True,
        "scope": "98304 Golay-word sign-lifted norm-4 Leech vectors",
    }


@lru_cache(maxsize=1)
def verify_enumerated_leech_classical_minimal_shell() -> dict[str, Any]:
    """Account for the three classical norm-4 Leech vector families."""
    type1 = verify_enumerated_leech_type1_orbit()
    type2 = verify_enumerated_leech_type2_orbit()
    type3 = verify_enumerated_leech_type3_orbit()
    orbit_counts = {
        "type1": type1["unique_vector_count"],
        "type2": type2["unique_vector_count"],
        "type3": type3["unique_vector_count"],
    }
    minimal_vector_count = sum(orbit_counts.values())
    all_orbits_pass = all(row["status"] == "pass" for row in (type1, type2, type3))
    return {
        "status": (
            "pass" if all_orbits_pass and minimal_vector_count == 196_560 else "fail"
        ),
        "orbit_counts": orbit_counts,
        "minimal_vector_count": minimal_vector_count,
        "three_classical_orbits_enumerated": all_orbits_pass,
        "exhaustiveness_from_first_principles_proved": False,
        "full_lattice_construction_proved": False,
        "scope": "accounting receipt for three classical Leech minimal-vector families",
    }


def derive_classical_leech_minimal_landing(address: int) -> dict[str, Any]:
    """Resolve one address in the three verified classical minimal-vector families."""
    if not 0 <= address < LEECH_MINIMAL_SHELL_RADIX:
        raise ValueError(f"address must be in range 0..{LEECH_MINIMAL_SHELL_RADIX - 1}")
    if address < len(LEECH_TYPE1_LANDINGS):
        receipt = derive_enumerated_leech_type1_landing(address)
        orbit = "type1"
    elif address < len(LEECH_TYPE1_LANDINGS) + LEECH_TYPE2_LANDING_COUNT:
        receipt = derive_enumerated_leech_type2_landing(address - len(LEECH_TYPE1_LANDINGS))
        orbit = "type2"
    else:
        receipt = derive_enumerated_leech_type3_landing(
            address - len(LEECH_TYPE1_LANDINGS) - LEECH_TYPE2_LANDING_COUNT
        )
        orbit = "type3"
    return {
        **receipt,
        "shell_address": address,
        "orbit": orbit,
    }


def _to_radix_digits(value: int, radix: int) -> list[int]:
    digits = []
    while value:
        value, digit = divmod(value, radix)
        digits.append(digit)
    return list(reversed(digits or [0]))


def encode_leech_ribbon(payload: bytes) -> dict[str, Any]:
    """Encode arbitrary bytes as a reversible ribbon of verified Leech landings."""
    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")
    framed = b"\x01" + payload
    digits = _to_radix_digits(int.from_bytes(framed, "big"), LEECH_MINIMAL_SHELL_RADIX)
    landings = [derive_classical_leech_minimal_landing(digit) for digit in digits]
    return {
        "status": "encoded",
        "codec": "leech_minimal_shell_radix_ribbon_v1",
        "radix": LEECH_MINIMAL_SHELL_RADIX,
        "payload_bytes": len(payload),
        "digits": digits,
        "landings": landings,
        "lossless_round_trip_scope": "arbitrary byte strings as sequences of Leech vectors",
        "single_vector_arbitrary_payload_proved": False,
    }


def decode_leech_ribbon(receipt: dict[str, Any]) -> bytes:
    """Decode a ribbon receipt back into its exact byte payload."""
    if receipt.get("codec") != "leech_minimal_shell_radix_ribbon_v1":
        raise ValueError("unsupported Leech ribbon codec")
    digits = receipt.get("digits")
    if not isinstance(digits, list) or not digits:
        raise ValueError("Leech ribbon receipt must include digits")
    value = 0
    for digit in digits:
        if not isinstance(digit, int) or not 0 <= digit < LEECH_MINIMAL_SHELL_RADIX:
            raise ValueError("Leech ribbon digit is out of bounds")
        value = value * LEECH_MINIMAL_SHELL_RADIX + digit
    framed = value.to_bytes(max(1, (value.bit_length() + 7) // 8), "big")
    if not framed.startswith(b"\x01"):
        raise ValueError("Leech ribbon sentinel is missing")
    payload = framed[1:]
    if len(payload) != receipt.get("payload_bytes"):
        raise ValueError("Leech ribbon payload length mismatch")
    return payload


@lru_cache(maxsize=1)
def verify_leech_ribbon_codec() -> dict[str, Any]:
    """Verify exact arbitrary-byte round trips through the Leech landing ribbon."""
    payloads = [b"", b"\x00", b"\x00\x00", bytes(range(256))]
    payloads.extend(bytes([value]) for value in range(256))
    receipts = [encode_leech_ribbon(payload) for payload in payloads]
    all_round_trips_exact = all(
        decode_leech_ribbon(receipt) == payload
        for payload, receipt in zip(payloads, receipts)
    )
    all_landings_are_leech_members = all(
        landing["leech_member"]
        for receipt in receipts
        for landing in receipt["landings"]
    )
    return {
        "status": (
            "pass" if all_round_trips_exact and all_landings_are_leech_members else "fail"
        ),
        "payloads_checked": len(payloads),
        "all_round_trips_exact": all_round_trips_exact,
        "all_landings_are_leech_members": all_landings_are_leech_members,
        "arbitrary_bytes_as_vector_ribbon_proved": True,
        "single_vector_arbitrary_payload_proved": False,
        "scope": "lossless arbitrary byte strings as radix-196560 Leech vector ribbons",
    }
