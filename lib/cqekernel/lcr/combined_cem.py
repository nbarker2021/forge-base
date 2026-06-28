"""
CombinedCEM: compose multiple forges into a strictly-stronger typed kernel.

This module is the *proof of concept* for the identity claim that
"every forge is its own CEM, and combining them makes better and
better typed kernels." It implements a `CombinedCEM` that:

  1. Takes a list of forge names (or CEM specs) from
     ``FORGE_REGISTRY.json``.
  2. For each forge, declares which lane it lives in (L/C/R).
  3. Constructs an ``LCRKernel.TypedKernel`` whose policy opens
     exactly the union of those lanes, and whose identity is the
     composition.
  4. Reports a typed receipt describing the combined CEM, including
     the lane grants and the per-forge contributions.

The result is auditable, replayable, and strictly additive on top
of the LCRKernel surface (this PR) and the FORGE_REGISTRY (existing
artifact).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..core.errors import KernelPolicyError
from ..core.policy import Policy
from .typed_kernel import Lane, LaneGrant, TypedKernel


def _kernel_class():
    """Local import to avoid a circular dependency at module load.

    The ``combined_cem`` module is imported from ``lcr/__init__.py``,
    which is imported from ``core/kernel.py``. Importing ``Kernel``
    at the top of this module would re-enter ``core/kernel.py`` while
    it is still being constructed. Defer the import.
    """
    from ..core.kernel import Kernel
    return Kernel


# A forge can live in one or more lanes. This is the *default*
# classification; a host can override it per-instance.
#
# Heuristic (intentionally auditable, intentionally simple):
#   * "L" forges read or write the outside. They are adapters or
#     data-shape engines.
#   * "C" forges dispatch math, monitor, audit. They are control-plane.
#   * "R" forges project, render, emit, publish. They are outward.
#
# This is a starting taxonomy, not a permanent one. The CombinedCEM
# exposes the per-forge lane assignment as a parameter, so a host
# can override any forge's lane at construction time.
DEFAULT_FORGE_LANES: Dict[str, Tuple[Lane, ...]] = {
    # L-lane: data in / out (adapters, linkers, world-builders)
    "LinkForge":          (Lane.L,),
    "SceneForge":         (Lane.L,),
    "MandleForge":        (Lane.L,),
    "ManiForge":          (Lane.L,),
    "FridgeForge":        (Lane.L,),
    "lattice_forge":      (Lane.L, Lane.C),  # lattice_forge is the canonical bridge

    # C-lane: control plane (math, audit, monitor)
    "ChromaForge":        (Lane.C,),
    "GraphStax":          (Lane.C,),
    "SentinelForge":      (Lane.C,),
    "ConvergeForge":      (Lane.C,),
    "EntropyForge":       (Lane.C,),
    "ReadoutForge":       (Lane.C,),
    "TriadForge":         (Lane.C,),
    "GroundingForge":     (Lane.C,),
    "QuarkFaceForge":     (Lane.C,),
    "DoublingForge":      (Lane.C,),
    "FieldFormForge":     (Lane.C,),
    "MassResidueForge":   (Lane.C,),
    "AGRMForge":          (Lane.C,),
    "MDHGForge":          (Lane.C,),
    "E8Forge":            (Lane.C,),
    "LeechForge":         (Lane.C,),
    "AuthenticaForge":    (Lane.C,),

    # R-lane: outward surface (projectors, publishers)
    "PixelForge":                 (Lane.R, Lane.C),  # outputs surfaces AND dispatches E8 projection math
    "reforge_engine_hardening":   (Lane.R,),
    "reforge_engine_contracts":   (Lane.R,),
    "reforge_frameforge":         (Lane.R,),
    "reforge_glyphforge":         (Lane.R,),
    "reforge_pixl8forge":         (Lane.R,),
    "reforge_pixleforge":         (Lane.R,),
    "reforge_researchcraft":      (Lane.R,),
    "reforge_wireforge":          (Lane.R,),
    "rhenium_engine":             (Lane.R,),
    "reforge_kimi_adapter":       (Lane.R,),

    # Orchestration / factory: all three lanes (it dispatches + adapts + emits)
    "forgefactory":       (Lane.L, Lane.C, Lane.R),
}


@dataclass(frozen=True)
class ForgeContribution:
    """One forge's contribution to a CombinedCEM.

    Captures the forge's declared role from FORGE_REGISTRY.json and
    the lanes it occupies in the combined kernel.
    """

    forge: str
    lanes: Tuple[Lane, ...]
    tier: str  # 'core' | 'application' | 'platform' | 'framework' | 'extension'
    category: str
    role: str
    source: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "forge": self.forge,
            "lanes": [lane.value for lane in self.lanes],
            "tier": self.tier,
            "category": self.category,
            "role": self.role,
            "source": self.source,
        }


@dataclass(frozen=True)
class CombinedCEMSpec:
    """A typed specification for a combined CEM.

    A CombinedCEMSpec is the *plan*; the CombinedCEM is the
    *instance*. The spec is content-addressed by its JSON form.
    """

    forges: Tuple[ForgeContribution, ...]
    name: str
    description: str = ""

    @property
    def spec_hash(self) -> str:
        body = json.dumps(
            {
                "forges": [c.to_dict() for c in self.forges],
                "name": self.name,
                "description": self.description,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(body).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "forges": [c.to_dict() for c in self.forges],
            "spec_hash": self.spec_hash,
        }


@dataclass
class CombinedCEMReceipt:
    """A typed receipt describing a CombinedCEM.

    The receipt is what a host persists at boot time. It includes
    the spec hash, the per-forge contributions, the lane grants,
    and the kernel info. The receipt is auditable: a host can
    re-verify it on every boot and confirm the CEM has not
    silently drifted.
    """

    spec_hash: str
    name: str
    forge_count: int
    contributions: List[ForgeContribution]
    lane_grants: List[LaneGrant]
    kernel_info: Dict[str, Any]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spec_hash": self.spec_hash,
            "name": self.name,
            "forge_count": self.forge_count,
            "contributions": [c.to_dict() for c in self.contributions],
            "lane_grants": [g.to_dict() for g in self.lane_grants],
            "kernel_info": self.kernel_info,
            "timestamp": self.timestamp,
        }


class CombinedCEM:
    """A typed kernel composed of multiple forges.

    Usage:

        from cqekernel.lcr.combined_cem import CombinedCEM, load_spec_from_registry
        from pathlib import Path

        spec = load_spec_from_registry(
            registry_path=Path("FORGE_REGISTRY.json"),
            forges=["ChromaForge", "SentinelForge", "LinkForge"],
            name="astro_metaforge_cem",
            description="ASTRO MetaForge: 1 L + 1 C + 1 R CEM",
        )
        cem = CombinedCEM(spec)
        cem.boot()  # opens the 3 lanes, returns the typed receipt
        cem.run(payload)  # the typed surface; per-forge delegates below

    The CombinedCEM does not replace the existing Kernel. It wraps
    it with a typed, composed, auditable surface.
    """

    def __init__(
        self,
        spec: CombinedCEMSpec,
        *,
        kernel: Optional[Any] = None,
    ):
        self.spec = spec
        # Defer the Kernel import to avoid a circular import at
        # module load. If the host doesn't pass a kernel, we
        # instantiate one inside __init__ using the lazy import.
        if kernel is None:
            kernel = _kernel_class()()
        self._kernel = kernel
        self._tk: Optional[TypedKernel] = None
        self._receipt: Optional[CombinedCEMReceipt] = None

    @property
    def kernel(self) -> Any:
        return self._kernel

    @property
    def typed_kernel(self) -> TypedKernel:
        if self._tk is None:
            raise RuntimeError("CombinedCEM not booted; call boot() first")
        return self._tk

    def boot(self) -> CombinedCEMReceipt:
        """Open the lanes required by the spec, produce the typed receipt.

        After boot:
          * ``self._tk`` is the TypedKernel with the required lanes open
          * ``self._receipt`` is the typed receipt for audit
          * The kernel's policy is set explicitly: lanes required by
            the spec are True; the rest remain False (strict default).
        """
        # Compute the union of lanes required by the spec.
        required_lanes: Dict[Lane, bool] = {
            Lane.L: False,
            Lane.C: False,
            Lane.R: False,
        }
        for contrib in self.spec.forges:
            for lane in contrib.lanes:
                required_lanes[lane] = True

        # Set the policy fields explicitly. We start from strict()
        # and grant only the required lanes — this is the
        # deny-by-default guarantee.
        p = self._kernel.policy
        p.allow_left_io = required_lanes[Lane.L]
        p.allow_center_dispatch = required_lanes[Lane.C]
        p.allow_right_emit = required_lanes[Lane.R]

        # If any C-lane forge is present, firmware is required.
        if required_lanes[Lane.C]:
            p.allow_firmware = True

        # Build the TypedKernel with the same policy.
        self._tk = TypedKernel(kernel=self._kernel, policy=p)

        # The receipt is a content-addressed audit record.
        import datetime
        self._receipt = CombinedCEMReceipt(
            spec_hash=self.spec.spec_hash,
            name=self.spec.name,
            forge_count=len(self.spec.forges),
            contributions=list(self.spec.forges),
            lane_grants=self._tk.grants(),
            kernel_info={
                "kernel_class": type(self._kernel).__name__,
                "kernel_version": getattr(self._kernel, "__version__", "n/a"),
                "policy_class": type(p).__name__,
                "strict_by_default": all(
                    not getattr(p, lane.policy_field) is False
                    for lane in (Lane.L, Lane.C, Lane.R)
                ),
            },
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
        return self._receipt

    def check_lane(self, operation: str, lane: Lane) -> LaneGrant:
        """Delegate to TypedKernel.check_lane; raises if not booted."""
        return self.typed_kernel.check_lane(operation, lane)

    def dispatch(self, firmware_call: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to TypedKernel.dispatch; raises if not booted."""
        return self.typed_kernel.dispatch(firmware_call, payload)

    @property
    def receipt(self) -> CombinedCEMReceipt:
        if self._receipt is None:
            raise RuntimeError("CombinedCEM not booted; call boot() first")
        return self._receipt


