"""
PixelForge BlotLift — 4D geometry -> 3D via an 8D moderation layer.

The algebraic fact this leans on is the standard D4 + D4 sublattice of E8
(E8 contains D8 at index 1 as the even-coordinate-sum sublattice of Z^8, and
D4 (+) D4 sits inside D8 block-diagonally; this is textbook lattice theory,
not a new claim here). Concretely: R^4 (+) R^4 = R^8 is just concatenation,
so any 4D point paired with a second 4D "moderation" vector lands in the
same 8D space `projection.py` already projects to 3D/screen for E8 states.
Nothing about `PROJECTIONS` changes — this module only supplies the lift
*into* that 8D space; projecting back down reuses `project`/`to_screen`
unchanged.

Why a *pair* of 4-vectors instead of one padded 4-vector: padding with
zeros throws the second half of the projection matrices away for nothing.
That is also why both vectors are required arguments here with no
default: this module makes no assumption about what "moderation" means;
that decision belongs to the caller (see SplatForge.vignette4d for the
GBS-specific one).

A "just default the moderation vector to mean4's antipode" attempt was
tried and reverted in this same slice. The corpus uses "antipode" for at
least three genuinely different operations depending on what's being
antipoded and at what layer: `cqe/hypervisor.py`'s `D4Token.antipode =
1 - pode` (per-bit complement of a representative); `centroid_voa.py`'s
`gluon`/`swap_LR` (swaps the *outer* two of an (L,C,R) triple, *holds C
fixed* — proven invariant: Γ(s) = C under this specific operation);
`chart_codec_d4.ANTIPODAL_LABEL` (full bitwise complement of a whole
triple, C flips too). None of these is "the" antipode in general — which
one applies depends on what the current C is holding and the Lucas
correction in force at that scale (`correction(t, x)` in
`lattice_forge/rule90_linearization.py`, the same mechanism already
driving `genesis_correction_density` elsewhere in this build). A generic
4D-lift module has no way to know that context, so it must not guess one
default for every caller — `antipode4` below is kept as a named,
documented utility (the D4Token-style full-negation case) for a caller
that has already determined that's the right one for its own context,
not as this module's own default.

Covariance projects by the same congruence rule 3DGS itself uses to take a
3D Gaussian's covariance to 2D screen space (EWA splatting: Sigma' = M Sigma
M^T) — this module just applies it one dimension higher, 8D -> 3D. Only the
projected diagonal (axis-aligned variance) is returned, matching
GaussianSplatInstance.covariance_or_scale's current 3-tuple shape; the full
3x3 off-diagonal terms are dropped (documented, not silently lost — see
`project_blot4d`'s docstring).

This is a CPU graphics-mapping utility for GS-07 (4D vignette playback)'s
algebraic-mapping prerequisite. It does not implement GPU playback, does
not implement `VignetteState.reconstruction_test`'s full obligation, and
makes no claim beyond: "this is a documented, reproducible linear map."

Stdlib only, no numpy — matches the rest of PixelForge.
"""
from __future__ import annotations

from typing import Dict, Sequence, Tuple

from PixelForge.projection import PROJECTIONS, digital_root, entropy, parity, project, to_screen

Vec4 = Tuple[float, float, float, float]
Mat4 = Tuple[Vec4, Vec4, Vec4, Vec4]
Vec8 = Tuple[float, float, float, float, float, float, float, float]
Mat8 = Tuple[Vec8, Vec8, Vec8, Vec8, Vec8, Vec8, Vec8, Vec8]


def antipode4(v4: Sequence[float]) -> Vec4:
    """The antipode of a real-valued 4-vector: negation through the
    origin — the continuous-domain generalization of D4Token's
    `antipode = 1 - pode` bit-flip (a reflection through 0.5 for a bit in
    {0,1} is the same operation as a reflection through 0 for an unbounded
    real value, just recentered)."""
    if len(v4) != 4:
        raise ValueError("antipode4 requires a length-4 vector")
    return tuple(-float(x) for x in v4)  # type: ignore[return-value]


