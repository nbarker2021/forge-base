"""NSL conservation port adapter."""
from __future__ import annotations

from typing import Any, Sequence

from ..ledger.nsl import NSLTerm
from .base import PortTool


class NSLTool(PortTool):
    port = "conservation"
    part_id = "nsl-conservation"

    @classmethod
    def available(cls) -> bool:
        return cls()._provider() is not None

    def invoke(
        self,
        *,
        v_before: Sequence[float] | None = None,
        v_after: Sequence[float] | None = None,
        term: NSLTerm | None = None,
        agent_id: str = "",
        service: str = "lattice-forge",
        operation: str = "",
        **_: Any,
    ) -> dict[str, Any]:
        prov = self._provider()
        if prov is None:
            if term is not None:
                return {
                    "available": False,
                    "provenance": self.provenance(),
                    "local_term": term.as_dict(),
                }
            return self.unavailable()

        if term is not None:
            v_before = (
                float(term.noether_residue),
                float(term.shannon_residue),
                float(term.landauer_cost),
            )
            v_after = (0.0, 0.0, 0.0)

        if v_before is None or v_after is None:
            return self.unavailable(reason="v_before_and_v_after_required")

        try:
            check = prov.check_and_record(
                v_before,
                v_after,
                agent_id=agent_id,
                service=service,
                operation=operation or "lattice_forge_nsl",
            )
            return {
                "available": True,
                "provenance": self.provenance(),
                "accepted": check.accepted,
                "delta_phi": check.delta_phi,
                "sectors": {
                    "dN": check.sectors.dN,
                    "dI": check.sectors.dI,
                    "dL": check.sectors.dL,
                },
            }
        except Exception as exc:
            return self.unavailable(reason=str(exc))
