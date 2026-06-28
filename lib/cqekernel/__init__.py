"""
cqekernel — stdlib-only CQE/CMPLX source-bound C-form runtime.

No external dependencies. Every operation is treated as an observation
that produces a canonical 4-bit carrier, a local L/C/R Gluon state, an
asymmetric admissibility split, correction-surface receipts, an 8-slot
ribbon, observer-frame obligations, and replayable proof ledger entries.

Optional math firmware may attach higher lattice, Jordan, F4, D12, oloid,
or Moonshine receipts, but the kernel itself remains dependency-free and
never promotes those layers without explicit evidence status.
"""

# Identity chain (declared 2026-06-24)
#
# The repo is the typed surface of the full identity chain. The chain
# is three layers; this package implements the middle one.
#
#   CQEEngine   - Cartan Quadratic Equivalence: the algebraic substrate
#                 (LCR triples, Rule 30, D4 tokens, E8, J3(O), Leech).
#                 This is the math.
#
#   LCRKernel   - the typed-kernel surface: three lanes (L/C/R) with
#                 strict-by-default policy enforcement. This package.
#                 The print-and-play universal CEM for any task.
#
#   CMPLX-1T    - the product line / brand. Pronounced "Complexity."
#                 CMPLX = compression of state into a micro-form
#                 representation; 1T = the additive nature + 1 Time,
#                 the input and output as a time arrow. Brand promise:
#                 reducing complexity by additive simplicity.
#
# See IDENTITY.md at the repo root for the full chain with citations.
__version__ = "0.1.0"
__identity_chain__ = ("CQEEngine", "LCRKernel", "CMPLX-1T")
__substrate__ = "CQEEngine"
__kernel__ = "LCRKernel"
__product__ = "CMPLX-1T"
__brand__ = "CMPLX-1T"
__brand_spoken__ = "Complexity"
__brand_promise__ = "reducing complexity by additive simplicity"

from .core.request import ObservedRequest, RequestMode
from .core.errors import (
    CQEError,
    KernelPolicyError,
    AdmissionError,
    ReplayMismatch,
    FirmwareUnavailable,
)
from .core.status import (
    EvidenceStatus,
    ReceiptStatus,
    AdmissionClass,
    ObligationStatus,
)
from .core.policy import Policy
from .core.kernel import Kernel, ObservationResult

__all__ = [
    "ObservedRequest",
    "RequestMode",
    "CQEError",
    "KernelPolicyError",
    "AdmissionError",
    "ReplayMismatch",
    "FirmwareUnavailable",
    "EvidenceStatus",
    "ReceiptStatus",
    "AdmissionClass",
    "ObligationStatus",
    "Policy",
    "Kernel",
    "ObservationResult",
    "__version__",
    "__identity_chain__",
    "__substrate__",
    "__kernel__",
    "__product__",
    "__brand__",
    "__brand_spoken__",
    "__brand_promise__",
]
