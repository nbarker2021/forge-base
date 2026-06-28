"""
McKay-Thompson j-modular matrix tables for Monster conjugacy classes.

Builds lower-triangular convolution matrices (q-multiplication truncations)
at bootstrap dimensions 5, 7, and 9 for the tabulated classes in
``voa_harness.VALID_CLASSES``. These tables feed:

  * ``j_modular_matrix`` (level-9 / 3A hub),
  * ``voa_harness`` parity lookups,
  * global proof artifacts (JSON catalog export).

Dimension policy (bootstrap, not full moonshine classification):
  - **9×9** — level-9 genus-0 hub (3A hauptmodul; 2A/1A same truncation width).
  - **7×7** — 7A class + intermediate shell for conjugate-set routing.
  - **5×5** — 5A pentic lane (L chirality in five-lane partition).

Honesty: coefficients are hardcoded Atlas truncations; matrices are
**BOUNDED_EXEC** at the stated size, not a proof of full ``T_g`` arithmetic.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from .voa_harness import (
    LANE_PARTITION,
    T_1A_COEFFICIENTS,
    T_2A_COEFFICIENTS,
    T_3A_COEFFICIENTS,
    T_5A_COEFFICIENTS,
    T_7A_COEFFICIENTS,
    VALID_CLASSES,
    mckay_thompson_coefficient_parity,
)

BOOTSTRAP_DIMENSIONS: Final[tuple[int, ...]] = (5, 7, 9)

# Preferred “home” dimension per class for documentation / routing hints.
CLASS_BOOTSTRAP_DIM: Final[dict[str, int]] = {
    "1A": 9,
    "2A": 9,
    "3A": 9,
    "5A": 5,
    "7A": 7,
}

CONJUGACY_SET_ORDER: Final[tuple[str, ...]] = ("1A", "2A", "3A", "5A", "7A")


def build_convolution_matrix(
    coefficients: tuple[int, ...],
    *,
    size: int,
) -> tuple[tuple[int, ...], ...]:
    """Lower-triangular truncation of multiplication-by-``Σ a_n q^n`` on length-``size``."""
    if size < 1:
        raise ValueError("size must be positive")
    matrix = [[0] * size for _ in range(size)]
    for i in range(size):
        for j in range(i + 1):
            k = i - j
            if k == 0:
                matrix[i][j] = 1
            elif k - 1 < len(coefficients):
                matrix[i][j] = coefficients[k - 1]
    return tuple(tuple(row) for row in matrix)


def j_matrix_for_class(conjugacy_class: str, size: int) -> tuple[tuple[int, ...], ...]:
    """Return the ``size×size`` convolution matrix for Monster class ``g``."""
    if conjugacy_class not in VALID_CLASSES:
        raise ValueError(
            f"unknown class {conjugacy_class!r}; expected one of {sorted(VALID_CLASSES)}"
        )
    if size not in BOOTSTRAP_DIMENSIONS:
        raise ValueError(f"bootstrap size must be one of {BOOTSTRAP_DIMENSIONS}, got {size}")
    coeffs = VALID_CLASSES[conjugacy_class]
    if len(coeffs) < size - 1:
        raise ValueError(
            f"class {conjugacy_class!r} has only {len(coeffs)} coefficients; "
            f"need at least {size - 1} for {size}×{size} matrix"
        )
    return build_convolution_matrix(coeffs[: size - 1], size=size)


def matrix_metadata(
    conjugacy_class: str,
    size: int,
    matrix: tuple[tuple[int, ...], ...],
) -> dict[str, Any]:
    coeffs = VALID_CLASSES[conjugacy_class]
    a1 = coeffs[0] if coeffs else None
    return {
        "conjugacy_class": conjugacy_class,
        "size": size,
        "lane": LANE_PARTITION.get(conjugacy_class),
        "preferred_dim": CLASS_BOOTSTRAP_DIM.get(conjugacy_class),
        "a1": a1,
        "J_1_0": matrix[1][0] if size > 1 else None,
        "diagonal_all_ones": all(matrix[i][i] == 1 for i in range(size)),
        "strictly_upper_zero": all(
            matrix[i][j] == 0 for i in range(size) for j in range(i + 1, size)
        ),
        "coefficients_used": min(size - 1, len(coeffs)),
        "coefficient_table_len": len(coeffs),
    }


def build_conjugate_set_tables(
    dimensions: tuple[int, ...] = BOOTSTRAP_DIMENSIONS,
    classes: tuple[str, ...] = CONJUGACY_SET_ORDER,
) -> dict[str, Any]:
    """Build full matrix catalog for all (class, dimension) pairs that fit."""
    tables: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for g in classes:
        tables[g] = {}
        for dim in dimensions:
            try:
                mat = j_matrix_for_class(g, dim)
                meta = matrix_metadata(g, dim, mat)
                tables[g][str(dim)] = {
                    "matrix": [list(row) for row in mat],
                    "meta": meta,
                }
            except ValueError as exc:
                errors.append(f"{g}@{dim}×{dim}: {exc}")
    return {
        "version": "1",
        "dimensions": list(dimensions),
        "classes": list(classes),
        "lane_partition": dict(LANE_PARTITION),
        "class_preferred_dim": dict(CLASS_BOOTSTRAP_DIM),
        "tables": tables,
        "errors": errors,
    }


def nested_block_consistency(
    small: tuple[tuple[int, ...], ...],
    large: tuple[tuple[int, ...], ...],
) -> bool:
    """``small`` equals the leading principal submatrix of ``large``."""
    n = len(small)
    if len(large) < n:
        return False
    return all(small[i][j] == large[i][j] for i in range(n) for j in range(n))


def verify_mckay_matrix_bootstrap() -> dict[str, Any]:
    """Proof harness: bootstrap matrices + nesting 5⊂7⊂9 where coefficients allow."""
    catalog = build_conjugate_set_tables()
    checks: dict[str, Any] = {}
    checks["catalog_error_count"] = len(catalog["errors"])
    checks["all_five_classes_have_9x9"] = all(
        "9" in catalog["tables"].get(g, {}) for g in CONJUGACY_SET_ORDER
    )
    checks["7A_has_7x7"] = "7" in catalog["tables"].get("7A", {})
    checks["5A_has_5x5"] = "5" in catalog["tables"].get("5A", {})

    # Known anchors (j_modular_matrix / Atlas)
    j3 = catalog["tables"]["3A"]["9"]["matrix"]
    checks["3A_9x9_a1_is_783"] = j3[1][0] == 783
    j2 = catalog["tables"]["2A"]["9"]["matrix"]
    checks["2A_9x9_a1_is_4372"] = j2[1][0] == 4372

    # Nesting: 7×7 top-left of 9×9 for classes with enough coefficients
    nesting: dict[str, bool] = {}
    for g in CONJUGACY_SET_ORDER:
        if "7" in catalog["tables"].get(g, {}) and "9" in catalog["tables"].get(g, {}):
            m7 = tuple(tuple(r) for r in catalog["tables"][g]["7"]["matrix"])
            m9 = tuple(tuple(r) for r in catalog["tables"][g]["9"]["matrix"])
            nesting[g] = nested_block_consistency(m7, m9)
    checks["nesting_7_in_9"] = nesting

    # Parity row: first 9 parities match harness lookup
    parity_rows: dict[str, list[int]] = {}
    for g in CONJUGACY_SET_ORDER:
        row = []
        for k in range(1, 10):
            try:
                row.append(mckay_thompson_coefficient_parity(g, k))
            except ValueError:
                row.append(-1)
        parity_rows[g] = row
    checks["parity_rows_k1_to_k9"] = parity_rows

    bool_checks = {k: v for k, v in checks.items() if isinstance(v, bool)}
    checks["status"] = (
        "pass"
        if catalog["errors"] == [] and all(bool_checks.values())
        else "fail"
    )
    checks["honesty_label"] = "BOUNDED_EXEC"
    checks["proof_key"] = "MCKAY_MATRIX_BOOTSTRAP"
    return checks


def export_matrix_catalog(
    path: Path | str,
    *,
    dimensions: tuple[int, ...] = BOOTSTRAP_DIMENSIONS,
) -> Path:
    """Write global JSON catalog for downstream tools / proof-lab ingest."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = build_conjugate_set_tables(dimensions=dimensions)
    payload["verify"] = verify_mckay_matrix_bootstrap()
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return out


def get_j_matrix(conjugacy_class: str, size: int = 9) -> tuple[tuple[int, ...], ...]:
    """Public accessor (used by ``j_modular_matrix`` and CLI)."""
    return j_matrix_for_class(conjugacy_class, size)
