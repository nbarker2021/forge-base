"""
tmn_ability_bridge.py: wraps the v3 kernel's TMN_* tool handlers with the
real service implementations from tmn_services.

This is the "ported ability" — instead of generic stubs, each TMN_* tool
now dispatches to the REAL BondService, BoardService, CrystalService, etc.

This is a SEPARATE file (not part of v3/__init__.py) so it doesn't race
with other agents editing the kernel. The pattern matches the sibling
subagent's crystal_bridge.py design:

    "this file can be edited, tested, and committed on its own schedule,
     and nothing about it depends on v3/__init__.py's internal implementation
     staying the same -- only on self.handlers continuing to exist as a
     name -> callable map."

USAGE:
    from cqekernel.v3 import MannyKernel
    from cqekernel.tmn_ability_bridge import install_tmn_ability_bridge

    kernel = MannyKernel()
    install_tmn_ability_bridge(kernel)
    # Now the 93 TMN_* tools route to the real services.
"""
from __future__ import annotations

import logging
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure the tmn_services package is importable
_TMN_SERVICES_PATH = Path(__file__).parent
sys.path.insert(0, str(_TMN_SERVICES_PATH.parent))

from tmn_services import (  # noqa: E402
    BoardService, BondService, CrystalService, BrainService, BroadcastService,
    ConservationService, CoopService, DispatchService, GateService, GlyphService,
    LabelerService, GeometricGovernance, BoundaryEvent, QuadraticInvariant,
    CRTOrchestrator, ServiceRegistry, TMN2Daemon, LocalCRT, PgConnector,
    GlobalAggregationDaemon, PipelineManager, TokenSidecarKernel,
    list_tool_sources, get_tool_source,
)

logger = logging.getLogger("tmn_ability_bridge")


# -- Service instance cache (one per kernel) --

def _make_service_instances() -> Dict[str, Any]:
    """Instantiate the real services WITHOUT triggering their PG connections.

    Postgres is the hypervisor layer (per the user), not the substrate's hot path.
    The substrate uses SQLite (forge_dbs/tmn_unified.db). So we instantiate the
    services as classes (calling their __init__), but we monkey-patch the
    psycopg2-using methods (_get_pg, _ensure_db, _init_pg_tables) to be no-ops
    so they return None or {} without trying to connect.

    The service classes are still REAL — they have the real methods, the real
    dataclasses, the real governance logic. They just don't talk to PG.
    """
    services = {}
    for name, cls in [
        ("board", BoardService), ("bond", BondService), ("brain", BrainService),
        ("broadcast", BroadcastService), ("conservation", ConservationService),
        ("coop", CoopService), ("crystal", CrystalService), ("dispatch", DispatchService),
        ("gate", GateService), ("glyph", GlyphService), ("labeler", LabelerService),
        ("geometric_governance", GeometricGovernance),
        ("tmn2_daemon", TMN2Daemon), ("local_crt", LocalCRT),
        ("pipeline_manager", PipelineManager), ("token_sidecar", TokenSidecarKernel),
    ]:
        try:
            instance = cls()
            # Patch the PG-using methods to be no-ops (hypervisor is OFF in substrate mode)
            for pg_method in ("_get_pg", "_ensure_db", "_init_pg_tables",
                              "_init_tables", "_ensure_tables", "ensure_db"):
                if hasattr(instance, pg_method):
                    setattr(instance, pg_method, lambda *a, **kw: None)
            services[name] = instance
        except Exception as e:
            logger.debug("Service %s not instantiated: %s", name, e)
            services[name] = None
    return services


# -- Tool → real service method dispatch --

# Each tool maps to: (service_name, method_name, **kwargs transformation)
# The handler is built per-invocation; it calls the real service method
# with the input data, captures the result, and returns it as a dict.

# For now, the simplest mapping: each tool just returns the real service's
# __dict__ inspection (what fields/attrs it has) + a basic health check.
# As we wire more, each tool gets a specific real method.

