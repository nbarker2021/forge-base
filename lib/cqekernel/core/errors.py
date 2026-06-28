"""Kernel error hierarchy."""


class CQEError(Exception):
    """Root of the CQE kernel exception tree."""


class KernelPolicyError(CQEError):
    """Raised when a request violates the active policy."""


class AdmissionError(CQEError):
    """Raised when the asymmetric admissibility gate refuses a candidate."""


class ReplayMismatch(CQEError):
    """Raised when a replay hash does not match its recorded value."""


class FirmwareUnavailable(CQEError):
    """Raised when an optional firmware module is requested but not installed."""
