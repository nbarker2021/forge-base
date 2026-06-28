from __future__ import annotations

import csv
import json
from pathlib import Path

from cqekernel.master_ribbon import MasterRibbonCompiler
from cqekernel.master_ribbon.compiler import _expand_claim

CUTOFF = "2026-06-20T00:50:00-07:00"


def fixture(tmp_path: Path, *, content_hash: str = "a" * 64, binary: bool = False,
            imported: bool = False) -> MasterRibbonCompiler:
    repo = tmp_path / "repo"; repo.mkdir(exist_ok=True)
    registry = repo / "sources.csv"
    with registry.open("w", encoding="utf-8", newline="") as handle:
        fields = ["source_id", "path", "sha256", "size", "modified_utc", "extension",
                  "authority_class", "lineage", "extraction_location", "preservation_status"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for alias in (("a.bin", "mirror/a.bin") if binary else ("a.md", "mirror/a.md")):
            writer.writerow({"source_id": "SRC-A", "path": alias, "sha256": content_hash,
                "size": "1", "modified_utc": "2026-06-20T07:49:00+00:00",
                "extension": ".bin" if binary else ".md", "authority_class": "test",
                "lineage": "fixture", "extraction_location": "", "preservation_status": "hashed"})
    (repo / "validator.py").write_text("assert True\n", encoding="utf-8")
    (repo / "receipt.json").write_text('{"result":"PASS"}\n', encoding="utf-8")
    claims = repo / "claims.jsonl"
    claim = {"record_id": "CLAIM-A", "paper_tile": "8.06.24",
             "imports": ["MISSING"] if imported else [], "exports": ["A"],
             "evidence": {"ED": ["SRC-A"], "ID": [], "DD": []},
             "validators": ["validator.py"], "receipts": ["receipt.json"],
             "proof_obligations": [], "internal_status": "computed", "external_status": "open",
             "boundary": "fixture", "coordinate_contract": "test"}
    claims.write_text(json.dumps(claim) + "\n", encoding="utf-8")
    return MasterRibbonCompiler(repo, registry, claims, repo / "epochs")


def traces(compiler: MasterRibbonCompiler, epoch: str) -> list[dict]:
    rows = []
    for path in (compiler.output_root / epoch / "claim-traces").glob("*.jsonl"):
        rows += [_expand_claim(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return rows


def test_deterministic_deduplicated_epoch(tmp_path: Path) -> None:
    compiler = fixture(tmp_path)
    first = compiler.build(CUTOFF); second = compiler.build(CUTOFF)
    assert first["root_hash"] == second["root_hash"]
    assert first["registry_rows_included"] == 2 and first["unique_sources"] == 1
    assert compiler.verify(first["epoch_id"])["result"] == "PASS"


def test_one_byte_mutation_changes_segment_edge_and_root(tmp_path: Path) -> None:
    compiler = fixture(tmp_path, content_hash="a" * 64, imported=True)
    first = compiler.build(CUTOFF)
    edge_before = (compiler.output_root / first["epoch_id"] / "edge-contracts.jsonl").read_bytes()
    compiler = fixture(tmp_path, content_hash="b" + "a" * 63, imported=True)
    second = compiler.build("2026-06-20T00:50:01-07:00")
    edge_after = (compiler.output_root / second["epoch_id"] / "edge-contracts.jsonl").read_bytes()
    assert first["root_hash"] != second["root_hash"] and edge_before != edge_after


def test_binary_has_extraction_obligation(tmp_path: Path) -> None:
    compiler = fixture(tmp_path, binary=True); manifest = compiler.build(CUTOFF)
    shard = compiler.output_root / manifest["epoch_id"] / "segments" / "aa.jsonl"
    ribbon = json.loads(shard.read_text(encoding="utf-8").splitlines()[0])
    assert "extract_and_address_binary:.bin" in ribbon["s"][5][1]["obligations"]


def test_single_exposure_token_per_unique_content(tmp_path: Path) -> None:
    compiler = fixture(tmp_path); manifest = compiler.build(CUTOFF)
    exposure = compiler.output_root / manifest["epoch_id"] / "dedupe-exposure.jsonl"
    rows = [json.loads(line) for line in exposure.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1 and rows[0]["alias_count"] == 2
    assert manifest["duplicates_sieved"] == 1
    assert manifest["sieve"]["max_interaction_width"] <= 64


def test_incomplete_legacy_claim_cannot_promote(tmp_path: Path) -> None:
    compiler = fixture(tmp_path); claim = json.loads(compiler.claims.read_text(encoding="utf-8"))
    claim["validators"] = []; claim["receipts"] = []
    compiler.claims.write_text(json.dumps(claim) + "\n", encoding="utf-8")
    manifest = compiler.build(CUTOFF); trace = traces(compiler, manifest["epoch_id"])[0]
    assert trace["resulting_internal_status"] == "source_bound" and not trace["complete"]


def test_stale_shard_fails_replay(tmp_path: Path) -> None:
    compiler = fixture(tmp_path); manifest = compiler.build(CUTOFF)
    shard = compiler.output_root / manifest["epoch_id"] / "segments" / "aa.jsonl"
    shard.write_bytes(shard.read_bytes() + b" ")
    result = compiler.verify(manifest["epoch_id"])
    assert result["result"] == "FAIL" and "epoch_root_mismatch" in result["errors"]


def test_claim_and_exposure_mutations_are_root_bound(tmp_path: Path) -> None:
    compiler = fixture(tmp_path); manifest = compiler.build(CUTOFF)
    claim = next(path for path in (compiler.output_root / manifest["epoch_id"] / "claim-traces").glob("*.jsonl")
                 if path.stat().st_size)
    claim.write_bytes(claim.read_bytes() + b" ")
    result = compiler.verify(manifest["epoch_id"])
    assert result["result"] == "FAIL"
    assert any(item.startswith("stale_or_mutated_claim_shard:") for item in result["errors"])

    compiler = fixture(tmp_path); manifest = compiler.build(CUTOFF)
    exposure = compiler.output_root / manifest["epoch_id"] / "dedupe-exposure.jsonl"
    exposure.write_bytes(exposure.read_bytes() + b" ")
    result = compiler.verify(manifest["epoch_id"])
    assert "stale_or_mutated_attachment:dedupe-exposure.jsonl" in result["errors"]
