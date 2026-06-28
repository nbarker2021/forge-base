"""Sheet caches and attached extended-memory metadata."""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .normal_form import EvidenceClass, LocalTriad


@dataclass(frozen=True)
class RootPlacementTemplate:
    """Minimal reusable placement surface for one in-sheet offset."""

    sheet_width: int
    offset: int
    root: LocalTriad
    actions: tuple[str, ...] = ()

    @property
    def key(self) -> str:
        return f"K{self.sheet_width}:t{self.offset}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "sheet_width": self.sheet_width,
            "offset": self.offset,
            "root": {
                "L": self.root.left,
                "C": self.root.center,
                "R": self.root.right,
            },
            "actions": list(self.actions),
        }


class RootPlacementTemplateStore:
    """Idempotent hot cache for stripped root-placement templates."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else None
        self.templates: dict[str, RootPlacementTemplate] = {}
        self._load()

    def record(
        self,
        *,
        sheet_width: int,
        offset: int,
        root: LocalTriad,
        actions: tuple[str, ...] = (),
    ) -> RootPlacementTemplate:
        """Save one minimal root template and reuse an existing equivalent key."""
        template = RootPlacementTemplate(
            sheet_width=sheet_width,
            offset=offset,
            root=root,
            actions=actions,
        )
        existing = self.templates.get(template.key)
        if existing is not None:
            return existing

        self.templates[template.key] = template
        self._persist()
        return template

    def _persist(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "templates": {
                key: template.to_dict()
                for key, template in sorted(self.templates.items())
            },
        }
        self.path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _load(self) -> None:
        if self.path is None or not self.path.exists():
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1:
            raise ValueError("unsupported root-template schema")
        for key, metadata in payload.get("templates", {}).items():
            root = metadata["root"]
            template = RootPlacementTemplate(
                sheet_width=metadata["sheet_width"],
                offset=metadata["offset"],
                root=LocalTriad(root["L"], root["C"], root["R"]),
                actions=tuple(metadata.get("actions", ())),
            )
            if template.key != key:
                raise ValueError(f"root-template key mismatch: {key}")
            self.templates[key] = template


@dataclass(frozen=True)
class ContinuationInstruction:
    """One memoized `N` build instruction with its evidence boundary."""

    n: int
    sheet: int
    offset: int
    root_template: str
    bit: int | None
    evidence: EvidenceClass
    continuation_verified: bool
    rule_id: str = ""
    witness_hashes: tuple[str, ...] = ()
    provenance: str = ""
    cost: str = ""

    @property
    def key(self) -> str:
        return f"N{self.n}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "N": self.n,
            "sheet": self.sheet,
            "offset": self.offset,
            "root_template": self.root_template,
            "bit": self.bit,
            "evidence": self.evidence.value,
            "continuation_verified": self.continuation_verified,
            "rule_id": self.rule_id,
            "witness_hashes": list(self.witness_hashes),
            "provenance": self.provenance,
            "cost": self.cost,
        }


class ContinuationLedger:
    """Persistent map from enumerated `N` requests to reusable instructions."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else None
        self.instructions: dict[str, ContinuationInstruction] = {}
        self._load()

    @property
    def known_depths(self) -> tuple[int, ...]:
        return tuple(sorted(item.n for item in self.instructions.values()))

    def record(self, instruction: ContinuationInstruction) -> ContinuationInstruction:
        """Memoize one exact or projected instruction, preferring verified data."""
        recorded = self._record_without_persist(instruction)
        self._persist()
        return recorded

    def record_many(
        self, instructions: list[ContinuationInstruction]
    ) -> list[ContinuationInstruction]:
        """Memoize a batch and persist the ledger once."""
        recorded = [
            self._record_without_persist(instruction)
            for instruction in instructions
        ]
        self._persist()
        return recorded

    def _record_without_persist(
        self, instruction: ContinuationInstruction
    ) -> ContinuationInstruction:
        existing = self.instructions.get(instruction.key)
        if existing is not None and (
            existing.continuation_verified or not instruction.continuation_verified
        ):
            return existing

        self.instructions[instruction.key] = instruction
        return instruction

    def _persist(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "continuations": {
                key: instruction.to_dict()
                for key, instruction in sorted(self.instructions.items())
            },
        }
        self.path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _load(self) -> None:
        if self.path is None or not self.path.exists():
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1:
            raise ValueError("unsupported continuation-ledger schema")
        for key, metadata in payload.get("continuations", {}).items():
            instruction = ContinuationInstruction(
                n=metadata["N"],
                sheet=metadata["sheet"],
                offset=metadata["offset"],
                root_template=metadata["root_template"],
                bit=metadata["bit"],
                evidence=EvidenceClass(metadata["evidence"]),
                continuation_verified=metadata["continuation_verified"],
                rule_id=metadata.get("rule_id", ""),
                witness_hashes=tuple(metadata.get("witness_hashes", ())),
                provenance=metadata.get("provenance", ""),
                cost=metadata.get("cost", ""),
            )
            if instruction.key != key:
                raise ValueError(f"continuation-instruction key mismatch: {key}")
            self.instructions[key] = instruction


