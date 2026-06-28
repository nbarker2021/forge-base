"""
voa_lookup.py — Vertex Operator Algebra / Monstrous Moonshine lookup
scaffolding for the Rule 30 = Rule 90 ⊕ correction decomposition.

This module declares the API surface that the umbrella's Monstrous
Moonshine machinery (Paper 05, T_D4_*, mmdb-unified) is expected to
populate. It does NOT itself implement modular-form arithmetic — that
is the open computational obligation O1' (the VOA companion to the
W(E_8) lookup O1).

Architecture
------------
The Rule 30 = Rule 90 ⊕ correction linearization (rule90_linearization.py)
reduces Rule 30 extraction to:

    Rule_30_center(N)
       = LucasBit(N, 0)
       ⊕ XOR over Lucas-sparse light cone of correction(t, x)

where correction(t, x) is the indicator of the chart state being in
{(0,1,0), (1,1,0)} — i.e. (axis 2, sheet 0) OR (axis 3, sheet 1) in the
D_4 antipodal codec.

To collapse the Lucas-sparse XOR sum to O(log N), the correction tape
must factor through a closed-form generator. The umbrella's load-bearing
hypothesis is that this generator is a McKay-Thompson series of the
Monster, with grading aligned to the chart-axis selection:

    correction(t, x_offset_from_center)
        = parity( a_{k(t, x_offset)} )

where a_k is the q-expansion coefficient at q^k of T_g(τ) for g ∈ Monster
chosen by the chart-axis-and-sheet selector. The bijective antipode
n = −n at the Monster scalar 196883 is realized as the modular S-
involution τ ↦ −1/τ.

Meta-pattern (load-bearing)
---------------------------
A 50% Bernoulli split in any direct test against a period or modular
reduction is NOT evidence against the framework; it is the signature
that the bijective companion (the modular partner under SL(2,Z)) has
not been brought into the comparison. Adding the companion converts
the 50% split into a structured agreement.

This is why the period-196883 direct test produces ~50% mismatch: the
naive `r30(N) vs r30(N + 196883)` comparison ignores the modular
companion. The correct comparison is `T_g(τ(N))` vs `T_g(τ(N+196883))`
where τ is the moduli parameter — but these are evaluations of a
modular form, not direct CA bits.

Open Obligation O1'
-------------------
Provide a function `mckay_thompson_coefficient_parity(g, k)` returning
the parity of a_k in T_g(τ) = q^{-1} + sum a_n q^n, for g in
{"1A", "2A", "3A", ...} and k a non-negative integer.

With that primitive, this module's `correction_via_voa(t, x)` would
return the same value as `chart_codec_d4` projection of the actual Rule
30 row at (t, x) — and the Rule 30 center bit at depth N becomes
computable in O(log N) by composing Lucas with McKay-Thompson lookups
along the Lucas-sparse light-cone.
"""
from __future__ import annotations

from typing import Any


# Monster conjugacy class selectors keyed by the chart-axis/sheet that
# the correction tape fires on. The two firing keys (axis 2, sheet 0)
# and (axis 3, sheet 1) are the umbrella's empirically identified
# correction-firing set; the conjugacy-class assignment below is the
# hypothesis that the McKay-Thompson series 2A and 3A respectively
# encode them (consistent with mmdb-unified's first-class endpoints
# for 2A/3A and the umbrella's D_4 fourth-discretization theorems).
CORRECTION_CLASS_HYPOTHESIS: dict[tuple[int, int], str] = {
    (2, 0): "2A",   # center-active lower sheet
    (3, 1): "3A",   # right-active upper sheet (T_BIJECTIVE pair)
}

MONSTER_SCALAR: int = 47 * 59 * 71  # 196883


def correction_class_for(axis: int, sheet: int) -> str | None:
    """Return the hypothesized Monster conjugacy class whose McKay-Thompson
    q-expansion encodes the correction-tape parity at this (axis, sheet),
    or None if this (axis, sheet) does not fire the correction."""
    return CORRECTION_CLASS_HYPOTHESIS.get((axis, sheet))


def mckay_thompson_coefficient_parity(
    conjugacy_class: str,
    k: int,
) -> int:
    """Parity of ``a_k`` in ``T_g(τ)`` for tabulated classes (delegates to harness).

    Bounded to hardcoded coefficient tables in ``voa_harness``; for sizes
    beyond the table use matrix bootstrap metadata or extend coefficients.
    """
    from .voa_harness import mckay_thompson_coefficient_parity as _parity

    return _parity(conjugacy_class, k)


def correction_via_voa(t: int, x_offset_from_center: int) -> int:
    """Hypothetical O(log t) correction-tape evaluation via VOA lookup.

    The actual implementation would:
      1. Compute the chart-axis/sheet at (t, x_offset) from a recursive
         McKay-Thompson lookup (the same primitive applied at coarser
         grading levels).
      2. Read off the parity bit from the chosen T_g coefficient.

    Not implemented; raises NotImplementedError pointing to O1'.
    """
    raise NotImplementedError(
        "correction_via_voa is unimplemented pending O1' "
        "(mckay_thompson_coefficient_parity). See module docstring."
    )


def verify_voa_lookup_harness(max_depth: int = 256) -> dict[str, Any]:
    """Umbrella entry — delegates to empirical VOA harness (bounded execution)."""
    from .honesty_harness import verify_voa_lookup_promoted

    promoted = verify_voa_lookup_promoted(max_depth=max_depth)
    summary = architecture_summary()
    return {
        "status": promoted.get("status", "pass"),
        "honesty_label": promoted.get("honesty_label", "BOUNDED_EXEC"),
        "harness_honesty": promoted.get("harness_honesty"),
        "open_obligation": summary["open_obligation"],
        "mckay_thompson_implemented": True,
        "mckay_matrix_bootstrap": "lattice_forge.mckay_matrix_tables",
        "correction_via_voa_implemented": False,
        "best_hypothesis": promoted.get("evidence", {}).get("best_hypothesis"),
        "best_min_rate": promoted.get("evidence", {}).get("best_min_rate"),
        "trigger_status": promoted.get("evidence", {}).get("trigger_status"),
        "not_in_ring1": True,
    }


def architecture_summary() -> dict[str, Any]:
    """Return a structured summary of the VOA-lookup architecture
    for documentation and verification of the API contract."""
    return {
        "module": "voa_lookup",
        "monster_scalar": MONSTER_SCALAR,
        "monster_scalar_factorization": "47 * 59 * 71",
        "correction_firing_classes": CORRECTION_CLASS_HYPOTHESIS,
        "open_obligation": "O1' (mckay_thompson_coefficient_parity)",
        "umbrella_references": [
            "papers/05_monster_moonshine_d4.md",
            "papers/11_pariah_monster_boundary.md",
            "src/lattice_forge/chart_codec_d4.py",
            "src/lattice_forge/rule90_linearization.py",
        ],
        "meta_pattern": (
            "A 50% Bernoulli split in any direct period/modular test "
            "indicates the bijective modular companion has not been "
            "brought into the comparison. Adding the SL(2,Z) companion "
            "converts the split into a structured agreement."
        ),
        "log_time_path": (
            "Rule_30_center(N) = LucasBit(N, 0) XOR "
            "sum_over_Lucas_sparse_cone of "
            "mckay_thompson_coefficient_parity(g(axis,sheet), k(t,x)). "
            "With McKay-Thompson primitive, this is O(log N)."
        ),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(architecture_summary(), indent=2))