def lift_pair(p4: Sequence[float], q4: Sequence[float]) -> Vec8:
    """R^4 (+) R^4 -> R^8 by concatenation. The D4+D4-in-E8 block-diagonal
    embedding, applied to mean vectors (no second-moment structure)."""
    if len(p4) != 4 or len(q4) != 4:
        raise ValueError("lift_pair requires two length-4 vectors")
    return tuple(float(v) for v in (*p4, *q4))  # type: ignore[return-value]


def _block_diag4(a4x4: Sequence[Sequence[float]], b4x4: Sequence[Sequence[float]]) -> Mat8:
    """Block-diagonal stack of two 4x4 matrices into one 8x8. Off-diagonal
    blocks are exactly zero: the lift asserts no prior correlation between
    the primary 4D state and the moderation state."""
    if len(a4x4) != 4 or len(b4x4) != 4:
        raise ValueError("_block_diag4 requires two 4x4 matrices")
    rows = []
    for r in range(4):
        rows.append(tuple(float(v) for v in a4x4[r]) + (0.0, 0.0, 0.0, 0.0))
    for r in range(4):
        rows.append((0.0, 0.0, 0.0, 0.0) + tuple(float(v) for v in b4x4[r]))
    return tuple(rows)  # type: ignore[return-value]


def lift_blot_to_8d(
    mean4: Vec4,
    cov4: Mat4,
    moderation_mean4: Vec4,
    moderation_cov4: Mat4,
) -> Tuple[Vec8, Mat8]:
    """Lift one 4D blot (mean + 4x4 covariance) and a required moderation
    4-vector/covariance into one 8D mean + 8x8 covariance, ready for
    `projection.project`/`_project_covariance_diag`. No default — see this
    module's docstring for why a generic lift cannot guess one."""
    mean8 = lift_pair(mean4, moderation_mean4)
    cov8 = _block_diag4(cov4, moderation_cov4)
    return mean8, cov8


def _project_covariance_diag(cov8: Mat8, kind: str = "standard") -> Tuple[float, float, float]:
    """diag(M Sigma M^T) for the 3x8 projection matrix M = PROJECTIONS[kind].
    Same congruence rule EWA splatting uses for 3D->2D; applied 8D->3D here.
    Off-diagonal (cross-axis) terms of the true 3x3 result are dropped — this
    is an axis-aligned simplification, matching the isotropic-scale shape
    `GaussianSplatInstance.covariance_or_scale` already uses everywhere
    else in SplatForge today."""
    m = PROJECTIONS.get(kind, PROJECTIONS["standard"])
    out = []
    for i in range(3):
        mi = m[i]
        acc = 0.0
        for j in range(8):
            mij = mi[j]
            if mij == 0.0:
                continue
            row = cov8[j]
            acc += mij * sum(row[k] * mi[k] for k in range(8))
        out.append(acc)
    return (out[0], out[1], out[2])


def project_blot4d(
    mean4: Vec4,
    cov4: Mat4,
    moderation_mean4: Vec4,
    moderation_cov4: Mat4,
    kind: str = "standard",
) -> Dict[str, object]:
    """Full record: lift the 4D blot through the 8D moderation layer and
    project to 3D + logical screen, the 4D/8D analogue of
    `projection.project_state`. Returns the projected mean, the projected
    (axis-aligned) covariance diagonal, and the same governance scalars
    `project_state` reports, computed on the lifted 8D mean for parity.
    Both moderation arguments are required — no default; see this module's
    docstring for why one cannot be guessed generically."""
    mean8, cov8 = lift_blot_to_8d(mean4, cov4, moderation_mean4, moderation_cov4)
    p3 = project(mean8, kind)
    lx, ly, depth = to_screen(p3)
    cov3_diag = _project_covariance_diag(cov8, kind)
    return {
        "mean4": [round(v, 6) for v in mean4],
        "moderation_mean4": [round(v, 6) for v in moderation_mean4],
        "mean8": [round(v, 6) for v in mean8],
        "p3": [round(v, 6) for v in p3],
        "screen": [round(lx, 6), round(ly, 6)],
        "depth": round(depth, 6),
        "covariance_diag_3d": [round(v, 6) for v in cov3_diag],
        "projection": kind if kind in PROJECTIONS else "standard",
        "digital_root": digital_root(sum(mean8)),
        "parity": parity(mean8),
        "entropy": entropy(mean8),
    }