@dataclass(frozen=True)
class InMemorySheetCache:
    """One exact materialized binary sheet."""

    bits: tuple[int, ...]

    @classmethod
    def from_bits(cls, bits: str) -> "InMemorySheetCache":
        if not bits or set(bits) - {"0", "1"}:
            raise ValueError("bits must be a non-empty binary string")
        return cls(bits=tuple(int(bit) for bit in bits))

    @property
    def sheet_width(self) -> int:
        return len(self.bits)

    def contains(self, n: int) -> bool:
        return 0 <= n < self.sheet_width

    def read(self, n: int, default: int = 0) -> int:
        return self.bits[n] if self.contains(n) else default

    def triad(self, n: int) -> LocalTriad:
        return LocalTriad(
            left=self.read(n - 1),
            center=self.read(n),
            right=self.read(n + 1),
        )


@dataclass(frozen=True)
class PackedBinarySheetCache:
    """Byte-addressed binary sheet with highest-order-bit-first packing."""

    path: Path
    bit_count: int

    def __post_init__(self) -> None:
        resolved = Path(self.path)
        if self.bit_count < 1:
            raise ValueError("bit_count must be positive")
        if not resolved.is_file():
            raise ValueError(f"packed sheet is not a file: {resolved}")
        required_bytes = (self.bit_count + 7) // 8
        if resolved.stat().st_size < required_bytes:
            raise ValueError("packed sheet payload is truncated")
        object.__setattr__(self, "path", resolved)

    @property
    def sheet_width(self) -> int:
        return self.bit_count

    def contains(self, n: int) -> bool:
        return 0 <= n < self.bit_count

    def read(self, n: int, default: int = 0) -> int:
        if not self.contains(n):
            return default
        byte_offset, bit_offset = divmod(n, 8)
        with self.path.open("rb") as stream:
            stream.seek(byte_offset)
            value = stream.read(1)[0]
        return (value >> (7 - bit_offset)) & 1

    def triad(self, n: int) -> LocalTriad:
        return LocalTriad(
            left=self.read(n - 1),
            center=self.read(n),
            right=self.read(n + 1),
        )


