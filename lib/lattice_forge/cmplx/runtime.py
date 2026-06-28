"""CMPLX budgeted execution surface.

CMPLX spends only work that CQE has made available: harvested savings, cached
closure, or explicit host budget. Anything else is rejected before execution.
"""
from __future__ import annotations

from dataclasses import dataclass

from lattice_forge.cqe import ManagedRibbon, manage_ribbon


@dataclass(frozen=True)
class RuntimeBudget:
    """Budget available to CMPLX for managed work."""

    cqe_savings: int = 0
    cached_closure: int = 0
    host_budget: int = 0

    @property
    def total(self) -> int:
        return self.cqe_savings + self.cached_closure + self.host_budget

    def spend(self, cost: int) -> tuple[str, "RuntimeBudget"]:
        if cost < 0:
            raise ValueError("cost must be non-negative")
        if cost == 0:
            return "ZERO_COST", self
        if self.cqe_savings >= cost:
            return (
                "CQE_SAVINGS",
                RuntimeBudget(self.cqe_savings - cost, self.cached_closure, self.host_budget),
            )
        if self.cached_closure >= cost:
            return (
                "CACHED_CLOSURE",
                RuntimeBudget(self.cqe_savings, self.cached_closure - cost, self.host_budget),
            )
        if self.host_budget >= cost:
            return (
                "HOST_BUDGET",
                RuntimeBudget(self.cqe_savings, self.cached_closure, self.host_budget - cost),
            )
        raise ValueError("CMPLX cannot spend unearned work")


@dataclass(frozen=True)
class RuntimeReceipt:
    """Receipt for one CMPLX accepted operation."""

    operation: str
    cost: int
    status: str
    funding_source: str
    remaining: RuntimeBudget
    managed: ManagedRibbon | None = None


class CMPLXRuntime:
    """Programmable runtime on top of CQE-earned compute savings."""

    def execute(self, operation: str, cost: int, budget: RuntimeBudget) -> RuntimeReceipt:
        source, remaining = budget.spend(cost)
        return RuntimeReceipt(
            operation=operation,
            cost=cost,
            status="EXECUTED",
            funding_source=source,
            remaining=remaining,
        )

    def execute_from_ribbon(self, ribbon: object, cost: int, operation: str) -> RuntimeReceipt:
        managed = manage_ribbon(ribbon)  # type: ignore[arg-type]
        source, remaining = RuntimeBudget(cqe_savings=managed.savings).spend(cost)
        return RuntimeReceipt(
            operation=operation,
            cost=cost,
            status="EXECUTED",
            funding_source=source,
            remaining=remaining,
            managed=managed,
        )
