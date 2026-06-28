"""Lossless hierarchical addresses over reusable oriented binary sheets."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PoleHamiltonianGeometry:
    """Split one outer pole into local 3|2 asymmetric Hamiltonian cells."""

    carrier_sheets: int = 50_000_000
    cell_slots: int = 5
    hamiltonian_slots: int = 3

    def __post_init__(self) -> None:
        if self.carrier_sheets <= 0 or self.carrier_sheets % self.cell_slots:
            raise ValueError("carrier_sheets must be a positive multiple of cell_slots")
        if not 0 < self.hamiltonian_slots < self.cell_slots:
            raise ValueError("hamiltonian_slots must define a non-empty asymmetric split")

    @property
    def block_count(self) -> int:
        return self.carrier_sheets // self.cell_slots

    @property
    def hamiltonian_sheets(self) -> int:
        return self.block_count * self.hamiltonian_slots

    @property
    def residual_sheets(self) -> int:
        return self.carrier_sheets - self.hamiltonian_sheets

    def decode(self, outer_sheet: int) -> dict[str, int | str]:
        if not 0 <= outer_sheet < self.carrier_sheets:
            raise ValueError(
                f"outer sheet {outer_sheet} out of pole bounds 0..{self.carrier_sheets - 1}"
            )
        block, lane = divmod(outer_sheet, self.cell_slots)
        sector = "hamiltonian" if lane < self.hamiltonian_slots else "residual"
        return {"block": block, "lane": lane, "sector": sector}

    def encode(self, address: dict[str, int | str]) -> int:
        block = int(address["block"])
        lane = int(address["lane"])
        if not 0 <= block < self.block_count:
            raise ValueError("block out of pole bounds")
        if not 0 <= lane < self.cell_slots:
            raise ValueError("lane out of pole bounds")
        return block * self.cell_slots + lane

    def to_dict(self) -> dict[str, Any]:
        return {
            "carrier_sheets": self.carrier_sheets,
            "cell_slots": self.cell_slots,
            "hamiltonian_slots": self.hamiltonian_slots,
            "residual_slots": self.cell_slots - self.hamiltonian_slots,
            "block_count": self.block_count,
            "hamiltonian_sheets": self.hamiltonian_sheets,
            "residual_sheets": self.residual_sheets,
            "ratio": "3|2",
        }


@dataclass(frozen=True)
class MacroStep:
    """One macro-sheet lookup and its selected ordering."""

    macro_bit: int
    ordering: int

    def to_dict(self) -> dict[str, int]:
        return {
            "macro_bit": self.macro_bit,
            "ordering": self.ordering,
        }


@dataclass(frozen=True)
class HierarchicalAtlasAddress:
    """One expanded mixed-radix address inside the hierarchical atlas."""

    local_bit: int
    local_rotation_degrees: int
    macro_steps: tuple[MacroStep, ...]
    start_rotation_degrees: int = 180

    def to_dict(self) -> dict[str, Any]:
        return {
            "local_bit": self.local_bit,
            "local_rotation_degrees": self.local_rotation_degrees,
            "start_rotation_degrees": self.start_rotation_degrees,
            "macro_steps": [step.to_dict() for step in self.macro_steps],
        }


@dataclass(frozen=True)
class HierarchicalAtlasGeometry:
    """Compile flat requests into reusable local and macro sheet instructions."""

    local_bits: int = 1_000_000
    local_rotations: int = 4
    macro_bits: int = 1_000_000_000
    macro_orderings: int = 8
    macro_levels: int = 4
    start_rotation_degrees: int = 180

    def __post_init__(self) -> None:
        values = (
            self.local_bits,
            self.local_rotations,
            self.macro_bits,
            self.macro_orderings,
            self.macro_levels,
        )
        if any(value <= 0 for value in values):
            raise ValueError("hierarchical atlas dimensions must be positive")
        if self.local_rotations != 4:
            raise ValueError("local_rotations must be 4 for the bonded LCR frames")
        if self.start_rotation_degrees != 180:
            raise ValueError("start_rotation_degrees must be 180")

    @property
    def capacity(self) -> int:
        return (
            self.local_bits
            * self.local_rotations
            * (self.macro_bits * self.macro_orderings) ** self.macro_levels
        )

    @staticmethod
    def _rotation_degrees(rotation_index: int) -> int:
        return rotation_index * 90

    @staticmethod
    def _rotation_index(rotation_degrees: int) -> int:
        if rotation_degrees not in (0, 90, 180, 270):
            raise ValueError("local_rotation_degrees must be one of 0, 90, 180, 270")
        return rotation_degrees // 90

    def decode(self, n: int) -> HierarchicalAtlasAddress:
        """Expand one flat request into its exact reusable build instruction."""
        if not 0 <= n < self.capacity:
            raise ValueError(
                f"address {n} out of hierarchical atlas bounds 0..{self.capacity - 1}"
            )
        remainder = n
        local_bit = remainder % self.local_bits
        remainder //= self.local_bits
        rotation_index = remainder % self.local_rotations
        remainder //= self.local_rotations
        macro_steps = []
        for _ in range(self.macro_levels):
            macro_bit = remainder % self.macro_bits
            remainder //= self.macro_bits
            ordering = remainder % self.macro_orderings
            remainder //= self.macro_orderings
            macro_steps.append(MacroStep(macro_bit=macro_bit, ordering=ordering))
        return HierarchicalAtlasAddress(
            local_bit=local_bit,
            local_rotation_degrees=self._rotation_degrees(rotation_index),
            macro_steps=tuple(macro_steps),
            start_rotation_degrees=self.start_rotation_degrees,
        )

    def encode(self, address: HierarchicalAtlasAddress) -> int:
        """Flatten one build instruction without losing any address digits."""
        if not 0 <= address.local_bit < self.local_bits:
            raise ValueError("local_bit out of hierarchical atlas bounds")
        if address.start_rotation_degrees != self.start_rotation_degrees:
            raise ValueError("address start rotation does not match atlas geometry")
        if len(address.macro_steps) != self.macro_levels:
            raise ValueError(f"address must contain exactly {self.macro_levels} macro steps")

        result = address.local_bit
        scale = self.local_bits
        result += self._rotation_index(address.local_rotation_degrees) * scale
        scale *= self.local_rotations
        for step in address.macro_steps:
            if not 0 <= step.macro_bit < self.macro_bits:
                raise ValueError("macro_bit out of hierarchical atlas bounds")
            if not 0 <= step.ordering < self.macro_orderings:
                raise ValueError("ordering out of hierarchical atlas bounds")
            result += step.macro_bit * scale
            scale *= self.macro_bits
            result += step.ordering * scale
            scale *= self.macro_orderings
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "formula": "local_bits * local_rotations * (macro_bits * macro_orderings) ** macro_levels",
            "local_bits": self.local_bits,
            "local_rotations": self.local_rotations,
            "macro_bits": self.macro_bits,
            "macro_orderings": self.macro_orderings,
            "macro_levels": self.macro_levels,
            "start_rotation_degrees": self.start_rotation_degrees,
            "capacity": self.capacity,
            "capacity_decimal": str(self.capacity),
        }

    def route(self, n: int) -> dict[str, Any]:
        """Emit an honest build instruction for one addressable request."""
        return {
            "N": n,
            "status": "addressable",
            "evidence": "registered_route",
            "addressable": True,
            "semantic_landing_verified": False,
            "cross_sheet_continuation_proved": False,
            "bit": None,
            "geometry": self.to_dict(),
            "outer_pole": PoleHamiltonianGeometry().to_dict(),
            "address": self.decode(n).to_dict(),
            "claim_boundary": (
                "The mixed-radix path is lossless and directly traversable. "
                "A bit value requires a separately verified semantic landing."
            ),
        }
