"""
SplatForge.circuit_breaker — the standard circuit-breaker pattern
(CLOSED/OPEN with hysteresis between a trip threshold and a strictly lower
reset threshold) applied to SplatForge.fracture_cascade.detect_tear's
shear measurement, and pre-provisioned across a whole compiled crystal
from the Crystal Zoo.

This is a real, standard software-engineering pattern — used to prevent
cascading failures in distributed systems — not new physics. A breaker
trips (CLOSED -> OPEN) when measured shear reaches `trip_threshold`, and
only resets (OPEN -> CLOSED) once shear relaxes below a strictly lower
`reset_threshold`. The gap between the two ("just below" the trip
threshold, per the operator's own phrasing) is the hysteresis band that
stops the breaker rapidly toggling on noise hovering at one single value
— the entire reason this pattern exists instead of a bare threshold check.

When a breaker trips OPEN, the repair is "preinstalled": this module
immediately attaches SplatForge.fracture_cascade.close_tear's void/glue
record for the boundary state, rather than waiting for the tear to be
separately detected and handled later.

crystal_breaker_map pre-provisions one breaker per adjacent same-site-label
tile pair across a whole compiled Crystal Zoo lattice (any of the 9
families SplatForge.tiling already generates) — "preposing all known
boundary adapters" for that crystal before any rendering happens. "ANY
known math" is bounded honestly: there are exactly 8 possible (L,C,R)
boundary states in this chart formalism (SplatForge.state_recipe_table's
whole domain), so "all known" here means all 8, not literally all
mathematics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .compiler import SPLAT_SCALE_FRACTION
from .fracture_cascade import close_tear, detect_tear
from .gluon_blob import lattice_neighbor_state, lucas_correction_radii
from .tiling import TileInstance, build_tile_family_asset, generate_tile_instances

LCRState = Tuple[int, int, int]
Radii = Tuple[float, float, float]


@dataclass
class CircuitBreaker:
    """One stateful breaker for one tile-boundary pair. CLOSED = stable;
    OPEN = shear detected, repair engaged. trip_threshold > reset_threshold
    strictly — that gap is the hysteresis band, not an implementation
    detail to be collapsed."""

    trip_threshold: float = 0.2
    reset_threshold: float = 0.15
    state: str = "CLOSED"
    trip_count: int = 0
    last_repair: Optional[Dict[str, Any]] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not (0.0 <= self.reset_threshold < self.trip_threshold):
            raise ValueError(
                "reset_threshold must be >= 0 and strictly less than trip_threshold "
                "(the hysteresis band would otherwise collapse to a single value)"
            )

    def toggle(self, radii_a: Radii, radii_b: Radii, tear_state: LCRState) -> Dict[str, Any]:
        """Measure the shear between two adjacent splats' radii and update
        the breaker's state with hysteresis. Returns the breaker's
        decision record for this single measurement."""
        is_tear = detect_tear(radii_a, radii_b, threshold=self.trip_threshold)
        is_relaxed = not detect_tear(radii_a, radii_b, threshold=self.reset_threshold)

        previous_state = self.state
        if self.state == "CLOSED" and is_tear:
            self.state = "OPEN"
            self.trip_count += 1
            self.last_repair = close_tear(tear_state)
        elif self.state == "OPEN" and is_relaxed:
            self.state = "CLOSED"
            self.last_repair = None
        # else: hold the current state -- this is the hysteresis band itself,
        # the entire point of the pattern

        return {
            "previous_state": previous_state,
            "state": self.state,
            "transitioned": previous_state != self.state,
            "trip_count": self.trip_count,
            "repair": self.last_repair,
        }


def _adjacent_x_pairs(tiles: List[TileInstance]) -> List[Tuple[TileInstance, TileInstance]]:
    """Genuine 1-to-1 geometric neighbor pairs at adjacent x cell-index
    positions, one per site-basis position per unit cell.

    tiling.py's site_label is a crystallographic symmetry label, not a
    unique per-site id: FCC's 4 face-centered sites are all labeled "A".
    Matching on (cell_index, site_label) alone — an earlier version of
    this function did — produces the full cross product of same-labeled
    sites across the whole lattice instead of true adjacency (confirmed:
    16 real neighbor pairs for CZ-FCC extent (2,2,2) became 256 false
    ones). generate_tile_instances always iterates a cell's site_basis
    list in the same fixed order, so zipping each cell's tile list against
    its (ix+1, iy, iz) neighbor's tile list — ordinal position to ordinal
    position — recovers the correct 1-to-1 pairing without needing a
    site-basis index tiling.py doesn't expose."""
    by_cell: Dict[Tuple[int, int, int], List[TileInstance]] = {}
    for tile in tiles:
        by_cell.setdefault(tile.cell_index, []).append(tile)

    pairs: List[Tuple[TileInstance, TileInstance]] = []
    for (ix, iy, iz), cell_tiles in by_cell.items():
        neighbor_tiles = by_cell.get((ix + 1, iy, iz))
        if neighbor_tiles is None:
            continue
        for tile_a, tile_b in zip(cell_tiles, neighbor_tiles):
            if tile_a.site_label == tile_b.site_label:
                pairs.append((tile_a, tile_b))
    return pairs


