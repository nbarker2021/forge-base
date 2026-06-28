"""
SplatForge.fold_anneal — "Damascus x10": repeated folding read structurally
through this corpus's own proven Hamming-centroid annealing, applied across
a real, compiled Crystal Zoo lattice instead of a single abstract state.

Composes, unmodified:
  lattice_forge.centroid_voa.anneal_to_lie_conjugate   the proven claim
                                        (verify_hamming_centroid_universality,
                                        status=pass, checked again below by
                                        this module's own verify()): applying
                                        the 3 S3 transpositions (swap_LR,
                                        swap_LC, swap_CR) in fixed order
                                        closes EVERY one of the 8 chart
                                        states to one of 4 Lie-conjugate
                                        attractors in <=3 steps, then stays
                                        there (the function stops once
                                        closed). This IS Damascus pattern-
                                        welding read structurally: repeated
                                        folding (= repeated transposition)
                                        drives a population toward a small,
                                        stable, homogeneous attractor set,
                                        with provably diminishing returns
                                        past closure.
  SplatForge.tiling.generate_tile_instances              the real, many-
                                        tile Crystal Zoo lattice the fold is
                                        applied across (not a single point).
  SplatForge.gluon_blob.lattice_neighbor_state           each tile's own
                                        starting (L,C,R) chart state.
  ChromaForge.morphon.morphon_delta / sector_split       the kappa-bounded
                                        Noether/Shannon/Landauer decay event
                                        (already used for gluon_color's
                                        intensity and color_e8's decay
                                        event), applied per fold step to
                                        that fold's tile-population content
                                        -- the entropy suite, not a new
                                        formula.

A real, checked finding, not assumed: LIE_CONJUGATES is closed under
swap_LR alone, but NOT under swap_LC or swap_CR individually (e.g.
swap_LC((1,0,1)) = (0,1,1), not a Lie conjugate) -- confirmed by direct
computation before writing this module. An unconditional periodic braid
(apply LR, then LC, then CR, repeating, to every tile regardless of
whether it is already closed) would therefore UN-close already-closed
tiles on later folds, breaking the "diminishing returns" claim. This
module avoids that by reusing anneal_to_lie_conjugate's own per-tile
trajectory directly: once a tile's trajectory reaches a Lie conjugate, it
stays there for every later fold, exactly mirroring the proven function's
own stopping rule rather than inventing a different one.

The waste-management read: fracture_cascade's void/glue split already
means "closed, no further processing" vs "still needs folding" -- the
waste metric here is the fraction of tiles not yet in LIE_CONJUGATES at a
given fold depth, falling to 0 at or before fold 3 by the proven bound.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ChromaForge.morphon import morphon_delta, sector_split
from lattice_forge.centroid_voa import (
    LIE_CONJUGATES,
    TRANSPOSITION_NAMES,
    anneal_to_lie_conjugate,
)

from .gluon_blob import lattice_neighbor_state
from .tiling import CRYSTAL_IDS, generate_tile_instances

LCRState = Tuple[int, int, int]

# The fixed order anneal_to_lie_conjugate itself uses (TRANSPOSITIONS is
# already exactly [swap_LR, swap_LC, swap_CR]) -- named here as the literal
# braid word (the weaving/interleaving of the 3 strands L, C, R), not a new
# ordering invented for this module.
BRAID_WORD = tuple(TRANSPOSITION_NAMES)


def _trajectory_for(state: LCRState) -> List[LCRState]:
    return anneal_to_lie_conjugate(state)["trajectory"]


def state_at_fold(trajectory: List[LCRState], fold_index: int) -> LCRState:
    """The tile's state at fold `fold_index` (1-indexed): once its own
    trajectory reaches a Lie conjugate it stays there for every later
    fold -- the proven function's own stopping rule, not a new one."""
    return trajectory[min(fold_index, len(trajectory) - 1)]


