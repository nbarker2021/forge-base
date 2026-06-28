"""
Filesystem adapter: a directory path in -> canonical manifest frame out.

The manifest lists each file under the directory with a SHA256, a
byte count, and a stable relative path. Symlinks are not followed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Union

from ..carrier.binary_boundary import BinaryBoundaryFrame, make_frame


ADAPTER_NAME = "FilesystemAdapter"
ADAPTER_VERSION = "0.1"


def _hash_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def adapt(path: Union[str, Path]) -> BinaryBoundaryFrame:
    """Adapt a directory (or single file) to a manifest frame."""
    p = Path(path)
    files: List[Dict[str, Any]] = []
    if p.is_file():
        files.append({
            "relpath": p.name,
            "bytes": p.stat().st_size,
            "sha256": _hash_file(p),
        })
    elif p.is_dir():
        for child in sorted(p.rglob("*")):
            if child.is_file():
                files.append({
                    "relpath": str(child.relative_to(p)).replace("\\", "/"),
                    "bytes": child.stat().st_size,
                    "sha256": _hash_file(child),
                })
    else:
        raise FileNotFoundError(str(p))
    payload = json.dumps({"root": str(p), "files": files},
                         sort_keys=True, separators=(",", ":")).encode("utf-8")
    return make_frame(
        payload=payload,
        source_type="directory_manifest",
        adapter=ADAPTER_NAME,
        encoding="utf-8",
        adapter_version=ADAPTER_VERSION,
        extras={"file_count": len(files)},
    )
