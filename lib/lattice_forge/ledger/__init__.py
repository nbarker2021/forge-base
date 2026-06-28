"""Lattice Forge seed ledger.

A small, exact-arithmetic scaffold for treating root systems, morphisms,
admissibility edges, 24D destinations, and pariah boundary objects as an
executable ledger rather than disconnected mathematical facts.
"""

from .ledger import Ledger
from .build import build_seed_database

__all__ = ["Ledger", "build_seed_database"]
__version__ = "0.6.0"
