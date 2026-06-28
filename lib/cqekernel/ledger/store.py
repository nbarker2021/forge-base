"""
JSONL append-only event store.

The store is a single line of JSON per event. The store supports:

  * append(event)         — append one event
  * read_all()            — return all events
  * read_since(event_id)  — return events after a given id
  * hash_chain()          — sha256 chain over the event payloads
  * size()                — number of events
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterator, List

from .event import Event


def _stable_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class EventStore:
    """Append-only JSONL event store."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def append(self, event: Event) -> None:
        line = json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def read_all(self) -> List[Event]:
        return list(self._iter())

    def _iter(self) -> Iterator[Event]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                yield Event.from_dict(json.loads(raw))

    def read_since(self, event_id: str) -> List[Event]:
        out: List[Event] = []
        seen = False
        for ev in self._iter():
            if seen:
                out.append(ev)
            elif ev.event_id == event_id:
                seen = True
        return out

    def size(self) -> int:
        n = 0
        for _ in self._iter():
            n += 1
        return n

    def hash_chain(self) -> str:
        """Return the sha256 chain hash of all events in order."""
        h = hashlib.sha256()
        for ev in self._iter():
            h.update(
                json.dumps(ev.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
            )
            h.update(b"\n")
        return h.hexdigest()

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()
        self.path.touch()
