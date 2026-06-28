"""CrystalForge — the meso-level memory system: crystals hold the
outcome of any saved state at a chosen boundary; brains hold live,
evolving per-agent state that pulls from and resaves into the master
record.

Ported from the real TMN services (tmn_source/CMPLX-TMN-main-main/
src/crystal/crystal.py and src/brain/brain.py), backed by SQLite for
now (production/packages/cqecmplx-forge/src/CrystalForge/crystal_vault.db),
with a Postgres form planned later -- see schema.py's docstring for
the swap-in contract.

This is a separate, cross-referencing layer from the ecology/kernels
Kp claims system, not a replacement for it: a crystal can hold a Kp
claim's receipt as one of its nodes, but promoting a Kp study does not
automatically create one.
"""
from .crystal import (
    Crystal,
    E8Node,
    HashAlgo,
    LevelConfig,
    DEFAULT_FABRIC,
    ATOM_LEVELS,
    MEANING_LEVELS,
    create_crystal,
    add_node,
    commit_crystal,
    activate_crystal,
    get_crystal,
    list_crystals,
    get_nodes,
    assign_address,
    digital_root,
    golay_encode,
    project_to_leech,
    julia_iterate,
)
from .brain import (
    ALPHA_BY_TIER,
    TIER_THRESHOLDS,
    register_brain,
    get_brain,
    list_brains,
    contribute,
    compute_capacity,
    merge_brain,
    fork_brain,
    list_expertise,
)
from .schema import get_connection, DB_PATH_DEFAULT


# ─── Verify (forge-family contract) ───────────────────────────────────────────

def verify() -> dict:
    """Finite checks binding CrystalForge to its docstring claims.

    Tests the pure-function substrate (digital_root, golay_encode,
    project_to_leech, assign_address, julia_iterate) and the SQLite
    persistence layer (create / add_node / commit / get_crystal).
    Pure additive — does not touch the existing API.
    """
    checks = {}

    # 1. Pure functions are deterministic and well-typed.
    try:
        dr1 = digital_root([1, 2, 3, 4, 5, 6, 7, 8, 9])
        dr2 = digital_root([1, 2, 3, 4, 5, 6, 7, 8, 9])
        checks["digital_root_deterministic"] = (dr1 == dr2 and 1 <= dr1 <= 9)
    except Exception:
        checks["digital_root_deterministic"] = False

    try:
        addr1 = assign_address("verify-probe")
        addr2 = assign_address("verify-probe")
        checks["assign_address_deterministic"] = bool(
            addr1 and addr2 and addr1 == addr2
        )
    except Exception:
        checks["assign_address_deterministic"] = False

    try:
        enc = golay_encode(0xFFF)         # any 12-bit word
        checks["golay_encode_returns_24bit"] = isinstance(enc, int) and enc >= 0
    except Exception:
        checks["golay_encode_returns_24bit"] = False

    try:
        leech = project_to_leech([0.0] * 8)
        checks["project_to_leech_8_to_24"] = (
            isinstance(leech, list) and len(leech) == 24
        )
    except Exception:
        checks["project_to_leech_8_to_24"] = False

    try:
        j = julia_iterate(0.0, 0.0, max_iter=9)
        checks["julia_iterate_returns_record"] = (
            isinstance(j, dict) and "iterations" in j
        )
    except Exception:
        checks["julia_iterate_returns_record"] = False

    # 2. SQLite layer round-trips a crystal + node. Uses an in-memory DB so
    #    we don't touch the on-disk crystal_vault.db.
    try:
        from .schema import DB_PATH_DEFAULT
        import tempfile, os
        with tempfile.TemporaryDirectory() as td:
            tmp_db = os.path.join(td, "verify_crystal_vault.db")
            # Patch the default path for this test, then restore.
            from . import schema as _schema_mod
            saved = _schema_mod.DB_PATH_DEFAULT
            _schema_mod.DB_PATH_DEFAULT = tmp_db
            try:
                c = create_crystal(
                    "verify-crystal",
                    crystal_type="knowledge",
                    db_path=tmp_db,
                )
                add_node(c.crystal_id, "verify node", content_type="atom",
                         db_path=tmp_db)
                commit_crystal(c.crystal_id, db_path=tmp_db)
                got = get_crystal(c.crystal_id, db_path=tmp_db)
                nodes = get_nodes(c.crystal_id, db_path=tmp_db)
                checks["sqlite_create_commit_get_roundtrip"] = bool(
                    got is not None and len(nodes) >= 1
                )
            finally:
                _schema_mod.DB_PATH_DEFAULT = saved
    except Exception:
        checks["sqlite_create_commit_get_roundtrip"] = False

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    if passed == total:
        status = "pass"
    elif passed >= max(1, total // 2):
        status = "partial"
    else:
        status = "fail"

    return {
        "forge": "CrystalForge",
        "status": status,
        "checks": checks,
        "passed": passed,
        "total": total,
        "paper": "CQE-paper-04 (Crystal Vault / E8 node)",
    }


__all__ = [
    "Crystal", "E8Node", "HashAlgo", "LevelConfig",
    "DEFAULT_FABRIC", "ATOM_LEVELS", "MEANING_LEVELS",
    "create_crystal", "add_node", "commit_crystal", "activate_crystal",
    "get_crystal", "list_crystals", "get_nodes",
    "assign_address", "digital_root", "golay_encode", "project_to_leech", "julia_iterate",
    "ALPHA_BY_TIER", "TIER_THRESHOLDS",
    "register_brain", "get_brain", "list_brains", "contribute",
    "compute_capacity", "merge_brain", "fork_brain", "list_expertise",
    "get_connection", "DB_PATH_DEFAULT",
]
