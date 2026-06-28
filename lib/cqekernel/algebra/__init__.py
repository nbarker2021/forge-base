"""
Kernel-side algebra primitives — octonion, J3O, F4/SU3 action.

This subpackage is a stdlib-only stub of
``lattice_forge.{octonion,jordan_j3,f4_action}``. When lattice_forge
is installed, the ``firmware.lattice_forge_bridge`` module routes
through the upstream implementations; otherwise the kernel uses
these classes as a complete local fallback.

The diff points against the upstream are:

  * the multiplication table signs (must match exactly)
  * the J3O Jordan product formula (symmetrized product)
  * the closed-form 8x8 Rule 30 transition matrix
  * the S3 permutation matrices on the 3-fundamental
  * the N3 / SU3 closure verifier (doubly-stochastic, symmetric)
"""

from .octonion import (
    Octonion,
    verify_octonion_axioms,
    CANONICAL_TABLE,
    FANO_TRIPLES,
)
from .jordan_j3 import J3O, verify_j3o_axioms
from .f4_action import (
    S3_PERMUTATION_NAMES,
    S3_PERMUTATIONS,
    s3_permutation_matrices,
    closed_form_rule30_8x8_transition,
    closed_form_shell2_3x3,
    verify_n3_su3_closure,
)

__all__ = [
    "Octonion", "verify_octonion_axioms", "CANONICAL_TABLE", "FANO_TRIPLES",
    "J3O", "verify_j3o_axioms",
    "S3_PERMUTATION_NAMES", "S3_PERMUTATIONS", "s3_permutation_matrices",
    "closed_form_rule30_8x8_transition", "closed_form_shell2_3x3",
    "verify_n3_su3_closure",
]
