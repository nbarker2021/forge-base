"""Public solver API."""
from __future__ import annotations

from .actions import normalize_at_c
from .cache import (
    ContinuationInstruction,
    ContinuationLedger,
    InMemorySheetCache,
    RootPlacementTemplateStore,
)
from .normal_form import EvidenceClass, SolverReceipt, decompose_address


class CmplxR30Solver:
    """Observer-relative Rule 30 stopped-state solver."""

    def __init__(
        self,
        cache: InMemorySheetCache,
        template_store: RootPlacementTemplateStore | None = None,
        continuation_ledger: ContinuationLedger | None = None,
    ):
        self.cache = cache
        self.template_store = template_store or RootPlacementTemplateStore()
        self.continuation_ledger = continuation_ledger or ContinuationLedger()

    def solve(self, n: int) -> SolverReceipt:
        """Return an exact receipt or an explicit unresolved escrow record."""
        sheet, offset = decompose_address(n, self.cache.sheet_width)
        root = self.cache.triad(offset)
        root_normalized = normalize_at_c(root)
        template = self.template_store.record(
            sheet_width=self.cache.sheet_width,
            offset=offset,
            root=root,
            actions=root_normalized.actions,
        )
        if not self.cache.contains(n):
            receipt = SolverReceipt(
                n=n,
                antipode_n=-n,
                sheet=sheet,
                offset=offset,
                bit=None,
                evidence=EvidenceClass.REGISTERED_ROUTE,
                actions=root_normalized.actions,
                local_closure=root_normalized.closed,
                continuation_verified=False,
                message="root placement route registered; continuation is not verified",
                root_template=template.key,
            )
            self._record(receipt)
            return receipt

        triad = self.cache.triad(n)
        normalized = normalize_at_c(triad)
        receipt = SolverReceipt(
            n=n,
            antipode_n=-n,
            sheet=sheet,
            offset=offset,
            bit=triad.center,
            evidence=EvidenceClass.MATERIALIZED_EXACT,
            actions=normalized.actions,
            local_closure=normalized.closed,
            continuation_verified=True,
            message="exact read from hydrated materialized sheet",
            root_template=template.key,
        )
        self._record(receipt)
        return receipt

    def _record(self, receipt: SolverReceipt) -> None:
        self.continuation_ledger.record(
            ContinuationInstruction(
                n=receipt.n,
                sheet=receipt.sheet,
                offset=receipt.offset,
                root_template=receipt.root_template or "",
                bit=receipt.bit,
                evidence=receipt.evidence,
                continuation_verified=receipt.continuation_verified,
            )
        )
