"""CQE sidecar monitor for first-touch and predeploy token streams."""
from __future__ import annotations

from dataclasses import dataclass

from .hypervisor import CQEHypervisor, RibbonInput


@dataclass(frozen=True)
class SidecarResult:
    """A CQE monitor result for one token-stream phase."""

    phase: str
    decision: str
    interrupt: bool
    guidance: str
    propagation_lanes: tuple[str, ...]
    need: str


class CQESidecarMonitor:
    """First-touch and last-validation monitor over token ribbons."""

    def __init__(self, hypervisor: CQEHypervisor | None = None) -> None:
        self.hypervisor = hypervisor or CQEHypervisor()

    def first_touch(self, ribbon: RibbonInput) -> SidecarResult:
        return self._check("FIRST_TOUCH", ribbon)

    def predeploy(self, ribbon: RibbonInput) -> SidecarResult:
        return self._check("PREDEPLOY", ribbon)

    def _check(self, phase: str, ribbon: RibbonInput) -> SidecarResult:
        managed = self.hypervisor.manage(ribbon)
        receipt = managed.receipts[0]
        interrupt = receipt.decision not in {"COAST", "RETIE"}
        return SidecarResult(
            phase=phase,
            decision=receipt.decision,
            interrupt=interrupt,
            guidance=receipt.guidance,
            propagation_lanes=receipt.propagation_lanes,
            need=receipt.need if interrupt else "",
        )