def crystal_breaker_map(crystal_id: str, extent: Tuple[int, int, int] = (2, 2, 2),
                         base_scale_fraction: float = SPLAT_SCALE_FRACTION,
                         trip_threshold: float = 0.2, reset_threshold: float = 0.15
                         ) -> Dict[str, Any]:
    """Pre-provision one CircuitBreaker per adjacent same-site tile pair
    across a whole compiled Crystal Zoo lattice, evaluate each once at
    compile time, and report which boundaries are already OPEN (repair
    pre-installed) before any rendering happens."""
    tiles = generate_tile_instances(crystal_id, extent)
    family = build_tile_family_asset(crystal_id)
    base_scale = family.nearest_neighbor_distance * base_scale_fraction

    breakers: Dict[str, Dict[str, Any]] = {}
    open_count = 0
    # Keyed by enumeration index, not tile_instance_id: tiling.py's
    # site_label is a crystallographic symmetry label shared by multiple
    # sites per cell (FCC's 4 face-centered sites are all "A"), so
    # tile_instance_id collides across genuinely distinct pairs from the
    # same cell -- an index avoids silently overwriting them in this dict
    # the way a string key built from colliding ids would.
    for i, (tile_a, tile_b) in enumerate(_adjacent_x_pairs(tiles)):
        radii_a = lucas_correction_radii(tile_a, extent, base_scale)
        radii_b = lucas_correction_radii(tile_b, extent, base_scale)
        state_a = lattice_neighbor_state(tile_a, extent)
        breaker = CircuitBreaker(trip_threshold=trip_threshold, reset_threshold=reset_threshold)
        decision = breaker.toggle(radii_a, radii_b, state_a)
        key = f"{i}:{tile_a.tile_instance_id}@{tile_a.position}|{tile_b.tile_instance_id}@{tile_b.position}"
        breakers[key] = {"breaker": breaker, "decision": decision}
        if breaker.state == "OPEN":
            open_count += 1

    return {
        "crystal_id": crystal_id,
        "extent": extent,
        "boundary_pair_count": len(breakers),
        "open_count": open_count,
        "closed_count": len(breakers) - open_count,
        "breakers": breakers,
    }


def verify_no_chatter(samples: int = 50) -> Dict[str, Any]:
    """The actual point of the hysteresis band, checked directly: a shear
    value oscillating just above and below the trip threshold (but never
    crossing the reset threshold) must NOT cause the breaker to toggle
    repeatedly -- it trips once and stays OPEN. A bare threshold check
    (no hysteresis) would chatter on every sample; this must not."""
    breaker = CircuitBreaker(trip_threshold=0.2, reset_threshold=0.15)
    transitions = 0
    states: List[str] = []
    # detect_tear's metric is relative: |a-b| / max(|a|,|b|), not a raw
    # offset -- so b must solve (b-1)/b = target, i.e. b = 1/(1-target),
    # to actually land the *relative* difference at the intended value.
    # b=1.2195 -> relative diff 0.18; b=1.2821 -> relative diff 0.22.
    # Both straddle the trip threshold (0.2) but neither drops anywhere
    # near the reset threshold (0.15, which needs b=1.1765).
    for i in range(samples):
        relative_target = 0.22 if i % 2 == 0 else 0.18
        b_value = 1.0 / (1.0 - relative_target)
        radii_a = (1.0, 1.0, 1.0)
        radii_b = (b_value, 1.0, 1.0)
        decision = breaker.toggle(radii_a, radii_b, (0, 1, 0))
        states.append(decision["state"])
        if decision["transitioned"]:
            transitions += 1

    return {
        "samples": samples,
        "states": states,
        "transition_count": transitions,
        "final_state": breaker.state,
        "trip_count": breaker.trip_count,
        "status": "pass" if transitions == 1 and breaker.state == "OPEN" else "fail",
    }
