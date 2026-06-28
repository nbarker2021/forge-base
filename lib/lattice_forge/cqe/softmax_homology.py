"""Softmax homology helpers for CQE lane rehydration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SoftmaxHomologyFrame:
    """Triadic placement recovered from an 8D softmax-like mass."""

    positive_lane: int
    centroid_lane: int
    negative_lane: int
    dr_class: int
    lift_power: int
    gaussian_mass: tuple[float, ...]
    rehydrated_antipode: int
    rotation_degrees: int
    rotation_path: tuple[str, ...]

    def closes_write(self, write_value: int) -> bool:
        """A write closes only when it lands on the rehydrated antipode."""

        return write_value == self.rehydrated_antipode


def rehydrate_negative_lane(
    gaussian_mass: Iterable[float],
    current_c: int,
    k: int = 1,
) -> SoftmaxHomologyFrame:
    """Recover the missing negative lane from an 8D softmax pressure field."""

    mass = tuple(float(value) for value in gaussian_mass)
    if len(mass) != 8:
        raise ValueError("gaussian_mass must contain exactly 8 lanes")
    positive = max(range(8), key=lambda index: mass[index])
    centroid = current_c % 8
    negative = _opposite_lane(positive, centroid)
    dr = _dr_class(positive)
    lift_power = k if dr == 9 else 0
    rotation_degrees, path = _rotation_from_centroid(centroid, positive, dr)
    return SoftmaxHomologyFrame(
        positive_lane=positive,
        centroid_lane=centroid,
        negative_lane=negative,
        dr_class=dr,
        lift_power=lift_power,
        gaussian_mass=mass,
        rehydrated_antipode=-positive,
        rotation_degrees=rotation_degrees,
        rotation_path=path,
    )


def _opposite_lane(positive: int, centroid: int) -> int:
    return (2 * centroid - positive) % 8


def _dr_class(lane: int) -> int:
    return 9 if lane == 7 else lane + 1


def _rotation_from_centroid(
    centroid: int,
    positive: int,
    dr_class: int,
) -> tuple[int, tuple[str, ...]]:
    if dr_class == 9:
        return 180, ("C", "R", "C", "R", "C")
    delta = (positive - centroid) % 8
    if delta == 0:
        return 0, ("C",)
    if delta <= 2:
        return 90, ("C", "R", "C")
    if delta >= 6:
        return 90, ("C", "L", "C")
    return 180, ("C", "R", "C", "R", "C")
