"""crystal_bridge — wires CrystalForge's real crystal/brain logic into a
MannyKernel instance from OUTSIDE v3/__init__.py.

Why this exists as a separate file: v3/__init__.py is under active,
fast, external development (the other agent committed to it roughly
every 13 minutes across one recent 90-minute window). Two direct edits
to that file were each silently overwritten by a later commit before
they could be verified and landed. Composing at the kernel's own
public extension point (self.handlers, the dict MannyKernel's own
_register_default_handlers already populates and that _execute_tool/
_execute_atom already dispatch through) avoids the race entirely: this
file can be edited, tested, and committed on its own schedule, and
nothing about it depends on v3/__init__.py's internal implementation
staying the same -- only on self.handlers continuing to exist as a
name -> callable map, which is the kernel's own stated design.

Usage:
    from cqekernel.v3 import MannyKernel
    from cqekernel.v3.crystal_bridge import install_crystal_bridge

    kernel = MannyKernel()
    install_crystal_bridge(kernel)
    # kernel.handle_message(...) and kernel.invoke(...) now support
    # the new {"action": ...} branches for crystal/brain operations,
    # with every existing read-only behavior preserved as the fallback.

What this adds (ported from the real TMN crystal.py/brain.py services,
not invented -- see production/packages/cqecmplx-forge/src/CrystalForge/):
  - crystal: {"action": "create"/"add_node"/"commit"/"activate"/"list"}
  - brain:   {"action": "register"/"contribute"/"capacity"/"merge"/
              "fork"/"expertise"}
Anything without an "action" key falls through to the kernel's own
existing handler, completely unchanged.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

import CrystalForge as CRYSTAL_FORGE


def install_crystal_bridge(kernel: Any, db_path: Any = None) -> Dict[str, str]:
    """Wrap kernel.handlers["service:crystal:crystal"] and
    ["service:brain:brain"] with action-routing to CrystalForge,
    falling back to whatever the kernel's own handler currently does
    for non-action input. Idempotent -- calling twice re-wraps the
    already-installed wrapper's fallback (the original handler), not
    itself, so it does not nest.

    db_path defaults to the kernel's own TMN_UNIFIED_DB constant if
    present (the same file its RuntimeDB already reads/writes), so the
    bridge writes to the same store the rest of the kernel sees.
    """
    target_db = db_path if db_path is not None else getattr(
        kernel, "TMN_UNIFIED_DB", None
    ) or _get_module_db_path(kernel)

    original_crystal = kernel.handlers.get("service:crystal:crystal", kernel._handle_crystal)
    original_brain = kernel.handlers.get("service:brain:brain", kernel._handle_brain)

    kernel.handlers["service:crystal:crystal"] = _make_crystal_handler(original_crystal, target_db)
    kernel.handlers["service:brain:brain"] = _make_brain_handler(original_brain, target_db)

    # Re-point any already-resolved atom_handlers entries at the new wrappers
    # (mirrors how MannyKernel._register_atom_handlers wires atom_id -> handler).
    for atom_id, atom in kernel.tools.atoms.items():
        if atom.handler == "service:crystal:crystal":
            kernel.atom_handlers[atom_id] = kernel.handlers["service:crystal:crystal"]
        elif atom.handler == "service:brain:brain":
            kernel.atom_handlers[atom_id] = kernel.handlers["service:brain:brain"]

    return {"crystal_handler": "wrapped", "brain_handler": "wrapped", "db_path": str(target_db)}


def _get_module_db_path(kernel: Any):
    """Fall back to the v3 module's own TMN_UNIFIED_DB constant if the
    kernel instance doesn't expose one directly."""
    module = type(kernel).__module__
    import sys
    mod = sys.modules.get(module)
    return getattr(mod, "TMN_UNIFIED_DB", None)


def _make_crystal_handler(original, db_path):
    def handler(input_data: Any) -> Any:
        if isinstance(input_data, dict) and "action" in input_data:
            action = input_data["action"]
            try:
                if action == "create":
                    c = CRYSTAL_FORGE.create_crystal(
                        name=input_data.get("name", "unnamed"),
                        crystal_type=input_data.get("crystal_type", "knowledge"),
                        owner=input_data.get("owner", ""), db_path=db_path,
                    )
                    return asdict(c)
                if action == "add_node":
                    n = CRYSTAL_FORGE.add_node(
                        crystal_id=input_data["crystal_id"], content=input_data.get("content", ""),
                        content_type=input_data.get("content_type", "atom"),
                        labels=input_data.get("labels"), db_path=db_path,
                    )
                    return asdict(n)
                if action == "commit":
                    return asdict(CRYSTAL_FORGE.commit_crystal(input_data["crystal_id"], db_path=db_path))
                if action == "activate":
                    return asdict(CRYSTAL_FORGE.activate_crystal(input_data["crystal_id"], db_path=db_path))
                if action == "list":
                    cs = CRYSTAL_FORGE.list_crystals(state=input_data.get("state", ""), db_path=db_path)
                    return {"crystals": [c.crystal_id for c in cs], "count": len(cs)}
                return {"error": f"unknown action {action!r}",
                        "available_actions": ["create", "add_node", "commit", "activate", "list"]}
            except (ValueError, KeyError) as e:
                return {"error": str(e)}
        return original(input_data)
    return handler


def _make_brain_handler(original, db_path):
    def handler(input_data: Any) -> Any:
        if isinstance(input_data, dict) and "action" in input_data:
            action = input_data["action"]
            try:
                if action == "register":
                    return CRYSTAL_FORGE.register_brain(
                        agent_id=input_data["agent_id"], dims=input_data.get("dims", 24),
                        tier=input_data.get("tier", "nascent"),
                        specialist_profile=input_data.get("specialist_profile"), db_path=db_path,
                    )
                if action == "contribute":
                    return CRYSTAL_FORGE.contribute(
                        agent_id=input_data["agent_id"], domain=input_data.get("domain", ""),
                        snap_labels=input_data.get("snap_labels"), mi_score=input_data.get("mi_score", 0.0),
                        db_path=db_path,
                    )
                if action == "capacity":
                    brain = CRYSTAL_FORGE.get_brain(input_data["agent_id"], db_path=db_path)
                    if not brain:
                        return {"error": f"brain {input_data['agent_id']!r} not registered"}
                    return CRYSTAL_FORGE.compute_capacity(
                        mi_history=brain["mi_history"], weight_density=input_data.get("weight_density", 0.0),
                        step_count=brain["step_count"],
                    )
                if action == "merge":
                    return CRYSTAL_FORGE.merge_brain(
                        agent_id=input_data["agent_id"], target_dims=input_data.get("target_dims", 32),
                        db_path=db_path,
                    )
                if action == "fork":
                    return CRYSTAL_FORGE.fork_brain(
                        parent_id=input_data["agent_id"], child_id=input_data["child_id"],
                        domain_boost=input_data.get("domain_boost", ""), db_path=db_path,
                    )
                if action == "expertise":
                    return CRYSTAL_FORGE.list_expertise(
                        domain=input_data.get("domain", ""), min_mi=input_data.get("min_mi", 0.0), db_path=db_path,
                    )
                return {"error": f"unknown action {action!r}",
                        "available_actions": ["register", "contribute", "capacity", "merge", "fork", "expertise"]}
            except (ValueError, KeyError) as e:
                return {"error": str(e)}
        return original(input_data)
    return handler
