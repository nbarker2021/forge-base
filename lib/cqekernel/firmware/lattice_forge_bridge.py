"""
Firmware bridge to ``lattice_forge`` 0.3.0+.

The CQE/CMPLX kernel is **stdlib-only** by default — it never
imports ``lattice_forge`` directly. When the host has installed
``lattice-forge``, this bridge detects it and routes the kernel's
``LightCone`` and ``Ribbon`` operations through the hardened
``lattice_forge.cqe`` and ``lattice_forge.cmplx`` implementations.

Contract:

  * Every public function in this module returns a
    ``FirmwareResult`` with ``status`` of either ``"OK"`` (carried
    back the result) or ``"EXTERNAL_REQUIRED"`` (lattice_forge is
    not installed) or ``"FAIL"`` (lattice_forge raised).

  * The kernel calls this module **opportunistically**. A failure
    here NEVER raises to the caller — the kernel has its own
    stdlib implementations that take over.

  * The kernel *never* promotes this layer to a higher evidence
    class. Calling ``bridge.managed_ribbon()`` still emits a
    ``KERNEL_PRIMITIVE`` receipt unless the caller explicitly
    wraps it in a firmware-backed receipt.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Public status / result types
# ---------------------------------------------------------------------------

# Reuse the kernel's status vocabulary so callers don't have to learn
# a second one.
from ..core.status import EvidenceStatus  # noqa: E402


@dataclass
class FirmwareResult:
    """Result of a bridge call.

    ``status`` mirrors the kernel's ReceiptStatus vocabulary
    (PASS/FAIL/EXTERNAL_REQUIRED). ``payload`` is whatever the
    firmware returned (or a small ``{"reason": ...}`` dict when the
    firmware is unavailable).
    """

    status: str
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {"status": self.status, "payload": dict(self.payload)}


# ---------------------------------------------------------------------------
# Module-level latching
# ---------------------------------------------------------------------------

# Once we discover lattice_forge, we cache the module references so
# we don't re-import on every call. If the import fails, we cache
# the None and never try again.
_lf_cqe = None
_lf_cmplx = None
_lf_discovery_error: Optional[str] = None
_discovery_done: bool = False


def _discover_lattice_forge() -> Tuple[Optional[Any], Optional[Any], Optional[str]]:
    """Try to import lattice_forge's CQE and CMPLX submodules.

    Returns ``(cqe_mod, cmplx_mod, error)``. Both modules are None
    if the import failed. ``error`` is a human-readable string
    explaining the failure (or None on success).
    """
    global _lf_cqe, _lf_cmplx, _lf_discovery_error, _discovery_done
    if _discovery_done:
        return _lf_cqe, _lf_cmplx, _lf_discovery_error
    _discovery_done = True
    try:
        import lattice_forge.cqe as cqe_mod  # type: ignore
        _lf_cqe = cqe_mod
    except Exception as e:  # pragma: no cover - depends on host env
        _lf_cqe = None
        _lf_discovery_error = repr(e)
    try:
        import lattice_forge.cmplx as cmplx_mod  # type: ignore
        _lf_cmplx = cmplx_mod
    except Exception as e:  # pragma: no cover - depends on host env
        _lf_cmplx = None
        if _lf_discovery_error is None:
            _lf_discovery_error = repr(e)
    return _lf_cqe, _lf_cmplx, _lf_discovery_error


def available() -> bool:
    """Return True iff lattice_forge is importable."""
    cqe, cmplx, _ = _discover_lattice_forge()
    return cqe is not None


def manifest() -> Dict[str, Any]:
    """Return a small manifest dict describing what's available."""
    cqe, cmplx, err = _discover_lattice_forge()
    out: Dict[str, Any] = {
        "pack_id": "lattice_forge",
        "available": cqe is not None,
        "module": "lattice_forge.cqe",
        "reason": err or ("ok" if cqe is not None else "not installed"),
        "capabilities": [],
    }
    if cqe is not None:
        caps = []
        for name in ("CQEHypervisor", "CQELightConeHypervisor",
                     "ManagedRibbon", "LightConeFrame", "D4Token",
                     "ReceiptPortal", "LCRBoundary", "RibbonReceipt",
                     "manage_ribbon", "launch_hypervisor"):
            if hasattr(cqe, name):
                caps.append(name)
        out["capabilities"] = caps
    if cmplx is not None:
        out["cmplx_available"] = True
        out["cmplx_capabilities"] = [
            n for n in ("CMPLXRuntime", "RuntimeBudget", "RuntimeReceipt")
            if hasattr(cmplx, n)
        ]
    else:
        out["cmplx_available"] = False
    return out


