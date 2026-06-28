"""Oriented binary atlas cells for downward reads and upward projections."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .normal_form import LocalTriad


def _validate_bit(value: int) -> int:
    bit = int(value)
    if bit not in (0, 1):
        raise ValueError(f"expected binary bit, got {value!r}")
    return bit


@dataclass(frozen=True)
class SignedBooleanRead:
    """One Boolean value plus the reusable negative observation lane."""

    value: int
    antipodal_lane: int = -1

    def __post_init__(self) -> None:
        _validate_bit(self.value)
        if self.antipodal_lane != -1:
            raise ValueError("antipodal_lane must be -1")

    @property
    def boolean_complement(self) -> int:
        """Return Boolean NOT without conflating it with geometric reversal."""
        return 1 - self.value

    def to_dict(self) -> dict[str, int]:
        return {
            "value": self.value,
            "antipodal_lane": self.antipodal_lane,
        }


@dataclass(frozen=True)
class BinaryRule:
    """Any radius-1 binary Boolean projector `f: {0,1}^3 -> {0,1}`."""

    rule_id: int | str
    truth_table: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.truth_table) != 8:
            raise ValueError("truth_table must contain exactly 8 bits")
        for bit in self.truth_table:
            _validate_bit(bit)

    @classmethod
    def from_rule_number(cls, rule_number: int) -> "BinaryRule":
        """Build one elementary CA profile using Wolfram's 0..255 numbering."""
        if not 0 <= rule_number <= 255:
            raise ValueError("rule_number must be in range 0..255")
        return cls(
            rule_id=rule_number,
            truth_table=tuple((rule_number >> mask) & 1 for mask in range(8)),
        )

    @classmethod
    def from_truth_table(cls, bits: str, *, rule_id: str) -> "BinaryRule":
        """Build a profile from mask-order outputs `000..111`."""
        if len(bits) != 8 or set(bits) - {"0", "1"}:
            raise ValueError("truth-table bits must be an 8-character binary string")
        return cls(rule_id=rule_id, truth_table=tuple(int(bit) for bit in bits))

    def emit(self, triad: LocalTriad) -> int:
        mask = (triad.left << 2) | (triad.center << 1) | triad.right
        return self.truth_table[mask]

    def correction_against(self, prior: "BinaryRule", triad: LocalTriad) -> int:
        """Return the one-bit residual needed to turn `prior` into this rule."""
        return self.emit(triad) ^ prior.emit(triad)


@dataclass(frozen=True)
class BondedFrames:
    """Four observer frames around one downward LCR edge."""

    observe_c: LocalTriad
    bridge_r: LocalTriad
    antipodal_c: LocalTriad
    bridge_l: LocalTriad

    @classmethod
    def from_triad(cls, triad: LocalTriad) -> "BondedFrames":
        left, center, right = triad.left, triad.center, triad.right
        return cls(
            observe_c=triad,
            bridge_r=LocalTriad(center, right, left),
            antipodal_c=LocalTriad(right, center, left),
            bridge_l=LocalTriad(right, left, center),
        )

    @staticmethod
    def _frame(centroid: str, triad: LocalTriad) -> dict[str, Any]:
        return {
            "centroid": centroid,
            "triad": [triad.left, triad.center, triad.right],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "0": self._frame("C", self.observe_c),
            "90": self._frame("R", self.bridge_r),
            "180": self._frame("C", self.antipodal_c),
            "270": self._frame("L", self.bridge_l),
        }


@dataclass(frozen=True)
class OrientedAtlasCell:
    """One directly readable ribbon edge and its upward projection receipt."""

    n: int
    downward: LocalTriad
    frames: BondedFrames
    upward: dict[str, Any]
    source_backend: str
    antipodal_lane: int = -1

    def to_dict(self) -> dict[str, Any]:
        return {
            "N": self.n,
            "source_backend": self.source_backend,
            "read_semantics": "downward_temporal_ribbon",
            "downward": {
                "L": self.downward.left,
                "C": self.downward.center,
                "R": self.downward.right,
            },
            "signed_reads": {
                "L": SignedBooleanRead(self.downward.left).to_dict(),
                "C": SignedBooleanRead(self.downward.center).to_dict(),
                "R": SignedBooleanRead(self.downward.right).to_dict(),
            },
            "antipodal_lane": self.antipodal_lane,
            "frames": self.frames.to_dict(),
            "upward": self.upward,
        }


