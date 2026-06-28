"""
ChromaForge MDHG — Multi-Dimensional Hash Graph, oloid resolution hierarchy.

9 levels: grain → dust → triad → block → cluster → domain → region → planet → universe

This IS the oloid's scale-invariant resolution ladder. At each level boundary,
local resolution at level N = global resolution at level N-1.

Hashes incorporate content + parent lineage + level + coupling constant κ.
Every node is content-addressed: same content at same level under same parent
always produces the same hash.

Design: MDHGEngine is a class — one instance per session context.
Module-level singleton `engine` available.
"""
import hashlib
import json
import math
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

# ─── Lookup tables (import-time, read-only) ────────────────────────────────────

PHI: float = (1 + math.sqrt(5)) / 2
COUPLING: float = math.log(PHI) / 16

HIERARCHY_LEVELS: Tuple[str, ...] = (
    "grain", "dust", "triad", "block", "cluster",
    "domain", "region", "planet", "universe",
)

# Level index → 2-char prefix (computed once)
_LEVEL_PREFIX: Dict[int, str] = {i: HIERARCHY_LEVELS[i][:2] for i in range(9)}

# Level name → index (computed once)
_LEVEL_INDEX: Dict[str, int] = {name: i for i, name in enumerate(HIERARCHY_LEVELS)}

SESSION_TTL: int = 1800
CLEANUP_INTERVAL: int = 300


# ─── Pure graph functions (stateless, use lookup tables) ─────────────────────

def _mdhg_hash(content: str, parent_hash: Optional[str], level: int,
               coupling: float) -> str:
    payload = json.dumps({
        "content": content,
        "parent":  parent_hash or "ROOT",
        "level":   level,
        "coupling": coupling,
    }, sort_keys=True).encode()
    full = hashlib.sha256(payload).hexdigest()
    return f"{_LEVEL_PREFIX[level]}-{full[:14]}"


def _node_depth(node: Dict, graph: Dict) -> int:
    depth = 0
    current = node
    visited: set = set()
    while current.get("parent_hash") and current["parent_hash"] in graph:
        if current["hash"] in visited:
            break
        visited.add(current["hash"])
        current = graph[current["parent_hash"]]
        depth += 1
    return depth


def _children_of(node_hash: str, graph: Dict) -> List[str]:
    return [h for h, n in graph.items() if n.get("parent_hash") == node_hash]


def _siblings_of(node_hash: str, graph: Dict) -> List[str]:
    node = graph.get(node_hash)
    if not node or not node.get("parent_hash"):
        return []
    parent = node["parent_hash"]
    return [h for h, n in graph.items()
            if n.get("parent_hash") == parent and h != node_hash]


def _ancestors_of(node_hash: str, graph: Dict) -> List[str]:
    path: List[str] = []
    current = graph.get(node_hash)
    visited: set = set()
    while current and current.get("parent_hash") and current["parent_hash"] in graph:
        if current["hash"] in visited:
            break
        visited.add(current["hash"])
        path.append(current["parent_hash"])
        current = graph[current["parent_hash"]]
    return path


def _subtree(node_hash: str, graph: Dict, max_depth: int) -> List[str]:
    result: List[str] = []
    queue: List[Tuple[str, int]] = [(node_hash, 0)]
    visited: set = {node_hash}
    while queue:
        h, d = queue.pop(0)
        if d > max_depth:
            continue
        result.append(h)
        for child in _children_of(h, graph):
            if child not in visited:
                visited.add(child)
                queue.append((child, d + 1))
    return result


def _graph_stats(graph: Dict) -> Dict:
    if not graph:
        return {"nodes": 0, "max_depth": 0, "roots": 0, "leaves": 0, "levels": {}}
    roots = [h for h, n in graph.items()
             if not n.get("parent_hash") or n["parent_hash"] not in graph]
    all_parents = {n.get("parent_hash") for n in graph.values()}
    leaves = [h for h in graph if h not in all_parents]
    level_counts: Dict[int, int] = {}
    for n in graph.values():
        lvl = n.get("level", 0)
        level_counts[lvl] = level_counts.get(lvl, 0) + 1
    max_depth = max((_node_depth(n, graph) for n in graph.values()), default=0)
    return {
        "nodes": len(graph),
        "max_depth": max_depth,
        "roots": len(roots),
        "leaves": len(leaves),
        "levels": {HIERARCHY_LEVELS[k]: v for k, v in sorted(level_counts.items())},
    }


# ─── Engine class ──────────────────────────────────────────────────────────────