# ---------------------------------------------------------------------------
# Coercion
# ---------------------------------------------------------------------------


RibbonInput = Union[bytes, bytearray, str]


def _coerce(ribbon: RibbonInput) -> bytes:
    """Match lattice_forge's RibbonInput coercion."""
    if isinstance(ribbon, (bytes, bytearray)):
        return bytes(ribbon)
    if isinstance(ribbon, str):
        # Match the original: only accept pure 0/1 strings as-is;
        # otherwise encode as utf-8.
        if set(ribbon) <= {"0", "1"} and ribbon:
            return ribbon.encode("ascii")
        return ribbon.encode("utf-8")
    # Iterable of ints (0/1)
    return bytes(int(b) & 0xFF for b in ribbon)


# ---------------------------------------------------------------------------
# Managed ribbon (kernel-side facade over lattice_forge)
# ---------------------------------------------------------------------------


@dataclass
class ManagedRibbonView:
    """Kernel-side view of a lattice_forge managed ribbon.

    Returned by ``bridge.manage_ribbon(input)``. This is a **view**,
    not a copy: ``ribbon`` holds the lattice_forge object. If
    lattice_forge is not available, ``ribbon`` is None.
    """

    input_bytes: bytes
    output_bytes: bytes
    decisions: Tuple[str, ...]
    receipt_count: int
    savings: int
    ribbon: Any  # the lattice_forge ManagedRibbon, or None
    source: str  # "lattice_forge" or "stdlib_fallback"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_hash": hashlib.sha256(self.input_bytes).hexdigest()[:16],
            "output_hash": hashlib.sha256(self.output_bytes).hexdigest()[:16],
            "decisions": list(self.decisions),
            "receipt_count": self.receipt_count,
            "savings": self.savings,
            "source": self.source,
        }


def manage_ribbon(ribbon: RibbonInput) -> FirmwareResult:
    """Call ``lattice_forge.cqe.manage_ribbon(input)`` if available.

    Returns a FirmwareResult whose payload is the
    ``ManagedRibbonView.to_dict()`` form. When lattice_forge is not
    installed, returns ``EXTERNAL_REQUIRED`` with a stdlib
    fallback that uses the kernel's own gluon correction identity.
    """
    cqe, _, err = _discover_lattice_forge()
    data = _coerce(ribbon)
    if cqe is not None:
        try:
            mr = cqe.manage_ribbon(ribbon)
            view = ManagedRibbonView(
                input_bytes=bytes(mr.input),
                output_bytes=bytes(mr.output),
                decisions=tuple(mr.decisions),
                receipt_count=len(mr.receipts),
                savings=int(mr.savings),
                ribbon=mr,
                source="lattice_forge",
            )
            return FirmwareResult(status="OK", payload=view.to_dict())
        except Exception as e:
            return FirmwareResult(status="FAIL", payload={"reason": repr(e)})
    # stdlib fallback: compute the kernel's own correction surface
    # count. This is what the kernel was doing before firmware was
    # available. Note: this is NOT promoted to a higher evidence
    # class — the receipt is still KERNEL_PRIMITIVE.
    correction = _stdlib_correction_count(data)
    decisions = ("COAST",) if correction == 0 else ("NUDGE_R",)
    return FirmwareResult(
        status="EXTERNAL_REQUIRED",
        payload={
            "reason": err or "lattice_forge not installed",
            "input_hash": hashlib.sha256(data).hexdigest()[:16],
            "decisions": list(decisions),
            "correction_count": correction,
            "source": "stdlib_fallback",
        },
    )


