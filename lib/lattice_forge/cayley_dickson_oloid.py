"""Cayley-Dickson/Oloid normal form for CMPLX-R30.

User rule encoded here:

* Enumerated `N` resolves with its antipode `-N`.
* The Oloid generative is indexed by `N + 1` Cayley-Dickson doubling.
* Extension sheets repeat the same terminal pattern as the first sheet.
* The network grows as `1 + 8 + 8 + 1` until the observing device reaches its
  terminal energy budget.

This module is a normal-form generator. It does not claim that the generated
form alone predicts a Rule 30 center bit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


CAYLEY_DICKSON_SHEET_PATTERN: tuple[int, int, int, int] = (1, 8, 8, 1)
ROLE_PATTERN: tuple[str, str, str, str] = (
    "sheet_entry",
    "positive_octet",
    "negative_octet",
    "sheet_terminal",
)


@dataclass(frozen=True)
class CayleyDicksonOloidNormalForm:
    N: int
    antipode: int
    cayley_dickson_doubling_order: int
    podal_pair: tuple[int, int]
    network_weights: tuple[int, ...]
    total_network_weight: int
    terms: tuple[dict[str, Any], ...]
    honesty: str


def network_prefix(term_count: int) -> tuple[int, ...]:
    """Return the repeating `1,8,8,1` network prefix."""
    if term_count < 0:
        raise ValueError("term_count must be >= 0")
    return tuple(
        CAYLEY_DICKSON_SHEET_PATTERN[index % len(CAYLEY_DICKSON_SHEET_PATTERN)]
        for index in range(term_count)
    )


def cayley_dickson_oloid_normal_form(
    N: int,
    *,
    energy_terms: int = 16,
) -> CayleyDicksonOloidNormalForm:
    """Generate the CMPLX-R30 Cayley-Dickson/Oloid normal form for `N`.

    `energy_terms` is the observing-device terminal budget expressed as the
    number of network terms to materialize. The mathematical pattern is
    periodic; the budget controls how much of it is placed locally.
    """
    if N < 0:
        raise ValueError("N must be enumerated as a non-negative integer")
    if energy_terms < 0:
        raise ValueError("energy_terms must be >= 0")

    weights = network_prefix(energy_terms)
    terms = []
    for index, weight in enumerate(weights):
        local_index = index % len(CAYLEY_DICKSON_SHEET_PATTERN)
        sheet_index = index // len(CAYLEY_DICKSON_SHEET_PATTERN)
        terms.append(
            {
                "term_index": index,
                "sheet_index": sheet_index,
                "local_index": local_index,
                "weight": weight,
                "role": ROLE_PATTERN[local_index],
                "N": N,
                "antipode": -N,
                "cayley_dickson_doubling_order": N + 1,
                "extension_of_sheet_zero": sheet_index > 0 and local_index == 0,
            }
        )

    return CayleyDicksonOloidNormalForm(
        N=N,
        antipode=-N,
        cayley_dickson_doubling_order=N + 1,
        podal_pair=(N, -N),
        network_weights=weights,
        total_network_weight=sum(weights),
        terms=tuple(terms),
        honesty=(
            "normal_form_only: generates podal/antipodal Cayley-Dickson sheet "
            "placement; does not by itself prove nth-bit extraction"
        ),
    )


def verify_cayley_dickson_oloid_normal_form(max_n: int = 64, energy_terms: int = 16) -> dict[str, Any]:
    errors: list[str] = []
    for n in range(max_n + 1):
        form = cayley_dickson_oloid_normal_form(n, energy_terms=energy_terms)
        if form.antipode != -n:
            errors.append(f"N={n} antipode mismatch")
        if form.cayley_dickson_doubling_order != n + 1:
            errors.append(f"N={n} doubling order mismatch")
        if form.network_weights != network_prefix(energy_terms):
            errors.append(f"N={n} network prefix mismatch")
        for term in form.terms:
            expected_weight = CAYLEY_DICKSON_SHEET_PATTERN[term["local_index"]]
            if term["weight"] != expected_weight:
                errors.append(f"N={n} term {term['term_index']} weight mismatch")
    return {
        "status": "pass" if not errors else "fail",
        "max_n": max_n,
        "energy_terms": energy_terms,
        "pattern": CAYLEY_DICKSON_SHEET_PATTERN,
        "errors": errors,
    }