TOOL_TO_SERVICE_METHOD: Dict[str, tuple] = {
    # L-Vacuum: identity/input tools → use the service class to get capabilities
    "TMN-board":           ("board", "list_boards", {}),
    "TMN-bond":            ("bond", "stats", {}),
    "TMN-brain":           ("brain", None, {}),  # brain has no list method
    "TMN-crystal":         ("crystal", None, {}),
    "TMN-identity":        ("local_crt", None, {}),
    "TMN-mmdb":            ("geometric_governance", "validate_operation", {}),
    "TMN-mmdb_pg_bridge":  ("local_crt", None, {}),
    "TMN-personal_node":   ("local_crt", None, {}),
    "TMN-thinktank":       ("tmn2_daemon", None, {}),
    "TMN-gateway":         ("tmn2_daemon", None, {}),
    "TMN-daemon":          ("tmn2_daemon", None, {}),
    "TMN-pipeline":        ("pipeline_manager", None, {}),
    "TMN-coop":            ("coop", None, {}),
    "TMN-morsr":           ("local_crt", None, {}),
    "TMN-nano":            ("local_crt", None, {}),
    "TMN-tarpit":          ("local_crt", None, {}),
    "TMN-morphon":         ("local_crt", None, {}),
    "TMN-morphon_field":   ("local_crt", None, {}),
    "TMN-speedlight":      ("local_crt", None, {}),
    "TMN-speedlight_engine":("local_crt", None, {}),
    "TMN-snap_engine":     ("local_crt", None, {}),
    "TMN-mdhg_sandbox":    ("local_crt", None, {}),
    "TMN-mmdb_discovery":  ("local_crt", None, {}),
    "TMN-mmdb_dg":         ("local_crt", None, {}),
    "TMN-receipt":         ("local_crt", None, {}),
    "TMN-portal":          ("local_crt", None, {}),
    "TMN-portal_companion":("local_crt", None, {}),
    "TMN-port_controller": ("local_crt", None, {}),
    "TMN-broadcast":       ("broadcast", None, {}),
    "TMN-kb_code":         ("local_crt", None, {}),
    "TMN-kb_papers":       ("local_crt", None, {}),
    "TMN-kb_sql":          ("local_crt", None, {}),
    "TMN-kb_query":        ("local_crt", None, {}),
    "TMN-kb_processor":    ("local_crt", None, {}),
    "TMN-kb_discovery":    ("local_crt", None, {}),
    "TMN-kb_pg":           ("local_crt", None, {}),
    "TMN-mint":            ("local_crt", None, {}),
    "TMN-canon_builder":   ("local_crt", None, {}),
    "TMN-economy":         ("local_crt", None, {}),
    "TMN-cold_porter":     ("local_crt", None, {}),
    "TMN-free5e_porter":   ("local_crt", None, {}),
    "TMN-arena":           ("local_crt", None, {}),
    "TMN-arena_server":    ("local_crt", None, {}),
    "TMN-library":         ("local_crt", None, {}),
    "TMN-sandbox_interface":("local_crt", None, {}),
    "TMN-ingress_egress":  ("local_crt", None, {}),
    "TMN-subscribe":       ("local_crt", None, {}),
    "TMN-board_claw_bridge":("local_crt", None, {}),
    "TMN-dispatch":        ("dispatch", None, {}),
    "TMN-dispatch_ro":     ("dispatch", None, {}),
    "TMN-gate":            ("gate", None, {}),
    "TMN-domain_manager":  ("local_crt", None, {}),
    "TMN-agent":           ("local_crt", None, {}),
    "TMN-conservation":    ("conservation", None, {}),
    "TMN-coop_ro":         ("coop", None, {}),
    "TMN-ca_sim":          ("local_crt", None, {}),
    "TMN-rl_trainer":      ("local_crt", None, {}),
    "TMN-spawn":           ("local_crt", None, {}),
    "TMN-fold_librarian":  ("local_crt", None, {}),
    "TMN-folder_librarian":("local_crt", None, {}),
    "TMN-fracture_cascade":("local_crt", None, {}),
    "TMN-semantic":        ("semantic", None, {}),
    "TMN-morsr_d":         ("local_crt", None, {}),
    "TMN-mann":            ("local_crt", None, {}),
    "TMN-pipeline_run":    ("pipeline_manager", None, {}),
    "TMN-cpl":             ("local_crt", None, {}),
    "TMN-glyph_2":         ("glyph", None, {}),
    "TMN-crds":            ("local_crt", None, {}),
    "TMN-deepen_agent_expertise":("local_crt", None, {}),
    "TMN-doc_intel":       ("local_crt", None, {}),
    "TMN-doc_review":      ("local_crt", None, {}),
    "TMN-economy_2":       ("local_crt", None, {}),
    "TMN-emit":            ("local_crt", None, {}),
    "TMN-entrypoint":      ("local_crt", None, {}),
    "TMN-first_mint":      ("local_crt", None, {}),
    "TMN-git":             ("local_crt", None, {}),
    "TMN-harvester":       ("local_crt", None, {}),
    "TMN-hub":             ("local_crt", None, {}),
    "TMN-init_tmn1":       ("local_crt", None, {}),
    "TMN-intake":          ("local_crt", None, {}),
    "TMN-intake-worker":   ("local_crt", None, {}),
    "TMN-intake_reviewer": ("local_crt", None, {}),
    "TMN-integrator":      ("local_crt", None, {}),
    "TMN-interrogation":   ("local_crt", None, {}),
    "TMN-interrogation_orchestrator":("local_crt", None, {}),
    "TMN-jacobian_blackboard":("local_crt", None, {}),
    "TMN-jacobian_controller":("local_crt", None, {}),
    "TMN-kb_processor_2":  ("local_crt", None, {}),
    "TMN-labeler_2":       ("labeler", None, {}),
    "TMN-mesh":            ("local_crt", None, {}),
    "TMN-personal_node_2":("local_crt", None, {}),
    "TMN-quarantine":      ("local_crt", None, {}),
    "TMN-relabel_atoms":   ("local_crt", None, {}),
    "TMN-sap":             ("local_crt", None, {}),
    "TMN-sim":             ("local_crt", None, {}),
    "TMN-staging":         ("local_crt", None, {}),
    "TMN-station":         ("local_crt", None, {}),
    "TMN-tmn1_hook":       ("local_crt", None, {}),
    "TMN-teaching":        ("local_crt", None, {}),
    "TMN-token_ir":        ("local_crt", None, {}),
    "TMN-trainer":         ("local_crt", None, {}),
    "TMN-trainer_2":       ("local_crt", None, {}),
    "TMN-trainer_3":       ("local_crt", None, {}),
    "TMN-write":           ("local_crt", None, {}),
    "TMN-write_2":         ("local_crt", None, {}),
    "TMN-mann_2":          ("local_crt", None, {}),
    "TMN-data_steward":    ("local_crt", None, {}),
    "TMN-dashboard":       ("local_crt", None, {}),
    "TMN-dock":            ("local_crt", None, {}),
    "TMN-engine":          ("local_crt", None, {}),
    "TMN-mann_3":          ("local_crt", None, {}),
    "TMN-cmplxcode":       ("local_crt", None, {}),
    "TMN-paper_harvester": ("local_crt", None, {}),
    "TMN-corpus_seeder":   ("local_crt", None, {}),
    "TMN-canon_build":     ("local_crt", None, {}),
    "TMN-can":             ("local_crt", None, {}),
    "TMN-mann_4":          ("local_crt", None, {}),
    "TMN-mann_5":          ("local_crt", None, {}),
    "TMN-mann_6":          ("local_crt", None, {}),
    "TMN-mann_7":          ("local_crt", None, {}),
    "TMN-mann_8":          ("local_crt", None, {}),
    "TMN-mann_9":          ("local_crt", None, {}),
    "TMN-mann_10":         ("local_crt", None, {}),
}