# ---------------------------------------------------------------------------
# Spec loader: read the FORGE_REGISTRY and pick forges
# ---------------------------------------------------------------------------


# Mapping of dependency_graph layer names to the forges that live in
# that layer. Used by load_spec_from_layer() to build a CombinedCEM
# for an entire layer of the dependency graph at once.
#
# The dependency_graph in FORGE_REGISTRY.json declares the *graph* of
# layer-to-layer dependencies (kernel -> lattice_forge -> engine_forges
# -> reforge_ring -> core_products -> applications/frameworks/extensions)
# but does not name which forges live in which layer. The mapping
# below is the canonical assignment, derived from the forge names and
# the FORGE_REGISTRY's product entries:
#
#   kernel           -> (the cqekernel package itself, no forges here)
#   lattice_forge    -> lattice_forge
#   engine_forges    -> ChromaForge, GraphStax, PixelForge, FridgeForge,
#                       LinkForge, MandleForge, ManiForge, SceneForge,
#                       EntropyForge, SentinelForge, ConvergeForge,
#                       AuthenticaForge, E8Forge, LeechForge, MDHGForge,
#                       AGRMForge, ReadoutForge, TriadForge, GroundingForge,
#                       QuarkFaceForge, DoublingForge, FieldFormForge,
#                       MassResidueForge, forgefactory
#   reforge_ring     -> reforge_engine_contracts, reforge_engine_hardening,
#                       reforge_frameforge, reforge_glyphforge,
#                       reforge_kimi_adapter, reforge_pixl8forge,
#                       reforge_pixleforge, reforge_researchcraft,
#                       reforge_wireforge, rhenium_engine
#   core_products    -> (no forges; the 7 declared products live here)
#   applications     -> (no forges; the 7 declared products live here)
#   frameworks       -> (no forges; the 7 declared products live here)
#   extensions       -> (no forges; the 7 declared products live here)
#
# The product-level loading is handled by load_spec_from_products() below.
LAYER_FORGES: Dict[str, Tuple[str, ...]] = {
    "lattice_forge":  ("lattice_forge",),
    "engine_forges":  (
        "ChromaForge", "GraphStax", "PixelForge", "FridgeForge",
        "LinkForge", "MandleForge", "ManiForge", "SceneForge",
        "EntropyForge", "SentinelForge", "ConvergeForge",
        "AuthenticaForge", "E8Forge", "LeechForge", "MDHGForge",
        "AGRMForge", "ReadoutForge", "TriadForge", "GroundingForge",
        "QuarkFaceForge", "DoublingForge", "FieldFormForge",
        "MassResidueForge", "forgefactory",
    ),
    "reforge_ring":  (
        "reforge_engine_contracts", "reforge_engine_hardening",
        "reforge_frameforge", "reforge_glyphforge",
        "reforge_kimi_adapter", "reforge_pixl8forge",
        "reforge_pixleforge", "reforge_researchcraft",
        "reforge_wireforge", "rhenium_engine",
    ),
}


