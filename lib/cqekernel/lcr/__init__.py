"""
LCR windows: the channel-level resolution surface.

The LCR window machine is the kernel's primary surface. Every
observation produces at most ceil(N/4) 2x2 windows, ceil(N/16)
4x4 windows, and (at most) one 8x8 window — the same fixed
small channel budget regardless of input size.
"""

from ..carrier.lcr import LocalGluon, admit
from .windows import (
    WindowSize,
    WINDOW_BITS,
    LCRWindow,
    LCRChannel,
    LCRGluon,
    envelope_into_windows,
    gluon_stream_from_bits,
    resolve_channel,
)
from .typed_kernel import (
    Lane,
    LaneGrant,
    LAdapter,
    CKernel,
    RChannel,
    TypedKernel,
    lane_of_lcr,
    lane_role_string,
)
from .oloid import (
    OloidChart,
    OloidMode,
    OloidState,
    OLOID_CHART_LANES,
    build_oloid_chart,
)
from .combined_cem import (
    CombinedCEM,
    CombinedCEMReceipt,
    CombinedCEMSpec,
    DEFAULT_FORGE_LANES,
    ForgeContribution,
    LAYER_FORGES,
    PRODUCT_TIER_TO_LAYER,
    load_spec_from_layer,
    load_spec_from_products,
    load_spec_from_registry,
)

__all__ = [
    "WindowSize",
    "WINDOW_BITS",
    "LCRWindow",
    "LCRChannel",
    "LCRGluon",
    "LocalGluon",
    "admit",
    "envelope_into_windows",
    "gluon_stream_from_bits",
    "resolve_channel",
    # L/C/R typed-kernel surface (2026-06-24)
    "Lane",
    "LaneGrant",
    "LAdapter",
    "CKernel",
    "RChannel",
    "TypedKernel",
    "lane_of_lcr",
    "lane_role_string",
    # Oloid chart (2026-06-24)
    "OloidChart",
    "OloidMode",
    "OloidState",
    "OLOID_CHART_LANES",
    "build_oloid_chart",
    # CombinedCEM: typed kernel composed of multiple forges (2026-06-24)
    "CombinedCEM",
    "CombinedCEMReceipt",
    "CombinedCEMSpec",
    "DEFAULT_FORGE_LANES",
    "ForgeContribution",
    "LAYER_FORGES",
    "PRODUCT_TIER_TO_LAYER",
    "load_spec_from_layer",
    "load_spec_from_products",
    "load_spec_from_registry",
]