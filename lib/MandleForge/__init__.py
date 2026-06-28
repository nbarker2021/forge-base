"""MandleForge — Mandelbrot/Julia Dynamics on Gluon Mass

The Gluon mass trajectory C_accumulated lives in the Mandelbrot parameter space.
Each paper's C-form = a point in M-set. The skip fraction = escape time at boundary.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import math

# ---------------------------------------------------------------------------
# Mandelbrot Parameter Space
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GluonMassPoint:
    """A Gluon mass as a complex parameter in the Mandelbrot space."""
    real: float      # C_accumulated / scaling
    imag: float      # accumulated phase / coupling
    
    @property
    def c(self) -> complex:
        return complex(self.real, self.imag)
    
    @classmethod
    def from_accumulated(cls, C_accumulated: int, scaling: float = 0.1) -> "GluonMassPoint":
        # C_accumulated is the running XOR (0 or 1 per step) scaled to complex
        return cls(real=C_accumulated * scaling, imag=0.0)
    
    @classmethod
    def from_coupling(cls, C_accumulated: int, phi_coupling: float = 0.03) -> "GluonMassPoint":
        # Use the COUPLING constant from the solver: log(φ)/16 ≈ 0.03
        return cls(real=C_accumulated * phi_coupling, imag=0.0)


# ---------------------------------------------------------------------------
# Mandelbrot Iteration
# ---------------------------------------------------------------------------

def mandelbrot_escape_time(
    c: complex,
    max_iter: int = 9,          # K_max = 9 (Nebe shell bound)
    escape_radius: float = 2.0
) -> Tuple[int, bool]:
    """
    Compute escape time for Mandelbrot iteration z = z² + c.
    
    Returns: (iterations, escaped)
    - escaped=False means bounded (real page / Lucas weight = 1)
    - escaped=True means K-window violation (skip pad / CAPACITY_EXCEEDED)
    
    K_max=9 is the native page depth — exact match to Paper 08 governance.
    """
    z = 0.0 + 0.0j
    for k in range(max_iter):
        z = z*z + c
        if abs(z) > escape_radius:
            return (k+1, True)  # escaped at iteration k+1
    return (max_iter, False)    # bounded within K_max


def mandelbrot_basin_depth(c: complex, max_iter: int = 9) -> int:
    """Depth of stay in the Mandelbrot basin before escape (or max_iter if bounded)."""
    iterations, escaped = mandelbrot_escape_time(c, max_iter)
    return iterations


# ---------------------------------------------------------------------------
# Julia Fibers
# ---------------------------------------------------------------------------

@dataclass
class JuliaFiber:
    """The Julia set J_c for a fixed Gluon mass c."""
    c: complex
    resolution: int = 512
    bounds: Tuple[float, float, float, float] = (-2, 2, -2, 2)  # x_min, x_max, y_min, y_max
    
    def escape_time_grid(self, max_iter: int = 9) -> List[List[int]]:
        """Compute escape-time grid for Julia set J_c.
        
        Each point z₀ in the grid represents a possible VOA sector trajectory.
        Escape time = depth at which that trajectory violates K-window.
        """
        x_min, x_max, y_min, y_max = self.bounds
        grid = []
        for i in range(self.resolution):
            row = []
            y = y_min + (y_max - y_min) * i / (self.resolution - 1)
            for j in range(self.resolution):
                x = x_min + (x_max - x_min) * j / (self.resolution - 1)
                z = complex(x, y)
                iterations = 0
                for k in range(max_iter):
                    z = z*z + self.c
                    if abs(z) > 2.0:
                        break
                    iterations += 1
                row.append(iterations)
            grid.append(row)
        return grid
    
    def VOA_sector_map(self, max_iter: int = 9) -> dict:
        """Classify points in the Julia fiber by VOA sector."""
        grid = self.escape_time_grid(max_iter)
        # bounded (never escaped) = vacuum sector (weight 0)
        # escaped = excited sector (weight 5)
        vacuum_count = sum(1 for row in grid for v in row if v == max_iter)
        excited_count = self.resolution * self.resolution - vacuum_count
        return {
            "vacuum_fraction": vacuum_count / (self.resolution ** 2),
            "excited_fraction": excited_count / (self.resolution ** 2),
            "total_points": self.resolution ** 2,
        }


# ---------------------------------------------------------------------------
# The C-Sequence Path in M-set
# ---------------------------------------------------------------------------

@dataclass
class MandelbrotPath:
    """The path traced by the paper C-forms in Mandelbrot parameter space."""
    points: List[GluonMassPoint]  # C₀, C₁, ..., C₅
    
    def escape_times(self, max_iter: int = 9) -> List[Tuple[int, bool]]:
        return [mandelbrot_escape_time(p.c, max_iter) for p in self.points]
    
    def skip_fraction(self, max_iter: int = 9) -> float:
        """Fraction of papers whose C-form escapes the K-window."""
        results = self.escape_times(max_iter)
        return sum(1 for _, escaped in results if escaped) / len(results)
    
    def is_bounded(self, max_iter: int = 9) -> bool:
        """All papers' C-forms stay within K-max (native page)."""
        return all(not escaped for _, escaped in self.escape_times(max_iter))


# ---------------------------------------------------------------------------
# Convergence Diagnostics
# ---------------------------------------------------------------------------

