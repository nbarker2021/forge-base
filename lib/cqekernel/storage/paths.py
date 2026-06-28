"""
Workspace path resolution and the ``.cqe/`` directory layout.

All paths are relative to a workspace anchor. The anchor can be:

  1. explicit ``paths.anchor(override=...)`` argument
  2. ``CQE_ANCHOR`` environment variable
  3. parent of the ``cqekernel/`` package (its enclosing folder)

The kernel never hardcodes ``D:/...`` style paths.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def anchor(override: Optional[str] = None) -> Path:
    """Resolve the workspace anchor directory.

    Returns the directory that contains the ``.cqe/`` workspace folder.
    """
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get("CQE_ANCHOR")
    if env:
        return Path(env).expanduser().resolve()
    # parent of the package directory (this file is in cqekernel/storage/paths.py)
    return Path(__file__).resolve().parents[2]


def workspace(override: Optional[str] = None) -> Path:
    """Return the ``.cqe/`` workspace directory, creating it if missing."""
    root = anchor(override) / ".cqe"
    root.mkdir(parents=True, exist_ok=True)
    return root


def subdir(name: str, override: Optional[str] = None) -> Path:
    """Return a named subdirectory of the workspace, creating it if missing."""
    d = workspace(override) / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure_snapshots(override: Optional[str] = None) -> Path:
    """Return the ``snapshots/`` subdirectory of the workspace, creating it if missing."""
    d = workspace(override) / "snapshots"
    d.mkdir(parents=True, exist_ok=True)
    return d
