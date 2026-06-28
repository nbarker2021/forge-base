"""
Kernel-side CQE primitives — D4 tokens, ribbon receipts, and the
managed-ribbon / light-cone facade objects.

This subpackage is a stdlib-only stub of ``lattice_forge.cqe``.
When lattice_forge is installed, the ``firmware.lattice_forge_bridge``
module routes through the upstream implementations; otherwise the
kernel uses these classes as a complete local fallback.
"""

from .d4_token import D4Token, tokens_from_bits

__all__ = ["D4Token", "tokens_from_bits"]
