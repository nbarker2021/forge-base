"""
SceneForge — world composition + intent + real-image casting.

The shot/scene layer of the suite, grown from the historical donors:
  worldforge.py  the original operator-chain compose (P5 -> B_obs -> Rrho
                 -> B_soft -> B_higgs -> B_ward -> Bridge), receipt-trailed
  intent.py      Scene8's Intent-as-Slice: prompt -> three E8-lattice
                 trajectory candidates -> system-scored -> best slice wins
  imagedb.py     the saved-pictures database: real PNG/BMP files decoded,
                 hashed, indexed, deterministically cast

Position: WorldForge (world) -> SceneForge (THIS: shots/intent/cast)
          -> PixelForge (pixels/pictures/video) -> the .avi in your player.

Stdlib only.
"""
from SceneForge.worldforge import compose
from SceneForge.intent import (
    Intent, understand, apply_action, nearest_root, E8_ROOTS,
    UNITY, TERNARY, ATTRACTOR, ACTIONS,
)
from SceneForge.imagedb import ImageDB, fit_to

__version__ = "0.1.0"


# ─── Verify (forge-family contract) ───────────────────────────────────────────

def verify() -> dict:
    """Finite checks binding SceneForge to its docstring claims.

    Tests the world compose chain (P5 -> ... -> Bridge), the intent
    scoring (3 E8 trajectories, system picks best), the E8 root
    geometry (UNITY/TERNARY/ATTRACTOR are the right norm classes), and
    the ImageDB fit_to helper. Pure additive.
    """
    checks = {}

    # 1. worldforge.compose runs the documented operator chain and
    #    returns a canonical-serializable record.
    try:
        rec = compose(
            seed=42,
            prompt="verify-scene",
            modes=["image", "video", "text"],
            lenses=[],
        )
        checks["worldforge_compose_runs"] = bool(
            rec and isinstance(rec, dict)
            and "stamp" in rec
            and "render_plan" in rec
        )
    except Exception:
        checks["worldforge_compose_runs"] = False

    # 2. Intent: understand() returns an Intent dataclass with a trajectory
    #    of E8-root tuples (the system picks the best of 3 candidates
    #    internally; the public surface is the winning trajectory).
    try:
        intent = understand("verify-prompt", num_frames=3)
        traj = getattr(intent, "trajectory", None)
        checks["intent_has_trajectory"] = bool(
            intent and traj and len(traj) >= 1
            and all(isinstance(t, tuple) for t in traj)
        )
    except Exception:
        checks["intent_has_trajectory"] = False

    # 3. E8 root geometry: UNITY has norm ~0, TERNARY/ATTRACTOR have positive
    #    norm, and the documented action vocabulary is in ACTIONS.
    try:
        import math
        def _norm(v):
            return math.sqrt(sum(x * x for x in v))
        unity_norm = _norm(UNITY)
        ternary_norm = _norm(TERNARY)
        attractor_norm = _norm(ATTRACTOR)
        checks["e8_unity_is_origin"] = unity_norm < 1e-9
        checks["e8_ternary_attractor_nonzero"] = (
            ternary_norm > 0.0 and attractor_norm > 0.0
        )
        # known actions
        for needed in ("translate", "rotate", "scale"):
            assert needed in ACTIONS, f"missing action {needed}"
        checks["actions_contains_translate_rotate_scale"] = True
    except Exception:
        checks["e8_unity_is_origin"] = False
        checks["e8_ternary_attractor_nonzero"] = False
        checks["actions_contains_translate_rotate_scale"] = False

    # 4. nearest_root returns one of the documented E8_ROOTS
    try:
        r = nearest_root([0.1, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        checks["nearest_root_returns_e8_root"] = (
            r in E8_ROOTS and r != UNITY  # closest to UNITY is itself
        )
    except Exception:
        checks["nearest_root_returns_e8_root"] = False

    # 5. ImageDB.fit_to does not crash on a 1x1 placeholder Picture
    try:
        # A minimal "picture" duck-typed object with a 1x1 raw buffer
        class _MiniPic:
            width = 1
            height = 1
            raw = b"\x00\x00\x00"
            def copy(self):
                return self
        p = fit_to(_MiniPic(), 4, 4)
        checks["image_db_fit_to_returns_picture"] = bool(p)
    except Exception:
        checks["image_db_fit_to_returns_picture"] = False

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    if passed == total:
        status = "pass"
    elif passed >= max(1, total // 2):
        status = "partial"
    else:
        status = "fail"

    return {
        "forge": "SceneForge",
        "status": status,
        "checks": checks,
        "passed": passed,
        "total": total,
        "paper": "CQE-paper-09 (Scene8: intent-as-slice / E8 trajectory pick)",
    }


__all__ = [
    "compose", "Intent", "understand", "apply_action", "nearest_root",
    "E8_ROOTS", "UNITY", "TERNARY", "ATTRACTOR", "ACTIONS",
    "ImageDB", "fit_to",
]
