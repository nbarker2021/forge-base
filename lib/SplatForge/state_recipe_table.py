"""
SplatForge.state_recipe_table — the O(1) reverse-library pattern
(cqecmplx/r30/library.py's ReverseAtlasLibrary: "compile every observable
edge once and persist its canonical recipe", giving O(1) lookup instead
of recomputing per address) applied to this build's own state space.

There are only 8 possible (L,C,R) lattice-boundary states (SplatForge.
gluon_blob.lattice_neighbor_state's whole range). Every per-state
computation this build does — the QCD color axis, the lossless Jordan-
diagonal hologram windows, the fracture-cascade void/glue classification —
is therefore precomputed exactly once, here, at import time, and looked
up by compile_gluon_blobs instead of recomputed per splat. ReverseAtlasLibrary
persists its table to disk because its domain (a whole bit ribbon) doesn't
fit in memory; this domain is 8 states, so the "library" is just a dict —
same discipline, no disk needed at this scale.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

from .fracture_cascade import close_tear
from .gluon_blob import qcd_color_axis
from .gluon_hologram import jordan_diagonal_windows
from .weyl_address import full_spectrum_color, weyl_address

LCRState = Tuple[int, int, int]

ALL_STATES: Tuple[LCRState, ...] = tuple(
    (left, center, right) for left in (0, 1) for center in (0, 1) for right in (0, 1)
)


def _build_recipe(state: LCRState) -> Dict[str, Any]:
    axis = qcd_color_axis(state)
    windows = jordan_diagonal_windows(state, key=f"recipe:{state}")
    tear = close_tear(state)
    return {
        "state": state,
        "qcd_color_axis": axis,
        "base_hue": full_spectrum_color(state),
        "hologram_window_colors": [[gluon.color for gluon in window] for window in windows],
        "void_slot_count": len(tear["void_slots"]),
        "glue_slot_count": len(tear["glue_slots"]),
        "is_tear_prone": len(tear["glue_slots"]) > len(tear["void_slots"]),
        "weyl_address": weyl_address(state),
    }


# Compiled once, at import time — the whole 8-entry library.
STATE_RECIPE_TABLE: Dict[LCRState, Dict[str, Any]] = {s: _build_recipe(s) for s in ALL_STATES}


def lookup(state: LCRState) -> Dict[str, Any]:
    """O(1) lookup of the precomputed recipe for one of the 8 states."""
    try:
        return STATE_RECIPE_TABLE[state]
    except KeyError:
        raise ValueError(f"not a valid (L,C,R) chart state: {state!r}") from None


def verify() -> Dict[str, Any]:
    """The table covers exactly the 8 states, and every recipe's hologram
    windows decode back to that exact state — the lookup table is not
    just present, its lossless claim holds for every entry."""
    from PixelForge.rgb import pixel_gluon
    from .gluon_hologram import GluonBit, decode_jordan_diagonal_windows

    mismatches = []
    for state, recipe in STATE_RECIPE_TABLE.items():
        windows = [
            tuple(GluonBit(bit=pixel_gluon(*color) & 1, color=color) for color in window)
            for window in recipe["hologram_window_colors"]
        ]
        decoded = decode_jordan_diagonal_windows(windows)
        if decoded != state:
            mismatches.append({"state": state, "decoded": decoded})
    return {
        "states_in_table": len(STATE_RECIPE_TABLE),
        "expected_states": 8,
        "mismatches": mismatches,
        "status": "pass" if len(STATE_RECIPE_TABLE) == 8 and not mismatches else "fail",
    }