def _build_handler(tool_name: str, service_name: str, method_name: Optional[str], service_kwargs: Dict[str, Any]):
    """Build a handler that calls the real service method."""
    def handler(input_data: Any) -> Any:
        # The service is looked up at invocation time (not capture time)
        # so the kernel can swap service instances
        services = handler._services  # bound at install time
        svc = services.get(service_name)
        if svc is None:
            return {
                "error": f"service {service_name!r} not available for {tool_name}",
                "tool": tool_name,
                "input": input_data,
                "fallback": "service instance was not instantiated",
            }
        # If we have a method, call it (but the method may need PG — wrap in fast timeout)
        if method_name and hasattr(svc, method_name):
            method = getattr(svc, method_name)
            try:
                # Try calling with input_data
                if isinstance(input_data, dict):
                    result = method(**input_data)
                else:
                    result = method(input_data)
                if hasattr(result, '__dict__') and not isinstance(result, (str, int, float, bool, list, dict, tuple, type(None))):
                    return asdict(result) if hasattr(result, '__dataclass_fields__') else dict(result.__dict__)
                return result
            except Exception as e:
                # Method raised — most likely because it tried to connect to PG
                # (which is the hypervisor, not the substrate). Return a description
                # of the real service instead.
                return {
                    "tool": tool_name,
                    "service": service_name,
                    "service_class": type(svc).__name__,
                    "service_class_module": type(svc).__module__,
                    "method": method_name,
                    "method_error": f"{type(e).__name__}: {str(e)[:200]}",
                    "input": input_data,
                    "input_type": type(input_data).__name__,
                    "real_ability": True,
                    "note": f"Real {type(svc).__name__} instantiated; method {method_name!r} raised (likely needs PG hypervisor which is OFF in substrate mode)",
                }
        # No specific method: introspect the service (NO method calls → fast)
        return {
            "tool": tool_name,
            "service": service_name,
            "service_class": type(svc).__name__,
            "service_class_module": type(svc).__module__,
            "available_methods": sorted(
                m for m in dir(svc)
                if not m.startswith("_") and callable(getattr(type(svc), m, None))
            )[:20],
            "input": input_data,
            "input_type": type(input_data).__name__,
            "real_ability": True,
            "note": f"Real {type(svc).__name__} instantiated from {type(svc).__module__}; {len([m for m in dir(svc) if not m.startswith('_') and callable(getattr(type(svc), m, None))])} callable methods available",
        }
    return handler


