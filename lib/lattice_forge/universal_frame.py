"""
universal_frame.py — compatibility shim.

The canonical implementation is binary_boundary_adapter.py.
This module re-exports everything under the original names so existing
imports continue to work.
"""

from .binary_boundary_adapter import (
    adapt as frame,
    adapt,
    print_adaptation as print_frame,
    print_adaptation,
    from_bytes,
    from_hex,
    from_int,
    from_file,
    cascade_level,
    emission_level,
    rules_consistent_with,
    BinaryBoundaryAdapter,
    CIRCLE_F,
    CIRCLE_P,
    CORRECTION_FIRING,
    _to_bits,
    _emit as _t_emission,
)

__all__ = [
    "frame", "adapt", "print_frame", "print_adaptation",
    "from_bytes", "from_hex", "from_int", "from_file",
    "cascade_level", "emission_level", "rules_consistent_with",
    "BinaryBoundaryAdapter",
    "CIRCLE_F", "CIRCLE_P", "CORRECTION_FIRING",
    "_to_bits",
]
