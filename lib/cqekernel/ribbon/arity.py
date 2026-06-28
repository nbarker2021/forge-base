"""
Arity report module.

This is a thin re-export of the ``ArityReport`` and ``arity_report``
from ``slot.py``. It is a separate module because the spec lists it
as its own file in the file tree.
"""

from .slot import ArityReport, arity_report


__all__ = ["ArityReport", "arity_report"]
