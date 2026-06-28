"""
Firmware bridge to the lattice_forge algebra modules.

Calls into ``lattice_forge.octonion``, ``lattice_forge.jordan_j3``,
``lattice_forge.f4_action`` when available; otherwise falls back
to the stdlib stubs in ``cqekernel.algebra``.

The diff point: when both surfaces are present, the same
function call on the same input should produce the same answer.
The bridge exposes a ``diff()`` helper that runs the same call on
both surfaces and reports any divergence.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


# Reuse the stdlib fallback layer
from ..algebra import (
    J3O as StdlibJ3O,
    Octonion as StdlibOctonion,
    closed_form_rule30_8x8_transition as stdlib_8x8,
    closed_form_shell2_3x3 as stdlib_3x3,
    s3_permutation_matrices as stdlib_s3,
    verify_j3o_axioms as stdlib_j3o_check,
    verify_n3_su3_closure as stdlib_su3_check,
    verify_octonion_axioms as stdlib_octonion_check,
)


# Module-level latching
_lf_octonion = None
_lf_jordan = None
_lf_f4 = None
_discovery_done = False
_discovery_error: Optional[str] = None


def _discover_lattice_forge() -> None:
    global _lf_octonion, _lf_jordan, _lf_f4, _discovery_done, _discovery_error
    if _discovery_done:
        return
    _discovery_done = True
    try:
        import lattice_forge.octonion as o  # type: ignore
        _lf_octonion = o
    except Exception as e:
        _discovery_error = f"octonion: {e!r}"
    try:
        import lattice_forge.jordan_j3 as j  # type: ignore
        _lf_jordan = j
    except Exception as e:
        _discovery_error = (_discovery_error or "") + f" jordan_j3: {e!r}"
    try:
        import lattice_forge.f4_action as f  # type: ignore
        _lf_f4 = f
    except Exception as e:
        _discovery_error = (_discovery_error or "") + f" f4_action: {e!r}"


def available() -> bool:
    _discover_lattice_forge()
    return (_lf_octonion is not None
            and _lf_jordan is not None
            and _lf_f4 is not None)


def manifest() -> Dict[str, Any]:
    _discover_lattice_forge()
    return {
        "octonion_available": _lf_octonion is not None,
        "jordan_j3_available": _lf_jordan is not None,
        "f4_action_available": _lf_f4 is not None,
        "available": available(),
        "discovery_error": _discovery_error,
    }


# ---------------------------------------------------------------------------
# Diff helpers
# ---------------------------------------------------------------------------


@dataclass
class DiffResult:
    """Result of running the same call on both the stdlib and
    the lattice_forge surfaces."""

    surface: str  # "octonion" / "j3o" / "f4_3x3" / "f4_8x8" / "su3_closure"
    agree: bool
    stdlib_value: Any
    lf_value: Any
    diff: Optional[Dict[str, Any]] = None  # detailed diff if any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "surface": self.surface,
            "agree": self.agree,
            "stdlib": self.stdlib_value if _safe(self.stdlib_value) else repr(self.stdlib_value),
            "lf": self.lf_value if _safe(self.lf_value) else repr(self.lf_value),
            "diff": self.diff,
        }


def _safe(v: Any) -> bool:
    try:
        if isinstance(v, (str, int, float, bool, list, dict, tuple)):
            return True
    except Exception:
        return False
    return False


def _diff_lists(a, b, *, tol: float = 1e-9) -> Dict[str, Any]:
    """Compare two nested-list numeric structures with tolerance."""
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return {"shape_mismatch": (len(a), len(b))}
        diffs = []
        for i, (x, y) in enumerate(zip(a, b)):
            d = _diff_lists(x, y, tol=tol)
            if d:
                diffs.append((i, d))
        if not diffs:
            return {}
        return {"per_index": diffs[:5], "count": len(diffs)}
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if abs(a - b) > tol:
            return {"a": a, "b": b, "delta": a - b}
        return {}
    if a == b:
        return {}
    return {"a": a, "b": b}


# ---------------------------------------------------------------------------
# Octonion diff
# ---------------------------------------------------------------------------


def diff_octonion_axioms() -> Optional[DiffResult]:
    """Run ``verify_octonion_axioms`` on both surfaces, report
    agreement. Returns None if lattice_forge is not available."""
    if not available():
        return None
    std = stdlib_octonion_check()
    lf = _lf_octonion.verify_octonion_axioms()
    agree = std["status"] == lf["status"]
    diff = None
    if not agree:
        diff = {"stdlib_status": std["status"], "lf_status": lf["status"]}
    return DiffResult(
        surface="octonion",
        agree=agree,
        stdlib_value=std,
        lf_value=lf,
        diff=diff,
    )


# ---------------------------------------------------------------------------
# J3O diff
# ---------------------------------------------------------------------------


def diff_j3o_axioms() -> Optional[DiffResult]:
    if not available():
        return None
    std = stdlib_j3o_check()
    lf = _lf_jordan.verify_j3o_axioms()
    agree = std["status"] == lf["status"]
    diff = None
    if not agree:
        diff = {"stdlib_status": std["status"], "lf_status": lf["status"]}
    return DiffResult(
        surface="j3o",
        agree=agree,
        stdlib_value=std,
        lf_value=lf,
        diff=diff,
    )


# ---------------------------------------------------------------------------
# F4 3x3 closed-form diff
# ---------------------------------------------------------------------------


def diff_closed_form_3x3() -> Optional[DiffResult]:
    if not available():
        return None
    std = stdlib_3x3()
    lf = _lf_f4.closed_form_shell2_3x3()
    std_m = std["matrix"]
    # lattice_forge returns 'conditional_matrix', stdlib returns 'matrix'
    lf_m = lf.get("conditional_matrix", lf.get("matrix"))
    if lf_m is None:
        return DiffResult(
            surface="f4_3x3",
            agree=False,
            stdlib_value=std_m,
            lf_value=lf,
            diff={"error": "lf missing matrix/conditional_matrix key", "lf_keys": list(lf.keys())},
        )
    diff = _diff_lists(std_m, lf_m)
    return DiffResult(
        surface="f4_3x3",
        agree=(not diff),
        stdlib_value=std_m,
        lf_value=lf_m,
        diff=(diff if diff else None),
    )


# ---------------------------------------------------------------------------
# F4 8x8 transition diff
# ---------------------------------------------------------------------------


def diff_closed_form_8x8() -> Optional[DiffResult]:
    if not available():
        return None
    std = stdlib_8x8()
    lf = _lf_f4.closed_form_rule30_8x8_transition()
    # lattice_forge returns different structure: 'transitions', 'marginalization', 'rule'
    # stdlib returns 'matrix'. These are fundamentally different representations.
    # Check if lf has 'matrix' key (fake or compatible), otherwise skip comparison
    if "matrix" not in lf:
        return DiffResult(
            surface="f4_8x8",
            agree=False,
            stdlib_value=std.get("matrix"),
            lf_value=lf,
            diff={"note": "lf returns different structure (transitions/marginalization/rule), not directly comparable to stdlib matrix", "lf_keys": list(lf.keys())},
        )
    diff = _diff_lists(std["matrix"], lf["matrix"])
    return DiffResult(
        surface="f4_8x8",
        agree=(not diff),
        stdlib_value=std["matrix"],
        lf_value=lf["matrix"],
        diff=(diff if diff else None),
    )


# ---------------------------------------------------------------------------
# N3 / SU3 closure diff
# ---------------------------------------------------------------------------


def diff_su3_closure() -> Optional[DiffResult]:
    if not available():
        return None
    std = stdlib_su3_check()
    lf = _lf_f4.verify_n3_su3_closure_exact()
    agree = std["status"] == lf["status"]
    diff = None
    if not agree:
        diff = {"stdlib_status": std["status"], "lf_status": lf["status"]}
    return DiffResult(
        surface="su3_closure",
        agree=agree,
        stdlib_value=std,
        lf_value=lf,
        diff=diff,
    )


# ---------------------------------------------------------------------------
# All at once
# ---------------------------------------------------------------------------


def diff_all() -> Dict[str, Any]:
    """Run every diff and return a summary.

    If lattice_forge is not installed, returns
    ``{"available": False, "diffs": {}}`` and a
    ``stdlib_alone`` summary using the kernel's stdlib checks.
    """
    out: Dict[str, Any] = {"available": available(), "diffs": {}}
    if not available():
        # Stdlib-only summary
        out["stdlib_alone"] = {
            "octonion": stdlib_octonion_check()["status"],
            "j3o": stdlib_j3o_check()["status"],
            "su3_closure": stdlib_su3_check()["status"],
        }
        return out
    diffs = {
        "octonion": diff_octonion_axioms(),
        "j3o": diff_j3o_axioms(),
        "f4_3x3": diff_closed_form_3x3(),
        "f4_8x8": diff_closed_form_8x8(),
        "su3_closure": diff_su3_closure(),
    }
    out["diffs"] = {k: v.to_dict() for k, v in diffs.items() if v is not None}
    out["all_agree"] = all(d.agree for d in diffs.values() if d is not None)
    return out


__all__ = [
    "DiffResult",
    "available",
    "manifest",
    "diff_octonion_axioms",
    "diff_j3o_axioms",
    "diff_closed_form_3x3",
    "diff_closed_form_8x8",
    "diff_su3_closure",
    "diff_all",
]
