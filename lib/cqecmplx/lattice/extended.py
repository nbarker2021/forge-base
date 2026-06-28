"""cqecmplx.lattice.extended — E8/Leech lattice, MCP, Aletheia, Morphonic, Merit, Snap extraction (stub).

Source: D:/CQE_CMPLX/g/CMPLX/
This is a stub — extraction targets from the cmplx_monorepo.
Install editable: pip install -e D:/CQE_CMPLX/g/CMPLX
"""

__version__ = "1.0.0"
__source__ = "D:/CQE_CMPLX/g/CMPLX/"

EXTRACTION_TARGETS = [
    "E8 lattice operations",
    "Leech lattice operations",
    "MCP server/client",
    "Aletheia (v1, v2, MVP)",
    "Morphonic CQE Unified",
    "Merit blockchain",
    "Snap cluster computing",
]

def install_editable():
    """Install the full monorepo in editable mode."""
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", __source__])

__all__ = ["EXTRACTION_TARGETS", "install_editable"]