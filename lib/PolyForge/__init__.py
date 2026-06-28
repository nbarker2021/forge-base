"""PolyForge - polynomial / shape-form reader (the MorphForge family, Paper 21).

Referenced but never packaged. Built here as a real, importable, stdlib-only
module: reads a polynomial (coefficient list) or a polyline (point list) as a
MorphForge ribbon, and exposes the digital-root reduced form per coefficient
(the slot center C). Same lossless ribbon discipline as MorphForge.
"""
from __future__ import annotations

from MorphForge import ribbon, round_trip


def digital_root(n: int) -> int:
    n = abs(int(n))
    return 0 if n == 0 else 1 + (n - 1) % 9


def poly_ribbon(coeffs) -> dict:
    """Ribbon-encode a coefficient list; reduce each to its digital-root center."""
    r = ribbon(coeffs)
    centers = [digital_root(c) for c in coeffs]
    return {"degree": max(0, len(coeffs) - 1), "ribbon": r,
            "dr_centers": centers, "lossless": round_trip(coeffs)}


def verify() -> dict:
    p = poly_ribbon([1, 4, 7, 10, 13])
    return {"forge": "PolyForge", "paper": 21, "status": "pass" if p["lossless"] else "fail",
            "dr_centers": p["dr_centers"]}
