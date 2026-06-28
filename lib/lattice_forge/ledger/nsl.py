from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NSLTerm:
    """Noether-Shannon-Landauer boundary term container.

    This is intentionally unit-agnostic. The caller must normalize the three
    terms into compatible units or supply weights that do so.
    """

    noether_residue: float
    shannon_residue: float
    landauer_cost: float
    absorption_capacity: float = 0.0
    alpha: float = 1.0
    beta: float = 1.0
    gamma: float = 1.0

    @property
    def theta(self) -> float:
        return self.alpha * self.noether_residue + self.beta * self.shannon_residue + self.gamma * self.landauer_cost - self.absorption_capacity

    @property
    def closes_internally(self) -> bool:
        return self.theta <= 0.0

    def as_dict(self) -> dict[str, float | bool]:
        return {
            "noether_residue": self.noether_residue,
            "shannon_residue": self.shannon_residue,
            "landauer_cost": self.landauer_cost,
            "absorption_capacity": self.absorption_capacity,
            "alpha": self.alpha,
            "beta": self.beta,
            "gamma": self.gamma,
            "theta": self.theta,
            "closes_internally": self.closes_internally,
        }
