"""Prize-core falsification CLI hooks."""

from lattice_forge.falsify.tier_a import run_tier_a, tier_a_break_specs, tier_a_breaks
from lattice_forge.falsify.tier_b import run_tier_b

__all__ = ["run_tier_a", "run_tier_b", "tier_a_break_specs", "tier_a_breaks"]
