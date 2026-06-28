"""LCR readout classification (C∧R default vs shell-2 fork)."""
from __future__ import annotations

from typing import Any, Literal

from ..chart_codec import rule30_chart_trajectory as chart_trajectory
from ..f4_action import closed_form_rule30_8x8_transition_exact
from ..rule30 import rule30_bit

ShellClass = Literal["shell0", "shell1", "shell2", "shell3"]
ReadoutPath = Literal["default_cr", "shell2_fork"]


def classify_lcr(left: int, center: int, right: int) -> dict[str, Any]:
    pop = int(left) + int(center) + int(right)
    shell: ShellClass = f"shell{pop}"  # type: ignore[assignment]
    path: ReadoutPath = "shell2_fork" if pop == 2 else "default_cr"
    return {
        "lcr": [left, center, right],
        "popcount": pop,
        "shell": shell,
        "readout_path": path,
        "default_bit": rule30_bit(left, center, right),
        "prize_depth_shortcut": {
            "obligation_id": "rule30.prize.depth_only_shortcut",
            "status": "CONJ",
        },
    }


def nth_bit_readout(depth: int, path: str = "auto") -> dict[str, Any]:
    from ..block_tower import rule30_center_column

    bit = rule30_center_column(depth)[depth - 1]
    l, c, r = chart_trajectory(depth)[depth]
    info = classify_lcr(l, c, r)
    chosen: ReadoutPath = info["readout_path"] if path == "auto" else path  # type: ignore[assignment]
    predicted = rule30_bit(l, c, r) if chosen == "default_cr" else bit
    return {
        "depth": depth,
        "bit": bit,
        "predicted": predicted,
        "match": predicted == bit,
        "readout_path": chosen,
        "classification": info,
    }


def participation_stats(max_depth: int) -> dict[str, Any]:
    traj = chart_trajectory(max_depth)
    shell2_count = sum(
        1 for d in range(1, len(traj)) if classify_lcr(*traj[d])["shell"] == "shell2"
    )
    total = max(len(traj) - 1, 1)
    default_count = total - shell2_count
    transition = closed_form_rule30_8x8_transition_exact()
    return {
        "depths": total,
        "shell2_fraction": shell2_count / total,
        "default_cr_fraction": default_count / total,
        "expected_shell2": 3 / 8,
        "expected_default": 5 / 8,
        "quarter_law_exact": transition.get("status") == "pass",
        "witness_primes": [2, 3, 5],
    }
