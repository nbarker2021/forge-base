"""Load and write empirical platform manifest (JSONL)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class EmpiricalPlatform:
    claim_id: str
    verifier_id: str
    honesty_label: str
    exhaustion_mode: str
    depth_ladder: list[int] = field(default_factory=list)
    falsify_break: str | None = None
    proof_key: str | None = None
    ring: int = 1
    kind: str = "theorem"
    statement_ref: str = ""
    platform_id: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.platform_id:
            self.platform_id = self.claim_id


def manifest_path() -> Path:
    # package root = .../packages/lattice-forge (parent of src/)
    return Path(__file__).resolve().parents[3] / "empirical" / "platforms.manifest.jsonl"


def load_platform_manifest(path: Path | None = None) -> list[EmpiricalPlatform]:
    p = path or manifest_path()
    if not p.is_file():
        return []
    rows: list[EmpiricalPlatform] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        rows.append(EmpiricalPlatform(**{k: v for k, v in raw.items() if k in EmpiricalPlatform.__dataclass_fields__}))
    return rows


def write_platform_manifest(platforms: list[EmpiricalPlatform], path: Path | None = None) -> Path:
    p = path or manifest_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(asdict(pl), sort_keys=True) for pl in platforms]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def platform_by_claim(platforms: list[EmpiricalPlatform], claim_id: str) -> EmpiricalPlatform | None:
    for pl in platforms:
        if pl.claim_id == claim_id:
            return pl
    return None


def default_ladder_for_label(honesty_label: str, exhaustion_mode: str) -> list[int]:
    from lattice_forge.empirical.exhaust import ladder_for_mode

    if honesty_label == "CONJ":
        return ladder_for_mode("exhaustive" if exhaustion_mode != "quick" else "quick")
    if honesty_label in {"PROVEN", "TRANSPORTED"}:
        return ladder_for_mode(exhaustion_mode if exhaustion_mode in {"quick", "standard", "exhaustive", "full"} else "exhaustive")
    return ladder_for_mode(exhaustion_mode if exhaustion_mode != "full" else "standard")