# ---------------------------------------------------------------------------
# Light cone (kernel-side facade over lattice_forge)
# ---------------------------------------------------------------------------


def light_cone(ribbon: RibbonInput, *, split_bias: int = 1, tick: int = 0) -> FirmwareResult:
    """Call ``lattice_forge.cqe.CQELightConeHypervisor`` if available.

    ``split_bias`` is constrained to {1, 2, 4, 8} exactly as in
    lattice_forge.cqe.CQELightConeHypervisor.__init__. Invalid
    values are rejected before calling firmware.
    """
    if split_bias not in (1, 2, 4, 8):
        return FirmwareResult(
            status="FAIL",
            payload={"reason": f"split_bias must be one of 1,2,4,8; got {split_bias}"},
        )
    cqe, _, err = _discover_lattice_forge()
    data = _coerce(ribbon)
    if cqe is not None:
        try:
            hyp = cqe.CQELightConeHypervisor(split_bias=split_bias)
            frame = hyp.sample(ribbon, tick=tick)
            return FirmwareResult(
                status="OK",
                payload={
                    "source": "lattice_forge",
                    "frame": {
                        "full": frame.full,
                        "monad": list(frame.monad),
                        "triad_count": len(frame.triad),
                        "quadratic_count": len(frame.quadratic),
                        "centroid": frame.centroid,
                        "an_spine_count": len(frame.an_spine),
                        "jordan_lanes_count": len(frame.jordan_lanes),
                        "hamiltonians_count": len(frame.hamiltonians),
                        "lcr_boundary": {
                            "left": list(frame.lcr_boundary.left),
                            "center": frame.lcr_boundary.center,
                            "right": list(frame.lcr_boundary.right),
                        },
                        "split_bias": frame.split_bias,
                        "tick": frame.tick,
                    },
                },
            )
        except TypeError as e:
            # lattice_forge API mismatch - treat as not available
            return FirmwareResult(
                status="EXTERNAL_REQUIRED",
                payload={"reason": f"lattice_forge API mismatch: {e}", "source": "stdlib_fallback"}
            )
        except Exception as e:
            return FirmwareResult(status="FAIL", payload={"reason": repr(e)})
    return FirmwareResult(
        status="EXTERNAL_REQUIRED",
        payload={
            "reason": err or "lattice_forge not installed",
            "split_bias": split_bias,
            "input_hash": hashlib.sha256(data).hexdigest()[:16],
            "source": "stdlib_fallback",
        },
    )


def launch_hypervisor(ribbons, *, split_bias: int = 1, max_samples=None) -> FirmwareResult:
    """Call ``lattice_forge.cqe.launch_hypervisor`` if available."""
    if split_bias not in (1, 2, 4, 8):
        return FirmwareResult(
            status="FAIL",
            payload={"reason": f"split_bias must be one of 1,2,4,8; got {split_bias}"},
        )
    cqe, _, err = _discover_lattice_forge()
    if cqe is not None:
        try:
            handle = cqe.launch_hypervisor(
                list(ribbons), max_samples=max_samples, split_bias=split_bias
            )
            return FirmwareResult(
                status="OK",
                payload={
                    "source": "lattice_forge",
                    "frame_count": len(handle.frames),
                    "running": bool(handle.running),
                },
            )
        except TypeError as e:
            # lattice_forge API mismatch - treat as not available
            return FirmwareResult(
                status="EXTERNAL_REQUIRED",
                payload={"reason": f"lattice_forge API mismatch: {e}", "source": "stdlib_fallback"}
            )
        except Exception as e:
            return FirmwareResult(status="FAIL", payload={"reason": repr(e)})
    return FirmwareResult(
        status="EXTERNAL_REQUIRED",
        payload={"reason": err or "lattice_forge not installed", "source": "stdlib_fallback"},
    )


