"""Deterministic Papers 1-10 compiler and sharded epoch store."""

from __future__ import annotations

from collections import defaultdict
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .model import (ClaimTrace, EdgeContract, EvidenceRibbonV2, EvidenceSlotV2,
                    StageTrace, canonical_bytes, sha256)

STAGES = (
    (1, "P01", "lcr_carrier_boundaries", "LCR(C,L,R)"),
    (2, "P02", "correction_residue", "C_and_not_R"),
    (3, "P03", "d4_j3_triality_coordinates", "D4/J3/triality"),
    (4, "P04", "boundary_repair_constraints", "boundary_repair"),
    (5, "P05", "path_oloid_transport", "path/oloid"),
    (6, "P06", "causal_dependency_edges", "directed_claim_graph"),
    (7, "P07", "discrete_continuous_presentation", "discrete-continuous"),
    (8, "P08", "lattice_tile_closure_carrier", "lattice/tile"),
    (9, "P09", "hamiltonian_kappa_window_ordering", "Hamiltonian/kappa"),
    (10, "P10", "master_receipt_replay_trust_anchor", "receipt/trust-anchor"),
)
TEXT_EXTENSIONS = {".md", ".txt", ".rst", ".tex", ".py", ".json", ".jsonl", ".yaml",
                   ".yml", ".sql", ".csv", ".tsv", ".toml", ".ini", ".xml"}
PROMOTED_INTERNAL = {"computed", "proved"}
SIEVE_BLOCK = 8 * 8


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timezone required: {value}")
    return parsed


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True,
                                ensure_ascii=False).encode("utf-8") + b"\n")


def _jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        for row in rows:
            handle.write(canonical_bytes(row) + b"\n")


def _content_bytes(path: Path) -> bytes:
    """Read bytes with Git-portable newline semantics for known text files.

    Epochs are generated with LF. Git may check them out as CRLF on Windows;
    that transport-only rewrite must not invalidate the content trust root.
    Binary artifacts remain byte-exact.
    """
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_EXTENSIONS:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return data


def _content_hash(path: Path) -> str:
    return hashlib.sha256(_content_bytes(path)).hexdigest()


