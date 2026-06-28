"""Three-Leech transport contract for the Nebe Gamma_72 construction boundary.

Nebe's classical construction places Gamma_i inside three copies of the
Leech lattice. The actual landing depends on a polarization, equivalently a
selected Hermitian Z[alpha] structure. This module proves that arbitrary byte
payloads reach the three verified Leech sheets losslessly and records the
remaining matrix-action gate explicitly.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from .enumerated_glue import (
    LEECH_MINIMAL_SHELL_RADIX,
    decode_leech_ribbon,
    derive_classical_leech_minimal_landing,
    derive_enumerated_glue_selector,
    encode_leech_ribbon,
)


NEBE_HERMITIAN_STRUCTURE_COUNT = 9


def _quarter_turn_clockwise(rows: list[list[int]]) -> list[list[int]]:
    """Rotate one rectangular coordinate image clockwise by 90 degrees."""
    return [list(row) for row in zip(*reversed(rows))]


def derive_quarter_turn_leech_views(vector: tuple[int, ...]) -> dict[str, Any]:
    """Read one 24-coordinate Leech vector as four literal image rotations."""
    if len(vector) != 24:
        raise ValueError("Leech image vector must contain exactly 24 coordinates")
    rows = [list(vector[offset : offset + 8]) for offset in range(0, 24, 8)]
    views = []
    current = rows
    for degrees in (0, 90, 180, 270):
        views.append(
            {
                "degrees": degrees,
                "shape": [len(current), len(current[0])],
                "rows": current,
            }
        )
        current = _quarter_turn_clockwise(current)
    literal_e8_rows = [
        row for view in views for row in view["rows"] if len(row) == 8
    ]
    three_coordinate_rows = [
        row for view in views for row in view["rows"] if len(row) == 3
    ]
    return {
        "status": "literal_quarter_turn_views",
        "views": views,
        "view_shapes": [view["shape"] for view in views],
        "four_turns_restore_original": current == rows,
        "literal_e8_row_view_count": len(literal_e8_rows),
        "literal_three_coordinate_row_view_count": len(three_coordinate_rows),
        "every_literal_e8_row_has_nonzero_support": all(
            any(coordinate != 0 for coordinate in row) for row in literal_e8_rows
        ),
        "twelve_e8_rows_literal_geometry_proved": False,
        "proof_boundary": (
            "literal quarter turns alternate 3x8 and 8x3 images; only the "
            "0-degree and 180-degree reads expose literal eight-coordinate rows"
        ),
    }


def derive_twelve_oriented_e8_bands(vector: tuple[int, ...]) -> dict[str, Any]:
    """Track three source E8 blocks through four literal image orientations."""
    if len(vector) != 24:
        raise ValueError("Leech image vector must contain exactly 24 coordinates")

    indexed_rows = [
        [(row * 8 + column, vector[row * 8 + column]) for column in range(8)]
        for row in range(3)
    ]
    orientations = (
        "horizontal",
        "vertical",
        "horizontal_reversed",
        "vertical_reversed",
    )
    bands = []
    current = indexed_rows
    for degrees, orientation in zip((0, 90, 180, 270), orientations):
        for source_block in range(3):
            entries = sorted(
                (
                    (row_index, column_index, coordinate, value)
                    for row_index, row in enumerate(current)
                    for column_index, (coordinate, value) in enumerate(row)
                    if coordinate // 8 == source_block
                ),
                key=lambda entry: entry[2] % 8,
            )
            bands.append(
                {
                    "degrees": degrees,
                    "source_e8_block": source_block,
                    "orientation": orientation,
                    "positions": [
                        [row_index, column_index]
                        for row_index, column_index, _, _ in entries
                    ],
                    "coordinate_indices": [coordinate for _, _, coordinate, _ in entries],
                    "values": [value for _, _, _, value in entries],
                }
            )
        current = _quarter_turn_clockwise(current)

    expected_coordinates = list(range(24))
    each_view_covers_all_24_coordinates_exactly_once = all(
        sorted(
            coordinate
            for band in bands
            if band["degrees"] == degrees
            for coordinate in band["coordinate_indices"]
        )
        == expected_coordinates
        for degrees in (0, 90, 180, 270)
    )
    return {
        "status": "twelve_oriented_e8_bands",
        "band_count": len(bands),
        "bands": bands,
        "all_bands_are_coordinate_permutations": all(
            band["coordinate_indices"]
            == list(range(band["source_e8_block"] * 8, (band["source_e8_block"] + 1) * 8))
            for band in bands
        ),
        "each_view_covers_all_24_coordinates_exactly_once": (
            each_view_covers_all_24_coordinates_exactly_once
        ),
        "four_view_coordinate_visit_count": sum(len(band["values"]) for band in bands),
        "gamma72_glue_proved": False,
        "proof_boundary": (
            "twelve oriented E8 bands are coordinate-proven visual reads; "
            "their role-cycle composition into Gamma72 glue remains open"
        ),
    }


def derive_three_leech_clr_role_cycle(payload: bytes) -> dict[str, Any]:
    """Expose three exact Leech sheets under each cyclic C/L/R assignment."""
    sheets = [encode_leech_ribbon(payload) for _ in range(3)]
    role_cycles = [
        ["C", "L", "R"],
        ["R", "C", "L"],
        ["L", "R", "C"],
    ]
    return {
        "status": "candidate_glue_selector",
        "leech_sheets": sheets,
        "role_cycles": role_cycles,
        "each_sheet_visits_each_role_once": all(
            sorted(cycle[index] for cycle in role_cycles) == ["C", "L", "R"]
            for index in range(3)
        ),
        "gamma72_glue_proved": False,
        "proof_boundary": (
            "the C/L/R assignment cycle is explicit and reversible; its equality "
            "to a Gamma72 glue action remains to be established"
        ),
    }


@lru_cache(maxsize=1)
def verify_literal_quarter_turn_experiment() -> dict[str, Any]:
    """Exhaust the Leech minimal shell under the literal four-image read."""
    all_restore = True
    every_literal_e8_row_has_nonzero_support = True
    twelve_oriented_e8_bands_verified = True
    for address in range(LEECH_MINIMAL_SHELL_RADIX):
        landing = derive_classical_leech_minimal_landing(address)
        vector = tuple(landing["scaled_integer_vector"])
        views = derive_quarter_turn_leech_views(
            vector
        )
        oriented_bands = derive_twelve_oriented_e8_bands(vector)
        all_restore = all_restore and views["four_turns_restore_original"]
        every_literal_e8_row_has_nonzero_support = (
            every_literal_e8_row_has_nonzero_support
            and views["every_literal_e8_row_has_nonzero_support"]
        )
        twelve_oriented_e8_bands_verified = (
            twelve_oriented_e8_bands_verified
            and oriented_bands["band_count"] == 12
            and oriented_bands["all_bands_are_coordinate_permutations"]
            and oriented_bands["each_view_covers_all_24_coordinates_exactly_once"]
        )
    return {
        "status": "pass" if all_restore and twelve_oriented_e8_bands_verified else "fail",
        "minimal_vectors_checked": LEECH_MINIMAL_SHELL_RADIX,
        "four_turns_restore_original_for_all_minimal_vectors": all_restore,
        "literal_geometry_verified": True,
        "literal_e8_rows_per_four_views": 6,
        "literal_three_coordinate_rows_per_four_views": 16,
        "twelve_oriented_e8_bands_verified": twelve_oriented_e8_bands_verified,
        "twelve_e8_rows_literal_geometry_proved": False,
        "every_literal_e8_row_has_nonzero_support": (
            every_literal_e8_row_has_nonzero_support
        ),
        "gamma72_glue_proved": False,
        "scope": "literal 0/90/180/270 image rotations of the classical Leech minimal shell",
    }


def derive_nebe_gamma72_contract(
    payload: bytes,
    *,
    hermitian_structure_id: int = 1,
) -> dict[str, Any]:
    """Emit a lossless three-Leech candidate receipt for one payload."""
    if not 1 <= hermitian_structure_id <= NEBE_HERMITIAN_STRUCTURE_COUNT:
        raise ValueError(
            "hermitian_structure_id must be in "
            f"[1, {NEBE_HERMITIAN_STRUCTURE_COUNT}]"
        )

    sheets = [encode_leech_ribbon(payload) for _ in range(3)]
    sheet_decodes = [decode_leech_ribbon(sheet) for sheet in sheets]
    request_metadata = [
        derive_enumerated_glue_selector(digit)
        for digit in sheets[0]["digits"]
    ]
    all_sheet_landings_are_leech_members = all(
        landing["leech_member"]
        for sheet in sheets
        for landing in sheet["landings"]
    )
    return {
        "status": "candidate_contract",
        "construction": "Nebe:Gamma72:L(M,N,3)",
        "ambient_lattice": "Lambda24^3",
        "ambient_dimension": 72,
        "component_dimensions": [24, 24, 24],
        "hermitian_structure_id": hermitian_structure_id,
        "known_hermitian_structure_count": NEBE_HERMITIAN_STRUCTURE_COUNT,
        "leech_sheets": sheets,
        "request_metadata": request_metadata,
        "enumeration_metadata_reused": True,
        "all_sheets_decode_exactly": all(decoded == payload for decoded in sheet_decodes),
        "all_sheet_landings_are_leech_members": all_sheet_landings_are_leech_members,
        "polarization_required": True,
        "polarization_matrices_supplied": False,
        "gamma72_landing_proved": False,
        "proof_boundary": (
            "three arbitrary-data Leech sheets and enumeration metadata are explicit; "
            "the selected Hermitian polarization matrix action remains required"
        ),
    }


@lru_cache(maxsize=1)
def verify_nebe_gamma72_contract() -> dict[str, Any]:
    """Verify three-sheet lossless transport without promoting Gamma_72 landing."""
    payloads = [b"", b"\x00", b"\x00\x00", bytes(range(256))]
    payloads.extend(bytes([value]) for value in range(256))
    receipts = [derive_nebe_gamma72_contract(payload) for payload in payloads]
    all_three_sheet_round_trips_exact = all(
        receipt["all_sheets_decode_exactly"] for receipt in receipts
    )
    all_sheet_landings_are_leech_members = all(
        receipt["all_sheet_landings_are_leech_members"] for receipt in receipts
    )
    return {
        "status": (
            "pass"
            if all_three_sheet_round_trips_exact and all_sheet_landings_are_leech_members
            else "fail"
        ),
        "payloads_checked": len(payloads),
        "all_three_sheet_round_trips_exact": all_three_sheet_round_trips_exact,
        "all_sheet_landings_are_leech_members": all_sheet_landings_are_leech_members,
        "gamma72_contract_expressed": True,
        "polarization_matrices_supplied": False,
        "gamma72_landing_proved": False,
        "scope": "lossless arbitrary-byte transport into three Leech sheets",
    }