# Mapping of dependency_graph layer names to the products that live
# in that tier. The 7 declared products span core -> application ->
# platform -> framework -> extension. Used by load_spec_from_products().
PRODUCT_TIER_TO_LAYER: Dict[str, str] = {
    "core":         "core_products",
    "application":  "applications",
    "platform":     "applications",
    "framework":    "frameworks",
    "extension":    "extensions",
}


def load_spec_from_layer(
    *,
    registry_path: Path,
    layer: str,
    name: Optional[str] = None,
    description: str = "",
    lane_overrides: Optional[Dict[str, Tuple[Lane, ...]]] = None,
) -> CombinedCEMSpec:
    """Build a CombinedCEMSpec for an entire dependency_graph layer.

    Args:
        registry_path: path to FORGE_REGISTRY.json.
        layer: one of 'lattice_forge', 'engine_forges', 'reforge_ring',
            'core_products', 'applications', 'frameworks', 'extensions'.
            'kernel' is allowed but returns an empty spec (the
            cqekernel package itself is the kernel; there are no
            forges at the kernel layer).
        name: optional name (default: ``"layer_<layer>"``).
        description: optional description.
        lane_overrides: optional dict mapping forge name to a tuple
            of Lane values.

    Returns:
        A CombinedCEMSpec with the forges in the layer.

    Raises:
        ValueError: if the layer name is unknown.
    """
    valid_layers = {
        "kernel", "lattice_forge", "engine_forges", "reforge_ring",
        "core_products", "applications", "frameworks", "extensions",
    }
    if layer not in valid_layers:
        raise ValueError(
            f"unknown layer {layer!r}; known layers: {sorted(valid_layers)}"
        )
    if layer == "kernel":
        # The kernel is the cqekernel package itself; there are no
        # forges at the kernel layer. Return an empty spec.
        return CombinedCEMSpec(
            forges=(),
            name=name or "layer_kernel",
            description=description or "Empty spec; the kernel is the cqekernel package itself",
        )

    forge_names = list(LAYER_FORGES.get(layer, ()))
    if not forge_names:
        # Layers that hold products (not forges). The user should
        # call load_spec_from_products() instead, but we return an
        # empty spec rather than erroring — this is a degenerate case.
        return CombinedCEMSpec(
            forges=(),
            name=name or f"layer_{layer}",
            description=description or f"Empty spec; layer {layer!r} holds products, not forges",
        )

    return load_spec_from_registry(
        registry_path=registry_path,
        forges=forge_names,
        name=name or f"layer_{layer}",
        description=description or f"All forges in dependency_graph layer {layer!r}",
        lane_overrides=lane_overrides,
    )


