"""Extraction helpers for CQE/CMPLX formalization target sheets."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class FormalizationTarget:
    """A source document selected for CQE/CMPLX transport review."""

    family: str
    label: str
    path: Path
    priority: int


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return slug or "target"


def read_target_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except Exception as exc:  # pragma: no cover - depends on optional env
            raise RuntimeError("pypdf is required to extract PDF targets") from exc

        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n\n".join(pages).strip()

    return path.read_text(encoding="utf-8", errors="ignore")


def extract_targets(
    targets: Iterable[FormalizationTarget],
    output_dir: Path,
) -> dict[str, Any]:
    """Extract targets into a normalized text corpus and write manifest JSON."""

    output_dir.mkdir(parents=True, exist_ok=True)
    texts_dir = output_dir / "texts"
    texts_dir.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    counts = {"extracted": 0, "missing": 0, "failed": 0}

    for target in sorted(targets, key=lambda item: (-item.priority, item.family, item.label)):
        source = Path(target.path)
        base_entry: dict[str, Any] = {
            "family": target.family,
            "label": target.label,
            "priority": target.priority,
            "source_path": str(source),
            "status": "",
            "extracted_path": "",
            "error": "",
        }

        if not source.exists():
            base_entry["status"] = "missing"
            counts["missing"] += 1
            entries.append(base_entry)
            continue

        try:
            text = read_target_text(source)
            slug = slugify(f"{target.priority:03d}-{target.family}-{target.label}")
            extracted_path = texts_dir / f"{slug}.md"
            extracted_path.write_text(
                "\n".join(
                    [
                        f"# {target.label}",
                        "",
                        f"Family: {target.family}",
                        f"Priority: {target.priority}",
                        f"Source: {source}",
                        "",
                        "---",
                        "",
                        text,
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            base_entry["status"] = "extracted"
            base_entry["extracted_path"] = str(extracted_path)
            counts["extracted"] += 1
        except Exception as exc:
            base_entry["status"] = "failed"
            base_entry["error"] = str(exc)
            counts["failed"] += 1

        entries.append(base_entry)

    manifest: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "total": len(entries),
            **counts,
        },
        "targets": entries,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest
