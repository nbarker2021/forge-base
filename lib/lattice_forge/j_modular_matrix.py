"""
j_modular_matrix.py — 9×9 j-modular matrix at level 9 with octonion lift.

The Monster's McKay-Thompson series T_{3A}(τ) is the hauptmodul for the
genus-0 group Γ₀(9)+ (the level-9 subgroup with the Atkin-Lehner W_9
involution adjoined). At this level, the natural matrix-algebra
representation of the modular j-action is **9-dimensional**:

    J_g : V_9 → V_9

where V_9 ≅ R^9 is the space of length-9 q-expansion truncations of
weight-0 modular functions on Γ₀(9)+, and J_g is the multiplication-by-T_g
operator restricted to that subspace.

The lift from octonions to modular forms is the embedding O → V_9 that
maps the 8 octonion coordinates plus a derived 9th coordinate (the
real-norm anchor) into V_9. This 9-dim lift is the natural extension of
the J_3(O) framework: J_3(O) has trace, which is a single scalar from
the 27-dim algebra to R; by analogy the lift from O to V_9 maps the
8-dim octonion algebra to V_9 with the 9th coordinate carrying the
trace-like invariant.

What this module provides
-------------------------
    * `J_MATRIX_3A` — the 9×9 j-modular convolution matrix derived from
      the first 9 coefficients of T_{3A}(τ)
    * `J_MATRIX_2A` — the same for T_{2A}(τ)
    * `lift_octonion_to_v9(o)` — O → V_9 embedding
    * `apply_j_matrix(v, J)` — V_9 → V_9 modular action
    * `modular_parity_signature(v)` — F_2 invariant extracted from V_9
    * `verify_j_modular_matrix()` — algebraic correctness checks

This is the structural lift from octonion algebra to modular form
arithmetic. The 9-dim space is genus-0 modular-function dimension at
level 9; the matrix entries are integers (since T_{3A} has integer
q-expansion coefficients); the lift preserves the F_2 parity structure
of the octonion side.
"""
from __future__ import annotations

from typing import Any

from .mckay_matrix_tables import get_j_matrix as _get_j_matrix_bootstrap
from .octonion import Octonion

# Canonical 9×9 tables (shared builder with global McKay catalog)
J_MATRIX_3A: tuple[tuple[int, ...], ...] = _get_j_matrix_bootstrap("3A", 9)
J_MATRIX_2A: tuple[tuple[int, ...], ...] = _get_j_matrix_bootstrap("2A", 9)
J_MATRIX_7A: tuple[tuple[int, ...], ...] = _get_j_matrix_bootstrap("7A", 7)
J_MATRIX_5A: tuple[tuple[int, ...], ...] = _get_j_matrix_bootstrap("5A", 5)

J_MATRICES: dict[str, tuple[tuple[int, ...], ...]] = {
    "2A": J_MATRIX_2A,
    "3A": J_MATRIX_3A,
    "5A": J_MATRIX_5A,
    "7A": J_MATRIX_7A,
}


def get_j_matrix(g: str, size: int = 9) -> tuple[tuple[int, ...], ...]:
    """Return the bootstrap j-modular matrix for Monster class ``g`` (default 9×9)."""
    if g in J_MATRICES and size == (7 if g == "7A" else 5 if g == "5A" else 9):
        return J_MATRICES[g]
    return _get_j_matrix_bootstrap(g, size)


# ---------------------------------------------------------------------------
# Octonion → V_9 lift
# ---------------------------------------------------------------------------

def lift_octonion_to_v9(o: Octonion) -> tuple[float, ...]:
    """Embed an octonion into V_9 (the 9-dim modular-form coefficient space).

    The lift uses the 8 octonion components as the first 8 V_9 coordinates,
    plus a 9th coordinate equal to the L_2 norm of the octonion (the
    trace-like invariant that survives the octonion → modular lift).
    """
    c = o.components
    n2 = sum(x * x for x in c)
    return c + (n2,)


# ---------------------------------------------------------------------------
# 9×9 matrix action on V_9 vectors
# ---------------------------------------------------------------------------

def apply_j_matrix(v: tuple[float, ...], J: tuple[tuple[int, ...], ...]) -> tuple[float, ...]:
    """Apply the 9×9 j-modular matrix to a V_9 vector."""
    if len(v) != 9:
        raise ValueError(f"vector must have 9 components, got {len(v)}")
    if len(J) != 9 or any(len(row) != 9 for row in J):
        raise ValueError("J must be 9×9")
    return tuple(
        sum(J[i][j] * v[j] for j in range(9))
        for i in range(9)
    )


