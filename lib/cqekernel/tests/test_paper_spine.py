from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


def test_every_topology_tile_has_auditable_paper_body() -> None:
    topology = json.loads((ROOT / "ecology/registries/paper_topology.json").read_text(encoding="utf-8"))
    required = ["Dependency and boundary edges", "First-pass obligations",
                "Existing proof and evidence attachments",
                "Existing edge resolutions and honesty boundaries",
                "Supersession", "Closure boundary"]
    missing = []
    for tile in topology["tiles"]:
        paper_id = tile["paper_id"]
        path = ROOT / "ecology/kernels" / f"Kp{paper_id}" / "publication" / f"{paper_id}.md"
        if not path.exists():
            missing.append(paper_id)
            continue
        body = path.read_text(encoding="utf-8")
        assert "<!-- GENERATED-FIRST-PASS:BEGIN -->" in body
        assert "<!-- GENERATED-FIRST-PASS:END -->" in body
        for heading in required:
            assert heading in body, f"{paper_id} lacks {heading}"
    assert not missing


def test_spine_coverage_matches_topology() -> None:
    coverage = json.loads((ROOT / "ecology/registries/paper_spine_coverage.json").read_text(encoding="utf-8"))
    assert coverage["paper_bodies"] == coverage["topology_tiles"] == 149
    assert coverage["missing"] == []
