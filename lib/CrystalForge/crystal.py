"""CrystalForge.crystal — Crystal + MDHG + CPL, ported from the real
TMN service (tmn_source/CMPLX-TMN-main-main/src/crystal/crystal.py).

A Crystal holds the outcome of any state you choose to save, at
whatever boundary you choose -- one computation, one session, one
kernel result, anything. It is not tied to the Kp claims/StudyIncubator
system; it can cite a Kp claim's receipt as one of its nodes, or hold
something that has nothing to do with Kp at all.

The MDHG addressing (assign_address), Golay encoding, Leech projection,
and Julia dynamics below are taken essentially verbatim from the real
service -- they are pure math with no FastAPI/Postgres dependency, so
porting them is a direct copy, not a rewrite. Only the persistence
layer (_save_crystal/_save_node/_init_tables, originally psycopg2)
is replaced with sqlite3 against schema.get_connection().
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

from .schema import get_connection
from .stable_ids import crystal_id_for_name, node_id_for

PHI = (1 + math.sqrt(5)) / 2
COUPLING = math.log(PHI) / 16  # kappa, same constant used throughout this corpus


# ═══════════════════════════════════════════════════════════════════════
# MDHG Hash Fabric — per-level hash algorithms
# ═══════════════════════════════════════════════════════════════════════

class HashAlgo(str, Enum):
    SHA3_512 = "sha3_512"
    SHA3_256 = "sha3_256"
    BLAKE2B = "blake2b"
    SHA256 = "sha256"


@dataclass
class LevelConfig:
    name: str
    algorithm: HashAlgo
    output_bytes: int
    description: str = ""


DEFAULT_FABRIC = [
    LevelConfig("universe", HashAlgo.SHA3_512, 64, "Global attractor"),
    LevelConfig("galaxies", HashAlgo.BLAKE2B, 32, "Domain cluster"),
    LevelConfig("systems", HashAlgo.SHA3_256, 32, "Functional group"),
    LevelConfig("planets", HashAlgo.SHA3_256, 32, "Module observer"),
    LevelConfig("cities", HashAlgo.BLAKE2B, 32, "Route observer / AGRM"),
    LevelConfig("locals", HashAlgo.SHA256, 32, "District hash"),
    LevelConfig("neighborhoods", HashAlgo.SHA256, 32, "Semantic cluster"),
    LevelConfig("buildings", HashAlgo.SHA256, 16, "Structure hash"),
    LevelConfig("rooms", HashAlgo.SHA256, 16, "Interior space"),
    LevelConfig("atoms", HashAlgo.SHA256, 8, "Semantic atom"),
]

ATOM_LEVELS = [
    LevelConfig("planet", HashAlgo.SHA3_256, 32, "Digital root family"),
    LevelConfig("city", HashAlgo.BLAKE2B, 32, "Content type"),
    LevelConfig("building", HashAlgo.SHA256, 16, "E8 quadrant"),
    LevelConfig("floor", HashAlgo.SHA256, 16, "Content hash slice"),
    LevelConfig("room", HashAlgo.SHA256, 16, "Label hash"),
    LevelConfig("atom", HashAlgo.SHA256, 8, "Content identity"),
]

PLANET_NAMES = ["alpha", "beta", "gamma", "delta", "epsilon",
                "zeta", "eta", "theta", "kappa"]

CITY_MAP = {
    "atom": "code", "code": "forge", "doc": "library", "data": "vault",
    "config": "tower", "mixed": "nexus", "tool": "tool", "agent": "agent",
    "document": "doc", "compose": "compose", "image": "image",
    "contract": "contract", "schema": "schema", "test": "test",
    "system": "system", "module": "module",
}

MEANING_LEVELS = ["surface", "semantic", "latent", "archetypal", "transcendent"]


def _hash(data: bytes, algo: HashAlgo, size: int) -> str:
    if algo == HashAlgo.SHA3_512:
        h = hashlib.sha3_512(data).digest()
    elif algo == HashAlgo.SHA3_256:
        h = hashlib.sha3_256(data).digest()
    elif algo == HashAlgo.BLAKE2B:
        h = hashlib.blake2b(data, digest_size=min(size, 64)).digest()
    else:
        h = hashlib.sha256(data).digest()
    return h[:size].hex()


def digital_root(values: List[float]) -> int:
    total = int(sum(abs(v) * 1000 for v in values))
    while total >= 10:
        total = sum(int(d) for d in str(total))
    return total if total > 0 else 9


def assign_address(content: str = "", e8_coords: Optional[List[float]] = None,
                    entry_type: str = "atom", labels: Optional[List[str]] = None,
                    content_hash: str = "", levels: Optional[List[LevelConfig]] = None) -> Dict:
    """Deterministic MDHG address from content + geometry."""
    e8 = list(e8_coords or [0.0] * 8)[:8]
    while len(e8) < 8:
        e8.append(0.0)
    ch = content_hash or hashlib.sha256(content.encode()).hexdigest()[:16]
    lvls = levels or ATOM_LEVELS

    address: Dict[str, Any] = {}
    for i, lv in enumerate(lvls):
        nm = lv.name.lower()
        if nm in ("planet", "universe"):
            dr = digital_root(e8)
            address[lv.name] = PLANET_NAMES[dr - 1] if 1 <= dr <= 9 else "alpha"
        elif nm in ("city", "galaxies"):
            address[lv.name] = CITY_MAP.get(entry_type, "nexus")
        elif nm in ("building", "systems"):
            address[lv.name] = "".join("+" if c >= 0 else "-" for c in e8[:4])
        elif nm in ("floor", "locals", "neighborhoods"):
            seg = ch[i * 2:(i * 2) + 4] if len(ch) > i * 2 + 3 else ch[:4]
            address[lv.name] = f"F{int(seg, 16) % 64:02d}"
        elif nm in ("room", "cities"):
            lbl = "|".join(sorted(labels or []))
            address[lv.name] = f"R{int(hashlib.sha256(lbl.encode()).hexdigest()[:4], 16) % 128:03d}"
        elif nm in ("atom", "atoms"):
            address[lv.name] = ch[:8]
        else:
            address[lv.name] = _hash(f"{lv.name}:{ch}".encode(), lv.algorithm, lv.output_bytes)[:8]

    address["full"] = ".".join(address[l.name] for l in lvls)
    address["digital_root"] = digital_root(e8)
    return address


# ═══════════════════════════════════════════════════════════════════════
# CPL — Crystal Projection (Golay, Julia, Leech projection)
# ═══════════════════════════════════════════════════════════════════════

GOLAY_GENERATOR = [
    0b110111000101, 0b101110001011, 0b011100010111,
    0b111000101101, 0b110001011011, 0b100010110111,
]


def golay_encode(data_12: int) -> int:
    """Golay [24,12,8] encode: 12 data bits -> 24 coded bits."""
    parity = 0
    for i, row in enumerate(GOLAY_GENERATOR):
        if data_12 & (1 << i):
            parity ^= row
    return (data_12 << 12) | parity


def project_to_leech(e8_coords: List[float]) -> List[float]:
    """Project 8D E8 coordinates to 24D Leech lattice (E8x3 with phase)."""
    leech = []
    for phase in range(3):
        shift = phase * 2.0944  # 2*pi/3
        for i, c in enumerate(e8_coords[:8]):
            leech.append(c * math.cos(shift + i * 0.7854))
    return leech


def julia_iterate(c_real: float, c_imag: float, max_iter: int = 50) -> Dict:
    """Compute Julia set dynamics from crystal seed coordinates."""
    z_r, z_i = 0.0, 0.0
    for n in range(max_iter):
        z_r2, z_i2 = z_r * z_r, z_i * z_i
        if z_r2 + z_i2 > 4.0:
            return {"escaped": True, "iterations": n, "z_norm": math.sqrt(z_r2 + z_i2)}
        z_i = 2 * z_r * z_i + c_imag
        z_r = z_r2 - z_i2 + c_real
    return {"escaped": False, "iterations": max_iter, "z_norm": math.sqrt(z_r * z_r + z_i * z_i)}


# ═══════════════════════════════════════════════════════════════════════
# Crystal / E8Node — the state-snapshot containers
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Crystal:
    crystal_id: str = ""
    name: str = ""
    crystal_type: str = "knowledge"
    state: str = "growing"
    e8_root: List[float] = field(default_factory=lambda: [0.0] * 8)
    meaning_levels: List[str] = field(default_factory=lambda: MEANING_LEVELS[:3])
    level_config: List[Dict] = field(default_factory=list)
    owner: str = ""
    snap_address: str = ""
    receipt_chain: str = ""
    created_at: float = 0.0
    committed_at: Optional[float] = None
    activated_at: Optional[float] = None
    node_count: int = 0
    total_mass: float = 0.0

    def __post_init__(self):
        if not self.crystal_id:
            if self.name:
                self.crystal_id = crystal_id_for_name(self.name)
            else:
                raise ValueError("crystal_id or name required for stable crystal identity")
        if not self.receipt_chain:
            self.receipt_chain = hashlib.sha256(f"crystal:{self.crystal_id}".encode()).hexdigest()[:32]
        if not self.created_at:
            self.created_at = time.time()
        if not self.snap_address:
            self.snap_address = f"crystal://{self.name or self.crystal_id}"


@dataclass
class E8Node:
    node_id: str = ""
    crystal_id: str = ""
    content: str = ""
    content_type: str = "atom"
    e8_coords: List[float] = field(default_factory=lambda: [0.0] * 8)
    snap_labels: List[str] = field(default_factory=list)
    mdhg_address: Dict = field(default_factory=dict)
    importance: float = 0.5
    meaning_level: int = 0
    mass: float = 0.0
    created_at: float = 0.0

    def __post_init__(self):
        if not self.node_id:
            if self.crystal_id and self.content:
                self.node_id = node_id_for(self.crystal_id, self.content, self.snap_labels)
            else:
                raise ValueError("node_id required, or crystal_id+content for stable derivation")
        if not self.mass:
            self.mass = len(self.snap_labels) * COUPLING
        if not self.created_at:
            self.created_at = time.time()


# ═══════════════════════════════════════════════════════════════════════
# Persistence (sqlite3, replacing the original psycopg2 layer)
# ═══════════════════════════════════════════════════════════════════════

def _row_to_crystal(row) -> Crystal:
    return Crystal(
        crystal_id=row["crystal_id"], name=row["name"], crystal_type=row["crystal_type"],
        state=row["state"], e8_root=json.loads(row["e8_root"]),
        meaning_levels=json.loads(row["meaning_levels"]), level_config=json.loads(row["level_config"]),
        owner=row["owner"], snap_address=row["snap_address"], receipt_chain=row["receipt_chain"],
        created_at=row["created_at"], committed_at=row["committed_at"], activated_at=row["activated_at"],
        node_count=row["node_count"], total_mass=row["total_mass"],
    )


def _save_crystal(c: Crystal, db_path=None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """INSERT INTO crystals (crystal_id, name, crystal_type, state, e8_root,
                meaning_levels, level_config, owner, snap_address, receipt_chain,
                node_count, total_mass, created_at, committed_at, activated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(crystal_id) DO UPDATE SET
                state=excluded.state, node_count=excluded.node_count,
                total_mass=excluded.total_mass, receipt_chain=excluded.receipt_chain,
                committed_at=excluded.committed_at, activated_at=excluded.activated_at""",
            (c.crystal_id, c.name, c.crystal_type, c.state, json.dumps(c.e8_root),
             json.dumps(c.meaning_levels), json.dumps(c.level_config), c.owner,
             c.snap_address, c.receipt_chain, c.node_count, c.total_mass,
             c.created_at, c.committed_at, c.activated_at),
        )
        conn.commit()
    finally:
        conn.close()


def _save_node(n: E8Node, db_path=None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """INSERT INTO e8_nodes (node_id, crystal_id, content, content_type,
                e8_coords, snap_labels, mdhg_address, importance, meaning_level, mass, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(node_id) DO NOTHING""",
            (n.node_id, n.crystal_id, n.content[:2000], n.content_type,
             json.dumps(n.e8_coords), json.dumps(n.snap_labels), json.dumps(n.mdhg_address),
             n.importance, n.meaning_level, n.mass, n.created_at),
        )
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
# Crystal Manager — public API
# ═══════════════════════════════════════════════════════════════════════

def create_crystal(name: str, crystal_type: str = "knowledge",
                    e8_seed: Optional[List[float]] = None, meaning_depth: int = 3,
                    level_count: int = 6, owner: str = "", db_path=None) -> Crystal:
    if not e8_seed:
        sb = hashlib.sha256(name.encode()).digest()[:8]
        e8_seed = [(b / 127.5 - 1.0) for b in sb]
        n = math.sqrt(sum(c * c for c in e8_seed)) or 1.0
        e8_seed = [c / n * PHI for c in e8_seed]
    levels = DEFAULT_FABRIC[:level_count] if level_count <= 10 else DEFAULT_FABRIC
    cid = crystal_id_for_name(name)
    crystal = Crystal(
        crystal_id=cid, name=name, crystal_type=crystal_type, e8_root=e8_seed,
        meaning_levels=MEANING_LEVELS[:meaning_depth],
        level_config=[asdict(l) for l in levels], owner=owner,
    )
    _save_crystal(crystal, db_path)
    return crystal


def add_node(crystal_id: str, content: str, content_type: str = "atom",
             e8_coords: Optional[List[float]] = None, labels: Optional[List[str]] = None,
             db_path=None) -> E8Node:
    crystal = get_crystal(crystal_id, db_path)
    if not crystal:
        raise ValueError(f"Crystal {crystal_id} not found")
    levels = [LevelConfig(**l) for l in crystal.level_config] if crystal.level_config else ATOM_LEVELS
    mdhg = assign_address(content=content, e8_coords=e8_coords or crystal.e8_root,
                           entry_type=content_type, labels=labels, levels=levels)
    lab = labels or []
    nid = node_id_for(crystal_id, content, lab)
    node = E8Node(
        node_id=nid, crystal_id=crystal_id, content=content, content_type=content_type,
        e8_coords=e8_coords or crystal.e8_root, snap_labels=lab,
        mdhg_address=mdhg, mass=len(lab) * COUPLING,
    )
    crystal.node_count += 1
    crystal.total_mass += node.mass
    crystal.receipt_chain = hashlib.sha256(
        f"{crystal.receipt_chain}:node:{node.node_id}".encode()).hexdigest()[:32]
    _save_node(node, db_path)
    _save_crystal(crystal, db_path)
    return node


def commit_crystal(crystal_id: str, db_path=None) -> Crystal:
    """growing -> committed. The first half of the lifecycle: this
    state's content is now fixed, but it has not yet been promoted to
    the active/live set anything else can pull from."""
    crystal = get_crystal(crystal_id, db_path)
    if not crystal:
        raise ValueError(f"Crystal {crystal_id} not found")
    crystal.state = "committed"
    crystal.committed_at = time.time()
    _save_crystal(crystal, db_path)
    return crystal


def activate_crystal(crystal_id: str, db_path=None) -> Crystal:
    """committed -> active. Now part of the live set that bridges to
    other systems (e.g. an agent brain's contribution pulling this
    crystal's nodes back into its working memory)."""
    crystal = get_crystal(crystal_id, db_path)
    if not crystal:
        raise ValueError(f"Crystal {crystal_id} not found")
    crystal.state = "active"
    crystal.activated_at = time.time()
    _save_crystal(crystal, db_path)
    return crystal


def get_crystal(crystal_id: str, db_path=None) -> Optional[Crystal]:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM crystals WHERE crystal_id = ?", (crystal_id,)).fetchone()
        return _row_to_crystal(row) if row else None
    finally:
        conn.close()


def list_crystals(state: str = "", db_path=None) -> List[Crystal]:
    conn = get_connection(db_path)
    try:
        if state:
            rows = conn.execute("SELECT * FROM crystals WHERE state = ?", (state,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM crystals").fetchall()
        return [_row_to_crystal(r) for r in rows]
    finally:
        conn.close()


def get_nodes(crystal_id: str, db_path=None) -> List[E8Node]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT * FROM e8_nodes WHERE crystal_id = ?", (crystal_id,)).fetchall()
        return [
            E8Node(
                node_id=r["node_id"], crystal_id=r["crystal_id"], content=r["content"],
                content_type=r["content_type"], e8_coords=json.loads(r["e8_coords"]),
                snap_labels=json.loads(r["snap_labels"]), mdhg_address=json.loads(r["mdhg_address"]),
                importance=r["importance"], meaning_level=r["meaning_level"], mass=r["mass"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
    finally:
        conn.close()
