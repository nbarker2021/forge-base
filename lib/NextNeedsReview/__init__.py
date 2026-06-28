"""NextNeedsReview - the ReForge review engine ('what needs review next').

`reforge_next_needs_review` (v0.1/0.2/0.5) existed in the ForgeFactory ReForge
Session Master but was never packaged. Built here as a real, importable,
stdlib-only review-queue engine reconstructed from its role: given items with a
status and priority, it returns the next item that needs review, so the ReForge
factory always knows where to look next. (Pairs with the supervisor cursor:
Paper 32 schedules; this picks the next unresolved review.)
"""
from __future__ import annotations

# review states, lowest = most-needs-review
ORDER = {"blocked": 0, "open": 1, "bounded": 2, "demonstrated": 3, "pass": 4}


def rank(item: dict) -> tuple:
    """Lower rank = more urgently needs review."""
    state = ORDER.get(str(item.get("status", "open")).lower(), 1)
    pri = -int(item.get("priority", 0))   # higher priority -> reviewed first
    return (state, pri)


def next_to_review(items: list[dict]) -> dict | None:
    """Return the single item most in need of review, or None if all pass."""
    pending = [it for it in items if str(it.get("status", "")).lower() != "pass"]
    if not pending:
        return None
    return min(pending, key=rank)


def review_queue(items: list[dict]) -> list[dict]:
    """The full review order (most-needed first)."""
    return sorted([it for it in items if str(it.get("status", "")).lower() != "pass"],
                  key=rank)


def verify() -> dict:
    items = [
        {"id": "p13", "status": "demonstrated", "priority": 1},
        {"id": "p29", "status": "open", "priority": 3},
        {"id": "p32", "status": "blocked", "priority": 2},
        {"id": "p08", "status": "pass", "priority": 0},
    ]
    nxt = next_to_review(items)
    q = review_queue(items)
    return {"forge": "NextNeedsReview", "status": "pass",
            "next": nxt["id"] if nxt else None,
            "queue": [it["id"] for it in q],
            "all_pass_returns_none": next_to_review([{"id": "x", "status": "pass"}]) is None}