def _file_record(path: Path, root: Path) -> dict[str, Any]:
    """Return the canonical content token used by the epoch trust root."""
    data = _content_bytes(path)
    return {
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _compact_ribbon(ribbon: EvidenceRibbonV2) -> dict[str, Any]:
    """Normalize repeated Papers 1-10 fields out of every source row.

    STAGES in the epoch manifest is the shared relation.  A compact row stores
    only the values that vary by source.  The full EvidenceRibbonV2 is exactly
    reconstructable and is rebuilt during verification.
    """
    return {
        "v": ribbon.schema_version,
        "id": ribbon.ribbon_id,
        "sid": ribbon.source_id,
        "h": ribbon.source_hash,
        "a": list(ribbon.aliases),
        "s": [
            [slot.name, slot.value, slot.provenance, slot.status,
             list(slot.evidence_refs), slot.source_kind, slot.content_hash]
            for slot in ribbon.slots
        ],
        # Inputs chain from h and each preceding output. Operation/coordinate,
        # evidence, boundary, and status are normalized by STAGES and the
        # source-bound intake contract.
        "g": [stage.outputs[0] for stage in ribbon.stages],
        "o": list(ribbon.stages[-1].obligations_opened),
        "rh": ribbon.ribbon_hash,
    }


def _expand_ribbon(row: dict[str, Any]) -> EvidenceRibbonV2:
    slots = tuple(
        EvidenceSlotV2(item[0], item[1], item[2], item[3], tuple(item[4]), item[5])
        for item in row["s"]
    )
    prior = row["h"]
    expanded = []
    for index, ((number, paper, operation, coordinate), output) in enumerate(zip(STAGES, row["g"])):
        opened = tuple(row.get("o", [])) if index == 9 else ()
        expanded.append(StageTrace(number, paper, operation, coordinate,
                                   (prior,), (output,), (row["sid"],), (), (), (), opened,
                                   "Artifact transport only; no physical correspondence is inferred.",
                                   "source_bound"))
        prior = output
    stages = tuple(expanded)
    return EvidenceRibbonV2(row["sid"], row["h"], tuple(row["a"]), slots, stages)


def _compact_claim(trace: ClaimTrace) -> dict[str, Any]:
    return {
        "id": trace.trace_id, "rid": trace.record_id, "tile": trace.paper_tile,
        "er": list(trace.evidence_ribbons), "g": [stage.outputs[0] for stage in trace.stages],
        "v": list(trace.validators), "r": list(trace.receipts),
        "va": list(trace.validator_anchors), "ra": list(trace.receipt_anchors),
        "o": list(trace.obligations_open), "b": trace.boundary,
        "ri": trace.requested_internal_status, "re": trace.requested_external_status,
        "oi": trace.resulting_internal_status, "oe": trace.resulting_external_status,
        "c": trace.complete,
    }


def _expand_claim(row: dict[str, Any]) -> dict[str, Any]:
    prior = sha256({"record": row["rid"], "evidence": tuple(row["er"])})
    stages = []
    for index, ((number, paper, operation, coordinate), output) in enumerate(zip(STAGES, row["g"])):
        opened = row["o"] if index == 9 else []
        stages.append(StageTrace(number, paper, operation, coordinate, (prior,), (output,),
                                 (row["rid"],), (), (), (), tuple(opened),
                                 "Artifact transport only; no physical correspondence is inferred.",
                                 "source_bound").to_dict())
        prior = output
    return {"trace_id": row["id"], "record_id": row["rid"], "paper_tile": row["tile"],
            "evidence_ribbons": row["er"], "stages": stages, "validators": row["v"],
            "receipts": row["r"], "validator_anchors": row["va"],
            "receipt_anchors": row["ra"], "obligations_open": row["o"], "boundary": row["b"],
            "requested_internal_status": row["ri"], "requested_external_status": row["re"],
            "resulting_internal_status": row["oi"], "resulting_external_status": row["oe"],
            "complete": row["c"]}


class MasterRibbonCompiler:
    def __init__(self, repo: Path, registry: Path | None = None,
                 claims: Path | None = None, output_root: Path | None = None) -> None:
        self.repo = Path(repo).resolve()
        self.registry = registry or self.repo / "corpus/source-manifests/source_registry.csv"
        self.claims = claims or self.repo / "ecology/registries/claim_proof_theorem_registry.jsonl"
        self.output_root = output_root or self.repo / "ecology/registries/master-ribbon/epochs"
        self._anchor_cache: dict[str, str | None] = {}

    @staticmethod
    def epoch_id(cutoff: str) -> str:
        parsed = _dt(cutoff)
        return parsed.isoformat(timespec="seconds").replace(":", "").replace("+", "p")

    @staticmethod
    def _sieve(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """Exact-hash radix sieve whose local comparison leaves never exceed 8x8.

        Rows sharing a digest are never separated.  An unusually large alias
        family is reduced against its one digest token sequentially, so it
        still requires no interaction wider than the local block.
        """
        leaves: list[list[dict[str, str]]] = []
        partitions = 0

        def partition(items: list[dict[str, str]], depth: int) -> None:
            nonlocal partitions
            partitions += 1
            digests = {item["_digest"] for item in items}
            if len(items) <= SIEVE_BLOCK or len(digests) == 1 or depth >= 64:
                leaves.append(items)
                return
            buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
            for item in items:
                buckets[item["_digest"][depth]].append(item)
            for key in sorted(buckets):
                partition(buckets[key], depth + 1)

        partition(rows, 0)
        grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
        max_leaf = 0
        for leaf in leaves:
            max_leaf = max(max_leaf, min(len(leaf), SIEVE_BLOCK))
            for row in leaf:
                grouped[row.pop("_digest")].append(row)
        unique = [{"source_hash": digest, "rows": aliases}
                  for digest, aliases in sorted(grouped.items())]
        return unique, {"block_width": SIEVE_BLOCK, "partitions": partitions,
                        "leaves": len(leaves), "max_interaction_width": max_leaf}

    def _sources(self, cutoff: str) -> tuple[list[dict[str, Any]], list[dict[str, str]], dict[str, int]]:
        limit = _dt(cutoff)
        selected: list[dict[str, str]] = []
        excluded: list[dict[str, str]] = []
        with self.registry.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                try:
                    modified = _dt(row["modified_utc"])
                except (KeyError, ValueError):
                    excluded.append({"source_id": row.get("source_id", ""), "reason": "invalid_modified_time"})
                    continue
                if modified <= limit:
                    row["_digest"] = row.get("sha256") or sha256(
                        {"source_id": row.get("source_id"), "path": row.get("path")})
                    selected.append(row)
                else:
                    excluded.append({"source_id": row.get("source_id", ""), "reason": "after_epoch"})
        selected.sort(key=lambda r: (-_dt(r["modified_utc"]).timestamp(), r.get("sha256", ""), r.get("path", "")))
        unique, sieve = self._sieve(selected)
        return unique, excluded, sieve

    def _stage_chain(self, source_id: str, source_hash: str,
                     obligations: tuple[str, ...] = ()) -> tuple[StageTrace, ...]:
        prior = source_hash
        result = []
        for number, paper, operation, coordinate in STAGES:
            output = sha256({"stage": number, "input": prior, "source": source_hash,
                             "operation": operation, "coordinate": coordinate})
            opened = obligations if number == 10 else ()
            result.append(StageTrace(number, paper, operation, coordinate, (prior,), (output,),
                                     (source_id,), (), (), (), opened,
                                     "Artifact transport only; no physical correspondence is inferred.",
                                     "source_bound"))
            prior = output
        return tuple(result)

    def _ribbon(self, group: dict[str, Any]) -> EvidenceRibbonV2:
        rows = group["rows"]
        first = rows[0]
        aliases = tuple(sorted({row.get("path", "") for row in rows if row.get("path")}))
        source_ids = tuple(sorted({row.get("source_id", "") for row in rows if row.get("source_id")}))
        ext = (first.get("extension") or Path(aliases[0]).suffix if aliases else "").lower()
        obligations: list[str] = []
        if ext not in TEXT_EXTENSIONS:
            obligations.append(f"extract_and_address_binary:{ext or 'unknown'}")
        if not first.get("sha256"):
            obligations.append("recover_and_verify_source_hash")
        provenance = first.get("authority_class", "unclassified")
        values = {
            "C": {"source_id": first.get("source_id"), "content_hash": group["source_hash"]},
            "L": {"modified_utc": first.get("modified_utc"), "cutoff_relation": "at_or_before"},
            "R": {"aliases": len(aliases), "size": first.get("size", "")},
            "B": {"rule": "registry_active_at_or_before_epoch", "preservation": first.get("preservation_status", "")},
            "T": {"compiler": "Kp8.06.24", "stages": 10},
            "O": {"obligations": obligations},
            "W": {"lineage": sorted({row.get("lineage", "") for row in rows if row.get("lineage")})},
            "A": {"source_ids": list(source_ids), "paths": list(aliases)},
        }
        slots = tuple(EvidenceSlotV2(name, values[name], provenance,
                                     "obligated" if name == "O" and obligations else "source_bound",
                                     source_ids) for name in "CLRBTOWA")
        return EvidenceRibbonV2(first.get("source_id", f"SRC-{group['source_hash'][:20]}"),
                                group["source_hash"], aliases, slots,
                                self._stage_chain(first.get("source_id", ""), group["source_hash"], tuple(obligations)))

    def _anchor(self, reference: str, source_map: dict[str, str]) -> str | None:
        if reference in source_map:
            return source_map[reference]
        if reference in self._anchor_cache:
            return self._anchor_cache[reference]
        path = Path(reference)
        if not path.is_absolute():
            path = self.repo / path
        if path.is_file():
            digest = _content_hash(path)
            if path.suffix.lower() == ".json":
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    verdict = str(payload.get("result", payload.get("status", "PASS"))).upper()
                    if verdict in {"FAIL", "FAILED", "FALSE", "INVALID"}:
                        digest = None
                except (UnicodeDecodeError, json.JSONDecodeError):
                    digest = None
            self._anchor_cache[reference] = digest
            return digest
        self._anchor_cache[reference] = None
        return None

    def _claim_traces(self, source_map: dict[str, str]) -> tuple[list[ClaimTrace], list[EdgeContract]]:
        records = []
        if self.claims.exists():
            with self.claims.open(encoding="utf-8") as handle:
                records = [json.loads(line) for line in handle if line.strip()]
        kernel_claims = self.repo / "ecology/kernels"
        if kernel_claims.exists():
            for path in sorted(kernel_claims.glob("Kp*/claims.jsonl")):
                if path.resolve() == self.claims.resolve():
                    continue
                with path.open(encoding="utf-8") as handle:
                    records.extend(json.loads(line) for line in handle if line.strip())
        by_id = {record["record_id"]: record for record in records}
        exports: dict[str, str] = {}
        for record in records:
            for name in record.get("exports", []):
                exports.setdefault(name, record["record_id"])
        traces: list[ClaimTrace] = []
        edges: list[EdgeContract] = []
        for record in records:
            evidence = [item for klass in ("ED", "ID", "DD") for item in record.get("evidence", {}).get(klass, [])]
            evidence_ribbons = tuple(sorted({source_map[item] for item in evidence if item in source_map}))
            missing_evidence = sorted(set(evidence) - set(source_map))
            validators = tuple(record.get("validators", []))
            receipts = tuple(record.get("receipts", []))
            validator_values = tuple(self._anchor(item, source_map) for item in validators)
            receipt_values = tuple(self._anchor(item, source_map) for item in receipts)
            missing_validators = [item for item, anchor in zip(validators, validator_values) if anchor is None]
            missing_receipts = [item for item, anchor in zip(receipts, receipt_values) if anchor is None]
            obligations = list(record.get("proof_obligations", []))
            obligations += [f"missing_evidence:{item}" for item in missing_evidence]
            obligations += [f"missing_validator:{item}" for item in missing_validators]
            obligations += [f"missing_receipt:{item}" for item in missing_receipts]
            if not validators:
                obligations.append("validator_required_for_promotion")
            if not receipts:
                obligations.append("receipt_required_for_promotion")
            complete = bool(evidence_ribbons and validators and receipts and not missing_evidence
                            and not missing_validators and not missing_receipts and not record.get("proof_obligations"))
            requested_i = record.get("internal_status", "source_bound")
            requested_e = record.get("external_status", "open")
            if requested_e == "supported":
                empirical = " ".join(str(record.get(key, "")) for key in ("calibration", "uncertainty", "falsifier")).lower()
                for required in ("dataset", "unit", "uncertainty", "residual", "falsif"):
                    if required not in empirical:
                        obligations.append(f"supported_claim_requires_{required}")
                complete = complete and not any(item.startswith("supported_claim_requires_") for item in obligations)
            result_i = requested_i if complete or requested_i not in PROMOTED_INTERNAL else "source_bound"
            result_e = requested_e if complete or requested_e != "supported" else "open"
            claim_hash = sha256({"record": record["record_id"], "evidence": evidence_ribbons})
            stages = self._stage_chain(record["record_id"], claim_hash, tuple(sorted(set(obligations))))
            traces.append(ClaimTrace(f"TRACE-{claim_hash[:24]}", record["record_id"],
                                     record.get("paper_tile", "unassigned"), evidence_ribbons, stages,
                                     validators, receipts,
                                     tuple(anchor or "" for anchor in validator_values),
                                     tuple(anchor or "" for anchor in receipt_values),
                                     tuple(sorted(set(obligations))),
                                     record.get("boundary", ""), requested_i, requested_e,
                                     result_i, result_e, complete))
            for imported in record.get("imports", []):
                target = imported if imported in by_id else exports.get(imported, "")
                edge_hash = sha256({"source": record["record_id"], "target": target,
                                    "import": imported, "source_trace": claim_hash})
                edge_obligations = () if target else (f"unresolved_import:{imported}",)
                edges.append(EdgeContract(f"EDGE-{edge_hash[:24]}", record["record_id"], target,
                                          imported, claim_hash, record.get("coordinate_contract", "unclassified"),
                                          "resolved" if target else "open", edge_obligations,
                                          "Claim dependency only; coordinate compatibility requires an explicit validator."))
        traces.sort(key=lambda item: item.record_id)
        edges.sort(key=lambda item: item.edge_id)
        return traces, edges

    def _external_obligations(self) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        tombstones = self.repo / "corpus/source-manifests/missing_source_tombstones.csv"
        if tombstones.exists():
            with tombstones.open(encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    if row.get("disposition") != "unique_missing_needs_recovery":
                        continue
                    result.append({"kind": "missing_source", "reference": row.get("path") or row.get("source_id", ""),
                                   "obligation": "recover_hash_and_ribbonize"})
        queue = self.repo / "governance/release/forge_replay_queue.csv"
        if queue.exists():
            with queue.open(encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    if row.get("priority") == "P0" or row.get("replay_status") == "missing_or_undeclared":
                        result.append({"kind": "undeclared_forge", "reference": row.get("forge", ""),
                                       "obligation": "resolve_register_and_replay"})
        return result

    def build(self, cutoff: str) -> dict[str, Any]:
        _dt(cutoff)
        epoch_id = self.epoch_id(cutoff)
        epoch = self.output_root / epoch_id
        groups, excluded, sieve = self._sources(cutoff)
        ribbons = [self._ribbon(group) for group in groups]
        source_map = {source_id: ribbon.ribbon_id for group, ribbon in zip(groups, ribbons)
                      for source_id in {row.get("source_id", "") for row in group["rows"]}}
        traces, edges = self._claim_traces(source_map)
        shard_rows: dict[str, list[dict[str, Any]]] = {f"{n:02x}": [] for n in range(256)}
        for ribbon in ribbons:
            shard_rows[ribbon.source_hash[:2]].append(_compact_ribbon(ribbon))
        claim_rows: dict[str, list[dict[str, Any]]] = {f"{n:02x}": [] for n in range(256)}
        for trace in traces:
            claim_rows[sha256(trace.record_id)[:2]].append(_compact_claim(trace))
        shard_manifest = []
        claim_manifest = []
        for prefix in sorted(shard_rows):
            path = epoch / "segments" / f"{prefix}.jsonl"
            _jsonl(path, shard_rows[prefix])
            digest = _content_hash(path)
            shard_manifest.append({"prefix": prefix, "count": len(shard_rows[prefix]), "sha256": digest})
            claim_path = epoch / "claim-traces" / f"{prefix}.jsonl"
            _jsonl(claim_path, claim_rows[prefix])
            claim_manifest.append({"prefix": prefix, "count": len(claim_rows[prefix]),
                                   "sha256": _content_hash(claim_path)})
        edge_path = epoch / "edge-contracts.jsonl"
        _jsonl(edge_path, (item.to_dict() for item in edges))
        external = self._external_obligations()
        residues = ([{"kind": "claim", "reference": trace.record_id, "obligation": obligation}
                     for trace in traces for obligation in trace.obligations_open] + external)
        residue_path = epoch / "unresolved-residue.jsonl"
        excluded_path = epoch / "excluded.jsonl"
        exposure_path = epoch / "dedupe-exposure.jsonl"
        _jsonl(residue_path, residues)
        _jsonl(excluded_path, excluded)
        # This is the one surviving exposure document from the ephemeral hash
        # sieve: one token per unique byte sequence, never one token per path.
        _jsonl(exposure_path, ({"source_hash": ribbon.source_hash,
                                "ribbon_hash": ribbon.ribbon_hash,
                                "ribbon_id": ribbon.ribbon_id,
                                "alias_count": len(ribbon.aliases),
                                "shard": ribbon.source_hash[:2]}
                               for ribbon in ribbons))
        attachments = [_file_record(path, epoch) for path in
                       (edge_path, residue_path, excluded_path, exposure_path)]
        root_payload = {"schema": "MasterRibbonEpoch/1.0", "cutoff": cutoff,
                        "stage_dictionary": [list(item) for item in STAGES],
                        "shards": shard_manifest, "claim_shards": claim_manifest,
                        "attachments": attachments}
        root_hash = sha256(root_payload)
        manifest = {**root_payload, "epoch_id": epoch_id, "root_hash": root_hash,
                    "registry_rows_included": sum(len(group["rows"]) for group in groups),
                    "unique_sources": len(ribbons), "lineage_aliases": sum(len(r.aliases) for r in ribbons),
                    "duplicates_sieved": sum(len(group["rows"]) for group in groups) - len(ribbons),
                    "sieve": sieve,
                    "claim_traces": len(traces), "edge_contracts": len(edges),
                    "unresolved_residues": len(residues), "excluded_records": len(excluded),
                    "promotion_rule": "computed/proved/supported require a complete ten-stage trace with evidence, validator, and receipt anchors"}
        _write_json(epoch / "manifest.json", manifest)
        manifest_path = epoch / "manifest.json"
        try:
            manifest_reference = str(manifest_path.relative_to(self.repo)).replace("\\", "/")
        except ValueError:
            manifest_reference = str(manifest_path.resolve()).replace("\\", "/")
        _write_json(self.repo / f"evidence/receipts/master-ribbon-{epoch_id}.json",
                    {"kernel": "Kp8.06.24", "epoch_id": epoch_id, "root_hash": root_hash,
                     "scope": "registered artifacts at or before cutoff; source-bound compilation",
                     "result": "PASS", "manifest": manifest_reference})
        self._write_mutation_receipt(epoch, manifest)
        return manifest

    def _write_mutation_receipt(self, epoch: Path, manifest: dict[str, Any]) -> None:
        """Prove mutation sensitivity without changing the stored epoch."""
        target = next(item for item in manifest["shards"] if item["count"])
        original = _content_bytes(epoch / "segments" / f"{target['prefix']}.jsonl")
        mutated = bytes([original[0] ^ 1]) + original[1:]
        mutated_shards = [dict(item) for item in manifest["shards"]]
        for item in mutated_shards:
            if item["prefix"] == target["prefix"]:
                item["sha256"] = hashlib.sha256(mutated).hexdigest()
        mutated_root = sha256({"schema": manifest["schema"], "cutoff": manifest["cutoff"],
                               "stage_dictionary": manifest["stage_dictionary"],
                               "shards": mutated_shards, "claim_shards": manifest["claim_shards"],
                               "attachments": manifest["attachments"]})
        edge_path = epoch / "edge-contracts.jsonl"
        edge_changed = True
        if edge_path.stat().st_size:
            edge = json.loads(edge_path.read_text(encoding="utf-8").splitlines()[0])
            before = sha256(edge)
            edge["source_trace_hash"] = ("0" if edge["source_trace_hash"][0] != "0" else "1") + edge["source_trace_hash"][1:]
            edge_changed = sha256(edge) != before
        passed = mutated_root != manifest["root_hash"] and edge_changed
        _write_json(epoch / "mutation-receipt.json", {
            "kernel": "Kp8.06.24", "probe": "one_byte_plus_dependent_edge",
            "segment": target["prefix"], "segment_changed": hashlib.sha256(mutated).hexdigest() != target["sha256"],
            "dependent_edge_changed": edge_changed, "epoch_root_changed": mutated_root != manifest["root_hash"],
            "stored_epoch_unchanged": True, "result": "PASS" if passed else "FAIL"
        })

    def verify(self, epoch_id: str) -> dict[str, Any]:
        epoch = self.output_root / epoch_id
        manifest = json.loads((epoch / "manifest.json").read_text(encoding="utf-8"))
        errors = []
        actual_shards = []
        ribbons: dict[str, dict[str, Any]] = {}
        for expected in manifest["shards"]:
            path = epoch / "segments" / f"{expected['prefix']}.jsonl"
            actual_hash = _content_hash(path) if path.exists() else "missing"
            rows = []
            if path.exists():
                try:
                    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
                except json.JSONDecodeError:
                    errors.append(f"invalid_jsonl:{expected['prefix']}")
            actual_shards.append({"prefix": expected["prefix"], "count": len(rows), "sha256": actual_hash})
            if actual_hash != expected["sha256"] or len(rows) != expected["count"]:
                errors.append(f"stale_or_mutated_shard:{expected['prefix']}")
            for row in rows:
                try:
                    rebuilt = _expand_ribbon(row)
                    if rebuilt.ribbon_hash != row["rh"]:
                        errors.append(f"forged_ribbon:{row.get('id')}")
                    ribbons[row["id"]] = row
                except (KeyError, TypeError, ValueError) as exc:
                    errors.append(f"invalid_ribbon:{row.get('id', 'unknown')}:{exc}")
        actual_claims = []
        for expected in manifest.get("claim_shards", []):
            path = epoch / "claim-traces" / f"{expected['prefix']}.jsonl"
            digest = _content_hash(path) if path.exists() else "missing"
            claim_rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
            count = len(claim_rows)
            actual_claims.append({"prefix": expected["prefix"], "count": count, "sha256": digest})
            if digest != expected["sha256"] or count != expected["count"]:
                errors.append(f"stale_or_mutated_claim_shard:{expected['prefix']}")
            for compact_trace in claim_rows:
                trace = _expand_claim(compact_trace)
                promoted = (trace.get("resulting_internal_status") in PROMOTED_INTERNAL
                            or trace.get("resulting_external_status") == "supported")
                if promoted and not trace.get("complete"):
                    errors.append(f"illegal_promotion:{trace.get('record_id')}")
                if not trace.get("complete") and not trace.get("obligations_open"):
                    errors.append(f"erased_obligations:{trace.get('record_id')}")
                references = trace.get("validators", []) + trace.get("receipts", [])
                anchors = trace.get("validator_anchors", []) + trace.get("receipt_anchors", [])
                for reference, anchor in zip(references, anchors):
                    if not anchor:
                        continue
                    if anchor.startswith("RIB2-"):
                        continue
                    if self._anchor(reference, {}) != anchor:
                        errors.append(f"stale_or_forged_anchor:{trace.get('record_id')}:{reference}")
        actual_attachments = []
        for expected in manifest.get("attachments", []):
            path = epoch / expected["path"]
            actual = _file_record(path, epoch) if path.exists() else {"path": expected["path"], "bytes": 0, "sha256": "missing"}
            actual_attachments.append(actual)
            if actual != expected:
                errors.append(f"stale_or_mutated_attachment:{expected['path']}")
        root = sha256({"schema": manifest["schema"], "cutoff": manifest["cutoff"],
                       "stage_dictionary": manifest["stage_dictionary"],
                       "shards": actual_shards, "claim_shards": actual_claims,
                       "attachments": actual_attachments})
        if root != manifest["root_hash"]:
            errors.append("epoch_root_mismatch")
        graph: dict[str, list[str]] = defaultdict(list)
        edge_path = epoch / "edge-contracts.jsonl"
        if edge_path.exists():
            for line in edge_path.read_text(encoding="utf-8").splitlines():
                edge = json.loads(line)
                if edge.get("target_claim"):
                    graph[edge["source_claim"]].append(edge["target_claim"])
        visiting: set[str] = set()
        visited: set[str] = set()
        def visit(node: str) -> None:
            if node in visiting:
                errors.append(f"dependency_cycle:{node}"); return
            if node in visited: return
            visiting.add(node)
            for target in graph.get(node, []): visit(target)
            visiting.remove(node); visited.add(node)
        for node in sorted(graph): visit(node)
        result = {"epoch_id": epoch_id, "root_hash": root, "ribbons": len(ribbons),
                  "result": "PASS" if not errors else "FAIL", "errors": sorted(set(errors))}
        _write_json(epoch / "replay-receipt.json", result)
        return result

    def project(self, paper_tile: str, epoch_id: str | None = None) -> dict[str, Any]:
        if epoch_id is None:
            epochs = sorted(path.name for path in self.output_root.iterdir() if (path / "manifest.json").exists())
            if not epochs: raise FileNotFoundError("no master-ribbon epochs")
            epoch_id = epochs[-1]
        rows = []
        for path in sorted((self.output_root / epoch_id / "claim-traces").glob("*.jsonl")):
            rows.extend(expanded for expanded in
                        (_expand_claim(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line)
                        if expanded.get("paper_tile") == paper_tile)
        projection = {"epoch_id": epoch_id, "paper_tile": paper_tile, "claim_count": len(rows), "claims": rows}
        _write_json(self.output_root / epoch_id / "kernel-projections" / f"Kp{paper_tile}.json", projection)
        return projection

    def delta(self, prior_epoch: str, new_cutoff: str) -> dict[str, Any]:
        prior = json.loads((self.output_root / prior_epoch / "manifest.json").read_text(encoding="utf-8"))
        current = self.build(new_cutoff)
        before = {item["prefix"]: item["sha256"] for item in prior["shards"]}
        after = {item["prefix"]: item["sha256"] for item in current["shards"]}
        changed = sorted(prefix for prefix in before if before[prefix] != after[prefix])
        result = {"prior_epoch": prior_epoch, "new_epoch": current["epoch_id"],
                  "changed_shards": changed, "prior_root": prior["root_hash"],
                  "new_root": current["root_hash"]}
        _write_json(self.output_root / current["epoch_id"] / "delta-receipt.json", result)
        return result
