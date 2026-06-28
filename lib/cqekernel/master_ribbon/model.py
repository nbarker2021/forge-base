"""Canonical records for the Master Ribbon Claim Compiler.

V2 deliberately does not change :mod:`cqekernel.ribbon` or its public ABI.
It reuses the exact eight slot names while strengthening their content hashes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any

from ..ribbon.slot import SLOT_NAMES


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class EvidenceSlotV2:
    name: str
    value: Any
    provenance: str
    status: str
    evidence_refs: tuple[str, ...] = ()
    source_kind: str = "registry_artifact"
    content_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.name not in SLOT_NAMES:
            raise ValueError(f"unknown ribbon slot: {self.name}")
        payload = {"name": self.name, "value": self.value,
                   "provenance": self.provenance, "status": self.status,
                   "evidence_refs": list(self.evidence_refs),
                   "source_kind": self.source_kind}
        object.__setattr__(self, "content_hash", sha256(payload))

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_refs"] = list(self.evidence_refs)
        return value


@dataclass(frozen=True)
class StageTrace:
    stage: int
    paper: str
    operation: str
    coordinate_contract: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    validator_refs: tuple[str, ...] = ()
    receipt_refs: tuple[str, ...] = ()
    obligations_closed: tuple[str, ...] = ()
    obligations_opened: tuple[str, ...] = ()
    boundary: str = ""
    status: str = "source_bound"

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in ("inputs", "outputs", "evidence_refs", "validator_refs",
                    "receipt_refs", "obligations_closed", "obligations_opened"):
            value[key] = list(value[key])
        return value


@dataclass(frozen=True)
class EvidenceRibbonV2:
    source_id: str
    source_hash: str
    aliases: tuple[str, ...]
    slots: tuple[EvidenceSlotV2, ...]
    stages: tuple[StageTrace, ...]
    schema_version: str = "EvidenceRibbonV2/2.0"
    ribbon_hash: str = field(init=False)
    ribbon_id: str = field(init=False)

    def __post_init__(self) -> None:
        if [slot.name for slot in self.slots] != SLOT_NAMES:
            raise ValueError("EvidenceRibbonV2 must contain C,L,R,B,T,O,W,A in ABI order")
        if [stage.stage for stage in self.stages] != list(range(1, 11)):
            raise ValueError("EvidenceRibbonV2 requires the Papers 1-10 stage sequence")
        body = {"schema_version": self.schema_version, "source_hash": self.source_hash,
                "slot_hashes": [slot.content_hash for slot in self.slots],
                "stage_hashes": [sha256(stage.to_dict()) for stage in self.stages]}
        digest = sha256(body)
        object.__setattr__(self, "ribbon_hash", digest)
        object.__setattr__(self, "ribbon_id", f"RIB2-{digest[:24]}")

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "ribbon_id": self.ribbon_id,
                "source_id": self.source_id, "source_hash": self.source_hash,
                "aliases": list(self.aliases),
                "slots": [slot.to_dict() for slot in self.slots],
                "stages": [stage.to_dict() for stage in self.stages],
                "ribbon_hash": self.ribbon_hash}


@dataclass(frozen=True)
class ClaimTrace:
    trace_id: str
    record_id: str
    paper_tile: str
    evidence_ribbons: tuple[str, ...]
    stages: tuple[StageTrace, ...]
    validators: tuple[str, ...]
    receipts: tuple[str, ...]
    validator_anchors: tuple[str, ...]
    receipt_anchors: tuple[str, ...]
    obligations_open: tuple[str, ...]
    boundary: str
    requested_internal_status: str
    requested_external_status: str
    resulting_internal_status: str
    resulting_external_status: str
    complete: bool

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in ("evidence_ribbons", "validators", "receipts", "validator_anchors",
                    "receipt_anchors", "obligations_open"):
            value[key] = list(value[key])
        value["stages"] = [stage.to_dict() for stage in self.stages]
        return value


@dataclass(frozen=True)
class EdgeContract:
    edge_id: str
    source_claim: str
    target_claim: str
    import_name: str
    source_trace_hash: str
    coordinate_contract: str
    status: str
    obligations: tuple[str, ...]
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["obligations"] = list(self.obligations)
        return value