def sidecar_check(ribbon: RibbonInput, *, phase: str = "FIRST_TOUCH") -> FirmwareResult:
    """Call ``lattice_forge.cqe.CQESidecarMonitor`` if available.

    ``phase`` is one of ``"FIRST_TOUCH"`` or ``"PREDEPLOY"``.
    """
    if phase not in ("FIRST_TOUCH", "PREDEPLOY"):
        return FirmwareResult(
            status="FAIL",
            payload={"reason": f"phase must be FIRST_TOUCH or PREDEPLOY; got {phase!r}"},
        )
    cqe, _, err = _discover_lattice_forge()
    if cqe is not None:
        try:
            monitor = cqe.CQESidecarMonitor()
            result = (
                monitor.first_touch(ribbon)
                if phase == "FIRST_TOUCH"
                else monitor.predeploy(ribbon)
            )
            return FirmwareResult(
                status="OK",
                payload={
                    "source": "lattice_forge",
                    "phase": result.phase,
                    "decision": result.decision,
                    "interrupt": bool(result.interrupt),
                    "guidance": result.guidance,
                    "propagation_lanes": list(result.propagation_lanes),
                    "need": result.need,
                },
            )
        except TypeError as e:
            # lattice_forge API mismatch - treat as not available
            return FirmwareResult(
                status="EXTERNAL_REQUIRED",
                payload={"reason": f"lattice_forge API mismatch: {e}", "source": "stdlib_fallback"}
            )
        except Exception as e:
            return FirmwareResult(status="FAIL", payload={"reason": repr(e)})
    return FirmwareResult(
        status="EXTERNAL_REQUIRED",
        payload={
            "reason": err or "lattice_forge not installed",
            "phase": phase,
            "source": "stdlib_fallback",
        },
    )


def match_paper_bundle(papers, *, top_k: int = 3) -> FirmwareResult:
    """Call ``lattice_forge.cqe.match_paper_bundle`` if available.

    ``papers`` is a list of dicts with keys ``title``, ``path``,
    ``text`` (see ``PaperDatum``). Returns a bundle match with
    candidate sheets and a ``TermBundleResult``.
    """
    cqe, _, err = _discover_lattice_forge()
    if cqe is not None:
        try:
            paper_data = [
                cqe.PaperDatum(
                    title=str(p.get("title", "")),
                    path=str(p.get("path", "")),
                    text=str(p.get("text", "")),
                )
                for p in papers
            ]
            result = cqe.match_paper_bundle(paper_data)
            sheets = [
                {"path": s.path, "sheet": s.sheet}
                for s in result.sheets
            ]
            bundle = result.bundle
            return FirmwareResult(
                status="OK",
                payload={
                    "source": "lattice_forge",
                    "sheet_count": len(sheets),
                    "sheets": sheets,
                    "bundle_terms": (
                        list(bundle.terms) if hasattr(bundle, "terms") else None
                    ),
                },
            )
        except TypeError as e:
            # lattice_forge API mismatch - treat as not available
            return FirmwareResult(
                status="EXTERNAL_REQUIRED",
                payload={"reason": f"lattice_forge API mismatch: {e}", "source": "stdlib_fallback", "paper_count": len(papers) if hasattr(papers, "__len__") else 0, "top_k": top_k}
            )
        except Exception as e:
            return FirmwareResult(status="FAIL", payload={"reason": repr(e)})
    return FirmwareResult(
        status="EXTERNAL_REQUIRED",
        payload={
            "reason": err or "lattice_forge not installed",
            "paper_count": len(papers) if hasattr(papers, "__len__") else 0,
            "top_k": top_k,
            "source": "stdlib_fallback",
        },
    )


# ---------------------------------------------------------------------------
# CMPLX runtime (kernel-side facade over lattice_forge)
# ---------------------------------------------------------------------------


@dataclass
class RuntimeBudgetView:
    """Kernel-side view of a CMPLX runtime budget."""

    cqe_savings: int
    cached_closure: int
    host_budget: int
    total: int
    source: str  # "lattice_forge" or "stdlib_fallback"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cqe_savings": self.cqe_savings,
            "cached_closure": self.cached_closure,
            "host_budget": self.host_budget,
            "total": self.total,
            "source": self.source,
        }


