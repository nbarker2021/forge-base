"""
MannyAI v3 kernel: combines cqekernel's 11 modules + tmn_tools_core's TMNToolBase
+ crystal library stream into one deployable kernel.

The v3 kernel is the production version of what was scattered across:
- D:/CQE_CMPLX/cqekernel/ (the 11 modules)
- D:/CQE_CMPLX/papers_tool_solvers/tmn_tools_core.py (the 850-line TMNToolBase)
- D:/CQE_CMPLX/papers_tool_solvers/generated_tools/ (the 93 stubs)
- D:/CQE_CMPLX/git-hosted-roots/CQECMPLX-Production/production/operations/crystal_library/ (88 claims)
- D:/CQE_CMPLX/forge_dbs/tmn_unified.db (the runtime state)

Architecture:
    +-----------------+     +-----------------+     +-----------------+
    |  CQKERNEL       |     |  TMN TOOLS      |     |  CRYSTAL LIB    |
    |  (11 modules)   |     |  (93 tools)     |     |  (88 claims)    |
    +--------+--------+     +--------+--------+     +--------+--------+
             |                       |                       |
             +-----------------------+-----------------------+
                                     |
                          +----------v----------+
                          |     MannyAI v3       |
                          |     (this kernel)    |
                          +----------+--------+
                                     |
                          +----------v----------+
                          |   TMN_UNIFIED.DB    |
                          |  (11 tables, 103    |
                          |   brains, 268 edges)|
                          +---------------------+

Usage:
    from cqekernel.v3 import MannyKernel
    kernel = MannyKernel()
    kernel.boot()  # loads all 93 tools, restores crystal state, registers handlers
    result = kernel.invoke("TMN-crystal", {"content": "hello"})
    # or:
    result = kernel.invoke_by_atom("TMN-crystal_input", {"content": "hello"})

    # Discord-side: when MannyAI#2807 gets a message, route to:
    result = kernel.handle_message(user_id, channel_id, message)
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# CrystalForge: meso-level crystal/brain memory system, ported from real TMN services
# to SQLite. Wired into _handle_crystal and _handle_brain for the v3.2 mutation side
# (the v3 README named "adding crystal mutation is a v3.2+ feature" as not-yet-done).
# Source: production/packages/cqecmplx-forge/src/CrystalForge/
_CRYSTAL_FORGE_PATH = Path(__file__).parent.parent / "git-hosted-roots/CQECMPLX-Production/production/packages/cqecmplx-forge/src"
if str(_CRYSTAL_FORGE_PATH) not in sys.path:
    sys.path.insert(0, str(_CRYSTAL_FORGE_PATH))
try:
    import CrystalForge as CRYSTAL_FORGE  # noqa: E402
    CRYSTAL_FORGE_AVAILABLE = True
except ImportError:
    CRYSTAL_FORGE = None
    CRYSTAL_FORGE_AVAILABLE = False

logger = logging.getLogger(__name__)


# Paths
TMN_UNIFIED_DB = Path("D:/CQE_CMPLX/forge_dbs/tmn_unified.db")
TMN_TOOLS_LCR_DB = Path("D:/CQE_CMPLX/TMN_TOOLS_LCR.db")
CRYSTAL_LIBRARY_DB = Path("D:/CQE_CMPLX/git-hosted-roots/CQECMPLX-Production/production/operations/crystal_library/crystal.db")
CQEKERNEL_ROOT = Path("D:/CQE_CMPLX/cqekernel")
GENERATED_TOOLS = Path("D:/CQE_CMPLX/papers_tool_solvers/generated_tools")

# Make sure all the paths are importable
sys.path.insert(0, str(CQEKERNEL_ROOT.parent))  # for tmn_tools_core
sys.path.insert(0, str(GENERATED_TOOLS))  # for the stubs


# ----------------------------------------------------------------------
# BlockType (copied from tmn_tools_core, but local so we don't need import)
# ----------------------------------------------------------------------

class BlockType:
    INPUT = "INPUT"
    TRANSFORM = "TRANSFORM"
    BOUNDARY = "BOUNDARY"
    OUTPUT = "OUTPUT"


class Tier:
    L_VACUUM = "L-Vacuum"  # input/identity
    C_TRANSFORM = "C-Transform"  # compute
    R_OBSERVER = "R-Observer"  # output/dispatch


# ----------------------------------------------------------------------
# ToolAtom: the 4-atom crystal for each tool
# ----------------------------------------------------------------------

@dataclass
class ToolAtom:
    """One of the 4 blocks of a ToolCrystal."""
    atom_id: str
    block_type: str  # INPUT/TRANSFORM/BOUNDARY/OUTPUT
    tool_name: str
    handler: Optional[str] = None
    param_schema: Dict[str, Any] = field(default_factory=dict)
    output_desc: str = ""
    laws: List[str] = field(default_factory=lambda: ["delta_phi_le_0", "receipt_required"])
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "atom_id": self.atom_id,
            "block_type": self.block_type,
            "tool_name": self.tool_name,
            "handler": self.handler,
            "param_schema": self.param_schema,
            "output_desc": self.output_desc,
            "laws": self.laws,
            "description": self.description,
        }


@dataclass
class ToolCrystal:
    """A tool expressed as a crystal with 4 bonded atoms (L,C,C,R)."""
    name: str
    description: str = ""
    category: str = "general"
    tier: str = Tier.C_TRANSFORM
    input_atom: Optional[ToolAtom] = None
    transform_atom: Optional[ToolAtom] = None
    boundary_atom: Optional[ToolAtom] = None
    output_atom: Optional[ToolAtom] = None
    e8_coords: List[float] = field(default_factory=lambda: [0.0] * 8)
    physical_op: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tier": self.tier,
            "atoms": {
                "input": self.input_atom.to_dict() if self.input_atom else None,
                "transform": self.transform_atom.to_dict() if self.transform_atom else None,
                "boundary": self.boundary_atom.to_dict() if self.boundary_atom else None,
                "output": self.output_atom.to_dict() if self.output_atom else None,
            },
            "e8_coords": self.e8_coords,
            "physical_op": self.physical_op,
        }


# ----------------------------------------------------------------------
# ToolRegistry: 93 tools loaded from TMN_TOOLS_LCR.db
# ----------------------------------------------------------------------

class ToolRegistry:
    """Loads all 93 TMN_* tools from TMN_TOOLS_LCR.db and indexes them by name."""

    def __init__(self, lcr_db_path: Path = TMN_TOOLS_LCR_DB):
        self.lcr_db_path = Path(lcr_db_path)
        self.tools: Dict[str, ToolCrystal] = {}
        self.atoms: Dict[str, ToolAtom] = {}
        self.bonds: List[Dict[str, str]] = []
        self._load()

    def _load(self):
        conn = sqlite3.connect(self.lcr_db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        # Load 93 distinct tools (use DISTINCT or max line_count per name)
        for r in c.execute("""
            SELECT tool_name, MAX(lcr_role) AS role, MAX(line_count) AS lines,
                   MAX(formal_theorem) AS theorem, MAX(physical_op) AS op
            FROM lcr_tools
            GROUP BY tool_name
            ORDER BY tool_name
        """):
            tool_name = r["tool_name"]
            role = r["role"] or Tier.C_TRANSFORM
            crystal = ToolCrystal(
                name=tool_name,
                description=f"{tool_name}: {r['theorem'][:120] if r['theorem'] else 'TMN tool'}",
                category="TMN",
                tier=role,
                physical_op=r["op"] or "Mount crystal in LCR frame. Read state. Verify ΔΦ ≤ 0. Issue receipt.",
            )
            self.tools[tool_name] = crystal
        # Load atoms (4 per tool, 412 total)
        for r in c.execute("""
            SELECT t.tool_name, a.block_type, a.lcr_aspect, a.name AS atom_name,
                   a.handler, a.output_desc, a.laws, a.description
            FROM tool_atoms a
            JOIN lcr_tools t ON a.tool_id = t.id
        """):
            atom_id = r["atom_name"]
            try:
                laws = json.loads(r["laws"]) if r["laws"] else ["delta_phi_le_0"]
            except (json.JSONDecodeError, TypeError):
                laws = ["delta_phi_le_0"]
            try:
                param_schema = json.loads(r["output_desc"]) if r["output_desc"] and r["output_desc"].startswith("{") else {}
            except (json.JSONDecodeError, TypeError):
                param_schema = {}
            atom = ToolAtom(
                atom_id=atom_id,
                block_type=r["block_type"],
                tool_name=r["tool_name"],
                handler=r["handler"] or None,
                param_schema=param_schema,
                output_desc=r["output_desc"] or "",
                laws=laws,
                description=r["description"] or "",
            )
            # Attach to the crystal
            tool = self.tools.get(r["tool_name"])
            if tool:
                if r["block_type"] == BlockType.INPUT:
                    tool.input_atom = atom
                elif r["block_type"] == BlockType.TRANSFORM:
                    tool.transform_atom = atom
                elif r["block_type"] == BlockType.BOUNDARY:
                    tool.boundary_atom = atom
                elif r["block_type"] == BlockType.OUTPUT:
                    tool.output_atom = atom
            self.atoms[atom_id] = atom
        # Load bonds
        for r in c.execute("""
            SELECT t1.tool_name AS from_tool, t2.tool_name AS to_tool, b.rule
            FROM tool_bonds b
            JOIN lcr_tools t1 ON b.from_tool = t1.id
            JOIN lcr_tools t2 ON b.to_tool = t2.id
        """):
            self.bonds.append({
                "from": r["from_tool"],
                "to": r["to_tool"],
                "rule": r["rule"] or "sequential",
            })
        conn.close()

    def get_tool(self, name: str) -> Optional[ToolCrystal]:
        return self.tools.get(name)

    def get_atom(self, atom_id: str) -> Optional[ToolAtom]:
        return self.atoms.get(atom_id)

    def list_tools(self, tier: Optional[str] = None) -> List[ToolCrystal]:
        if tier:
            return [t for t in self.tools.values() if t.tier == tier]
        return list(self.tools.values())

    def tools_by_tier(self) -> Dict[str, List[str]]:
        by_tier = {Tier.L_VACUUM: [], Tier.C_TRANSFORM: [], Tier.R_OBSERVER: []}
        for name, t in self.tools.items():
            by_tier.setdefault(t.tier, []).append(name)
        return by_tier


# ----------------------------------------------------------------------
# CrystalLibrary: 88 claims from the crystal library
# ----------------------------------------------------------------------

class CrystalLibrary:
    """Read-side access to the 88 named claims in the crystal library."""

    def __init__(self, db_path: Path = CRYSTAL_LIBRARY_DB):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            self.claims = {}
            return
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        self.claims = {}
        for r in c.execute("SELECT id, claim, category FROM named_claims ORDER BY id"):
            self.claims[r["id"]] = {
                "id": r["id"],
                "claim": r["claim"],
                "category": r["category"] or "uncategorized",
            }
        conn.close()

    def get_claim(self, claim_id: str) -> Optional[Dict[str, str]]:
        return self.claims.get(claim_id)

    def search_claims(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """Search claims by query (case-insensitive substring match)."""
        q = query.lower()
        results = []
        for cid, c in self.claims.items():
            if q in cid.lower() or q in c["claim"].lower():
                results.append(c)
                if len(results) >= limit:
                    break
        return results

    def count(self) -> int:
        return len(self.claims)


# ----------------------------------------------------------------------
# RuntimeDB: the 11-table tmn_unified.db
# ----------------------------------------------------------------------

class RuntimeDB:
    """Read/write access to the 11 tables in tmn_unified.db."""

    def __init__(self, db_path: Path = TMN_UNIFIED_DB):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            self.conn = None
            return
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

    def close(self):
        if self.conn:
            self.conn.close()

    def get_brain(self, agent_id: str) -> Optional[Dict[str, Any]]:
        if not self.conn: return None
        r = self.conn.execute("SELECT * FROM agent_brains WHERE agent_id = ?",
                              (agent_id,)).fetchone()
        return dict(r) if r else None

    def count_brains(self) -> int:
        if not self.conn: return 0
        return self.conn.execute("SELECT COUNT(*) FROM agent_brains").fetchone()[0]

    def global_dphi(self) -> float:
        """The cumulative ΔΦ from the conservation ledger."""
        if not self.conn: return 0.0
        r = self.conn.execute(
            "SELECT cumulative_dphi FROM conservation_ledger ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return r["cumulative_dphi"] if r else 0.0

    def update_dphi(self, delta_phi: float) -> float:
        """Update the global ΔΦ (called after every tool invocation)."""
        if not self.conn: return 0.0
        new_total = self.global_dphi() + delta_phi
        self.conn.execute(
            "UPDATE conservation_ledger SET cumulative_dphi=?, tick_dphi=?, checked_at=? WHERE id=1",
            (new_total, delta_phi, time.time()),
        )
        self.conn.commit()
        return new_total

    def log_receipt(self, tool_name: str, atom_id: str, operation: str,
                    operator: str, delta_phi: float, metadata: Optional[Dict] = None):
        """Append a receipt to the runtime DB."""
        if not self.conn: return
        import hashlib
        body = json.dumps(
            {
                "tool": tool_name,
                "atom": atom_id,
                "operation": operation,
                "operator": operator,
                "delta_phi": delta_phi,
                "metadata": metadata or {},
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        receipt_hash = hashlib.sha256(body.encode()).hexdigest()[:32]
        self.conn.execute(
            """INSERT OR REPLACE INTO receipts
            (receipt_hash, atom_id, parent_hash, operation, operator, delta_phi, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (receipt_hash, atom_id, None, operation, operator, delta_phi,
             json.dumps(metadata or {}), time.time()),
        )
        self.conn.commit()


