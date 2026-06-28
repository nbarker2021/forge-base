"""Per-claim empirical testing platforms for exhaustive proofing."""

from lattice_forge.empirical.manifest import load_platform_manifest
from lattice_forge.empirical.runner import run_claim_platform, run_empirical_matrix

__all__ = ["load_platform_manifest", "run_claim_platform", "run_empirical_matrix"]