class MDHGEngine:
    """Multi-Dimensional Hash Graph engine. One instance = one session namespace."""

    def __init__(self, coupling: float = COUPLING, session_ttl: int = SESSION_TTL):
        self.coupling: float = coupling
        self.session_ttl: int = session_ttl
        self._sessions: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._start_cleanup()

    # ── Hash ───────────────────────────────────────────────────────────────────

    def hash(self, content: str, parent_hash: Optional[str] = None,
             level: int = 0) -> str:
        """Compute a content-addressed MDHG hash."""
        level = max(0, min(8, level))
        return _mdhg_hash(content, parent_hash, level, self.coupling)

    # ── Session lifecycle ──────────────────────────────────────────────────────

    def create_session(self, name: Optional[str] = None,
                       max_depth: int = 9) -> Dict:
        session_id = uuid.uuid4().hex[:12]
        session = {
            "session_id":  session_id,
            "name":        name or f"mdhg-{session_id}",
            "max_depth":   max(1, min(9, max_depth)),
            "graph":       {},
            "created_at":  time.time(),
            "last_access": time.time(),
            "root_hashes": [],
        }
        self._sessions[session_id] = session
        return {"session_id": session_id, "name": session["name"], "ttl": self.session_ttl}

    def add_node(self, session_id: str, content: str,
                 parent_hash: Optional[str] = None,
                 level: int = 0,
                 metadata: Optional[Dict] = None) -> Dict:
        session = self._get_session(session_id)
        if parent_hash and parent_hash not in session["graph"]:
            raise KeyError(f"Parent {parent_hash} not in graph")
        level = max(0, min(8, level))
        node_hash = _mdhg_hash(content, parent_hash, level, self.coupling)

        if node_hash in session["graph"]:
            return {"hash": node_hash, "exists": True, "level": HIERARCHY_LEVELS[level]}

        node = {
            "hash":        node_hash,
            "content":     content,
            "parent_hash": parent_hash,
            "level":       level,
            "level_name":  HIERARCHY_LEVELS[level],
            "metadata":    metadata or {},
            "created_at":  time.time(),
        }
        session["graph"][node_hash] = node
        if not parent_hash:
            session["root_hashes"].append(node_hash)

        return {
            "hash":       node_hash,
            "level":      HIERARCHY_LEVELS[level],
            "depth":      _node_depth(node, session["graph"]),
            "graph_size": len(session["graph"]),
        }

    def traverse(self, session_id: str, start_hash: str,
                 direction: str = "down", max_steps: int = 10) -> Dict:
        """direction: 'up' | 'down' | 'siblings' | 'all'"""
        session = self._get_session(session_id)
        graph = session["graph"]
        if start_hash not in graph:
            raise KeyError(f"Node {start_hash} not found")

        if direction == "down":
            visited = _subtree(start_hash, graph, max_steps)
        elif direction == "up":
            visited = [start_hash] + _ancestors_of(start_hash, graph)[:max_steps]
        elif direction == "siblings":
            visited = [start_hash] + _siblings_of(start_hash, graph)[:max_steps]
        else:
            down = _subtree(start_hash, graph, max_steps // 2)
            up = _ancestors_of(start_hash, graph)[:max_steps // 2]
            sibs = _siblings_of(start_hash, graph)
            visited = list(dict.fromkeys(up + [start_hash] + sibs + down))

        return {
            "session_id":    session_id,
            "start":         start_hash,
            "direction":     direction,
            "nodes_visited": len(visited),
            "path":          [graph[h] for h in visited if h in graph],
        }

    def get_graph(self, session_id: str) -> Dict:
        session = self._get_session(session_id)
        return {
            "session_id": session_id,
            "name":       session["name"],
            "stats":      _graph_stats(session["graph"]),
            "roots":      session["root_hashes"],
            "nodes":      list(session["graph"].values()),
        }

    def delete_session(self, session_id: str) -> Dict:
        session = self._sessions.pop(session_id, None)
        if not session:
            raise KeyError(f"Session {session_id} not found")
        return {
            "session_id":  session_id,
            "destroyed":   True,
            "nodes_freed": len(session["graph"]),
        }

    # ── Internals ──────────────────────────────────────────────────────────────

    def _get_session(self, session_id: str) -> Dict:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session {session_id} not found or expired")
        session["last_access"] = time.time()
        return session

    def _cleanup_expired(self) -> int:
        now = time.time()
        with self._lock:
            expired = [
                sid for sid, s in self._sessions.items()
                if now - s["last_access"] > self.session_ttl
            ]
            for sid in expired:
                del self._sessions[sid]
        return len(expired)

    def _start_cleanup(self) -> None:
        def loop():
            while True:
                time.sleep(CLEANUP_INTERVAL)
                self._cleanup_expired()
        t = threading.Thread(target=loop, daemon=True)
        t.start()

    @property
    def session_count(self) -> int:
        return len(self._sessions)


# ─── Module-level singleton + forwarding ──────────────────────────────────────

engine = MDHGEngine()

def mdhg_hash(content: str, parent_hash: Optional[str] = None,
              level: int = 0) -> str:
    return engine.hash(content, parent_hash, level)

def create_session(name: Optional[str] = None, max_depth: int = 9) -> Dict:
    return engine.create_session(name, max_depth)

def add_node(session_id: str, content: str, parent_hash: Optional[str] = None,
             level: int = 0, metadata: Optional[Dict] = None) -> Dict:
    return engine.add_node(session_id, content, parent_hash, level, metadata)

def traverse(session_id: str, start_hash: str,
             direction: str = "down", max_steps: int = 10) -> Dict:
    return engine.traverse(session_id, start_hash, direction, max_steps)
