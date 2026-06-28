"""Literal LCR actions and observer-relative local closure."""
from __future__ import annotations

from dataclasses import dataclass

from .normal_form import LocalTriad


@dataclass(frozen=True)
class NormalizationResult:
    """Outcome of bounded local normalization."""

    triad: LocalTriad
    actions: tuple[str, ...]
    closed: bool


def swap_lr(triad: LocalTriad) -> LocalTriad:
    """Read one LCR triad from its LR-podal direction."""
    return LocalTriad(triad.right, triad.center, triad.left)


def place_lcr(triad: LocalTriad) -> LocalTriad:
    """Apply one cyclic L -> C -> R placement."""
    return LocalTriad(triad.center, triad.right, triad.left)


def lcr_cycle(triad: LocalTriad) -> LocalTriad:
    """Apply the complete three-placement LCR cycle."""
    current = triad
    for _ in range(3):
        current = place_lcr(current)
    return current


def emit(triad: LocalTriad) -> int:
    """Emit the Rule 30 local bit from one LCR triad."""
    if triad.center == 1:
        return 1 - triad.left
    return triad.left ^ triad.right


def idempotent_at_c(triad: LocalTriad) -> bool:
    """Check the approved local closure predicate at centroid C."""
    return (
        triad.center == swap_lr(triad).center
        and emit(triad) == emit(lcr_cycle(triad))
    )


def normalize_at_c(triad: LocalTriad, max_steps: int = 4) -> NormalizationResult:
    """Close the local triad using the cheapest admissible action first."""
    if max_steps < 0:
        raise ValueError("max_steps must be >= 0")
    if idempotent_at_c(triad):
        return NormalizationResult(triad=triad, actions=(), closed=True)
    current = triad
    actions: list[str] = []
    for _ in range(max_steps):
        current = swap_lr(current)
        actions.append("swap_lr")
        if idempotent_at_c(current):
            return NormalizationResult(
                triad=current,
                actions=tuple(actions),
                closed=True,
            )
    return NormalizationResult(triad=current, actions=tuple(actions), closed=False)