@dataclass(frozen=True)
class OrientedBinaryAtlas:
    """O(1) addressable atlas over one hydrated binary ribbon."""

    bits: tuple[int, ...]

    @classmethod
    def from_bits(cls, bits: str) -> "OrientedBinaryAtlas":
        if not bits or set(bits) - {"0", "1"}:
            raise ValueError("bits must be a non-empty binary string")
        return cls(bits=tuple(int(bit) for bit in bits))

    def _read(self, n: int, default: int = 0) -> int:
        return self.bits[n] if 0 <= n < len(self.bits) else default

    def cell(
        self,
        n: int,
        *,
        projector: BinaryRule,
        prior: BinaryRule | None = None,
    ) -> OrientedAtlasCell:
        """Read one ribbon edge and project one selected Boolean rule upward."""
        return _build_cell(
            n=n,
            bit_count=len(self.bits),
            read=self._read,
            projector=projector,
            prior=prior,
            source_backend="materialized_bits",
        )

    def project_to_packed(
        self,
        output: Path,
        *,
        projector: BinaryRule,
        prior: BinaryRule | None = None,
        start: int = 0,
        stop: int | None = None,
    ) -> dict[str, Any]:
        """Project one observable ribbon interval into a packed output sheet."""
        return _project_to_packed(
            output=output,
            start=start,
            stop=len(self.bits) if stop is None else stop,
            bit_count=len(self.bits),
            read=self._read,
            projector=projector,
            prior=prior,
            source_backend="materialized_bits",
        )


