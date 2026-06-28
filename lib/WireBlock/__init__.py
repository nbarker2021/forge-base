"""WireBlock - legality engine for initialized-wireframe CAD.

Documented in the CADForge+WireBlock promotion slice (2026-06-11) but never
implemented as a module. Built here as a real, importable, stdlib-only legality
kernel: a wireframe graph (nodes, edges) plus an allowed-attachable list and
bounded variables; it rejects illegal attachables, illegal anchor nodes,
out-of-range variables, and uninitialized states, and emits a graph receipt.

Receipt schema matches the demo `wireblock_receipt.json` / `cadforge_design.json`:
base_template, nodes, edges, attachables, variables, design_id, legal.
"""
from __future__ import annotations

import hashlib
import json


class WireBlockError(ValueError):
    pass


class WireBlock:
    def __init__(self, base_template: str, nodes: list, edges: list,
                 allowed_attachables: list, variables: dict):
        # variables: {name: {"min": .., "max": .., "default": ..}}
        self.base_template = base_template
        self.nodes = list(nodes)              # [{"id":..,"x":..,"y":..,"z":..,"role":..}]
        self.edges = list(edges)              # [{"source":..,"target":..,"edge_type":..}]
        self.allowed = set(allowed_attachables)
        self.var_spec = variables
        self.values = {k: v["default"] for k, v in variables.items()}
        self.attachables: list[dict] = []
        self._initialized = bool(nodes)

    @property
    def node_ids(self) -> set:
        return {n["id"] for n in self.nodes}

    def set_var(self, name: str, value) -> None:
        if name not in self.var_spec:
            raise WireBlockError(f"unknown variable {name!r}")
        lo, hi = self.var_spec[name]["min"], self.var_spec[name]["max"]
        if not (lo <= value <= hi):
            raise WireBlockError(f"{name}={value} out of range [{lo},{hi}]")
        self.values[name] = value

    def attach(self, attachment_id: str, name: str, anchor_node: str,
               template: str | None = None, scale: float = 1.0,
               orientation: str = "external") -> None:
        if not self._initialized:
            raise WireBlockError("cannot attach to an uninitialized design")
        if name not in self.allowed:
            raise WireBlockError(f"illegal attachable {name!r}; allowed={sorted(self.allowed)}")
        if anchor_node not in self.node_ids:
            raise WireBlockError(f"illegal anchor node {anchor_node!r}")
        self.attachables.append({
            "attachment_id": attachment_id, "name": name,
            "anchor_node": anchor_node, "template": template or name,
            "scale": scale, "orientation": orientation,
        })

    def receipt(self, name: str = "design") -> dict:
        body = {
            "base_template": self.base_template,
            "nodes": self.nodes, "edges": self.edges,
            "attachables": self.attachables,
            "variables": self.values,
        }
        design_id = "cad_" + hashlib.sha256(
            json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]
        legal = (self._initialized
                 and all(a["name"] in self.allowed for a in self.attachables)
                 and all(a["anchor_node"] in self.node_ids for a in self.attachables)
                 and all(self.var_spec[k]["min"] <= v <= self.var_spec[k]["max"]
                         for k, v in self.values.items()))
        return {"design_id": design_id, "name": name, "legal": legal, **body}


def verify() -> dict:
    wb = WireBlock("lattice_2x2", [{"id": "base:n0", "x": 0, "y": 0}],
                   [], ["rib"], {"width_mm": {"min": 10, "max": 200, "default": 50}})
    wb.set_var("width_mm", 96)
    wb.attach("a0", "rib", "base:n0")
    r = wb.receipt()
    return {"forge": "WireBlock", "status": "pass" if r["legal"] else "fail",
            "design_id": r["design_id"], "attachables": len(r["attachables"])}
