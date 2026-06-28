"""Optional Tier B falsification wrappers (non-blocking; CONJ unchanged)."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from typing import Any


def _load_script_module(name: str, script_name: str):
    scripts = pathlib.Path(__file__).resolve().parents[2] / "scripts"
    path = scripts / script_name
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {script_name}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_tier_b(
    *,
    max_period: int = 128,
    sample_depth: int = 512,
    density_max_depth: int = 256,
) -> dict[str, Any]:
    period_mod = _load_script_module("lf_tier_b_period", "tier_b_period_search.py")
    density_mod = _load_script_module("lf_tier_b_density", "tier_b_density_estimate.py")
    period = period_mod.search_periods(max_period=max_period, sample_depth=sample_depth)
    density = density_mod.estimate_density(max_depth=density_max_depth)
    return {
        "tier": "B",
        "blocking": False,
        "honesty_invariant": "CONJ obligations unchanged; no status upgrades",
        "scripts": [period, density],
        "overall_status": "available",
    }
