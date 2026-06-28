"""Witness state key grammar and validation (stub index)."""

from __future__ import annotations

import re
from typing import Any

STATE_KEY_PATTERN = re.compile(
    r"^lf/state/(?P<regime>[A-Za-z0-9_]+)(?:/(?P<suffix>.+))?$"
)

VALID_REGIMES = frozenset({"A", "B", "C", "Cprime", "substrate"})


def parse_state_key(key: str) -> dict[str, Any]:
    match = STATE_KEY_PATTERN.match(key)
    if not match:
        return {"valid": False, "key": key, "error": "grammar_mismatch"}
    regime = match.group("regime")
    if regime not in VALID_REGIMES:
        return {"valid": False, "key": key, "error": "unknown_regime", "regime": regime}
    return {
        "valid": True,
        "key": key,
        "regime": regime,
        "suffix": match.group("suffix") or "",
    }


def make_regime_encode_key(*, from_regime: str, to_regime: str, max_depth: int) -> str:
    return f"lf/state/{to_regime}/encode/from_{from_regime}/depth_{max_depth}"


def record_encode_keys(
    *,
    from_regime: str,
    to_regime: str,
    max_depth: int,
) -> list[str]:
    """Return canonical keys recorded on regime encode (index stub only)."""
    primary = make_regime_encode_key(
        from_regime=from_regime, to_regime=to_regime, max_depth=max_depth
    )
    return [primary, f"{primary}/witness_stub"]