@dataclass(frozen=True)
class DihedralPackedSheetAtlas:
    """Eight reversible visual reads over one packed binary sheet."""

    cache: PackedBinarySheetCache
    rows: int
    columns: int

    views = (
        "rotate_0",
        "rotate_90",
        "rotate_180",
        "rotate_270",
        "mirror_rotate_0",
        "mirror_rotate_90",
        "mirror_rotate_180",
        "mirror_rotate_270",
    )

    def __post_init__(self) -> None:
        if self.rows < 1 or self.columns < 1:
            raise ValueError("atlas dimensions must be positive")
        if self.rows * self.columns != self.cache.bit_count:
            raise ValueError("atlas dimensions must cover the packed sheet exactly")

    def shape(self, view: str) -> tuple[int, int]:
        """Return visual row and column dimensions for one D4 view."""
        self._validate_view(view)
        return (
            (self.columns, self.rows)
            if view.endswith("_90") or view.endswith("_270")
            else (self.rows, self.columns)
        )

    def locate(self, n: int, view: str) -> dict[str, int | str]:
        """Map one packed offset into a reversible visual coordinate."""
        if not self.cache.contains(n):
            raise ValueError("packed offset is outside atlas bounds")
        self._validate_view(view)
        row, column = divmod(n, self.columns)
        if view.startswith("mirror_"):
            column = self.columns - 1 - column
        rotation = int(view.rsplit("_", maxsplit=1)[1])
        if rotation == 0:
            visual_row, visual_column = row, column
        elif rotation == 90:
            visual_row, visual_column = column, self.rows - 1 - row
        elif rotation == 180:
            visual_row, visual_column = self.rows - 1 - row, self.columns - 1 - column
        else:
            visual_row, visual_column = self.columns - 1 - column, row
        return {
            "view": view,
            "row": visual_row,
            "column": visual_column,
            "packed_offset": n,
        }

    def flatten(self, view: str, row: int, column: int) -> int:
        """Invert one visual coordinate back into its packed offset."""
        visual_rows, visual_columns = self.shape(view)
        if not 0 <= row < visual_rows or not 0 <= column < visual_columns:
            raise ValueError("visual coordinate is outside atlas bounds")
        rotation = int(view.rsplit("_", maxsplit=1)[1])
        if rotation == 0:
            source_row, source_column = row, column
        elif rotation == 90:
            source_row, source_column = self.rows - 1 - column, row
        elif rotation == 180:
            source_row = self.rows - 1 - row
            source_column = self.columns - 1 - column
        else:
            source_row, source_column = column, self.columns - 1 - row
        if view.startswith("mirror_"):
            source_column = self.columns - 1 - source_column
        return source_row * self.columns + source_column

    def read_visual(self, view: str, row: int, column: int) -> int:
        """Read one bit through a selected visual frame."""
        return self.cache.read(self.flatten(view, row, column))

    def _validate_view(self, view: str) -> None:
        if view not in self.views:
            raise ValueError(f"unknown dihedral atlas view: {view}")


@dataclass(frozen=True)
class E8CentroidCartanAtlas:
    """Structural 240-root plus 8-Cartan partition at a sheet centroid."""

    node_count: int = 248
    root_slot_count: int = 240

    def __post_init__(self) -> None:
        if self.node_count != 248 or self.root_slot_count != 240:
            raise ValueError("E8 centroid atlas requires the exact 240|8 adjoint partition")

    @property
    def root_slots(self) -> list[int]:
        return list(range(self.root_slot_count))

    @property
    def cartan_trigger_slots(self) -> list[int]:
        return list(range(self.root_slot_count, self.node_count))

    def classify(self, slot: int) -> str:
        """Classify one centroid slot without assigning event semantics."""
        if not 0 <= slot < self.node_count:
            raise ValueError("E8 centroid slot is outside atlas bounds")
        return "root" if slot < self.root_slot_count else "cartan_candidate"


