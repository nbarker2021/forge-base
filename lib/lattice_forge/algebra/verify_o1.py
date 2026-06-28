"""Optional SymPy cross-check for O(1) algebra constants (theory extra only)."""
from __future__ import annotations

import argparse

from lattice_forge.algebra.o1_registry import (
    E8_ROOT_COUNT,
    E8_WEYL_ORDER,
    WEYL_ORDER,
    root_count_ade,
    weyl_order,
)
from lattice_forge.ledger.roots import root_system_E8


def _local_checks() -> list[str]:
    errors: list[str] = []
    e8 = root_system_E8()
    built_count = len(e8.roots)
    if built_count != E8_ROOT_COUNT:
        errors.append(f"E8 root count: registry={E8_ROOT_COUNT} built={built_count}")
    if root_count_ade("E", 8) != E8_ROOT_COUNT:
        errors.append("root_count_ade(E,8) mismatch")
    if weyl_order("E8") != E8_WEYL_ORDER:
        errors.append("weyl_order(E8) mismatch")
    return errors


def _sympy_checks() -> tuple[list[str], bool]:
    errors: list[str] = []
    try:
        from sympy.liealgebras.weyl_group import WeylGroup
    except ImportError:
        return [], False

    for label, expected in WEYL_ORDER.items():
        series = label[0]
        rank = int(label[1:]) if len(label) > 1 else 1
        if series == "G":
            ct_label: str | list = "G2"
        elif series == "F":
            ct_label = "F4"
        elif series == "E":
            ct_label = ["E", rank]
        else:
            ct_label = f"{series}{rank}"
        got = int(WeylGroup(ct_label).group_order())
        if int(got) != expected:
            errors.append(f"Weyl order {label}: registry={expected} sympy={got}")
    return errors, True


def run_verify_o1(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lattice-forge-verify-algebra",
        description="Cross-check O(1) registry (optional SymPy via lattice-forge[theory])",
    )
    parser.parse_args(argv)

    sympy_errors, sympy_ran = _sympy_checks()
    errors = _local_checks() + sympy_errors
    if errors:
        for e in errors:
            print("FAIL:", e)
        return 1
    suffix = " + SymPy" if sympy_ran else " (SymPy skipped; pip install lattice-forge[theory])"
    print("PASS: O(1) registry matches built roots" + suffix)
    return 0


def main() -> int:
    return run_verify_o1()
