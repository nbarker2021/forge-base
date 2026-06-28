"""cqecmplx — the unified Forge namespace.

One import root for the whole ring:

    import cqecmplx
    cqecmplx.lattice            # merged lattice_forge substrate (PROOF + PartsFactory union)
    cqecmplx.engines.chroma     # ChromaForge (Event Law machinery)
    cqecmplx.engines.graphstax  # GraphStax  (graph identity / PermForge)
    cqecmplx.engines.pixel      # PixelForge (surfaces / ink / frames)
    cqecmplx.engines.fridge     # FridgeForge
    cqecmplx.engines.link       # LinkForge  (databases as lib items)
    cqecmplx.engines.mandle / .mani
    cqecmplx.reforge.contracts / .hardening / .glyph / .frame / .wire
    cqecmplx.reforge.pixl8 / .pixle / .researchcraft / .kimi
    cqecmplx.factory            # forgefactory
    cqecmplx.rhenium            # rhenium_engine

The historical top-level names (lattice_forge, ChromaForge, reforge_*, ...)
remain installed and importable unchanged — the compatibility ring. The whole
ring is stdlib-only; registration is eager so dotted imports
(`from cqecmplx.lattice.binary_boundary_adapter import adapt`) resolve.
"""
import importlib
import sys

__version__ = "0.9.0"

_RING = {
    "lattice": "lattice_forge",
    "factory": "forgefactory",
    "rhenium": "rhenium_engine",
}
_ENGINES = {
    "chroma": "ChromaForge", "graphstax": "GraphStax", "pixel": "PixelForge",
    "fridge": "FridgeForge", "link": "LinkForge",
    "mandle": "MandleForge", "mani": "ManiForge",
    "scene": "SceneForge",
}
_REFORGE = {
    "contracts": "reforge_engine_contracts", "hardening": "reforge_engine_hardening",
    "glyph": "reforge_glyphforge", "frame": "reforge_frameforge",
    "wire": "reforge_wireforge", "pixl8": "reforge_pixl8forge",
    "pixle": "reforge_pixleforge", "researchcraft": "reforge_researchcraft",
    "kimi": "reforge_kimi_adapter",
}

def _mount(prefix: str, aliases: dict, container) -> None:
    for new, old in aliases.items():
        mod = importlib.import_module(old)
        sys.modules[f"{prefix}.{new}"] = mod
        setattr(container, new, mod)

_this = sys.modules[__name__]
_mount(__name__, _RING, _this)

from cqecmplx import engines as _engines_pkg   # the subpackage shells
from cqecmplx import reforge as _reforge_pkg
_mount(f"{__name__}.engines", _ENGINES, _engines_pkg)
_mount(f"{__name__}.reforge", _REFORGE, _reforge_pkg)


def ring() -> dict:
    """The full ring: unified name -> installed package name."""
    out = {f"cqecmplx.{k}": v for k, v in _RING.items()}
    out.update({f"cqecmplx.engines.{k}": v for k, v in _ENGINES.items()})
    out.update({f"cqecmplx.reforge.{k}": v for k, v in _REFORGE.items()})
    return out
