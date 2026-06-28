"""CQE hypervisor primitives for managed ribbon processing."""

from .frame import (
    CQECurrentFrame,
    DiagonalBundleResult,
    HistoricalSheet,
    SheetSelection,
    TermBundleResult,
)
from .extraction import FormalizationTarget, extract_targets, read_target_text, slugify
from .hypervisor import (
    CQEHypervisor,
    D4Token,
    ManagedRibbon,
    ReceiptPortal,
    RibbonReceipt,
    manage_ribbon,
)
from .light_cone import (
    CQELightConeHypervisor,
    HypervisorLaunchHandle,
    LCRBoundary,
    LightConeFrame,
    launch_hypervisor,
)
from .paper_match import PaperBundleMatch, PaperDatum, PaperSheet, match_paper_bundle, paper_sheet_from_text
from .sidecar import CQESidecarMonitor, SidecarResult
from .softmax_homology import SoftmaxHomologyFrame, rehydrate_negative_lane

__all__ = [
    "CQEHypervisor",
    "CQELightConeHypervisor",
    "CQESidecarMonitor",
    "CQECurrentFrame",
    "D4Token",
    "DiagonalBundleResult",
    "FormalizationTarget",
    "HypervisorLaunchHandle",
    "HistoricalSheet",
    "LCRBoundary",
    "LightConeFrame",
    "ManagedRibbon",
    "PaperBundleMatch",
    "PaperDatum",
    "PaperSheet",
    "ReceiptPortal",
    "RibbonReceipt",
    "SidecarResult",
    "SheetSelection",
    "SoftmaxHomologyFrame",
    "TermBundleResult",
    "launch_hypervisor",
    "manage_ribbon",
    "match_paper_bundle",
    "paper_sheet_from_text",
    "rehydrate_negative_lane",
    "extract_targets",
    "read_target_text",
    "slugify",
]