def diagnose_C_convergence(C_sequence: List[int], max_iter: int = 9) -> dict:
    """
    Given the raw C_accumulated sequence [C₀, C₁, ..., C_N],
    diagnose Mandelbrot convergence properties.
    """
    points = [GluonMassPoint.from_accumulated(C) for C in C_sequence]
    path = MandelbrotPath(points)
    
    results = path.escape_times(max_iter)
    return {
        "total_papers": len(C_sequence),
        "bounded_papers": sum(1 for _, e in results if not e),
        "escape_depths": [k for k, e in results if e],
        "skip_fraction": path.skip_fraction(max_iter),
        "all_bounded": path.is_bounded(max_iter),
        "mandelbrot_diagnosis": (
            "All C-forms bounded: the proof stays within native K-max page."
            if path.is_bounded(max_iter)
            else "Some C-forms escape: those papers lift to higher K (Paper 08+)."
        ),
    }


# ---------------------------------------------------------------------------
# Public Surface
# ---------------------------------------------------------------------------

__all__ = [
    "GluonMassPoint",
    "mandelbrot_escape_time",
    "mandelbrot_basin_depth",
    "JuliaFiber",
    "MandelbrotPath",
    "diagnose_C_convergence",
]


# ─── Verify (forge-family contract) ───────────────────────────────────────────

def verify() -> dict:
    """Finite checks binding MandleForge to its docstring claims.

    Tests the documented Mandelbrot / Julia primitives: c=0 boundedness,
    c=2 immediate escape, K_max=9 native-page boundary, the GluonMassPoint
    factories, the C-sequence path diagnostics, and the Julia fiber VOA
    sector map. Pure additive.
    """
    checks = {}

    # 1. c=0 is bounded (the origin is in the Mandelbrot set), c=2 escapes
    #    at iteration 1 (|0^2 + 2| = 2 -> escape_radius = 2, so iteration 1).
    try:
        k0, esc0 = mandelbrot_escape_time(0 + 0j, max_iter=9)
        k2, esc2 = mandelbrot_escape_time(2 + 0j, max_iter=9)
        checks["c0_is_bounded"] = (not esc0) and k0 == 9
        checks["c2_escapes"] = esc2 and k2 == 1
    except Exception:
        checks["c0_is_bounded"] = False
        checks["c2_escapes"] = False

    # 2. K_max=9 is the native page depth: escape-time never returns > 9
    #    in a single call, and basin_depth == iterations on a bounded point.
    try:
        k, esc = mandelbrot_escape_time(0 + 0j, max_iter=9)
        checks["k_max_is_native_9"] = (k <= 9) and (mandelbrot_basin_depth(0 + 0j) == 9)
    except Exception:
        checks["k_max_is_native_9"] = False

    # 3. GluonMassPoint factories
    try:
        p1 = GluonMassPoint.from_accumulated(7)
        p2 = GluonMassPoint.from_coupling(7)
        checks["gluon_mass_point_c_property"] = (
            p1.c == complex(0.7, 0.0) and p2.c == complex(7 * 0.03, 0.0)
        )
    except Exception:
        checks["gluon_mass_point_c_property"] = False

    # 4. A path of bounded points is is_bounded=True, an escaping one is False
    try:
        bounded_path = MandelbrotPath([GluonMassPoint(0.0, 0.0),
                                        GluonMassPoint(-1.0, 0.0)])
        escaping_path = MandelbrotPath([GluonMassPoint(0.0, 0.0),
                                        GluonMassPoint(2.0, 0.0)])
        checks["path_bounded_vs_escaping"] = (
            bounded_path.is_bounded() and not escaping_path.is_bounded()
        )
    except Exception:
        checks["path_bounded_vs_escaping"] = False

    # 5. C-sequence diagnostic reports bounded vs escaping sequences
    try:
        bounded_seq = diagnose_C_convergence([0, 0, 0, 0])
        escaping_seq = diagnose_C_convergence([0, 30])  # 30*0.1 = 3.0 -> escapes
        checks["c_seq_diagnosis_distinguishes"] = (
            bounded_seq["all_bounded"]
            and not escaping_seq["all_bounded"]
            and "skip_fraction" in escaping_seq
        )
    except Exception:
        checks["c_seq_diagnosis_distinguishes"] = False

    # 6. Julia fiber VOA sector map sums to 1.0 (vacuum + excited = total)
    try:
        # Use a coarse 8x8 fiber to keep the test fast
        jf = JuliaFiber(c=0 + 0j, resolution=8)
        m = jf.VOA_sector_map(max_iter=9)
        total_frac = m["vacuum_fraction"] + m["excited_fraction"]
        checks["julia_fiber_sector_map_sums_to_one"] = (
            abs(total_frac - 1.0) < 1e-9
            and m["total_points"] == 64
        )
    except Exception:
        checks["julia_fiber_sector_map_sums_to_one"] = False

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    if passed == total:
        status = "pass"
    elif passed >= max(1, total // 2):
        status = "partial"
    else:
        status = "fail"

    return {
        "forge": "MandleForge",
        "status": status,
        "checks": checks,
        "passed": passed,
        "total": total,
        "paper": "CQE-paper-08 (Native K-max page, paper C-forms in M-set)",
    }