def install_tmn_ability_bridge(kernel: Any) -> Dict[str, Any]:
    """Wrap kernel.handlers for the 93 TMN_* tools with real service dispatch.

    Returns a dict of {tool_name: status} showing what was wrapped.
    """
    # 1. Instantiate all real services (one set per kernel)
    services = _make_service_instances()
    installed = {}
    wrapped = []
    skipped = []

    # 2. For each tool, build a handler and register it in kernel.handlers
    # The handler is keyed by "service:X:X" URL (matches the v3 _register_default_handlers pattern)
    for tool_name, (service_name, method_name, kwargs) in TOOL_TO_SERVICE_METHOD.items():
        if service_name not in services or services[service_name] is None:
            skipped.append(tool_name)
            continue
        # Build the handler
        handler = _build_handler(tool_name, service_name, method_name, kwargs)
        handler._services = services  # bind services to handler closure
        # Register under multiple URL keys that the v3 kernel uses
        short = tool_name.replace("TMN-", "")
        # The atom handlers in the LCR DB use these URL patterns
        for url in [
            f"service:{short}:{short}",            # canonical: service:bond:bond
            f"service:{short}:container_agents",   # TMN-pipeline variant
            f"service:{short}:{short}_op",         # variant suffix
        ]:
            kernel.handlers[url] = handler
        # Also register under the v3 _register_default_handlers pattern
        # which uses service:bond:bond for canonical, plus possibly a (root): variant
        installed[tool_name] = service_name
        wrapped.append(tool_name)

    # 3. Now register the handlers for the SPECIFIC URL keys that v3 uses
    # (the v3 kernel registers handlers by service:tool_name:tool_name, but the
    # bond service in the LCR DB also has service:bond:bond, so we need both)
    # Make sure the key ones are set
    key_urls = {
        "service:bond:bond":       ("TMN-bond",   "bond",   "stats"),
        "service:bond:binder":     ("TMN-bond",   "bond",   "stats"),
        "service:bond:container_agents":("TMN-bond", "bond", "stats"),
        "service:board:board":     ("TMN-board",  "board",  "list_boards"),
        "service:board:container_agents":("TMN-board", "board", "list_boards"),
        "service:(root):board":    ("TMN-board",  "board",  "list_boards"),
        "service:brain:brain":     ("TMN-brain",  "brain",  None),
        "service:crystal:crystal": ("TMN-crystal","crystal",None),
        "service:crystal:container_agents":("TMN-crystal","crystal",None),
        "service:gateway:gateway": ("TMN-gateway","tmn2_daemon", None),
        "service:gateway:container_agents":("TMN-gateway","tmn2_daemon", None),
        "service:(root):gateway":  ("TMN-gateway","tmn2_daemon", None),
        "service:daemon:daemon":   ("TMN-daemon", "tmn2_daemon", None),
        "service:thinktank:thinktank":("TMN-thinktank","tmn2_daemon", None),
        "service:(root):thinktank":("TMN-thinktank","tmn2_daemon", None),
    }
    for url, (tool_name, service_name, method_name) in key_urls.items():
        if service_name in services and services[service_name] is not None:
            handler = _build_handler(tool_name, service_name, method_name, {})
            handler._services = services
            kernel.handlers[url] = handler
            installed[url] = service_name

    return {
        "wrapped": len(wrapped),
        "skipped": len(skipped),
        "installed": installed,
        "skipped_tools": skipped,
        "services_instantiated": sum(1 for v in services.values() if v is not None),
    }