def make_budget(
    *, cqe_savings: int = 0, cached_closure: int = 0, host_budget: int = 0
) -> FirmwareResult:
    """Construct a CMPLX RuntimeBudget. Uses lattice_forge when
    available; otherwise constructs a stdlib analog with the same
    spend() / total / source semantics."""
    _, cmplx, err = _discover_lattice_forge()
    if cmplx is not None:
        try:
            b = cmplx.RuntimeBudget(
                cqe_savings=cqe_savings,
                cached_closure=cached_closure,
                host_budget=host_budget,
            )
            return FirmwareResult(
                status="OK",
                payload=RuntimeBudgetView(
                    cqe_savings=b.cqe_savings,
                    cached_closure=b.cached_closure,
                    host_budget=b.host_budget,
                    total=b.total,
                    source="lattice_forge",
                ).to_dict(),
            )
        except TypeError as e:
            # lattice_forge API mismatch - treat as not available
            return FirmwareResult(
                status="EXTERNAL_REQUIRED",
                payload={"reason": f"lattice_forge API mismatch: {e}", "source": "stdlib_fallback"}
            )
        except Exception as e:
            return FirmwareResult(status="FAIL", payload={"reason": repr(e)})
    return FirmwareResult(
        status="EXTERNAL_REQUIRED",
        payload=RuntimeBudgetView(
            cqe_savings=cqe_savings,
            cached_closure=cached_closure,
            host_budget=host_budget,
            total=cqe_savings + cached_closure + host_budget,
            source="stdlib_fallback",
        ).to_dict() | {"reason": err or "lattice_forge not installed"},
    )


def spend(budget: Dict[str, Any], cost: int) -> FirmwareResult:
    """Spend ``cost`` from a budget dict. Mirrors lattice_forge's
    RuntimeBudget.spend() — returns which lane was debited."""
    if cost < 0:
        return FirmwareResult(status="FAIL", payload={"reason": "cost must be non-negative"})
    cqe_savings = int(budget.get("cqe_savings", 0))
    cached_closure = int(budget.get("cached_closure", 0))
    host_budget = int(budget.get("host_budget", 0))
    if cost == 0:
        return FirmwareResult(
            status="OK",
            payload={"lane": "ZERO_COST", "remaining": budget},
        )
    if cqe_savings >= cost:
        return FirmwareResult(
            status="OK",
            payload={
                "lane": "CQE_SAVINGS",
                "remaining": {
                    "cqe_savings": cqe_savings - cost,
                    "cached_closure": cached_closure,
                    "host_budget": host_budget,
                },
            },
        )
    if cached_closure >= cost:
        return FirmwareResult(
            status="OK",
            payload={
                "lane": "CACHED_CLOSURE",
                "remaining": {
                    "cqe_savings": cqe_savings,
                    "cached_closure": cached_closure - cost,
                    "host_budget": host_budget,
                },
            },
        )
    if host_budget >= cost:
        return FirmwareResult(
            status="OK",
            payload={
                "lane": "HOST_BUDGET",
                "remaining": {
                    "cqe_savings": cqe_savings,
                    "cached_closure": cached_closure,
                    "host_budget": host_budget - cost,
                },
            },
        )
    return FirmwareResult(
        status="FAIL",
        payload={"reason": "CMPLX cannot spend unearned work"},
    )


# ---------------------------------------------------------------------------
# stdlib fallback helpers
# ---------------------------------------------------------------------------


def _stdlib_correction_count(data: bytes) -> int:
    """Count the C AND NOT R firings in a stdlib 3-bit window scan.

    Used only when lattice_forge is not installed. Mirrors
    lattice_forge's correction primitive so the kernel's own
    ribbon receives a sensible receipt count without external
    dependencies.
    """
    if len(data) == 0:
        return 0
    bits = "".join(f"{b:08b}" for b in data)
    n = 0
    for i in range(len(bits) - 2):
        L, C, R = int(bits[i]), int(bits[i + 1]), int(bits[i + 2])
        if C == 1 and R == 0:
            n += 1
    return n


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "FirmwareResult",
    "ManagedRibbonView",
    "RuntimeBudgetView",
    "available",
    "manifest",
    "manage_ribbon",
    "light_cone",
    "launch_hypervisor",
    "sidecar_check",
    "match_paper_bundle",
    "make_budget",
    "spend",
]
