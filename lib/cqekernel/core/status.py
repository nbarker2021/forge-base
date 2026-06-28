"""
Evidence and receipt status enums.

These are first-class governance: every receipt carries an
``EvidenceStatus`` and a ``ReceiptStatus``. The kernel never silently
promotes a claim to a higher evidence class than the receipts support.
"""

from __future__ import annotations

from enum import Enum


class KernelPolicyError(Exception):
    """Raised when a kernel operation violates the active policy."""
    pass


class EvidenceStatus(Enum):
    """How strongly a piece of evidence supports the claim it is attached to."""

    KERNEL_PRIMITIVE = "kernel_primitive"      # machine-checked local primitive
    BOUNDED_EXEC = "bounded_exec"              # bounded executable harness
    LOOKUP_BACKED = "lookup_backed"            # looked up in trusted table
    FIRMWARE_BACKED = "firmware_backed"        # produced by an external firmware
    SPEC_ONLY = "spec_only"                    # surface only, no execution
    CONJ = "conj"                              # conjectural bridge
    EXTERNAL_REQUIRED = "external_required"    # needs an external verifier
    PASS_WITH_OPEN_GAPS = "pass_with_open_gaps"
    WORKBOOK_BACKED = "workbook_backed"        # analog workbook protocol


class ReceiptStatus(Enum):
    """Disposition of a single receipt."""

    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    DEFERRED = "DEFERRED"
    PASS_WITH_OPEN_GAPS = "PASS_WITH_OPEN_GAPS"


class AdmissionClass(Enum):
    """Outcome of the asymmetric admissibility gate."""

    ADMITTED = "ADMITTED"
    BOUNDARY = "BOUNDARY"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"
    DEFERRED = "DEFERRED"


class ObligationStatus(Enum):
    """Lifecycle of an obligation."""

    OPEN = "OPEN"
    BLOCKED = "BLOCKED"
    DEFERRED = "DEFERRED"
    SATISFIED = "SATISFIED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


__all__ = [
    "EvidenceStatus",
    "ReceiptStatus",
    "AdmissionClass",
    "ObligationStatus",
    "KernelPolicyError",
]