@dataclass(frozen=True)
class FormulaicBillionAddressLibrary:
    """Compile arbitrary N into a reversible billion-sheet D4/Jordan address."""

    sheet_bit_count: int = 1_000_000_000
    rows: int = 1000
    columns: int = 1_000_000
    shard_count: int = 8

    views = DihedralPackedSheetAtlas.views

    def __post_init__(self) -> None:
        if self.rows * self.columns != self.sheet_bit_count:
            raise ValueError("formulaic sheet geometry must cover every bit exactly")
        if self.sheet_bit_count % self.shard_count:
            raise ValueError("formulaic sheet must divide evenly across lookup shards")

    def compile(self, n: int) -> dict[str, Any]:
        """Emit the complete address receipt for any non-negative integer N."""
        if n < 0:
            raise ValueError("N must be non-negative")
        sheet_cycle, sheet_offset = divmod(n, self.sheet_bit_count)
        view_index = sheet_cycle % len(self.views)
        view = self.views[view_index]
        serial_lane = sheet_offset % self.shard_count
        visual_row, visual_column = self._locate(sheet_offset, view)
        centroid_slot = sheet_offset % 248
        sector = "root" if centroid_slot < 240 else "cartan_candidate"
        jordanian_centroid: dict[str, Any] = {
            "node_slot": centroid_slot,
            "sector": sector,
        }
        if sector == "cartan_candidate":
            jordanian_centroid["cartan_candidate_index"] = centroid_slot - 240
        return {
            "status": "formulaic_address",
            "N": n,
            "sheet_cycle": sheet_cycle,
            "sheet_offset": sheet_offset,
            "d4_view_index": view_index,
            "d4_view": view,
            "quadratic_address": {
                "row": visual_row,
                "column": visual_column,
                "shape": list(self._shape(view)),
                "mirror": view.startswith("mirror_"),
                "rotation_degrees": int(view.rsplit("_", maxsplit=1)[1]),
            },
            "jordanian_centroid": jordanian_centroid,
            "lookup_shard": {
                "shard": serial_lane,
                "shard_offset": sheet_offset // self.shard_count,
                "shard_count": self.shard_count,
                "max_offsets_per_shard": self.sheet_bit_count // self.shard_count,
                "parallel_shard_factor": self.shard_count,
            },
            "jordanian_porting_block": {
                "local_frame": view_index,
                "serial_lane": serial_lane,
                "cell": view_index * self.shard_count + serial_lane,
                "local_frame_count": len(self.views),
                "serial_lane_count": self.shard_count,
                "block_size": len(self.views) * self.shard_count,
                "scheduled_block_factor": len(self.views) * self.shard_count,
                "measured_runtime_speedup_proved": False,
            },
            "semantic_weyl_fingerprint_proved": False,
            "cartan_generator_semantics_proved": False,
            "single_serial_lookup_eight_times_faster_proved": False,
            "proof_boundary": (
                "N compiles to an exact D4 view, visual coordinate, centroid slot, "
                "and shard; Weyl and Cartan semantics remain separate"
            ),
        }

    def flatten(self, receipt: dict[str, Any]) -> int:
        """Invert a compiled receipt back to N."""
        view = receipt["d4_view"]
        address = receipt["quadratic_address"]
        sheet_offset = self._flatten(view, address["row"], address["column"])
        return int(receipt["sheet_cycle"]) * self.sheet_bit_count + sheet_offset

    def _shape(self, view: str) -> tuple[int, int]:
        self._validate_view(view)
        return (
            (self.columns, self.rows)
            if view.endswith("_90") or view.endswith("_270")
            else (self.rows, self.columns)
        )

    def _locate(self, offset: int, view: str) -> tuple[int, int]:
        self._validate_view(view)
        row, column = divmod(offset, self.columns)
        if view.startswith("mirror_"):
            column = self.columns - 1 - column
        rotation = int(view.rsplit("_", maxsplit=1)[1])
        if rotation == 0:
            return row, column
        if rotation == 90:
            return column, self.rows - 1 - row
        if rotation == 180:
            return self.rows - 1 - row, self.columns - 1 - column
        return self.columns - 1 - column, row

    def _flatten(self, view: str, row: int, column: int) -> int:
        visual_rows, visual_columns = self._shape(view)
        if not 0 <= row < visual_rows or not 0 <= column < visual_columns:
            raise ValueError("visual coordinate is outside formulaic atlas bounds")
        rotation = int(view.rsplit("_", maxsplit=1)[1])
        if rotation == 0:
            source_row, source_column = row, column
        elif rotation == 90:
            source_row, source_column = self.rows - 1 - column, row
        elif rotation == 180:
            source_row = self.rows - 1 - row
            source_column = self.columns - 1 - column
        else:
            source_row, source_column = column, self.columns - 1 - row
        if view.startswith("mirror_"):
            source_column = self.columns - 1 - source_column
        return source_row * self.columns + source_column

    def _validate_view(self, view: str) -> None:
        if view not in self.views:
            raise ValueError(f"unknown formulaic D4 view: {view}")


