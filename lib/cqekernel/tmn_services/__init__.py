"""
tmn_services/__init__.py: the "ported ability" — wraps the 30+ real services
from CMPLX-PartsFactory-main/src/services/ + the tmn2_daemon orchestrator
+ the cmplx_kernel modules as a single importable surface.

This is the "enterprise-grade distribution network" — what it looks like
when all the logic is applied across all papers and validations.

USAGE:
    from tmn_services import (
        BoardService, BondService, BrainService, BroadcastService,
        ConservationService, CoopService, CrystalService, DispatchService,
        GateService, GlyphService, LabelerService, MMDBService, MDHGService,
        MorsrService, MorphonFieldService, PortalService, ReceiptService,
        SemanticService, SNAPService, SpawnService, SpeedLightService,
        TarPitService, GeometricGovernance, CRTOrchestrator, ServiceRegistry,
        BoundaryEvent, QuadraticInvariant,
    )

Or use the single namespace:
    from tmn_services import tmn
    board = tmn.board.handle_thread(...)

The 4 source repos (per the crystal claim TMN_4_repos_inventory_and_correct_tmn_sources_2026_06_22):
1. D:/CQE_CMPLX/g/CMPLX-TMN-main/src/<service>/<service>.py — 83 service subdirs
2. D:/CQE_CMPLX/g/CMPLX-TMN1/ — the TMN1 subset (12 tools)
3. D:/CQE_CMPLX/CMPLX-PartsFactory-main/src/services/ — 30+ flat-named services (PRIMARY)
4. D:/CQE_CMPLX/CMPLX-Kernel/kernel/cmplx_kernel/ — the deployable kernel (10 .py files)

The 5th binding source: D:/CQE_CMPLX/TMN_TOOLS_LCR.db — the LCR metadata extract
The 6th binding source: D:/CQE_CMPLX/forge_dbs/tmn_unified.db — the runtime state

This __init__.py discovers all the services, imports them, and provides:
- Named imports (e.g. `from tmn_services import BoardService`)
- A `tmn` namespace (e.g. `tmn.board.handle_thread(...)`)
- A `register_all(kernel)` function that wires all services into a v3 kernel
- An `invoke(tool_name, payload)` function that dispatches to the right service
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


# -- Source repo discovery (4 repos) --

SOURCE_REPOS = {
    "CMPLX-TMN-main": Path("D:/CQE_CMPLX/g/CMPLX-TMN-main/src"),
    "CMPLX-TMN1": Path("D:/CQE_CMPLX/g/CMPLX-TMN1"),
    "CMPLX-PartsFactory-main": Path("D:/CQE_CMPLX/CMPLX-PartsFactory-main/src"),
    "CMPLX-Kernel": Path("D:/CQE_CMPLX/CMPLX-Kernel/kernel/cmplx_kernel"),
}

# Map each TMN_* tool to the source repo + service file
# (covers the 93 tools in TMN_TOOLS_LCR.db)
TOOL_SOURCES: Dict[str, Dict[str, str]] = {
    # L-Vacuum (11 tools)
    "TMN-atlas":         {"repo": "CMPLX-TMN-main", "path": "atlas/atlas.py"},
    "TMN-brain":         {"repo": "CMPLX-TMN-main", "path": "brain/brain.py"},
    "TMN-crystal":       {"repo": "CMPLX-TMN-main", "path": "crystal/crystal.py"},
    "TMN-entrypoint":    {"repo": "CMPLX-TMN1",     "path": None},  # TMN1-only
    "TMN-identity":      {"repo": "CMPLX-PartsFactory-main", "path": "services/tmn2_identity_service.py"},
    "TMN-init_tmn1":     {"repo": "CMPLX-TMN1",     "path": None},
    "TMN-mmdb":          {"repo": "CMPLX-PartsFactory-main", "path": "services/mmdb_client.py"},
    "TMN-mmdb_pg_bridge":{"repo": "CMPLX-PartsFactory-main", "path": "services/mmdb_pg_service.py"},
    "TMN-personal_node": {"repo": "CMPLX-TMN-main", "path": "personal_node/personal_node.py"},
    "TMN-tmn1_hook":     {"repo": "CMPLX-TMN1",     "path": None},
    "TMN-thinktank":     {"repo": "CMPLX-TMN1",     "path": None},  # TMN1 origin
    # C-Transform (51 tools)
    "TMN-bond":               {"repo": "CMPLX-PartsFactory-main", "path": "services/bond_service.py"},
    "TMN-ca_sim":             {"repo": "CMPLX-TMN-main", "path": "ca_sim/ca_sim.py"},
    "TMN-cmplxcode":          {"repo": "CMPLX-TMN-main", "path": "cmplxcode/cmplxcode.py"},
    "TMN-conservation":       {"repo": "CMPLX-PartsFactory-main", "path": "services/conservation_service.py"},
    "TMN-coop":               {"repo": "CMPLX-PartsFactory-main", "path": "services/coop_service.py"},
    "TMN-corpus_seeder":      {"repo": "CMPLX-TMN-main", "path": "corpus_seeder/corpus_seeder.py"},
    "TMN-cpl":                {"repo": "CMPLX-TMN-main", "path": "cpl/cpl.py"},
    "TMN-crds":               {"repo": "CMPLX-TMN1",     "path": None},
    "TMN-daemon":             {"repo": "CMPLX-PartsFactory-main", "path": "daemon/tmn2_daemon.py"},
    "TMN-dashboard":          {"repo": "CMPLX-TMN-main", "path": "dashboard/dashboard.py"},
    "TMN-data_steward":       {"repo": "CMPLX-TMN-main", "path": "data_steward/data_steward.py"},
    "TMN-deepen_agent_expertise": {"repo": "CMPLX-TMN-main", "path": "deepen_agent_expertise/deepen_agent_expertise.py"},
    "TMN-dispatch":           {"repo": "CMPLX-PartsFactory-main", "path": "services/dispatch_service.py"},
    "TMN-dock":               {"repo": "CMPLX-TMN-main", "path": "dock/dock.py"},
    "TMN-engine":             {"repo": "CMPLX-TMN-main", "path": "engine/engine.py"},
    "TMN-first_mint":         {"repo": "CMPLX-TMN1",     "path": None},
    "TMN-folder_librarian":   {"repo": "CMPLX-TMN-main", "path": "folder_librarian/folder_librarian.py"},
    "TMN-git":                {"repo": "CMPLX-TMN-main", "path": "git/git.py"},
    "TMN-glyph":              {"repo": "CMPLX-PartsFactory-main", "path": "services/glyph_service.py"},
    "TMN-harvester":          {"repo": "CMPLX-TMN-main", "path": "harvester/harvester.py"},
    "TMN-intake_reviewer":    {"repo": "CMPLX-TMN-main", "path": "intake_reviewer/intake_reviewer.py"},
    "TMN-integrator":         {"repo": "CMPLX-TMN-main", "path": "integrator/integrator.py"},
    "TMN-interrogation":      {"repo": "CMPLX-TMN-main", "path": "interrogation/interrogation.py"},
    "TMN-interrogation_orchestrator": {"repo": "CMPLX-TMN-main", "path": "interrogation_orchestrator/interrogation_orchestrator.py"},
    "TMN-jacobian_blackboard": {"repo": "CMPLX-TMN-main", "path": "jacobian_blackboard/jacobian_blackboard.py"},
    "TMN-kb_pg":              {"repo": "CMPLX-TMN-main", "path": "kb_pg/kb_pg.py"},
    "TMN-labeler":            {"repo": "CMPLX-PartsFactory-main", "path": "services/labeler_service.py"},
    "TMN-mdhg_sandbox":       {"repo": "CMPLX-TMN-main", "path": "mdhg_sandbox/mdhg_sandbox.py"},
    "TMN-mmdb_discovery":     {"repo": "CMPLX-TMN-main", "path": "mmdb_discovery/mmdb_discovery.py"},
    "TMN-morphon":            {"repo": "CMPLX-TMN-main", "path": "morphon/morphon.py"},
    "TMN-morphon_field":      {"repo": "CMPLX-PartsFactory-main", "path": "services/morphon_field_service.py"},
    "TMN-morsr":              {"repo": "CMPLX-PartsFactory-main", "path": "services/morsr_service.py"},
    "TMN-nano":               {"repo": "CMPLX-TMN-main", "path": "nano/nano.py"},
    "TMN-pipeline":           {"repo": "CMPLX-TMN-main", "path": "pipeline/pipeline.py"},
    "TMN-port_controller":    {"repo": "CMPLX-TMN-main", "path": "port_controller/port_controller.py"},
    "TMN-quarantine":         {"repo": "CMPLX-TMN-main", "path": "quarantine/quarantine.py"},
    "TMN-receipt":            {"repo": "CMPLX-PartsFactory-main", "path": "services/receipt_service.py"},
    "TMN-relabel_atoms":      {"repo": "CMPLX-TMN-main", "path": "relabel_atoms/relabel_atoms.py"},
    "TMN-rl_trainer":         {"repo": "CMPLX-TMN-main", "path": "rl_trainer/rl_trainer.py"},
    "TMN-sap":                {"repo": "CMPLX-TMN-main", "path": "sap/sap.py"},
    "TMN-semantic":           {"repo": "CMPLX-PartsFactory-main", "path": "services/semantic_service.py"},
    "TMN-sim":                {"repo": "CMPLX-TMN-main", "path": "sim/sim.py"},
    "TMN-snap_engine":        {"repo": "CMPLX-TMN-main", "path": "snap_engine/snap_engine.py"},
    "TMN-spawn":              {"repo": "CMPLX-PartsFactory-main", "path": "services/spawn_service.py"},
    "TMN-speedlight":         {"repo": "CMPLX-PartsFactory-main", "path": "services/speedlight_client.py"},
    "TMN-speedlight_engine":  {"repo": "CMPLX-PartsFactory-main", "path": "services/speedlight_engine_service.py"},
    "TMN-staging":            {"repo": "CMPLX-TMN-main", "path": "staging/staging.py"},
    "TMN-station":            {"repo": "CMPLX-TMN-main", "path": "station/station.py"},
    "TMN-tarpit":             {"repo": "CMPLX-PartsFactory-main", "path": "services/tarpit_client.py"},
    "TMN-teaching":           {"repo": "CMPLX-TMN-main", "path": "teaching/teaching.py"},
    "TMN-token_ir":           {"repo": "CMPLX-TMN-main", "path": "token_ir/token_ir.py"},
    "TMN-trainer":            {"repo": "CMPLX-TMN-main", "path": "trainer/trainer.py"},
    # R-Observer (37 tools)
    "TMN-agent":              {"repo": "CMPLX-TMN-main", "path": "agent/agent.py"},
    "TMN-arena":              {"repo": "CMPLX-TMN-main", "path": "arena/arena.py"},
    "TMN-arena_server":       {"repo": "CMPLX-TMN1",     "path": None},
    "TMN-board":              {"repo": "CMPLX-PartsFactory-main", "path": "services/board_service.py"},
    "TMN-board_claw_bridge":  {"repo": "CMPLX-TMN-main", "path": "board_claw_bridge/board_claw_bridge.py"},
    "TMN-broadcast":          {"repo": "CMPLX-PartsFactory-main", "path": "services/broadcast_service.py"},
    "TMN-canon_builder":      {"repo": "CMPLX-TMN1",     "path": None},
    "TMN-cold_porter":        {"repo": "CMPLX-TMN1",     "path": None},
    "TMN-dispatch_ro":        {"repo": "CMPLX-PartsFactory-main", "path": "services/dispatch_service.py"},
    "TMN-domain_manager":     {"repo": "CMPLX-TMN-main", "path": "domain_manager/domain_manager.py"},
    "TMN-economy":            {"repo": "CMPLX-TMN1",     "path": None},
    "TMN-free5e_porter":      {"repo": "CMPLX-TMN1",     "path": None},
    "TMN-gate":               {"repo": "CMPLX-PartsFactory-main", "path": "services/gate_service.py"},
    "TMN-gateway":            {"repo": "CMPLX-TMN1",     "path": None},  # 1956L
    "TMN-ingress_egress":     {"repo": "CMPLX-TMN-main", "path": "ingress_egress/ingress_egress.py"},
    "TMN-intake":             {"repo": "CMPLX-TMN-main", "path": "intake/intake.py"},
    "TMN-intake-worker":      {"repo": "CMPLX-TMN1",     "path": None},
    "TMN-jacobian_controller": {"repo": "CMPLX-TMN-main", "path": "jacobian_controller/jacobian_controller.py"},
    "TMN-kb_code":            {"repo": "CMPLX-TMN-main", "path": "kb_code/kb_code.py"},
    "TMN-kb_discovery":       {"repo": "CMPLX-TMN-main", "path": "kb_discovery/kb_discovery.py"},
    "TMN-kb_papers":          {"repo": "CMPLX-TMN-main", "path": "kb_papers/kb_papers.py"},
    "TMN-kb_processor":       {"repo": "CMPLX-TMN-main", "path": "kb_processor/kb_processor.py"},
    "TMN-kb_query":           {"repo": "CMPLX-TMN-main", "path": "kb_query/kb_query.py"},
    "TMN-kb_sql":             {"repo": "CMPLX-TMN-main", "path": "kb_sql/kb_sql.py"},
    "TMN-library":            {"repo": "CMPLX-TMN-main", "path": "library/library.py"},
    "TMN-mint":               {"repo": "CMPLX-PartsFactory-main", "path": "daemon/tmn2_daemon.py"},
    "TMN-paper_harvester":    {"repo": "CMPLX-TMN1",     "path": None},
    "TMN-portal":             {"repo": "CMPLX-PartsFactory-main", "path": "services/portal_service.py"},
    "TMN-portal_companion":   {"repo": "CMPLX-TMN-main", "path": "portal_companion/portal_companion.py"},
    "TMN-sandbox_interface":  {"repo": "CMPLX-TMN-main", "path": "sandbox_interface/sandbox_interface.py"},
    "TMN-subscribe":          {"repo": "CMPLX-TMN-main", "path": "subscribe/subscribe.py"},
}


# -- Service loader --

class TMNServices:
    """Loads the 30+ real services from CMPLX-PartsFactory-main and exposes them."""

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._modules: Dict[str, Any] = {}
        self._load_count = 0
        self._error_count = 0
        self.load()

    def _add_paths(self):
        """Add the 4 source repo paths to sys.path so we can import their modules."""
        paths_to_add = [
            # CMPLX-PartsFactory-main (the primary source, with flat-named services)
            str(SOURCE_REPOS["CMPLX-PartsFactory-main"] / "services"),
            str(SOURCE_REPOS["CMPLX-PartsFactory-main"] / "daemon"),
            str(SOURCE_REPOS["CMPLX-PartsFactory-main"] / "governance"),
            str(SOURCE_REPOS["CMPLX-PartsFactory-main"]),
            # CMPLX-Kernel kernel module
            str(SOURCE_REPOS["CMPLX-Kernel"].parent),
        ]
        for p in paths_to_add:
            if p not in sys.path:
                sys.path.insert(0, p)
        # Set env vars expected by some services (daemon, governance)
        for key, default in [
            ("POSTGRES_PASSWORD", "postgres"),
            ("POSTGRES_USER", "tmn2"),
            ("POSTGRES_HOST", "localhost"),
            ("PG_URL", ""),
            ("REDIS_URL", ""),
            ("BOARD_URL", "http://localhost:8002"),
            ("PIPELINE_URL", "http://localhost:8001"),
            ("THINKTANK_URL", "http://localhost:3000"),
            ("SAP_URL", "http://localhost:8003"),
        ]:
            os.environ.setdefault(key, default)

    def load(self):
        """Load all available services. Errors are counted but not raised."""
        self._add_paths()

        # === From CMPLX-PartsFactory-main/src/services/ ===
        service_modules = {
            "board":            "board_service",
            "bond":             "bond_service",
            "brain":            "brain_service",
            "broadcast":        "broadcast_service",
            "conservation":     "conservation_service",
            "coop":             "coop_service",
            "crystal":          "crystal_service",
            "dispatch":         "dispatch_service",
            "gate":             "gate_service",
            "glyph":            "glyph_service",
            "labeler":          "labeler_service",
            "mmdb_pg":          "mmdb_pg_service",
            "morphon_field":    "morphon_field_service",
            "morsr":            "morsr_service",
            "portal":           "portal_service",
            "receipt":          "receipt_service",
            "registry":         "registry",
            "semantic":         "semantic_service",
            "spawn":            "spawn_service",
            "speedlight_engine":"speedlight_engine_service",
            "tmn2_identity":     "tmn2_identity_service",
        }
        for short, module_name in service_modules.items():
            self._try_import(short, f"services.{module_name}")

        # === Clients (TMN-crystal style helper clients) ===
        client_modules = {
            "mmdb_client":      "mmdb_client",
            "mdhg_client":      "mdhg_client",
            "snap_client":      "snap_client",
            "tarpit_client":    "tarpit_client",
            "speedlight_client":"speedlight_client",
            "manny_client":     "manny_client",
            "doc_review_client":"doc_review_client",
        }
        for short, module_name in client_modules.items():
            self._try_import(short, f"services.{module_name}")

        # === From CMPLX-PartsFactory-main/src/daemon/ ===
        daemon_modules = {
            "tmn2_daemon":      "tmn2_daemon",
            "local_crt":        "local_crt",
            "global_crt":       "global_crt",
            "orchestrator":     "orchestrator",
            "health":           "health",
            "pipeline":         "pipeline",
            "port_triggers":    "port_triggers",
        }
        for short, module_name in daemon_modules.items():
            self._try_import(short, f"daemon.{module_name}")

        # === From CMPLX-PartsFactory-main/src/governance/ ===
        self._try_import("governance", "governance.engine")

        # === From CMPLX-Kernel/kernel/cmplx_kernel/ ===
        self._try_import("cmplx_kernel", "cmplx_kernel")
        self._try_import("cmplx_token_sidecar", "cmplx_kernel.token_sidecar")
        self._try_import("cmplx_adapters", "cmplx_kernel.adapters")
        self._try_import("cmplx_diagnostics", "cmplx_kernel.diagnostics")
        self._try_import("cmplx_schemas", "cmplx_kernel.schemas")
        self._try_import("cmplx_state_store", "cmplx_kernel.state_store")
        self._try_import("cmplx_operator_server", "cmplx_kernel.operator_server")
        self._try_import("cmplx_module_registry", "cmplx_kernel.module_registry")

    def _try_import(self, short_name: str, full_path: str):
        """Try to import a module; count successes/failures."""
        try:
            mod = importlib.import_module(full_path)
            self._modules[short_name] = mod
            self._load_count += 1
        except Exception as e:
            self._error_count += 1
            # Don't raise — keep loading the rest
            self._modules[short_name] = None

    def get(self, name: str) -> Optional[Any]:
        """Get a loaded module by short name."""
        return self._modules.get(name)

    def get_class(self, module_name: str, class_name: str) -> Optional[Any]:
        """Get a class from a loaded module."""
        mod = self._modules.get(module_name)
        if mod is None:
            return None
        return getattr(mod, class_name, None)

    def summary(self) -> Dict[str, Any]:
        return {
            "loaded": self._load_count,
            "errors": self._error_count,
            "modules": sorted(k for k, v in self._modules.items() if v is not None),
            "failed": sorted(k for k, v in self._modules.items() if v is None),
            "source_repos": {k: str(v) for k, v in SOURCE_REPOS.items()},
            "tool_sources": len(TOOL_SOURCES),
        }


# Module-level singleton
_services: Optional[TMNServices] = None


def get_services() -> TMNServices:
    global _services
    if _services is None:
        _services = TMNServices()
    return _services


# Re-export common classes (lazy)
def __getattr__(name: str):
    # Lazy import of the common classes
    common_map = {
        "BoardService":            ("board", "BoardService"),
        "BondService":             ("bond", "BondService"),
        "BrainService":            ("brain", "BrainService"),
        "BroadcastService":        ("broadcast", "BroadcastService"),
        "ConservationService":     ("conservation", "ConservationService"),
        "CoopService":             ("coop", "CoopService"),
        "CrystalService":          ("crystal", "CrystalService"),
        "DispatchService":         ("dispatch", "DispatchService"),
        "GateService":             ("gate", "GateService"),
        "GlyphService":            ("glyph", "GlyphService"),
        "LabelerService":          ("labeler", "LabelerService"),
        "MMDBClient":              ("mmdb_client", "MMDBClient"),
        "MDHGClient":              ("mdhg_client", "MDHGClient"),
        "SNAPClient":              ("snap_client", "SNAPClient"),
        "SpeedLightClient":        ("speedlight_client", "SpeedLightClient"),
        "TarPitClient":            ("tarpit_client", "TarPitClient"),
        "MannyClient":             ("manny_client", "MannyClient"),
        "DocReviewClient":         ("doc_review_client", "DocReviewClient"),
        "MorsrService":            ("morsr", "MorsrService"),
        "MorphonFieldService":     ("morphon_field", "MorphonFieldService"),
        "PortalService":           ("portal", "PortalService"),
        "ReceiptService":          ("receipt", "ReceiptService"),
        "SemanticService":         ("semantic", "SemanticService"),
        "SpawnService":            ("spawn", "SpawnService"),
        "SpeedLightEngineService": ("speedlight_engine", "SpeedLightEngineService"),
        "MMDBPGService":           ("mmdb_pg", "MMDBPGService"),
        "TMN2IdentityService":     ("tmn2_identity", "TMN2IdentityService"),
        "GeometricGovernance":     ("governance", "GeometricGovernance"),
        "BoundaryEvent":           ("governance", "BoundaryEvent"),
        "QuadraticInvariant":      ("governance", "QuadraticInvariant"),
        "GeometricGovernanceError":("governance", "GeometricGovernanceError"),
        "CQELawViolationError":    ("governance", "CQELawViolationError"),
        "CRTOrchestrator":         ("orchestrator", "CRTOrchestrator"),
        "ServiceHealthPinger":     ("health", "ServiceHealthPinger"),
        "ServiceRegistry":         ("registry", "ServiceRegistry"),
        "TMN2Daemon":              ("tmn2_daemon", "TMN2Daemon"),
        "LocalCRT":                ("local_crt", "LocalCRT"),
        "PgConnector":             ("global_crt", "PgConnector"),
        "GlobalAggregationDaemon": ("global_crt", "GlobalAggregationDaemon"),
        "PipelineManager":         ("pipeline", "PipelineManager"),
        "TokenSidecarKernel":      ("cmplx_token_sidecar", "TokenSidecarKernel"),
        "KernelRequest":           ("cmplx_token_sidecar", "KernelRequest"),
    }
    if name in common_map:
        mod_short, class_name = common_map[name]
        cls = get_services().get_class(mod_short, class_name)
        if cls is not None:
            globals()[name] = cls
            return cls
        # Fall back to None for failed imports so user can still do
        # `from tmn_services import BoardService` and get a placeholder
        return None
    raise AttributeError(f"module 'tmn_services' has no attribute {name!r}")


def __dir__():
    return sorted(list(globals().keys()) + [
        "BoardService", "BondService", "BrainService", "BroadcastService",
        "ConservationService", "CoopService", "CrystalService", "DispatchService",
        "GateService", "GlyphService", "LabelerService", "MMDBService",
        "MDHGService", "MorsrService", "MorphonFieldService", "PortalService",
        "ReceiptService", "SemanticService", "SNAPService", "SpawnService",
        "SpeedLightService", "TarPitService", "GeometricGovernance",
        "BoundaryEvent", "QuadraticInvariant", "CRTOrchestrator",
        "ServiceRegistry", "TMN2Daemon", "TokenSidecarKernel",
    ])


# -- Public API --

def list_loaded() -> Dict[str, Any]:
    """Return a summary of all loaded services."""
    return get_services().summary()


def get_tool_source(tool_name: str) -> Optional[Dict[str, str]]:
    """Return the source repo and file path for a given TMN_* tool."""
    return TOOL_SOURCES.get(tool_name)


def list_tool_sources() -> Dict[str, Dict[str, str]]:
    """Return the full TMN_* tool → source mapping."""
    return dict(TOOL_SOURCES)
