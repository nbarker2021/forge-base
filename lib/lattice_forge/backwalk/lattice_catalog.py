from __future__ import annotations

from typing import Any

from ..ledger.build import NIEMEIER_FORMS
from ..ledger.roots import parse_root_system_label
from ..seed import SeedStore
from ..terminal_tree import build_terminal_composition_tree
from .schema import WorkStore


def _component_product_label(components: list[tuple[str, int, int]]) -> str:
    parts = []
    for fam, rank, mult in components:
        label = f"{fam}{rank}"
        parts.append(f"{mult}x{label}" if mult > 1 else label)
    return " + ".join(parts)


def materialize_lattice_catalog(store: WorkStore) -> dict[str, Any]:
    """All lattice forms accessible to each 24D Niemeier terminal (product, byproduct, terminal)."""
    count = 0
    with SeedStore.packaged().ledger() as ledger:
        for terminal_id, root_system, coxeter_h, note in NIEMEIER_FORMS:
            store.insert_lattice_form(
                lattice_form_id=f"lf:{terminal_id}:terminal",
                terminal_24d_id=terminal_id,
                access_kind="terminal_24d",
                root_system_label=root_system,
                payload={
                    "coxeter_number": coxeter_h,
                    "note": note,
                    "role": "Niemeier terminal shell",
                },
                evidence_level="exact" if root_system != "rootless" else "template",
            )
            count += 1

            if root_system == "rootless":
                continue

            components = parse_root_system_label(root_system)
            product_label = _component_product_label(components)
            store.insert_lattice_form(
                lattice_form_id=f"lf:{terminal_id}:product:{product_label}",
                terminal_24d_id=terminal_id,
                access_kind="product",
                root_system_label=product_label,
                payload={"components": components, "composition": "direct_sum"},
                evidence_level="exact",
            )
            count += 1

            tree = build_terminal_composition_tree(ledger, terminal_id)
            closure = tree.get("closure_residue") or {}
            store.insert_lattice_form(
                lattice_form_id=f"lf:{terminal_id}:byproduct:glue_residue",
                terminal_24d_id=terminal_id,
                access_kind="byproduct",
                root_system_label=root_system,
                payload={
                    "closure_residue": closure,
                    "glue_requirements": tree.get("legacy_glue_records"),
                },
                evidence_level="template",
            )
            count += 1

            for fam, rank, mult in components:
                for inst in range(mult):
                    store.insert_lattice_form(
                        lattice_form_id=f"lf:{terminal_id}:component:{fam}{rank}:{inst}",
                        terminal_24d_id=terminal_id,
                        access_kind="component_instance",
                        root_system_label=f"{fam}{rank}",
                        payload={
                            "family": fam,
                            "rank": rank,
                            "instance_index": inst,
                            "multiplicity": mult,
                        },
                        evidence_level="exact",
                    )
                    count += 1

    store.flush()
    return {"lattice_forms_written": count}
