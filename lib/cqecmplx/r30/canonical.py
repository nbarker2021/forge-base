"""Canonical Rule 30 witnesses and bounded continuation promotion."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .cache import ContinuationInstruction, ContinuationLedger
from .normal_form import EvidenceClass


def canonical_center_bits(max_depth: int) -> str:
    """Return center-column bits for depths `0..max_depth` from a single seed."""
    if max_depth < 0:
        raise ValueError("max_depth must be >= 0")

    row: dict[int, int] = {0: 1}
    bits = ["1"]
    for _ in range(max_depth):
        next_row: dict[int, int] = {}
        for x in range(-max_depth - 1, max_depth + 2):
            left = row.get(x - 1, 0)
            center = row.get(x, 0)
            right = row.get(x + 1, 0)
            value = left ^ (center | right)
            if value:
                next_row[x] = value
        row = next_row
        bits.append(str(row.get(0, 0)))
    return "".join(bits)


def _digest_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_canonical_witness(max_depth: int, path: Path) -> dict[str, Any]:
    """Materialize a digest-protected bounded canonical center-column witness."""
    witness = {
        "schema_version": 1,
        "rule": 30,
        "seed": "single_center_1",
        "max_depth": max_depth,
        "center_bits": canonical_center_bits(max_depth),
    }
    witness["sha256"] = _digest_payload(witness)
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(witness, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return witness


def validate_canonical_witness(path: Path) -> dict[str, Any]:
    """Validate witness metadata, digest, and canonical Rule 30 contents."""
    resolved = Path(path)
    witness = json.loads(resolved.read_text(encoding="utf-8"))
    if witness.get("schema_version") != 1:
        raise ValueError("unsupported canonical-witness schema")
    if witness.get("rule") != 30 or witness.get("seed") != "single_center_1":
        raise ValueError("witness is not canonical Rule 30 from a single center seed")

    digest = witness.get("sha256")
    unsigned = dict(witness)
    unsigned.pop("sha256", None)
    if digest != _digest_payload(unsigned):
        raise ValueError("canonical witness digest mismatch")

    expected = canonical_center_bits(witness["max_depth"])
    if witness.get("center_bits") != expected:
        raise ValueError("canonical witness contents mismatch")
    return witness


def promote_canonical_window(
    *,
    witness_path: Path,
    ledger: ContinuationLedger,
    sheet_width: int,
) -> dict[str, Any]:
    """Promote every bounded canonical datum to a verified continuation row."""
    if sheet_width <= 0:
        raise ValueError("sheet_width must be > 0")
    witness = validate_canonical_witness(witness_path)
    digest = witness["sha256"]
    instructions = []
    for n, character in enumerate(witness["center_bits"]):
        sheet, offset = divmod(n, sheet_width)
        instructions.append(
            ContinuationInstruction(
                n=n,
                sheet=sheet,
                offset=offset,
                root_template=f"K{sheet_width}:t{offset}",
                bit=int(character),
                evidence=EvidenceClass.VERIFIED_CONTINUATION,
                continuation_verified=True,
                rule_id="canonical_rule30_v1",
                witness_hashes=(digest,),
                provenance=str(Path(witness_path)),
                cost="bounded canonical generation; replay O(1)",
            )
        )
    ledger.record_many(instructions)
    return {
        "status": "pass",
        "rule_id": "canonical_rule30_v1",
        "max_depth": witness["max_depth"],
        "promoted_count": len(witness["center_bits"]),
        "sheet_width": sheet_width,
        "witness": str(Path(witness_path)),
        "witness_sha256": digest,
        "scope": "finite canonical center-column depths 0..max_depth",
    }
