"""Always-open CQE idempotent library cache.

The cache stores only bonded terms that can be recomputed by current package
modules. It is a convenience layer over the contributions registry, not a new
source of truth.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .chart_codec_d4 import ANTIPODAL_LABEL, CHART_STATES, SHEET_SIGN
from .contribution_validators import install_default_validators
from .contributions_registry import Registry
from .d12_action import D12_ELEMENTS, d12_acts_on_d4_state
from .forced_involution_cache import run_forced_involution_sweep
from .jordan_j3 import J3O


class CQEIdempotentLibCache:
    """SQLite-backed cache for exact CQE idempotent/bonded terms."""

    def __init__(self, path: str | Path = ".lattice_forge/cqe_idempotent_cache.sqlite") -> None:
        self.registry = Registry(path)
        install_default_validators(self.registry)
        self.registry.register_validator("d4_chart_idempotent", _validate_d4_chart_idempotent)
        self.registry.register_validator("forced_involution_orbit", _validate_forced_involution)
        self.registry.register_validator("d12_axis_action", _validate_d12_axis_action)

    def seed_core(self, max_rule30_depth: int = 16) -> dict[str, Any]:
        chart_results = [self._propose_chart_state(state) for state in CHART_STATES]
        forced_results = [
            self._propose_forced_involution(name, pattern)
            for name, pattern in _forced_involution_expected().items()
        ]
        d12_results = [
            self._propose_d12_axis_action(element, (axis, sheet))
            for element in D12_ELEMENTS
            for axis in range(4)
            for sheet in range(2)
        ]
        rule30_results = [
            self._propose_rule30_depth(depth)
            for depth in range(1, max_rule30_depth + 1)
        ]
        all_results = chart_results + forced_results + d12_results + rule30_results
        accepted_or_present = sum(
            1 for result in all_results if result["status"] in {"accepted", "already_present"}
        )
        return {
            "status": "seeded",
            "chart_terms": len(chart_results),
            "forced_involution_terms": len(forced_results),
            "d12_axis_terms": len(d12_results),
            "rule30_depth_terms": len(rule30_results),
            "accepted_or_present": accepted_or_present,
            "registry": self.stats(),
        }

    def lookup_chart_state(self, state: tuple[int, int, int]) -> dict[str, Any] | None:
        return self.registry.lookup("d4_chart_idempotent", {"state": list(state)})

    def lookup_rule30_depth(self, depth: int) -> dict[str, Any] | None:
        return self.registry.lookup("rule30_center_bit", {"N": depth})

    def lookup_d12_axis_action(
        self,
        element: tuple[int, int],
        state: tuple[int, int],
    ) -> dict[str, Any] | None:
        return self.registry.lookup(
            "d12_axis_action",
            {"element": list(element), "state": list(state)},
        )

    def stats(self) -> dict[str, Any]:
        return self.registry.stats()

    def close(self) -> None:
        self.registry.close()

    def _propose_chart_state(self, state: tuple[int, int, int]) -> dict[str, Any]:
        j3 = J3O.from_diagonal(*state)
        return self.registry.propose(
            kind="d4_chart_idempotent",
            key={"state": list(state)},
            value={
                "axis": ANTIPODAL_LABEL[state],
                "sheet": SHEET_SIGN[state],
                "trace": int(sum(state)),
                "is_idempotent": j3.is_idempotent(),
            },
            provenance="CQEIdempotentLibCache.seed_core.chart_codec_d4+jordan_j3",
            validator_name="d4_chart_idempotent",
        )

    def _propose_forced_involution(self, name: str, expected: dict[str, Any]) -> dict[str, Any]:
        return self.registry.propose(
            kind="forced_involution_orbit",
            key={"name": name},
            value=expected,
            provenance="CQEIdempotentLibCache.seed_core.forced_involution_cache",
            validator_name="forced_involution_orbit",
        )

    def _propose_d12_axis_action(
        self,
        element: tuple[int, int],
        state: tuple[int, int],
    ) -> dict[str, Any]:
        image = d12_acts_on_d4_state(element, state)
        return self.registry.propose(
            kind="d12_axis_action",
            key={"element": list(element), "state": list(state)},
            value={"image": list(image)},
            provenance="CQEIdempotentLibCache.seed_core.d12_action",
            validator_name="d12_axis_action",
        )

    def _propose_rule30_depth(self, depth: int) -> dict[str, Any]:
        from .rule90_linearization import rule30_center_via_decomposition

        result = rule30_center_via_decomposition(depth)
        return self.registry.propose(
            kind="rule30_center_bit",
            key={"N": depth},
            value={"bit": result["bit"]},
            provenance="CQEIdempotentLibCache.seed_core.rule90_linearization",
            validator_name="rule30_decomposition",
        )


def _forced_involution_expected() -> dict[str, dict[str, Any]]:
    sweep = run_forced_involution_sweep()
    return {
        name: {
            "axis_invariant": details["axis_invariant"],
            "axis_failure_count": details["axis_failure_count"],
            "failure_bit_pattern": sweep["failure_bit_patterns_8bit"].get(name, 0),
        }
        for name, details in sweep["per_involution"].items()
    }


def _validate_d4_chart_idempotent(kind: str, key: Any, value: Any) -> tuple[bool, str]:
    if kind != "d4_chart_idempotent":
        return False, f"kind mismatch (expected d4_chart_idempotent, got {kind!r})"
    try:
        state = tuple(int(bit) for bit in key["state"])
    except Exception as exc:
        return False, f"invalid state key: {exc}"
    if state not in ANTIPODAL_LABEL:
        return False, f"unknown chart state {state}"
    expected = {
        "axis": ANTIPODAL_LABEL[state],
        "sheet": SHEET_SIGN[state],
        "trace": int(sum(state)),
        "is_idempotent": J3O.from_diagonal(*state).is_idempotent(),
    }
    if value != expected:
        return False, f"value mismatch: expected {expected}, got {value}"
    return True, "D4 chart axis/sheet and J3 diagonal idempotency recomputed"


def _validate_forced_involution(kind: str, key: Any, value: Any) -> tuple[bool, str]:
    if kind != "forced_involution_orbit":
        return False, f"kind mismatch (expected forced_involution_orbit, got {kind!r})"
    name = key.get("name") if isinstance(key, dict) else None
    expected = _forced_involution_expected().get(name)
    if expected is None:
        return False, f"unknown involution {name!r}"
    if value != expected:
        return False, f"value mismatch: expected {expected}, got {value}"
    return True, "forced-involution orbit signature recomputed"


def _validate_d12_axis_action(kind: str, key: Any, value: Any) -> tuple[bool, str]:
    if kind != "d12_axis_action":
        return False, f"kind mismatch (expected d12_axis_action, got {kind!r})"
    try:
        element = tuple(int(part) for part in key["element"])
        state = tuple(int(part) for part in key["state"])
    except Exception as exc:
        return False, f"invalid D12 action key: {exc}"
    try:
        image = d12_acts_on_d4_state(element, state)
    except Exception as exc:
        return False, f"D12 action failed: {exc}"
    expected = {"image": list(image)}
    if value != expected:
        return False, f"value mismatch: expected {expected}, got {value}"
    return True, "D12 action on D4 axis/sheet state recomputed"
