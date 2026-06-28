"""Formal witness classification labels."""
from __future__ import annotations

from enum import Enum


class WitnessHonesty(str, Enum):
    PROVEN = "PROVEN"
    PASS_WITH_OPEN_GAPS = "pass_with_open_gaps"
    ENGINEERING = "engineering"
    CONJ = "CONJ"
    FAIL = "fail"


class WitnessKind(str, Enum):
    LEDGER = "ledger"
    REGIME_A = "regime_a"
    REGIME_C = "regime_c"
    REGIME_CPRIME = "regime_cprime"
    SYNDROME = "syndrome"
    MORPHONICS = "morphonics"
    PROOF_BUNDLE = "proof_bundle"
    PROOF_BUNDLE_FULL = "proof_bundle_full"
    UNCLASSIFIED = "unclassified"


HONEST_STATUSES = frozenset(
    {
        "pass",
        "pass_with_open_gaps",
        "fail",
        "available",
        "generated_canonical_composition_tree",
    }
)
