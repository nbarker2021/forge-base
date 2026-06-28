"""Required reverse-recipe library for bounded binary atlas sheets."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from .atlas import BinaryRule, BondedFrames, load_binary_ribbon
from .normal_form import LocalTriad


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _triad_from_mask(mask: int) -> LocalTriad:
    return LocalTriad((mask >> 2) & 1, (mask >> 1) & 1, mask & 1)


def _iter_masks(bits: Iterator[int]) -> Iterator[int]:
    previous = 0
    try:
        current = next(bits)
    except StopIteration:
        return
    for following in bits:
        yield (previous << 2) | (current << 1) | following
        previous, current = current, following
    yield (previous << 2) | (current << 1)


def _iter_source_bits(source: Path, bit_count: int | None) -> tuple[int, Iterator[int]]:
    if source.suffix.lower() == ".json":
        ribbon = load_binary_ribbon(source, bit_limit=bit_count)
        return len(ribbon), (int(bit) for bit in ribbon)

    available_bits = source.stat().st_size * 8
    selected_bits = available_bits if bit_count is None else bit_count
    if not 0 < selected_bits <= available_bits:
        raise ValueError(f"bit_count must be in range 1..{available_bits}")

    def packed_bits() -> Iterator[int]:
        emitted = 0
        with source.open("rb") as stream:
            while emitted < selected_bits:
                byte = stream.read(1)
                if len(byte) != 1:
                    raise ValueError("packed atlas ended before bit_count")
                for shift in range(7, -1, -1):
                    if emitted == selected_bits:
                        return
                    yield (byte[0] >> shift) & 1
                    emitted += 1

    return selected_bits, packed_bits()


def _recipe_table(projector: BinaryRule, prior: BinaryRule) -> dict[str, Any]:
    inverse_masks = {
        emitted_bit: [
            mask
            for mask in range(8)
            if projector.emit(_triad_from_mask(mask)) == emitted_bit
        ]
        for emitted_bit in (0, 1)
    }
    recipes = {}
    for mask in range(8):
        triad = _triad_from_mask(mask)
        recipes[str(mask)] = {
            "recipe_id": mask,
            "downward": {
                "L": triad.left,
                "C": triad.center,
                "R": triad.right,
            },
            "frames": BondedFrames.from_triad(triad).to_dict(),
            "antipodal_lane": -1,
            "upward": {
                "projector_rule": projector.rule_id,
                "prior_rule": prior.rule_id,
                "prior_bit": prior.emit(triad),
                "correction_bit": projector.correction_against(prior, triad),
                "emitted_bit": projector.emit(triad),
            },
            "inverse_candidate_masks": inverse_masks[projector.emit(triad)],
        }
    return {
        "schema_version": 1,
        "recipes": recipes,
    }


@dataclass(frozen=True)
class ReverseAtlasLibrary:
    """Persisted O(1) map from bounded sheet addresses to reverse receipts."""

    path: Path
    manifest: dict[str, Any]
    recipes: dict[str, Any]

    @classmethod
    def compile(
        cls,
        *,
        source: Path,
        output: Path,
        projector: BinaryRule,
        prior: BinaryRule | None = None,
        bit_count: int | None = None,
    ) -> "ReverseAtlasLibrary":
        """Compile every observable edge once and persist its canonical recipe."""
        resolved_source = Path(source)
        if not resolved_source.is_file():
            raise ValueError(f"reverse-library source is not a file: {resolved_source}")
        selected_prior = prior or BinaryRule.from_rule_number(90)
        selected_count, bits = _iter_source_bits(resolved_source, bit_count)
        resolved_output = Path(output)
        resolved_output.mkdir(parents=True, exist_ok=True)
        map_path = resolved_output / "address_recipe_ids.bin"
        counts = [0] * 8
        digest = hashlib.sha256()
        with map_path.open("wb") as stream:
            for mask in _iter_masks(bits):
                stream.write(bytes([mask]))
                digest.update(bytes([mask]))
                counts[mask] += 1
        if sum(counts) != selected_count:
            raise ValueError("compiled address count does not match selected source bits")

        recipes_payload = _recipe_table(projector, selected_prior)
        recipes_path = resolved_output / "recipes.json"
        recipes_path.write_text(
            json.dumps(recipes_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest = {
            "schema_version": 1,
            "status": "pass",
            "source": str(resolved_source),
            "source_sha256": _sha256(resolved_source),
            "address_count": selected_count,
            "recipe_table_size": 8,
            "unique_observed_recipe_count": sum(count > 0 for count in counts),
            "recipe_counts": {str(mask): count for mask, count in enumerate(counts)},
            "recipe_map": "address_recipe_ids.bin",
            "recipe_map_sha256": digest.hexdigest(),
            "recipes": "recipes.json",
            "projector_rule": projector.rule_id,
            "prior_rule": selected_prior.rule_id,
            "antipodal_lane": -1,
            "lookup_complexity": "O(1)",
            "compile_scope": "bounded_observable_sheet",
            "cross_sheet_continuation_proved": False,
        }
        (resolved_output / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return cls.open(resolved_output)

    @classmethod
    def open(cls, path: Path) -> "ReverseAtlasLibrary":
        """Open and validate one persisted reverse library."""
        resolved = Path(path)
        manifest = json.loads((resolved / "manifest.json").read_text(encoding="utf-8"))
        recipes = json.loads(
            (resolved / manifest["recipes"]).read_text(encoding="utf-8")
        )
        if manifest.get("schema_version") != 1 or recipes.get("schema_version") != 1:
            raise ValueError("unsupported reverse-library schema")
        map_path = resolved / manifest["recipe_map"]
        if map_path.stat().st_size != manifest["address_count"]:
            raise ValueError("reverse-library recipe map size mismatch")
        if _sha256(map_path) != manifest["recipe_map_sha256"]:
            raise ValueError("reverse-library recipe map hash mismatch")
        return cls(path=resolved, manifest=manifest, recipes=recipes["recipes"])

    def lookup(self, n: int) -> dict[str, Any]:
        """Resolve one compiled address by a single recipe-map byte lookup."""
        if not 0 <= n < self.manifest["address_count"]:
            raise ValueError(
                f"address {n} out of reverse-library bounds "
                f"0..{self.manifest['address_count'] - 1}"
            )
        with (self.path / self.manifest["recipe_map"]).open("rb") as stream:
            stream.seek(n)
            recipe_id = stream.read(1)
        if len(recipe_id) != 1:
            raise ValueError(f"reverse-library read failed at address {n}")
        recipe = self.recipes[str(recipe_id[0])]
        return {
            "status": "resolved",
            "evidence": "reverse_library_exact",
            "N": n,
            **recipe,
        }


@dataclass(frozen=True)
class ReverseAtlasChain:
    """Ordered compiled-sheet registry for exact boundary-down backtracking."""

    path: Path
    layers: tuple[dict[str, Any], ...]

    @classmethod
    def open(cls, path: Path) -> "ReverseAtlasChain":
        """Open a chain whose libraries are relative to the registry file."""
        resolved = Path(path)
        payload = json.loads(resolved.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1:
            raise ValueError("unsupported reverse-chain schema")
        layers = tuple(payload.get("layers", ()))
        if not layers:
            raise ValueError("reverse chain must contain at least one layer")
        if [layer.get("depth") for layer in layers] != list(range(len(layers))):
            raise ValueError("reverse chain depths must be contiguous from zero")
        for layer in layers:
            ReverseAtlasLibrary.open(resolved.parent / layer["library"])
        return cls(path=resolved, layers=layers)

    def backtrack(self, n: int, *, depth: int | None = None) -> dict[str, Any]:
        """Return exact receipts from one compiled boundary down to root."""
        selected_depth = len(self.layers) - 1 if depth is None else depth
        if not 0 <= selected_depth < len(self.layers):
            raise ValueError(f"depth {selected_depth} out of reverse-chain bounds")
        hops = []
        for layer in reversed(self.layers[: selected_depth + 1]):
            library = ReverseAtlasLibrary.open(self.path.parent / layer["library"])
            hops.append(
                {
                    "depth": layer["depth"],
                    "library": layer["library"],
                    "transform": layer.get("transform"),
                    "receipt": library.lookup(n),
                }
            )
        return {
            "status": "resolved",
            "evidence": "reverse_chain_exact",
            "N": n,
            "selected_depth": selected_depth,
            "hop_count": len(hops),
            "lookup_complexity": "O(fixed_chain_depth)",
            "cross_sheet_continuation_proved": False,
            "hops": hops,
        }
