"""Adversarial semantic-bridge evaluation with explicit oracle separation."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol

from .library import ReverseAtlasLibrary


class Predictor(Protocol):
    """One candidate bridge that emits before the evaluator consults an oracle."""

    def predict(self, n: int) -> dict[str, Any]:
        """Return one resolved prediction or an explicit escrow receipt."""


@dataclass(frozen=True)
class ImmutableReverseAtlasBackend:
    """Bounded baseline backed by an immutable hydrated reverse atlas."""

    library: ReverseAtlasLibrary

    @classmethod
    def open(cls, path: Path) -> "ImmutableReverseAtlasBackend":
        """Open one validated reverse-atlas directory."""
        return cls(library=ReverseAtlasLibrary.open(Path(path)))

    def predict(self, n: int) -> dict[str, Any]:
        """Resolve an in-sheet target read or escrow an unavailable address."""
        address_count = self.library.manifest["address_count"]
        boundary = {
            "N": n,
            "source_library_hash": self.library.manifest["recipe_map_sha256"],
            "source_address_count": address_count,
            "target_read_from_hydrated_sheet": True,
            "cold_start_semantic_bridge_proved": False,
        }
        if not 0 <= n < address_count:
            return {
                "status": "escrow_open",
                "bit": None,
                "evidence": "registered_route",
                "reason": "address is outside immutable reverse-atlas bounds",
                **boundary,
            }

        lookup = self.library.lookup(n)
        return {
            "status": "resolved",
            "bit": lookup["downward"]["C"],
            "evidence": "hydrated_reverse_atlas_exact",
            "recipe_id": lookup["recipe_id"],
            "receipt_chain": lookup,
            **boundary,
        }


def evaluate_predictions(
    predictor: Predictor,
    requests: Iterable[int],
    oracle: Callable[[int], int],
) -> dict[str, Any]:
    """Score emitted predictions while keeping escrow rows out of oracle reads."""
    rows = []
    resolved_count = 0
    escrow_count = 0
    correct_count = 0
    defect_count = 0
    for n in requests:
        receipt = predictor.predict(n)
        row = {"N": n, "prediction": receipt}
        if receipt["bit"] is None:
            escrow_count += 1
            rows.append(row)
            continue

        expected = oracle(n)
        matched = receipt["bit"] == expected
        resolved_count += 1
        correct_count += int(matched)
        defect_count += int(not matched)
        row.update({"oracle_bit": expected, "matched": matched})
        rows.append(row)

    total_count = resolved_count + escrow_count
    return {
        "status": "pass" if defect_count == 0 else "defects_detected",
        "request_count": total_count,
        "resolved_count": resolved_count,
        "escrow_count": escrow_count,
        "correct_count": correct_count,
        "defect_count": defect_count,
        "coverage": resolved_count / total_count if total_count else 0.0,
        "accuracy_on_resolved": (
            correct_count / resolved_count if resolved_count else None
        ),
        "cold_start_semantic_bridge_proved": False,
        "rows": rows,
    }