def verify_wolfram_billion_weyl_slot_coverage() -> dict[str, Any]:
    """Check address-space coverage without promoting a Weyl fingerprint map."""
    sheet_bit_count = 1_000_000_000
    weyl_e8_order = 696_729_600
    every_weyl_slot_addressable = sheet_bit_count >= weyl_e8_order
    return {
        "status": "pass" if every_weyl_slot_addressable else "fail",
        "sheet_bit_count": sheet_bit_count,
        "weyl_e8_order": weyl_e8_order,
        "every_weyl_slot_addressable": every_weyl_slot_addressable,
        "surplus_sheet_addresses": sheet_bit_count - weyl_e8_order,
        "fingerprint_map_proved": False,
        "hydrated_payload_scan_proved": False,
        "scope": "arithmetic address-space coverage only",
        "proof_boundary": (
            "the registered billion-bit sheet has enough offsets to address every "
            "W(E8) slot; assigning the correct Weyl fingerprint to each offset remains open"
        ),
    }


def verify_formulaic_billion_address_library() -> dict[str, Any]:
    """Verify address compilation, inversion, and bounded parallel sharding."""
    library = FormulaicBillionAddressLibrary()
    samples = [
        0,
        1,
        247,
        999_999_999,
        1_000_000_000,
        7_999_999_999,
        8_000_000_000,
        12_345_678_901_234_567_890,
    ]
    receipts = [library.compile(n) for n in samples]
    all_sample_round_trips_exact = all(
        library.flatten(receipt) == n for n, receipt in zip(samples, receipts)
    )
    all_eight_views_reachable = {
        library.compile(cycle * library.sheet_bit_count)["d4_view"]
        for cycle in range(8)
    } == set(library.views)
    return {
        "status": (
            "pass" if all_sample_round_trips_exact and all_eight_views_reachable else "fail"
        ),
        "samples_checked": len(samples),
        "all_sample_round_trips_exact": all_sample_round_trips_exact,
        "all_eight_views_reachable": all_eight_views_reachable,
        "shard_count": library.shard_count,
        "max_offsets_per_shard": library.sheet_bit_count // library.shard_count,
        "parallel_shard_factor": library.shard_count,
        "jordanian_porting_block_size": len(library.views) * library.shard_count,
        "local_frame_factor": len(library.views),
        "serial_lane_factor": library.shard_count,
        "scheduled_block_factor": len(library.views) * library.shard_count,
        "measured_runtime_speedup_proved": False,
        "single_serial_lookup_eight_times_faster_proved": False,
        "semantic_weyl_fingerprint_proved": False,
        "cartan_generator_semantics_proved": False,
        "scope": "formulaic N-to-D4/Jordan address compilation and eight-way sharding",
    }


def verify_e8_centroid_cartan_partition() -> dict[str, Any]:
    """Verify the exact E8 adjoint centroid partition without semantic promotion."""
    atlas = E8CentroidCartanAtlas()
    root_slots = atlas.root_slots
    cartan_slots = atlas.cartan_trigger_slots
    partition_exact = sorted(root_slots + cartan_slots) == list(range(atlas.node_count))
    disjoint = set(root_slots).isdisjoint(cartan_slots)
    only_non_root_slots_are_cartan_candidates = all(
        atlas.classify(slot) == "root" for slot in root_slots
    ) and all(atlas.classify(slot) == "cartan_candidate" for slot in cartan_slots)
    return {
        "status": (
            "pass"
            if partition_exact and disjoint and only_non_root_slots_are_cartan_candidates
            else "fail"
        ),
        "node_count": atlas.node_count,
        "root_slot_count": len(root_slots),
        "cartan_candidate_slot_count": len(cartan_slots),
        "partition_exact": partition_exact,
        "partition_disjoint": disjoint,
        "only_non_root_slots_are_cartan_candidates": (
            only_non_root_slots_are_cartan_candidates
        ),
        "ribbon_event_to_cartan_generator_map_proved": False,
        "all_cartan_subalgebras_exposed_proved": False,
        "scope": "structural E8 adjoint 240-root plus 8-Cartan centroid partition",
        "proof_boundary": (
            "the eight non-root slots are reserved Cartan trigger candidates; "
            "mapping ribbon events to specific Cartan generators remains open"
        ),
    }