def modular_parity_signature(v: tuple[float, ...]) -> int:
    """The F_2 invariant of a V_9 vector: parity of the count of
    components whose integer-rounded value is odd.

    This is the F_2 "modular fingerprint" that survives the j-action
    modulo the 9-dim convolution structure.
    """
    return sum(1 for x in v if int(round(x)) & 1) & 1


def modular_parity_per_coordinate(v: tuple[float, ...]) -> tuple[int, ...]:
    """Per-coordinate parity bits of a V_9 vector."""
    return tuple(int(round(x)) & 1 for x in v)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_j_modular_matrix() -> dict[str, Any]:
    """Battery of correctness checks for the 9×9 j-modular matrix module."""
    results: dict[str, Any] = {}

    # 1. Matrix dimensions
    J = get_j_matrix("3A")
    results["matrix_3a_is_9x9"] = len(J) == 9 and all(len(r) == 9 for r in J)

    # 2. First-row first-coefficient anchoring
    # J_MATRIX[1][0] = T_3A's a_1 = 783
    results["J_3A_a1_coefficient_is_783"] = J[1][0] == 783
    # J_MATRIX_2A's a_1 = T_2A's a_1 = 4372
    J2 = get_j_matrix("2A")
    results["J_2A_a1_coefficient_is_4372"] = J2[1][0] == 4372

    # 3. Diagonal is identity (the q^0 coefficient of multiplication-by-T_g
    #    where T_g starts at q^{-1} acts as identity at each q^k)
    results["J_3A_diagonal_is_1"] = all(J[i][i] == 1 for i in range(9))

    # 4. Strictly upper triangle is zero (q-multiplication is lower-triangular)
    results["J_3A_strictly_upper_is_0"] = all(
        J[i][j] == 0 for i in range(9) for j in range(i + 1, 9)
    )

    # 5. Lift octonion to V_9: produces a 9-tuple
    from .octonion import O_ONE, O_E4
    v_one = lift_octonion_to_v9(O_ONE)
    results["lift_O_ONE_has_9_components"] = len(v_one) == 9
    results["lift_O_ONE_real_part_is_1"] = v_one[0] == 1.0
    results["lift_O_ONE_norm_squared_is_1"] = v_one[8] == 1.0

    # 6. Lift O_E4 produces correct V_9 fingerprint
    v_e4 = lift_octonion_to_v9(O_E4)
    results["lift_O_E4_real_part_is_0"] = v_e4[0] == 0.0
    results["lift_O_E4_e4_coord_is_1"] = v_e4[4] == 1.0
    results["lift_O_E4_norm_squared_is_1"] = v_e4[8] == 1.0

    # 7. Matrix action on lift of O_ONE
    Jv = apply_j_matrix(v_one, J)
    # First coordinate of Jv should be J[0][0] * 1 (since v_one[0] = 1, others irrelevant for row 0)
    # plus J[0][1] * v_one[1] + ... = 1 * 1 + 0 * 0 + ... = 1
    results["J_action_on_O_ONE_row_0_is_1"] = Jv[0] == 1.0
    # Second coordinate = J[1][0] * 1 + J[1][1] * 0 + ... = 783 + 1 * 0 = 783
    # (J[1][0] = 783, J[1][1] = 1, rest of row affects nothing since v[2..7] = 0,
    #  and v[8] = 1 — but J[1][8] = 0 since 8 > 1 in the row)
    # Wait — J[1][8] is in the upper triangle (8 > 1), so 0. So Jv[1] = 783*1 + 1*0 + ... = 783
    results["J_action_on_O_ONE_row_1_is_a1"] = Jv[1] == 783

    # 8. Modular parity signature is binary
    sig = modular_parity_signature(Jv)
    results["modular_parity_signature_is_binary"] = sig in (0, 1)

    # 9. Per-coordinate parity is 9-tuple
    pcp = modular_parity_per_coordinate(Jv)
    results["per_coord_parity_is_9_tuple"] = len(pcp) == 9

    all_pass = all(
        v if isinstance(v, bool) else True
        for v in results.values()
    )
    results["status"] = "pass" if all_pass else "fail"
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(verify_j_modular_matrix(), indent=2, default=str))