def run_damascus_folds(crystal_id: str, extent: Tuple[int, int, int] = (2, 2, 2),
                        folds: int = 10, seed_state: "LCRState | None" = None
                        ) -> Dict[str, Any]:
    """Seed every tile of a real, compiled Crystal Zoo lattice, then fold
    the whole population for `folds` rounds. Each tile's per-fold state
    comes from its own anneal_to_lie_conjugate trajectory (precomputed
    once, since the trajectory and the proven <=3-step closure are fixed
    facts about each starting state, independent of how many folds are
    run). By default every tile starts at its own real lattice boundary
    state (gluon_blob.lattice_neighbor_state) -- the same signal the rest
    of this session's SplatForge work uses. Pass `seed_state` to instead
    start every tile at one fixed state (e.g. a material's
    material_db.seed_state_for(oloid_closure)) -- used by the fold-anneal
    catalog to give a material's closure class an actual effect on the
    run, instead of being computed and then silently ignored."""
    tiles = generate_tile_instances(crystal_id, extent)
    if not tiles:
        raise ValueError(f"{crystal_id!r} at extent {extent!r} produced no tiles")
    if seed_state is not None:
        start_states = [seed_state for _ in tiles]
    else:
        start_states = [lattice_neighbor_state(tile, extent) for tile in tiles]
    trajectories = [_trajectory_for(state) for state in start_states]

    fold_records: List[Dict[str, Any]] = []
    closure_reached_at_fold = None
    for fold_index in range(1, folds + 1):
        current_states = [state_at_fold(traj, fold_index) for traj in trajectories]
        closed_count = sum(1 for s in current_states if s in LIE_CONJUGATES)
        waste_fraction = 1.0 - closed_count / len(current_states)
        content = f"{crystal_id}:fold{fold_index}:{sorted(current_states)}"
        delta = morphon_delta(content)
        record = {
            "fold": fold_index,
            "waste_fraction": round(waste_fraction, 6),
            "closed_count": closed_count,
            "tile_count": len(current_states),
            "entropy": {"delta_phi": delta, "sectors": sector_split(delta)},
        }
        fold_records.append(record)
        if closure_reached_at_fold is None and waste_fraction == 0.0:
            closure_reached_at_fold = fold_index

    return {
        "crystal_id": crystal_id,
        "extent": extent,
        "folds": folds,
        "braid_word": BRAID_WORD,
        "seed_state": seed_state,
        "tile_count": len(tiles),
        "closure_reached_at_fold": closure_reached_at_fold,
        "fold_records": fold_records,
    }


def verify() -> Dict[str, Any]:
    """The literal, falsifiable claims this module rests on, checked
    directly rather than asserted: every Crystal Zoo family reaches full
    closure (waste_fraction == 0) at or before fold 3 (the proven bound),
    and every fold past closure produces zero further change to the
    waste_fraction trace (the diminishing-returns claim)."""
    errors: List[str] = []
    per_family: Dict[str, Any] = {}

    for crystal_id in CRYSTAL_IDS:
        result = run_damascus_folds(crystal_id, extent=(2, 2, 2), folds=10)
        closure = result["closure_reached_at_fold"]
        per_family[crystal_id] = {
            "closure_reached_at_fold": closure,
            "tile_count": result["tile_count"],
        }
        if closure is None:
            errors.append(f"{crystal_id}: never reached full closure within 10 folds")
        elif closure > 3:
            errors.append(f"{crystal_id}: closure at fold {closure}, expected <=3")

        records = result["fold_records"]
        if closure is not None:
            after = [r for r in records if r["fold"] > closure]
            if any(r["waste_fraction"] != 0.0 for r in after):
                errors.append(f"{crystal_id}: waste_fraction changed after closure at fold {closure}")

    return {
        "forge": "SplatForge",
        "module": "fold_anneal",
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "families_checked": len(CRYSTAL_IDS),
        "per_family": per_family,
    }