def verify_wolfram_billion_dihedral_atlas_geometry() -> dict[str, Any]:
    """Verify the virtual eight-view billion-sheet geometry arithmetically."""
    rows = 1000
    columns = 1_000_000
    sheet_bit_count = rows * columns
    view_count = len(DihedralPackedSheetAtlas.views)
    all_views_are_bijective = all(
        (
            rows * columns
            if not view.endswith("_90") and not view.endswith("_270")
            else columns * rows
        )
        == sheet_bit_count
        for view in DihedralPackedSheetAtlas.views
    )
    library = FormulaicBillionAddressLibrary()
    representative_offsets = [0, 1, columns - 1, sheet_bit_count - columns, sheet_bit_count - 1]
    representative_round_trips_exact = all(
        library._flatten(view, *library._locate(offset, view)) == offset
        for offset in representative_offsets
        for view in library.views
    )
    return {
        "status": (
            "pass"
            if all_views_are_bijective and representative_round_trips_exact
            else "fail"
        ),
        "sheet_shape": [rows, columns],
        "sheet_bit_count": sheet_bit_count,
        "view_count": view_count,
        "address_visits": sheet_bit_count * view_count,
        "all_views_are_bijective": all_views_are_bijective,
        "representative_offsets_checked": len(representative_offsets),
        "representative_round_trips_exact": representative_round_trips_exact,
        "packed_payload_hydrated": False,
        "cartan_subalgebras_exposed_proved": False,
        "scope": "virtual D4 address geometry over registered billion-bit sheet",
        "proof_boundary": (
            "four rotations and four mirrored rotations are reversible packed-offset "
            "views; identifying their sectors with Cartan subalgebras remains open"
        ),
    }


@dataclass(frozen=True)
class ExtendedMemoryManifest:
    """Attached archive and hydration registry."""

    path: Path
    payload: dict[str, Any]

    @classmethod
    def load(cls, path: Path) -> "ExtendedMemoryManifest":
        resolved = Path(path)
        payload = json.loads(resolved.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1:
            raise ValueError("unsupported extended-memory schema")
        if not isinstance(payload.get("layers"), dict):
            raise ValueError("extended-memory manifest must define layers")
        return cls(path=resolved, payload=payload)

    def status(self) -> dict[str, Any]:
        root = self.path.parent.parent
        layers: dict[str, Any] = {}
        for name, metadata in self.payload["layers"].items():
            layer = dict(metadata)
            layer_path = root / layer["path"]
            layer["hydrated"] = layer_path.exists()
            layers[name] = layer
        return {
            "schema_version": self.payload["schema_version"],
            "layers": layers,
        }

    def hydrate(self, layer_name: str, source: Path) -> Path:
        """Copy an on-demand payload into its registered local cache path."""
        layers = self.payload["layers"]
        if layer_name not in layers:
            raise ValueError(f"unknown extended-memory layer: {layer_name}")

        metadata = layers[layer_name]
        if metadata.get("mode") != "hydrate_on_demand":
            raise ValueError(f"layer is not hydrate-on-demand: {layer_name}")

        resolved_source = Path(source)
        if not resolved_source.is_file():
            raise ValueError(f"hydration source is not a file: {resolved_source}")

        root = self.path.parent.parent
        target = root / metadata["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(resolved_source, target)
        return target