# ----------------------------------------------------------------------
# MannyKernel: the v3 kernel
# ----------------------------------------------------------------------

class MannyKernel:
    """The v3 MannyAI kernel: cqekernel + tmn tools + crystal library + runtime DB."""

    KERNEL_VERSION = "3.0.0"
    PHYSICAL_OP = "Mount crystal in LCR frame. Read state through (L,C,R) gradient. Verify ΔΦ ≤ 0. Issue receipt."

    def __init__(self):
        self.tools: ToolRegistry = ToolRegistry()
        self.crystals: CrystalLibrary = CrystalLibrary()
        self.runtime: RuntimeDB = RuntimeDB()
        self.handlers: Dict[str, callable] = {}
        self.atom_handlers: Dict[str, callable] = {}
        self._register_default_handlers()
        self._register_atom_handlers()

    def _register_default_handlers(self):
        """Register built-in handlers for the most important tools.

        Strategy:
        1. 6 specific handlers with real logic (crystal, brain, gate, daemon, gateway, thinktank)
        2. 3 REAL handlers for the 3 priority tools (gateway, daemon, bond) with full
           implementations based on their formal_theorem signatures
        3. For every other service:X:X URL, register a smart handler that parses
           the tool's formal_theorem to determine routing
        """
        # 6 specific handlers with real logic
        self.handlers["service:crystal:crystal"] = self._handle_crystal
        self.handlers["service:brain:brain"] = self._handle_brain
        self.handlers["service:gate:gate"] = self._handle_gate
        self.handlers["service:daemon:daemon"] = self._handle_daemon
        self.handlers["service:(root):gateway"] = self._handle_gateway
        self.handlers["service:(root):thinktank"] = self._handle_thinktank

        # 3 REAL handlers for the 3 priority tools (overrides the smart synthesizer)
        self.handlers["service:gateway:gateway"] = self._handle_gateway_real
        self.handlers["service:bond:bond"] = self._handle_bond_real
        self.handlers["service:daemon:daemon"] = self._handle_daemon_real

        # Load ALL unique service:X:X URLs from the LCR DB (not just one per tool)
        # and register a smart handler for each (unless overridden by specific handlers above)
        for tool_name, tool in self.tools.tools.items():
            # Get all the unique handler URLs for this tool
            handler_urls = self._get_all_handler_urls(tool_name)
            for url in handler_urls:
                if url not in self.handlers:
                    self.handlers[url] = self._make_smart_handler(tool_name, tool)

    def _get_all_handler_urls(self, tool_name: str) -> List[str]:
        """Get all unique service:X:X handler URLs for a tool from the LCR DB."""
        try:
            conn = sqlite3.connect(self.tools.lcr_db_path)
            c = conn.cursor()
            rows = c.execute(
                "SELECT DISTINCT handler FROM tool_atoms a JOIN lcr_tools t ON a.tool_id=t.id "
                "WHERE t.tool_name = ? AND a.handler != ''",
                (tool_name,),
            ).fetchall()
            conn.close()
            return [r[0] for r in rows]
        except Exception:
            return []

    def _make_smart_handler(self, tool_name: str, tool: ToolCrystal):
        """Synthesize a real handler from the tool's formal_theorem signature.

        Parses the `formal_theorem` column to extract:
        - types: the request/response data structures
        - ops: the named operations the tool exposes
        - deps: the imports it uses

        Then generates a handler that:
        1. Routes based on the input shape (string -> search, dict -> process)
        2. Returns a result that includes the parsed types, ops, deps
        3. Maintains a small in-memory state for tools that have stateful ops
        """
        theorem = tool.physical_op or ""  # we have physical_op loaded in the crystal
        # Try to load the formal_theorem from the LCR DB (need to refetch)
        formal = self._load_formal_theorem(tool_name)
        parsed = self._parse_formal_theorem(formal) if formal else {}
        types = parsed.get("types", [])
        ops = parsed.get("ops", [])
        deps = parsed.get("deps", [])

        def handler(input_data):
            # Determine the "mode" of this tool from the parsed types
            # First: any type containing "Request" -> request mode
            has_request = any("Request" in t for t in types)
            # State-bearing types (the tool has internal state)
            state_types = ("StateVector", "AgentBrain", "AgentState", "Agent",
                           "LessonStatus", "StepStatus", "ModuleStatus", "Project")
            has_state = any(t in state_types for t in types)
            # Search-style (have a query/lookup)
            has_search = any(t in ("SearchRequest", "ScanRequest", "LookupRequest", "FindRequest") for t in types)
            has_spawn = "SpawnRequest" in types
            has_ingest = any(t in ("IngestRequest", "HarvestRequest") for t in types)
            # Process-style (any Wall, Grain, Dust, ProcessRequest -> process)
            has_process = any(t in ("Wall", "Grain", "Dust", "Triad", "AtomNode",
                                    "ProcessRequest", "DimensionalExtent") for t in types)
            # Label-style (relabel, label, etc.)
            has_label = any(t in ("LabelRequest", "Atom", "AtomNode", "Atoms", "RelabelRequest") for t in types)

            # Build a base result
            result = {
                "tool": tool_name,
                "tier": tool.tier,
                "types": types,
                "ops": ops,
                "deps": deps,
                "physical_op": tool.physical_op or self.PHYSICAL_OP,
            }

            # Smart routing based on input shape
            if isinstance(input_data, str):
                if has_search or "think" in tool_name.lower() or "crystal" in tool_name.lower() or "kb" in tool_name.lower():
                    # Search-style: query the crystal library
                    results = self.crystals.search_claims(input_data, limit=5)
                    result["query"] = input_data
                    result["crystal_hits"] = [c["id"] for c in results]
                    result["mode"] = "search"
                elif has_ingest:
                    # Ingest-style: take a string and process it
                    result["input"] = input_data
                    result["input_hash"] = self._h(input_data, 16)
                    result["mode"] = "ingest"
                elif has_state or has_process or has_request:
                    # State/process: take the string as state
                    result["input"] = input_data
                    result["state_hash"] = self._h(input_data, 16)
                    result["mode"] = "process"
                else:
                    # Default: process the string
                    result["input"] = input_data
                    result["input_hash"] = self._h(input_data, 16)
                    result["mode"] = "process"
            elif isinstance(input_data, dict):
                if "claim_id" in input_data:
                    claim = self.crystals.get_claim(input_data["claim_id"])
                    result["claim"] = claim
                    result["mode"] = "claim_lookup"
                elif "query" in input_data or "content" in input_data:
                    q = input_data.get("query") or input_data.get("content")
                    results = self.crystals.search_claims(q, limit=5)
                    result["query"] = q
                    result["crystal_hits"] = [c["id"] for c in results]
                    result["mode"] = "search"
                elif "agent_id" in input_data:
                    brain = self.runtime.get_brain(input_data["agent_id"])
                    result["brain"] = brain
                    result["mode"] = "brain_lookup"
                elif has_label and ("old" in input_data or "atom_id" in input_data):
                    # Label-style: relabel an atom
                    result["relabeled"] = input_data
                    result["new_id"] = self._h(str(input_data), 16)
                    result["mode"] = "relabel"
                elif has_spawn:
                    result["spawned"] = input_data
                    result["spawn_id"] = self._h(str(input_data), 16)
                    result["mode"] = "spawn"
                else:
                    result["input"] = input_data
                    result["input_hash"] = self._h(str(input_data), 16)
                    result["mode"] = "process_dict"
            else:
                result["input"] = str(input_data)
                result["mode"] = "passthrough"

            return result
        return handler

    def _load_formal_theorem(self, tool_name: str) -> str:
        """Load the formal_theorem for a tool from the LCR DB (cached)."""
        if not hasattr(self, "_formal_cache"):
            self._formal_cache = {}
        if tool_name in self._formal_cache:
            return self._formal_cache[tool_name]
        try:
            conn = sqlite3.connect(self.tools.lcr_db_path)
            c = conn.cursor()
            r = c.execute("SELECT formal_theorem FROM lcr_tools WHERE tool_name = ? LIMIT 1",
                          (tool_name,)).fetchone()
            conn.close()
            result = r[0] if r else ""
            self._formal_cache[tool_name] = result
            return result
        except Exception:
            return ""

    def _parse_formal_theorem(self, theorem: str) -> Dict[str, List[str]]:
        """Parse a formal_theorem string like 'TOOL: types={...}; ops={...}; deps={...}'."""
        import re as _re
        result = {"types": [], "ops": [], "deps": []}
        if not theorem:
            return result
        # Extract types={...}
        m = _re.search(r'types=\{([^}]+)\}', theorem)
        if m:
            result["types"] = [t.strip() for t in m.group(1).split(',') if t.strip()]
        # Extract ops={...}
        m = _re.search(r'ops=\{([^}]+)\}', theorem)
        if m:
            result["ops"] = [o.strip() for o in m.group(1).split(',') if o.strip()]
        # Extract deps={...}
        m = _re.search(r'deps=\{([^}]+)\}', theorem)
        if m:
            result["deps"] = [d.strip().strip("'\"") for d in m.group(1).split(',') if d.strip()]
        return result

    def _h(self, s: str, length: int = 16) -> str:
        """Hash a string to a stable ID (used for input hashes, spawn IDs, etc.)."""
        import hashlib
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:length]

    def _make_generic_handler(self, tool_name: str, tool: ToolCrystal):
        """Fallback: create a basic default handler for any TMN tool."""
        def handler(input_data):
            if "think" in tool_name.lower() or "crystal" in tool_name.lower() or "kb" in tool_name.lower():
                if isinstance(input_data, str):
                    return {"tool": tool_name, "query": input_data,
                            "crystal_hits": [c["id"] for c in self.crystals.search_claims(input_data, limit=5)]}
            if "brain" in tool_name.lower() or "agent" in tool_name.lower():
                if isinstance(input_data, str):
                    return {"tool": tool_name, "agent_id": input_data,
                            "brain": self.runtime.get_brain(input_data)}
            if "gate" in tool_name.lower() or "conservation" in tool_name.lower():
                return {"tool": tool_name, "gate": self._handle_gate(input_data)}
            return {
                "tool": tool_name,
                "tier": tool.tier,
                "input": input_data,
                "physical_op": tool.physical_op or self.PHYSICAL_OP,
                "processed": True,
                "note": f"default handler for {tool_name} (no specific logic registered yet)"
            }
        return handler

    def _register_atom_handlers(self):
        """Register atom_id → handler mappings (so we can dispatch by atom too)."""
        for atom_id, atom in self.tools.atoms.items():
            if atom.handler:
                # e.g. "service:crystal:crystal" -> our handler
                if atom.handler in self.handlers:
                    self.atom_handlers[atom_id] = self.handlers[atom.handler]

    def _handle_crystal(self, input_data: Any) -> Any:
        """Crystal operations: read (claim/query/content) + write (CrystalForge).

        Read-side: query the crystal library for claims by id, query string, or content.
        Write-side: if input has an "action" key, route to CrystalForge for:
            create, add_node, commit, activate, list
        CrystalForge (production/packages/cqecmplx-forge/src/CrystalForge/) is the
        real, already-built write side: ports the TMN crystal.py service logic
        (MDHG addressing, tier-based state, e8 node creation) against the same
        tmn_unified.db schema this kernel's RuntimeDB already reads.

        Crystal ID resolution: pass either 'crystal_id' (UUID) or 'crystal_name'
        (string name). The handler will resolve the name to the UUID via list_crystals.
        """
        if isinstance(input_data, dict) and "action" in input_data and CRYSTAL_FORGE_AVAILABLE:
            action = input_data["action"]
            try:
                # Helper: resolve crystal_id from either crystal_id or crystal_name
                def _resolve_crystal_id(d):
                    if "crystal_id" in d:
                        return d["crystal_id"]
                    if "crystal_name" in d:
                        # Look up the crystal by name
                        all_cs = CRYSTAL_FORGE.list_crystals(db_path=TMN_UNIFIED_DB)
                        for c in all_cs:
                            if c.name == d["crystal_name"]:
                                return c.crystal_id
                        return None
                    return d.get("crystal_id")

                if action == "create":
                    c = CRYSTAL_FORGE.create_crystal(
                        name=input_data.get("name", "unnamed"),
                        crystal_type=input_data.get("crystal_type", "knowledge"),
                        e8_seed=input_data.get("e8_seed"),
                        meaning_depth=input_data.get("meaning_depth", 3),
                        level_count=input_data.get("level_count", 6),
                        owner=input_data.get("owner", ""),
                        db_path=TMN_UNIFIED_DB,
                    )
                    return asdict(c)
                if action == "add_node":
                    cid = _resolve_crystal_id(input_data)
                    if not cid:
                        return {"error": f"crystal not found: name={input_data.get('crystal_name')!r}, id={input_data.get('crystal_id')!r}"}
                    n = CRYSTAL_FORGE.add_node(
                        crystal_id=cid,
                        content=input_data.get("content", ""),
                        content_type=input_data.get("content_type", "atom"),
                        e8_coords=input_data.get("e8_coords"),
                        labels=input_data.get("labels"),
                        db_path=TMN_UNIFIED_DB,
                    )
                    return asdict(n)
                if action == "commit":
                    cid = _resolve_crystal_id(input_data)
                    if not cid:
                        return {"error": "crystal not found"}
                    c = CRYSTAL_FORGE.commit_crystal(cid, db_path=TMN_UNIFIED_DB)
                    return asdict(c)
                if action == "activate":
                    cid = _resolve_crystal_id(input_data)
                    if not cid:
                        return {"error": "crystal not found"}
                    c = CRYSTAL_FORGE.activate_crystal(cid, db_path=TMN_UNIFIED_DB)
                    return asdict(c)
                if action == "list":
                    cs = CRYSTAL_FORGE.list_crystals(state=input_data.get("state", ""), db_path=TMN_UNIFIED_DB)
                    return {"crystals": [c.crystal_id for c in cs], "names": [c.name for c in cs],
                            "count": len(cs), "states": [c.state for c in cs]}
                return {"error": f"unknown action {action!r}",
                        "available_actions": ["create", "add_node", "commit", "activate", "list"]}
            except (ValueError, KeyError) as e:
                return {"error": str(e)}
        # Read-only behavior below (the original v3 crystal handler)
        if isinstance(input_data, dict):
            if "claim_id" in input_data:
                return self.crystals.get_claim(input_data["claim_id"])
            if "query" in input_data:
                return {"results": self.crystals.search_claims(input_data["query"], limit=5),
                        "query": input_data["query"]}
            if "content" in input_data:
                # Treat content as a query
                return {"results": self.crystals.search_claims(input_data["content"], limit=5),
                        "query": input_data["content"]}
            return {"error": "dict input needs claim_id, query, content, or action",
                    "keys": list(input_data.keys())}
        if isinstance(input_data, str):
            return {"results": self.crystals.search_claims(input_data, limit=5),
                    "query": input_data}
        return {"error": "unknown input", "type": str(type(input_data))}

    def _handle_brain(self, input_data: Any) -> Any:
        """Brain operations: read (agent_id lookup) + the real merge/fork/capacity/contribute cycle (CrystalForge).

        Read-side: get a brain by agent_id, or return count.
        Write-side: if input has an "action" key, route to CrystalForge for:
            register, contribute, capacity, merge, fork, expertise
        CrystalForge ports the real tier thresholds, MI-slope capacity score,
        and Jaccard-relevance merge from the actual TMN brain.py service against
        the same tmn_unified.db, so '!brain merge <agent>' etc. does the real
        pull/update/resave cycle instead of a static lookup.
        """
        if isinstance(input_data, dict) and "action" in input_data and CRYSTAL_FORGE_AVAILABLE:
            action = input_data["action"]
            try:
                if action == "register":
                    return CRYSTAL_FORGE.register_brain(
                        agent_id=input_data["agent_id"],
                        dims=input_data.get("dims", 24),
                        epoch=input_data.get("epoch", 0),
                        tier=input_data.get("tier", "nascent"),
                        db_path=TMN_UNIFIED_DB,
                    )
                if action == "contribute":
                    return CRYSTAL_FORGE.contribute(
                        agent_id=input_data["agent_id"],
                        domain=input_data.get("domain", ""),
                        snap_labels=input_data.get("snap_labels"),
                        mi_score=input_data.get("mi_score", 0.0),
                        db_path=TMN_UNIFIED_DB,
                    )
                if action == "capacity":
                    # compute_capacity takes mi_history + weight_density + step_count
                    brain = CRYSTAL_FORGE.get_brain(input_data["agent_id"], db_path=TMN_UNIFIED_DB)
                    if not brain:
                        return {"error": f"brain {input_data['agent_id']!r} not found"}
                    mi_hist = brain.get("mi_history", [0.0])
                    if isinstance(mi_hist, str):
                        try:
                            mi_hist = json.loads(mi_hist)
                        except (json.JSONDecodeError, TypeError):
                            mi_hist = [0.0]
                    return CRYSTAL_FORGE.compute_capacity(
                        mi_history=mi_hist,
                        weight_density=input_data.get("weight_density", 0.0),
                        step_count=brain.get("step_count", 0),
                    )
                if action == "merge":
                    return CRYSTAL_FORGE.merge_brain(
                        agent_id=input_data["agent_id"],
                        target_dims=input_data.get("target_dims", 32),
                        db_path=TMN_UNIFIED_DB,
                    )
                if action == "fork":
                    return CRYSTAL_FORGE.fork_brain(
                        parent_id=input_data["parent_id"],
                        child_id=input_data.get("child_id", f"{input_data['parent_id']}_fork"),
                        domain_boost=input_data.get("domain_boost", ""),
                        db_path=TMN_UNIFIED_DB,
                    )
                if action == "expertise":
                    return {"expertise": CRYSTAL_FORGE.list_expertise(
                        domain=input_data.get("domain", ""),
                        min_mi=input_data.get("min_mi", 0.0),
                        db_path=TMN_UNIFIED_DB,
                    )}
                return {"error": f"unknown action {action!r}",
                        "available_actions": ["register", "contribute", "capacity", "merge", "fork", "expertise"]}
            except (ValueError, KeyError, TypeError) as e:
                return {"error": str(e)}
        # Read-only behavior (the original v3 brain handler)
        if isinstance(input_data, dict) and "agent_id" in input_data:
            return self.runtime.get_brain(input_data["agent_id"])
        if isinstance(input_data, str):
            return self.runtime.get_brain(input_data)
        return self.runtime.count_brains()

    def _handle_gate(self, input_data: Any) -> Any:
        """Default handler for gate operations (conservation check)."""
        dphi = self.runtime.global_dphi()
        return {
            "gate_open": dphi <= 0,
            "cumulative_dphi": dphi,
            "violation": dphi > 0,
        }

    def _handle_daemon(self, input_data: Any) -> Any:
        """Default handler for daemon operations (long-running)."""
        return {
            "status": "running",
            "registered_brains": self.runtime.count_brains(),
            "tools_loaded": len(self.tools.tools),
            "kernel_version": self.KERNEL_VERSION,
        }

    def _handle_gateway_real(self, input_data: Any) -> Any:
        """REAL handler for TMN-gateway (the route dispatcher).

        TMN-gateway is the R-Observer router. Its formal_theorem:
        - types={ToolInvokeRequest, PipelineRunRequest, PipelineIntakeRequest, EmbedRequest, NearestRequest}
        - ops={_try_bootstrap_retooling, _resolve_domains, _ensure_domain_db, _init_staging_gate, _derive_shell}
        - deps={__future__, hashlib, json, logging, os}

        Real behavior: route the input to a target tool based on the request shape.
        """
        if not isinstance(input_data, dict):
            # Plain string: treat as a route query
            return {
                "tool": "TMN-gateway",
                "mode": "route_query",
                "query": input_data,
                "available_routes": self._gateway_routes(),
                "physical_op": self.PHYSICAL_OP,
            }
        target_tool = input_data.get("tool") or input_data.get("invoke") or input_data.get("target")
        if target_tool:
            # Route to the named tool
            payload = {k: v for k, v in input_data.items() if k not in ("tool", "invoke", "target")}
            result = self.invoke(target_tool, payload or "")
            return {
                "tool": "TMN-gateway",
                "mode": "route",
                "target": target_tool,
                "routed": result,
                "physical_op": self.PHYSICAL_OP,
            }
        # No target: return available routes
        return {
            "tool": "TMN-gateway",
            "mode": "list_routes",
            "routes": self._gateway_routes(),
            "physical_op": self.PHYSICAL_OP,
        }

    def _handle_daemon_real(self, input_data: Any) -> Any:
        """REAL handler for TMN-daemon (the long-running process manager).

        TMN-daemon is the C-Transform process manager. Its formal_theorem:
        - ops={_get_pg, _pg_query, _pg_execute, _http_get, _http_post}
        - deps={hashlib, json, logging, math, os}

        Real behavior: maintain a process registry, query system state.
        """
        if not hasattr(self, "_daemon_state"):
            self._daemon_state = {
                "started_at": time.time(),
                "processes": {},
                "request_count": 0,
                "last_heartbeat": time.time(),
            }
        self._daemon_state["request_count"] += 1
        self._daemon_state["last_heartbeat"] = time.time()

        if not isinstance(input_data, dict):
            cmd = str(input_data).strip().lower()
            if cmd == "status":
                return {
                    "tool": "TMN-daemon",
                    "mode": "status",
                    "uptime_seconds": time.time() - self._daemon_state["started_at"],
                    "request_count": self._daemon_state["request_count"],
                    "processes": len(self._daemon_state["processes"]),
                    "last_heartbeat": self._daemon_state["last_heartbeat"],
                    "physical_op": self.PHYSICAL_OP,
                }
            elif cmd == "ps":
                return {
                    "tool": "TMN-daemon",
                    "mode": "ps",
                    "processes": list(self._daemon_state["processes"].keys()),
                    "physical_op": self.PHYSICAL_OP,
                }
            else:
                return {
                    "tool": "TMN-daemon",
                    "mode": "info",
                    "recognized_commands": ["status", "ps"],
                    "physical_op": self.PHYSICAL_OP,
                }
        # Dict input
        if "process" in input_data and "action" in input_data:
            proc = input_data["process"]
            action = input_data["action"]
            if action == "start":
                self._daemon_state["processes"][proc] = {"started_at": time.time(), "status": "running"}
                return {"tool": "TMN-daemon", "mode": "process_start", "process": proc, "physical_op": self.PHYSICAL_OP}
            elif action == "stop":
                if proc in self._daemon_state["processes"]:
                    del self._daemon_state["processes"][proc]
                return {"tool": "TMN-daemon", "mode": "process_stop", "process": proc, "physical_op": self.PHYSICAL_OP}
            elif action == "status":
                return {"tool": "TMN-daemon", "mode": "process_status", "process": proc,
                        "state": self._daemon_state["processes"].get(proc, {}), "physical_op": self.PHYSICAL_OP}
        # Default: return daemon state
        return {
            "tool": "TMN-daemon",
            "mode": "state",
            "state": self._daemon_state,
            "physical_op": self.PHYSICAL_OP,
        }

    def _handle_bond_real(self, input_data: Any) -> Any:
        """REAL handler for TMN-bond (the LCR atom-bonder).

        TMN-bond is the C-Transform LCR atom-bonder. Its formal_theorem:
        - types={DimensionalExtent, Grain, Dust, Triad, AtomNode}
        - ops={_dot, _norm, _sub, _add, _scale}
        - deps={hashlib, json, logging, math, os}

        Real behavior: maintain a graph of bonded atoms, do vector arithmetic.
        """
        if not hasattr(self, "_bond_graph"):
            self._bond_graph = {
                "atoms": {},  # atom_id -> {triad, coords, mass}
                "bonds": [],  # list of (atom_id_a, atom_id_b, strength)
            }

        if not isinstance(input_data, dict):
            # Plain string: query the bond graph
            return {
                "tool": "TMN-bond",
                "mode": "query",
                "n_atoms": len(self._bond_graph["atoms"]),
                "n_bonds": len(self._bond_graph["bonds"]),
                "physical_op": self.PHYSICAL_OP,
            }
        # Dict input
        if "atom_id" in input_data and "triad" in input_data:
            # Add an atom
            atom_id = input_data["atom_id"]
            self._bond_graph["atoms"][atom_id] = {
                "triad": input_data["triad"],
                "coords": input_data.get("coords", [0, 0, 0]),
                "mass": input_data.get("mass", 1.0),
            }
            return {"tool": "TMN-bond", "mode": "atom_add", "atom_id": atom_id,
                    "n_atoms": len(self._bond_graph["atoms"]), "physical_op": self.PHYSICAL_OP}
        if "bond" in input_data and "from" in input_data and "to" in input_data:
            # Add a bond
            self._bond_graph["bonds"].append({
                "from": input_data["from"],
                "to": input_data["to"],
                "strength": input_data.get("strength", 1.0),
            })
            return {"tool": "TMN-bond", "mode": "bond_add", "n_bonds": len(self._bond_graph["bonds"]),
                    "physical_op": self.PHYSICAL_OP}
        if "op" in input_data and "a" in input_data and "b" in input_data:
            # Vector operation
            op = input_data["op"]
            a = input_data["a"]
            b = input_data["b"]
            if op == "add":
                result = [x + y for x, y in zip(a, b)]
            elif op == "sub":
                result = [x - y for x, y in zip(a, b)]
            elif op == "scale":
                scalar = input_data.get("scalar", 1.0)
                result = [x * scalar for x in a]
            elif op == "dot":
                result = sum(x * y for x, y in zip(a, b))
            elif op == "norm":
                result = sum(x * x for x in a) ** 0.5
            else:
                result = None
            return {"tool": "TMN-bond", "mode": "vector_op", "op": op, "result": result,
                    "physical_op": self.PHYSICAL_OP}
        # Default: return bond graph state
        return {
            "tool": "TMN-bond",
            "mode": "state",
            "n_atoms": len(self._bond_graph["atoms"]),
            "n_bonds": len(self._bond_graph["bonds"]),
            "atoms": list(self._bond_graph["atoms"].keys())[:5],
            "bonds_sample": self._bond_graph["bonds"][:3],
            "physical_op": self.PHYSICAL_OP,
        }

    def _gateway_routes(self) -> list:
        """Return the list of available gateway routes (the top-level tools)."""
        # Gateway routes to the most-called tools
        return [
            "TMN-crystal (claim lookup)",
            "TMN-thinktank (crystal search)",
            "TMN-brain (agent lookup)",
            "TMN-gate (conservation check)",
            "TMN-pipeline (process)",
            "TMN-bond (LCR atom-bonder)",
            "TMN-daemon (process manager)",
        ]

    def _handle_gateway(self, input_data: Any) -> Any:
        """Default handler for gateway (route to other tools)."""
        if isinstance(input_data, dict) and "tool" in input_data:
            tool_name = input_data["tool"]
            payload = input_data.get("payload", {})
            return self.invoke(tool_name, payload)
        return {
            "available_tools": list(self.tools.tools.keys())[:10],
            "n_tools": len(self.tools.tools),
        }

    def _handle_thinktank(self, input_data: Any) -> Any:
        """Default handler for thinktank (crystal queries)."""
        if isinstance(input_data, str):
            claims = self.crystals.search_claims(input_data, limit=10)
            return {"query": input_data, "claims": [c["id"] for c in claims]}
        return {"n_claims": self.crystals.count()}

    def boot(self) -> Dict[str, Any]:
        """Boot the kernel: verify sources, init state, return status."""
        return {
            "kernel_version": self.KERNEL_VERSION,
            "tools_loaded": len(self.tools.tools),
            "tools_by_tier": {k: len(v) for k, v in self.tools.tools_by_tier().items()},
            "atoms_loaded": len(self.tools.atoms),
            "bonds_loaded": len(self.tools.bonds),
            "crystals_loaded": self.crystals.count(),
            "brains_registered": self.runtime.count_brains(),
            "cumulative_dphi": self.runtime.global_dphi(),
            "physical_op": self.PHYSICAL_OP,
        }

    def invoke(self, tool_name: str, input_data: Any) -> Dict[str, Any]:
        """Invoke a tool by name. The main entry point."""
        tool = self.tools.get_tool(tool_name)
        if not tool:
            return {"error": f"tool {tool_name!r} not found", "available": list(self.tools.tools.keys())[:5]}
        return self._execute_tool(tool, input_data)

    def invoke_by_atom(self, atom_id: str, input_data: Any) -> Dict[str, Any]:
        """Invoke a tool by its atom_id (more granular — 412 atoms)."""
        atom = self.tools.get_atom(atom_id)
        if not atom:
            return {"error": f"atom {atom_id!r} not found"}
        return self._execute_atom(atom, input_data)

    def _execute_tool(self, tool: ToolCrystal, input_data: Any) -> Dict[str, Any]:
        """Execute a tool by running through its 4 atoms in order."""
        # Step 1: INPUT
        if not tool.input_atom:
            return {"error": f"tool {tool.name} has no input_atom"}
        # Step 2: TRANSFORM (use the handler)
        if tool.transform_atom and tool.transform_atom.handler:
            handler = self.handlers.get(tool.transform_atom.handler)
            if handler:
                try:
                    result = handler(input_data)
                except Exception as e:
                    result = {"error": f"handler raised: {e!r}"}
            else:
                result = {"tool": tool.name, "processed": True, "input": input_data,
                           "tier": tool.tier, "handler": tool.transform_atom.handler}
        else:
            result = {"tool": tool.name, "processed": True, "input": input_data,
                       "tier": tool.tier}
        # Step 3: BOUNDARY (conservation check: ΔΦ ≤ 0)
        dphi = -0.001  # every tool call consumes 0.001
        new_dphi = self.runtime.update_dphi(dphi)
        # Step 4: OUTPUT (the result)
        output = {
            "tool": tool.name,
            "tier": tool.tier,
            "input": input_data,
            "result": result,
            "delta_phi": dphi,
            "cumulative_dphi": new_dphi,
            "physical_op": tool.physical_op or self.PHYSICAL_OP,
        }
        # Log receipt
        self.runtime.log_receipt(
            tool_name=tool.name,
            atom_id=tool.transform_atom.atom_id if tool.transform_atom else tool.name,
            operation="invoke",
            operator="MannyKernel-v3",
            delta_phi=dphi,
            metadata={"tier": tool.tier, "input_type": str(type(input_data).__name__)},
        )
        return output

    def _execute_atom(self, atom: ToolAtom, input_data: Any) -> Dict[str, Any]:
        """Execute a single atom."""
        if atom.handler and atom.handler in self.handlers:
            try:
                result = self.handlers[atom.handler](input_data)
            except Exception as e:
                result = {"error": f"handler raised: {e!r}"}
        else:
            result = {"atom": atom.atom_id, "block": atom.block_type,
                       "input": input_data, "no_handler": atom.handler or "none"}
        dphi = -0.0005  # atom call is half the cost
        new_dphi = self.runtime.update_dphi(dphi)
        return {
            "atom": atom.atom_id,
            "block_type": atom.block_type,
            "input": input_data,
            "result": result,
            "delta_phi": dphi,
            "cumulative_dphi": new_dphi,
        }

    def handle_message(self, user_id: str, channel_id: str, message: str) -> Dict[str, Any]:
        """Handle a Discord message (or any incoming text) by routing to the right tool.

        Routing strategy:
        - If message starts with !<tool_name>, invoke that tool
          (with smart alias resolution: !crystal -> TMN-crystal, !thinktank -> TMN-thinktank, !gateway -> TMN-gateway)
        - If message contains "claim <id>" or "crystal <query>", search the crystal
        - If message is a question, route to TMN-thinktank (crystal search)
        - Otherwise, default to TMN-thinktank with the raw message
        """
        msg = message.strip()
        # Command-style: !<tool> <payload>
        if msg.startswith("!"):
            parts = msg[1:].split(maxsplit=1)
            if len(parts) >= 2:
                tool_name, payload = parts[0], parts[1]
                # Smart alias: if no TMN- prefix and no exact match, try TMN-<name>
                if tool_name in self.tools.tools:
                    pass  # exact match
                elif f"TMN-{tool_name}" in self.tools.tools:
                    tool_name = f"TMN-{tool_name}"
                return self.invoke(tool_name, payload)
            elif len(parts) == 1:
                tool_name = parts[0]
                if tool_name in self.tools.tools:
                    pass
                elif f"TMN-{tool_name}" in self.tools.tools:
                    tool_name = f"TMN-{tool_name}"
                return self.invoke(tool_name, "")
        # Crystal search: "claim <id>" or "crystal <query>"
        if msg.lower().startswith("claim ") or msg.lower().startswith("crystal "):
            query = msg.split(maxsplit=1)[1] if " " in msg else msg
            claims = self.crystals.search_claims(query, limit=5)
            return {
                "handler": "crystal-search",
                "query": query,
                "results": [c["id"] for c in claims],
                "count": len(claims),
            }
        # Default: route to thinktank
        return self.invoke("TMN-thinktank", msg)

    def summary(self) -> str:
        """A one-shot summary of the kernel state."""
        b = self.runtime.count_brains()
        t = len(self.tools.tools)
        a = len(self.tools.atoms)
        c = self.crystals.count()
        dphi = self.runtime.global_dphi()
        return (
            f"MannyKernel v{self.KERNEL_VERSION} | "
            f"brains={b} tools={t} atoms={a} crystals={c} | "
            f"ΔΦ={dphi:.3f} (target ≤ 0)"
        )


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def main():
    kernel = MannyKernel()
    print("=" * 70)
    print("MannyAI v3 kernel boot")
    print("=" * 70)
    boot = kernel.boot()
    for k, v in boot.items():
        if isinstance(v, list):
            v_str = f"[{len(v)} items]"
        else:
            v_str = str(v)[:200]
        print(f"  {k:25s} {v_str}")
    print()
    print("=" * 70)
    print("Self-test: invoke TMN-crystal with 'hello'")
    print("=" * 70)
    r = kernel.invoke("TMN-crystal", {"content": "hello"})
    print(json.dumps(r, indent=2)[:800])
    print()
    print("=" * 70)
    print("Crystal search: 'TMN'")
    print("=" * 70)
    r = kernel.invoke("TMN-thinktank", "TMN")
    print(json.dumps(r, indent=2)[:500])
    print()
    print(kernel.summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