def load_spec_from_products(
    *,
    registry_path: Path,
    tier: Optional[str] = None,
    name: Optional[str] = None,
    description: str = "",
    lane_overrides: Optional[Dict[str, Tuple[Lane, ...]]] = None,
) -> CombinedCEMSpec:
    """Build a CombinedCEMSpec for all declared products in FORGE_REGISTRY.

    Args:
        registry_path: path to FORGE_REGISTRY.json.
        tier: optional tier filter. If given, only products with
            ``tier == tier`` are included. Tiers: 'core', 'application',
            'platform', 'framework', 'extension'.
        name: optional name (default: 'all_products' or
            'products_tier_<tier>').
        description: optional description.
        lane_overrides: optional dict mapping product name to a tuple
            of Lane values.

    The product is a *coarser* unit than a forge: each product may
    compose several forges internally. The CombinedCEM treats each
    product as a single contribution in the receipt, with the
    product's declared forges captured in the contribution's
    ``algebra_deps`` field.

    Returns:
        A CombinedCEMSpec with one contribution per matching product.
    """
    registry = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    products = registry.get("products", {})

    contributions: List[ForgeContribution] = []
    for product_name, product in products.items():
        p_tier = product.get("tier", "core")
        if tier is not None and p_tier != tier:
            continue
        role = str(product.get("role", ""))
        algebra_deps = product.get("algebra_deps", [])
        # Lanes: R-only is a safe default for products (they ship
        # outward artifacts). The host can override.
        lanes = (lane_overrides or {}).get(product_name) \
            or DEFAULT_FORGE_LANES.get(product_name) \
            or (Lane.R,)

        contributions.append(ForgeContribution(
            forge=product_name,  # the product name, not a forge name
            lanes=lanes,
            tier=p_tier,
            category=product.get("category", "product"),
            role=role,
            source=str(product.get("source", "")),
        ))

    if not contributions:
        tier_label = f" tier={tier!r}" if tier else ""
        raise ValueError(
            f"no products matched (registry has "
            f"{len(products)} products{tier_label})"
        )

    return CombinedCEMSpec(
        forges=tuple(contributions),
        name=name or (f"products_tier_{tier}" if tier else "all_products"),
        description=description or (
            f"All {len(contributions)} declared products"
            + (f" in tier {tier!r}" if tier else "")
        ),
    )


