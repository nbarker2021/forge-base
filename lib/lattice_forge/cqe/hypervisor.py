"""CQE managed ribbon hypervisor.

This module is intentionally dependency-free. It gives the larger Rule 30 and
D4 surfaces a concrete runtime edge: take a host ribbon, find only the sparse
podal lock windows worth touching, and return an output ribbon with receipts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


Decision = str
RibbonInput = bytes | bytearray | str | Iterable[int]


@dataclass(frozen=True)
class D4Token:
    """A D4 plot token that always carries a pode and its antipode."""

    index: int
    pode: int
    antipode: int
    orbit: int
    sheet: int
    spin_vignette: tuple[int, int]
    cartan_slot: int
    time_polarity: int
    write_record: int

    @classmethod
    def from_bit(cls, index: int, bit: int, write_record: int | None = None) -> "D4Token":
        pode = bit & 1
        antipode = 1 - pode
        recorded = antipode if write_record is None else write_record & 1
        return cls(
            index=index,
            pode=pode,
            antipode=antipode,
            orbit=index % 4,
            sheet=pode,
            spin_vignette=(index % 4, pode),
            cartan_slot=(index % 8) + 1,
            time_polarity=1 if index % 2 == 0 else -1,
            write_record=recorded,
        )

    @property
    def is_closed(self) -> bool:
        """A computation closes only when the write recorded the antipode."""

        return self.write_record == self.antipode

    @property
    def closure_state(self) -> str:
        return "CLOSED" if self.is_closed else "ESCROW"


@dataclass(frozen=True)
class ReceiptPortal:
    """Local C seam as 2x2 sheet swap against an antipode sheet."""

    window: tuple[int, int]
    source_2x2: tuple[tuple[int, int], tuple[int, int]]
    antipode_2x2: tuple[tuple[int, int], tuple[int, int]]
    center_2x2: tuple[tuple[int, int], tuple[int, int]]
    xor_left: tuple[tuple[int, int], tuple[int, int]]
    xor_right: tuple[tuple[int, int], tuple[int, int]]
    direction: str
    landing_pad: tuple[tuple[int, int], tuple[int, int]]
    action_path: tuple[str, ...]
    actuation_beat: tuple[str, str, str, str] = ("READ", "CENTER", "TURN", "WRITE")


@dataclass(frozen=True)
class RibbonReceipt:
    """A receipt for one CQE pressure decision."""

    decision: Decision
    reason: str
    window: tuple[int, int]
    dr: int
    savings: int
    guidance: str = "coast; no propagation lane required"
    propagation_lanes: tuple[str, ...] = ()
    need: str = ""
    portal: ReceiptPortal | None = None
    portal_stack: tuple[ReceiptPortal, ...] = ()
    depth_scale: int = 0


@dataclass(frozen=True)
class ManagedRibbon:
    """The emitted ribbon and the receipts proving how CQE touched it."""

    input: bytes
    output: bytes
    decisions: tuple[Decision, ...]
    receipts: tuple[RibbonReceipt, ...]
    savings: int


class CQEHypervisor:
    """Sparse backpressure valve for ordinary computation ribbons."""

    def __init__(self, idempotent_validations: Mapping[bytes, bytes] | None = None) -> None:
        self.idempotent_validations = dict(idempotent_validations or {})

    def manage(self, ribbon: RibbonInput) -> ManagedRibbon:
        data = _coerce_ribbon(ribbon)
        locks = _podal_locks(data)
        if not locks:
            receipt = RibbonReceipt(
                decision="COAST",
                reason="no bonded 2x2 podal lock",
                window=(0, len(data) * 8),
                dr=0,
                savings=1,
                guidance="coast; no propagation lane required",
                portal=_portal_for_window(0, len(data) * 8, "COAST"),
                portal_stack=(),
                depth_scale=0,
            )
            return ManagedRibbon(data, data, ("COAST",), (receipt,), 1)

        start_bit, width = locks[0]
        portal_stack = tuple(_portal_for_window(start, lock_width, "NUDGE_R") for start, lock_width in locks)
        window_bytes = _window_bytes(data, start_bit, width)
        dr = _digital_root(sum(window_bytes))
        if window_bytes in self.idempotent_validations:
            output = self.idempotent_validations[window_bytes]
            receipt = RibbonReceipt(
                decision="RETIE",
                reason="known idempotent validation retied to podal antipode",
                window=(0, width),
                dr=dr,
                savings=width,
                guidance="validation is idempotent; shortcut to resolved antipode",
                propagation_lanes=(
                    "L:reuse-known-read",
                    "C:preserve-centroid",
                    "R:emit-retied-antipode",
                ),
                need="record shortcut receipt before continuing",
                portal=_portal_for_window(0, width, "RETIE"),
                portal_stack=tuple(
                    _portal_for_window(0, lock_width, "RETIE") for _start, lock_width in locks
                ),
                depth_scale=len(locks),
            )
            return ManagedRibbon(data, output, ("RETIE",), (receipt,), width)

        output = bytearray(data)
        _write_bit(output, max(0, start_bit - 1), 1)
        receipt = RibbonReceipt(
            decision="NUDGE_R",
            reason="bonded 2x2 podal lock resolved by right write nudge",
            window=(0, width),
            dr=dr,
            savings=0,
            guidance="reading exceeds resolving; install right-write back-propagation lanes",
            propagation_lanes=(
                "L:freeze-read-window",
                "C:recenter-centroid",
                "R:write-antipode-correction",
            ),
            need="reduce unresolved read pressure before continuing",
            portal=_portal_for_window(0, width, "NUDGE_R"),
            portal_stack=portal_stack,
            depth_scale=len(portal_stack),
        )
        return ManagedRibbon(data, bytes(output), ("NUDGE_R",), (receipt,), 0)


def manage_ribbon(ribbon: RibbonInput) -> ManagedRibbon:
    """Manage a ribbon with the default CQE hypervisor."""

    return CQEHypervisor().manage(ribbon)


def _coerce_ribbon(ribbon: RibbonInput) -> bytes:
    if isinstance(ribbon, bytes):
        return ribbon
    if isinstance(ribbon, bytearray):
        return bytes(ribbon)
    if isinstance(ribbon, str):
        return ribbon.encode("utf-8")
    bits = [int(bit) & 1 for bit in ribbon]
    out = bytearray((len(bits) + 7) // 8)
    for index, bit in enumerate(bits):
        if bit:
            _write_bit(out, index, 1)
    return bytes(out)


def _first_podal_lock(data: bytes) -> tuple[int, int] | None:
    locks = _podal_locks(data)
    return locks[0] if locks else None


def _podal_locks(data: bytes) -> tuple[tuple[int, int], ...]:
    bits = _bits(data)
    locks: list[tuple[int, int]] = []
    for start in range(0, max(0, len(bits) - 3), 4):
        window = bits[start : start + 4]
        if len(window) == 4 and all(window):
            locks.append((start, 4))
    return tuple(locks)


def _bits(data: bytes) -> list[int]:
    return [(byte >> offset) & 1 for byte in data for offset in range(7, -1, -1)]


def _window_bytes(data: bytes, start_bit: int, width: int) -> bytes:
    bits = _bits(data)[start_bit : start_bit + width]
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return bytes([value])


def _write_bit(data: bytearray, bit_index: int, value: int) -> None:
    byte_index = bit_index // 8
    while byte_index >= len(data):
        data.append(0)
    bit_offset = 7 - (bit_index % 8)
    mask = 1 << bit_offset
    if value:
        data[byte_index] |= mask
    else:
        data[byte_index] &= ~mask


def _digital_root(value: int) -> int:
    if value == 0:
        return 0
    return 1 + ((value - 1) % 9)


def _portal_for_window(start_bit: int, width: int, decision: str) -> ReceiptPortal:
    source = ((1, 1), (1, 1)) if decision != "COAST" else ((0, 0), (0, 0))
    antipode = _flip_2x2(source)
    center = ((1, 0), (0, 1))
    xor_left = _xor_2x2(antipode, center)
    xor_right = _xor_2x2(source, center)
    direction = "R" if decision == "NUDGE_R" else "C"
    landing = ((1, 1), (1, 0)) if decision == "NUDGE_R" else source
    if decision == "COAST":
        path = ("hold-c",)
    elif decision == "RETIE":
        path = ("swap-source-2x2-with-antipode-2x2", "emit-retied-antipode")
    else:
        path = ("xor-right-vs-center", "swap-source-2x2-with-antipode-2x2")
    return ReceiptPortal(
        window=(start_bit, width),
        source_2x2=source,
        antipode_2x2=antipode,
        center_2x2=center,
        xor_left=xor_left,
        xor_right=xor_right,
        direction=direction,
        landing_pad=landing,
        action_path=path,
    )


def _flip_2x2(sheet: tuple[tuple[int, int], tuple[int, int]]) -> tuple[tuple[int, int], tuple[int, int]]:
    return tuple(tuple(1 - bit for bit in row) for row in sheet)  # type: ignore[return-value]


def _mirror_2x2(sheet: tuple[tuple[int, int], tuple[int, int]]) -> tuple[tuple[int, int], tuple[int, int]]:
    return tuple(tuple(reversed(row)) for row in sheet)  # type: ignore[return-value]


def _xor_2x2(
    left: tuple[tuple[int, int], tuple[int, int]],
    right: tuple[tuple[int, int], tuple[int, int]],
) -> tuple[tuple[int, int], tuple[int, int]]:
    return tuple(
        tuple(a ^ b for a, b in zip(left_row, right_row))
        for left_row, right_row in zip(left, right)
    )  # type: ignore[return-value]
