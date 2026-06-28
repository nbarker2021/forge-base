"""Sentinel VOA Partition Ratio Checker.

The VOA partition Z(q) = 2q^0 + 6q^5 provides the exact ratio of
invariant (2) to variable (6) components. This is the mathematical
law of any healthy system: 25% invariant, 75% variable.

When this ratio breaks, you have an anomaly — proven, not guessed.
"""

from .checker import VOAChecker, VOAResult, VOADeviationSeverity

__all__ = ["VOAChecker", "VOAResult", "VOADeviationSeverity"]
