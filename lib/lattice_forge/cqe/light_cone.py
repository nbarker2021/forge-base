"""Light-cone sampler for launched CQE hypervisors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator

from .hypervisor import RibbonInput, _coerce_ribbon


@dataclass(frozen=True)
class LCRBoundary:
    """Alternating Fibonacci boundary values around the sampled ribbon."""

    left: tuple[int, ...]
    center: int
    right: tuple[int, ...]


@dataclass(frozen=True)
class LightConeFrame:
    """One resolved read frame from the CQE hypervisor light cone."""

    full: str
    circular_table: tuple[dict[str, int], ...]
    monad: tuple[int, ...]
    rotated_monad: tuple[int, ...]
    dyad: tuple[tuple[int, int], ...]
    triad: tuple[tuple[int, int, int], ...]
    quadratic: tuple[tuple[int, int, int, int], ...]
    centroid: int
    an_spine: tuple[tuple[int, int], ...]
    jordan_lanes: tuple[dict[str, int | str], ...]
    left: str
    right: str
    split_bias: int
    hamiltonians: tuple[dict[str, int | str], ...]
    lcr_boundary: LCRBoundary
    control_plane: tuple[dict[str, int], ...]
    tick: int


@dataclass(frozen=True)
class HypervisorLaunchHandle:
    """State returned by a launched CQE sampler."""

    frames: tuple[LightConeFrame, ...]
    running: bool


class CQELightConeHypervisor:
    """Continuously sample host ribbons into CQE resolution frames."""

    def __init__(self, split_bias: int = 1) -> None:
        if split_bias not in {1, 2, 4, 8}:
            raise ValueError("split_bias must be one of 1, 2, 4, or 8")
        self.split_bias = split_bias

    def sample(self, ribbon: RibbonInput, tick: int = 0) -> LightConeFrame:
        full = _ribbon_bits(ribbon)
        circular = _circular_table(full)
        monad = tuple(1 if digit == "1" else -1 for digit in full)
        rotated = tuple(reversed(monad))
        dyad = tuple(_window(monad, index, 2) for index in range(len(monad)))
        triad = tuple(_window(monad, index, 3) for index in range(len(monad)))
        quadratic = tuple(_window(monad, index, 4) for index in range(len(monad)))
        centroid = len(full) // 2
        spine = tuple((local, rotated[index]) for index, local in enumerate(monad))
        lanes = tuple(_jordan_lane(index, pair) for index, pair in enumerate(spine))
        left, right = _split(full, self.split_bias)
        hamiltonians = tuple(_hamiltonian(index, full) for index in range(16))
        boundary = _lcr_boundary(len(full), centroid)
        control = tuple(_control_entry(index, centroid) for index in range(16))
        return LightConeFrame(
            full=full,
            circular_table=circular,
            monad=monad,
            rotated_monad=rotated,
            dyad=dyad,
            triad=triad,
            quadratic=quadratic,
            centroid=centroid,
            an_spine=spine,
            jordan_lanes=lanes,
            left=left,
            right=right,
            split_bias=self.split_bias,
            hamiltonians=hamiltonians,
            lcr_boundary=boundary,
            control_plane=control,
            tick=tick,
        )

    def launch(
        self,
        source: Iterable[RibbonInput],
        max_samples: int | None = None,
    ) -> HypervisorLaunchHandle:
        frames: list[LightConeFrame] = []
        for tick, ribbon in enumerate(_limited(source, max_samples)):
            frames.append(self.sample(ribbon, tick=tick))
        return HypervisorLaunchHandle(frames=tuple(frames), running=False)


def launch_hypervisor(
    source: Iterable[RibbonInput],
    max_samples: int | None = None,
    split_bias: int = 1,
) -> HypervisorLaunchHandle:
    """Launch a CQE light-cone sampler over a ribbon source."""

    return CQELightConeHypervisor(split_bias=split_bias).launch(source, max_samples=max_samples)


def _ribbon_bits(ribbon: RibbonInput) -> str:
    if isinstance(ribbon, str) and set(ribbon) <= {"0", "1"}:
        return ribbon
    data = _coerce_ribbon(ribbon)
    return "".join(f"{byte:08b}" for byte in data)


def _circular_table(full: str) -> tuple[dict[str, int], ...]:
    size = len(full)
    return tuple(
        {
            "index": index,
            "digit": int(digit),
            "prev": (index - 1) % size,
            "next": (index + 1) % size,
        }
        for index, digit in enumerate(full)
    )


def _window(values: tuple[int, ...], start: int, width: int) -> tuple[int, ...]:
    size = len(values)
    return tuple(values[(start + offset) % size] for offset in range(width))


def _jordan_lane(index: int, pair: tuple[int, int]) -> dict[str, int | str]:
    local, rotated = pair
    return {
        "index": index,
        "class": "idempotent" if local == rotated else "transfer",
        "d4_axis": index % 4,
        "charge": local + rotated,
    }


def _split(full: str, split_bias: int) -> tuple[str, str]:
    midpoint = len(full) // 2
    if len(full) % 2 == 0:
        return full[:midpoint], full[midpoint:]
    left_len = min(len(full), midpoint + (1 if split_bias in {1, 4} else 0))
    return full[:left_len], full[left_len:]


def _hamiltonian(index: int, full: str) -> dict[str, int | str]:
    rotated = full[index % len(full) :] + full[: index % len(full)]
    mirror = rotated[::-1]
    flip = "".join("1" if digit == "0" else "0" for digit in rotated)
    return {"index": index, "window": rotated, "mirror": mirror, "flip": flip}


def _lcr_boundary(size: int, centroid: int) -> LCRBoundary:
    fib = _signed_fibonacci(size)
    return LCRBoundary(left=fib, center=centroid, right=tuple(-value for value in reversed(fib)))


def _signed_fibonacci(size: int) -> tuple[int, ...]:
    values: list[int] = []
    a, b = 1, 1
    for index in range(size):
        sign = 1 if index % 2 == 0 else -1
        values.append(sign * a)
        a, b = b, a + b
    return tuple(values)


def _control_entry(index: int, centroid: int) -> dict[str, int]:
    conjugate = (index + 8) % 16
    return {"index": index, "conjugate_index": conjugate, "new_c": (index + conjugate) // 2}


def _limited(source: Iterable[RibbonInput], max_samples: int | None) -> Iterator[RibbonInput]:
    for count, item in enumerate(source):
        if max_samples is not None and count >= max_samples:
            break
        yield item
