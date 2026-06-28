"""
contribution_validators.py — F_2-deterministic governance gates for the
contributions registry.

Each validator takes (kind, key, value) and returns (accepted, rationale).
Validators must be deterministic: same input ⇒ same decision. The
rationale string is persisted with each accepted entry for audit.

Available validators
--------------------
    f2_arf                — accept iff value['arf'] matches a recomputation
                             of the F_2 quadratic form supplied in the key
    lucas_recurrence       — accept iff LucasBit(d, x) satisfies the
                             Pascal recurrence LucasBit(d, x) = LucasBit(d-1, x-1) XOR LucasBit(d-1, x+1)
    rule30_decomposition   — accept iff the decomposition of r30(N, 0) via
                             the linearization matches direct simulation
    f2_edge_glue           — accept iff two F_2 quadratic forms have
                             matching Arf invariants and the value field
                             reports glue=True
"""
from __future__ import annotations

from typing import Any

from .f2_majorana import F2Quadratic, can_glue_edges, rule30_correction_arf
from .rule90_linearization import lucas_bit, rule30_center_via_decomposition


def f2_arf_validator(kind: str, key: Any, value: Any) -> tuple[bool, str]:
    """Validate a proposed F_2 Arf invariant against the form in `key`."""
    if kind != "f2_arf":
        return False, f"kind mismatch (expected f2_arf, got {kind!r})"
    if not isinstance(key, dict) or "A" not in key:
        return False, "key must include matrix 'A'"
    try:
        q = F2Quadratic(key["A"])
        recomputed = q.arf_invariant()
    except Exception as exc:
        return False, f"failed to construct F2Quadratic: {exc}"
    if not isinstance(value, dict) or "arf" not in value:
        return False, "value must include 'arf'"
    if value["arf"] != recomputed:
        return False, (
            f"Arf mismatch: proposed value['arf']={value['arf']} but "
            f"recomputation gives {recomputed}"
        )
    return True, f"Arf invariant verified by recomputation: arf={recomputed}"


def lucas_recurrence_validator(
    kind: str, key: Any, value: Any
) -> tuple[bool, str]:
    """Validate a Lucas binomial mod 2 value against the Pascal recurrence
    that defines Rule 90: L(d, x) = L(d-1, x-1) XOR L(d-1, x+1)."""
    if kind != "lucas_term":
        return False, f"kind mismatch (expected lucas_term, got {kind!r})"
    if not isinstance(key, dict) or "d" not in key or "x" not in key:
        return False, "key must include 'd' and 'x'"
    d, x = key["d"], key["x"]
    if d < 1:
        return False, "recurrence requires d >= 1; check via direct lucas_bit"
    expected = lucas_bit(d, x)
    via_recur = lucas_bit(d - 1, x - 1) ^ lucas_bit(d - 1, x + 1)
    if expected != via_recur:
        return False, (
            f"Rule 90 recurrence violation at (d={d}, x={x}): "
            f"lucas_bit={expected}, recurrence={via_recur}"
        )
    if not isinstance(value, dict) or "bit" not in value:
        return False, "value must include 'bit'"
    if value["bit"] != expected:
        return False, (
            f"value['bit']={value['bit']} disagrees with lucas_bit={expected}"
        )
    return True, (
        f"Pascal recurrence verified at (d={d}, x={x}): "
        f"lucas_bit={expected} = lucas_bit(d-1,x-1) XOR lucas_bit(d-1,x+1)"
    )


def rule30_decomposition_validator(
    kind: str, key: Any, value: Any
) -> tuple[bool, str]:
    """Validate a Rule 30 center-bit claim at depth N via the linearization
    decomposition."""
    if kind != "rule30_center_bit":
        return False, f"kind mismatch (expected rule30_center_bit, got {kind!r})"
    if not isinstance(key, dict) or "N" not in key:
        return False, "key must include 'N'"
    N = key["N"]
    if N < 1:
        return False, "N must be >= 1"
    try:
        r = rule30_center_via_decomposition(N)
    except Exception as exc:
        return False, f"decomposition failed at N={N}: {exc}"
    if not r["match"]:
        return False, (
            f"decomposition disagrees with direct simulation at N={N}: "
            f"decomposed={r['decomposed_bit']} direct={r['direct_simulated_bit']}"
        )
    if not isinstance(value, dict) or "bit" not in value:
        return False, "value must include 'bit'"
    if value["bit"] != r["bit"]:
        return False, (
            f"proposed bit {value['bit']} disagrees with decomposition "
            f"{r['bit']} at N={N}"
        )
    return True, (
        f"Rule 30 center bit at N={N} verified via Rule 90 + correction "
        f"decomposition: bit={r['bit']} "
        f"(contributing terms: {r.get('contributing_terms', '?')})"
    )


def f2_edge_glue_validator(kind: str, key: Any, value: Any) -> tuple[bool, str]:
    """Validate an edge-gluing claim: two F_2 quadratic forms can glue iff
    their Arf invariants agree."""
    if kind != "f2_edge_glue":
        return False, f"kind mismatch (expected f2_edge_glue, got {kind!r})"
    if not isinstance(key, dict) or "left" not in key or "right" not in key:
        return False, "key must include 'left' and 'right' matrices"
    try:
        ql = F2Quadratic(key["left"])
        qr = F2Quadratic(key["right"])
    except Exception as exc:
        return False, f"failed to construct quadratic forms: {exc}"
    glue = can_glue_edges(ql, qr)
    if not isinstance(value, dict) or "can_glue" not in value:
        return False, "value must include 'can_glue'"
    if value["can_glue"] != glue["can_glue"]:
        return False, (
            f"proposed can_glue={value['can_glue']} disagrees with "
            f"Arf-based determination {glue['can_glue']} "
            f"(left_arf={glue['left_arf']}, right_arf={glue['right_arf']})"
        )
    return True, (
        f"edge-glue Arf comparison: left_arf={glue['left_arf']}, "
        f"right_arf={glue['right_arf']}, can_glue={glue['can_glue']}"
    )


def install_default_validators(registry) -> list[str]:
    """Install the four F_2-deterministic validators on a registry instance.
    Returns the list of validator names registered."""
    registry.register_validator("f2_arf", f2_arf_validator)
    registry.register_validator("lucas_recurrence", lucas_recurrence_validator)
    registry.register_validator(
        "rule30_decomposition", rule30_decomposition_validator
    )
    registry.register_validator("f2_edge_glue", f2_edge_glue_validator)
    return ["f2_arf", "lucas_recurrence", "rule30_decomposition", "f2_edge_glue"]