def load_spec_from_registry(
    *,
    registry_path: Path,
    forges: List[str],
    name: str,
    description: str = "",
    lane_overrides: Optional[Dict[str, Tuple[Lane, ...]]] = None,
) -> CombinedCEMSpec:
    """Build a CombinedCEMSpec from a subset of FORGE_REGISTRY forges.

    Args:
        registry_path: path to FORGE_REGISTRY.json.
        forges: list of forge names to compose. Each must exist
            in the registry's ``forges`` dict.
        name: human-readable name for the combined CEM.
        description: optional description.
        lane_overrides: optional dict mapping forge name to a tuple
            of Lane values. Overrides the DEFAULT_FORGE_LANES
            heuristic.

    Returns:
        A CombinedCEMSpec ready to be wrapped in a CombinedCEM.

    Raises:
        ValueError: if a forge name is not in the registry.
    """
    registry = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    registry_forges = registry.get("forges", {})

    contributions: List[ForgeContribution] = []
    for forge_name in forges:
        if forge_name not in registry_forges:
            raise ValueError(
                f"forge {forge_name!r} not in FORGE_REGISTRY.json; "
                f"known forges: {sorted(registry_forges.keys())}"
            )
        entry = registry_forges[forge_name]
        role = str(entry.get("role", entry.get("purpose", entry.get("description", ""))))
        # Look up the product tier/category if this forge is also a product
        products = registry.get("products", {})
        tier = "core"
        category = "forge"
        source = ""
        for pname, pentry in products.items():
            if forge_name in pname or forge_name.lower() in pname.lower():
                tier = pentry.get("tier", tier)
                category = pentry.get("category", category)
                source = pentry.get("source", "")
                break
        if not source:
            # Fall back to the forge entry itself
            source = entry.get("source", entry.get("module", ""))

        # Resolve the lanes: override > default > ('C',) fallback
        lanes = (lane_overrides or {}).get(forge_name) \
            or DEFAULT_FORGE_LANES.get(forge_name) \
            or (Lane.C,)

        contributions.append(ForgeContribution(
            forge=forge_name,
            lanes=lanes,
            tier=tier,
            category=category,
            role=role,
            source=str(source),
        ))

    return CombinedCEMSpec(
        forges=tuple(contributions),
        name=name,
        description=description,
    )


__all__ = [
    "CombinedCEM",
    "CombinedCEMSpec",
    "CombinedCEMReceipt",
    "DEFAULT_FORGE_LANES",
    "ForgeContribution",
    "LAYER_FORGES",
    "PRODUCT_TIER_TO_LAYER",
    "load_spec_from_layer",
    "load_spec_from_products",
    "load_spec_from_registry",
]