@dataclass(frozen=True)
class PackedBinaryAtlas:
    """Random-access atlas over an MSB-first packed byte stream."""

    path: Path
    bit_count: int

    @classmethod
    def from_file(
        cls,
        path: Path,
        *,
        bit_count: int | None = None,
    ) -> "PackedBinaryAtlas":
        resolved = Path(path)
        if not resolved.is_file():
            raise ValueError(f"packed atlas source is not a file: {resolved}")
        available_bits = resolved.stat().st_size * 8
        selected_bits = available_bits if bit_count is None else bit_count
        if not 0 < selected_bits <= available_bits:
            raise ValueError(
                f"bit_count must be in range 1..{available_bits}, got {selected_bits}"
            )
        return cls(path=resolved, bit_count=selected_bits)

    def _read(self, n: int, default: int = 0) -> int:
        if not 0 <= n < self.bit_count:
            return default
        with self.path.open("rb") as stream:
            stream.seek(n // 8)
            byte = stream.read(1)
        if len(byte) != 1:
            raise ValueError(f"packed atlas read failed at bit address {n}")
        return (byte[0] >> (7 - (n % 8))) & 1

    def cell(
        self,
        n: int,
        *,
        projector: BinaryRule,
        prior: BinaryRule | None = None,
    ) -> OrientedAtlasCell:
        """Read one packed ribbon edge without materializing the full tape."""
        return _build_cell(
            n=n,
            bit_count=self.bit_count,
            read=self._read,
            projector=projector,
            prior=prior,
            source_backend="packed_msb_first",
        )

    def project_to_packed(
        self,
        output: Path,
        *,
        projector: BinaryRule,
        prior: BinaryRule | None = None,
        start: int = 0,
        stop: int | None = None,
    ) -> dict[str, Any]:
        """Project a packed interval while retaining only one source byte."""
        cached_index = -1
        cached_value = 0

        with self.path.open("rb") as stream:

            def read(n: int, default: int = 0) -> int:
                nonlocal cached_index, cached_value
                if not 0 <= n < self.bit_count:
                    return default
                byte_index = n // 8
                if byte_index != cached_index:
                    stream.seek(byte_index)
                    byte = stream.read(1)
                    if len(byte) != 1:
                        raise ValueError(f"packed atlas read failed at bit address {n}")
                    cached_index = byte_index
                    cached_value = byte[0]
                return (cached_value >> (7 - (n % 8))) & 1

            return _project_to_packed(
                output=output,
                start=start,
                stop=self.bit_count if stop is None else stop,
                bit_count=self.bit_count,
                read=read,
                projector=projector,
                prior=prior,
                source_backend="packed_msb_first",
            )


def _project_to_packed(
    *,
    output: Path,
    start: int,
    stop: int,
    bit_count: int,
    read: Callable[[int, int], int],
    projector: BinaryRule,
    prior: BinaryRule | None,
    source_backend: str,
) -> dict[str, Any]:
    """Project a bounded ribbon interval and emit an MSB-first packed receipt."""
    if not 0 <= start <= stop <= bit_count:
        raise ValueError(f"source range must satisfy 0 <= start <= stop <= {bit_count}")
    selected_prior = prior or BinaryRule.from_rule_number(90)
    projected = bytearray()
    current_byte = 0
    bit_offset = 0
    correction_count = 0
    bit_digest = hashlib.sha256()

    for n in range(start, stop):
        downward = LocalTriad(read(n - 1, 0), read(n, 0), read(n + 1, 0))
        emitted_bit = projector.emit(downward)
        correction_count += projector.correction_against(selected_prior, downward)
        bit_digest.update(bytes([emitted_bit]))
        current_byte |= emitted_bit << (7 - bit_offset)
        bit_offset += 1
        if bit_offset == 8:
            projected.append(current_byte)
            current_byte = 0
            bit_offset = 0
    if bit_offset:
        projected.append(current_byte)

    resolved_output = Path(output)
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_bytes(projected)
    return {
        "status": "pass",
        "source_backend": source_backend,
        "antipodal_lane": -1,
        "source_range": {"start": start, "stop": stop},
        "projected_bits": stop - start,
        "packed_bytes": len(projected),
        "packing": "MSB-first; final byte zero-padded on the right",
        "projector_rule": projector.rule_id,
        "prior_rule": selected_prior.rule_id,
        "correction_count": correction_count,
        "output": str(resolved_output),
        "output_sha256": hashlib.sha256(projected).hexdigest(),
        "bit_sha256": bit_digest.hexdigest(),
    }


def _build_cell(
    *,
    n: int,
    bit_count: int,
    read: Callable[[int, int], int],
    projector: BinaryRule,
    prior: BinaryRule | None,
    source_backend: str,
) -> OrientedAtlasCell:
    if not 0 <= n < bit_count:
        raise ValueError(f"address {n} out of atlas bounds 0..{bit_count - 1}")
    selected_prior = prior or BinaryRule.from_rule_number(90)
    downward = LocalTriad(read(n - 1, 0), read(n, 0), read(n + 1, 0))
    correction = projector.correction_against(selected_prior, downward)
    upward = {
        "semantics": "selected_boolean_projector_applied_to_downward_edge",
        "projector_rule": projector.rule_id,
        "prior_rule": selected_prior.rule_id,
        "prior_bit": selected_prior.emit(downward),
        "correction_bit": correction,
        "emitted_bit": projector.emit(downward),
    }
    return OrientedAtlasCell(
        n=n,
        downward=downward,
        frames=BondedFrames.from_triad(downward),
        upward=upward,
        source_backend=source_backend,
    )


def open_binary_atlas(
    path: Path,
    *,
    bit_count: int | None = None,
) -> OrientedBinaryAtlas | PackedBinaryAtlas:
    """Open JSON ribbons as materialized bits and other files as packed bytes."""
    resolved = Path(path)
    if resolved.suffix.lower() == ".json":
        return OrientedBinaryAtlas.from_bits(
            load_binary_ribbon(resolved, bit_limit=bit_count)
        )
    return PackedBinaryAtlas.from_file(resolved, bit_count=bit_count)


def load_binary_ribbon(path: Path, *, bit_limit: int | None = None) -> str:
    """Load Wolfram JSON lists, canonical witnesses, or packed MSB-first bytes."""
    resolved = Path(path)
    if resolved.suffix.lower() == ".json":
        payload = json.loads(resolved.read_text(encoding="utf-8"))
        if isinstance(payload, list) and payload and payload[0] == "List":
            bits = "".join(str(_validate_bit(bit)) for bit in payload[1:])
        elif isinstance(payload, dict) and isinstance(payload.get("center_bits"), str):
            bits = payload["center_bits"]
        else:
            raise ValueError("unsupported JSON binary-ribbon format")
    else:
        bits = "".join(
            str((byte >> shift) & 1)
            for byte in resolved.read_bytes()
            for shift in range(7, -1, -1)
        )
    if bit_limit is not None:
        if bit_limit < 0:
            raise ValueError("bit_limit must be >= 0")
        bits = bits[:bit_limit]
    if not bits or set(bits) - {"0", "1"}:
        raise ValueError("loaded ribbon must contain at least one binary bit")
    return bits
