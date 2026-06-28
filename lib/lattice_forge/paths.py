"""Default paths for project-local Lattice Forge state."""
from __future__ import annotations

import os
from pathlib import Path


def project_lattice_forge_dir(root: Path | None = None) -> Path:
    """Directory for overlay and backwalk artifacts (default: ``./.lattice_forge``)."""
    if env := os.environ.get("LATTICE_FORGE_STATE_DIR"):
        return Path(env)
    base = root if root is not None else Path.cwd()
    return base / ".lattice_forge"


def backwalk_data_dir(root: Path | None = None) -> Path:
    """Writable backwalk reports and work DB (default: ``.lattice_forge/backwalk``)."""
    if env := os.environ.get("LATTICE_FORGE_BACKWALK_DIR"):
        return Path(env)
    return project_lattice_forge_dir(root) / "backwalk"


def backwalk_work_db(root: Path | None = None) -> Path:
    """Writable Niemeier backwalk SQLite (env ``LATTICE_FORGE_WORK_DB`` overrides)."""
    if env := os.environ.get("LATTICE_FORGE_WORK_DB"):
        return Path(env)
    return backwalk_data_dir(root) / "backwalk_work.db"


def resolve_work_db(path: Path | None, *, root: Path | None = None) -> Path:
    if path is not None:
        return path.expanduser().resolve()
    return backwalk_work_db(root).resolve()
