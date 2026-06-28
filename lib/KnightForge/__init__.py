"""KnightForge - greedy non-attacking knight placement as a local-rule CA receipt.

Paper 24. Was referenced across the corpus but never packaged. Built here as a
real, importable, stdlib-only module. The chessboard is the shadow; the receipt
is the proof object (a finite, replayable local-rule CA). Playability / OEIS
identity remain external (see Paper 24).
"""
from __future__ import annotations

KNIGHT_MOVES = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]


def place_knights(n: int = 8) -> dict:
    """Greedy non-attacking knight CA over an n x n board in boustrophedon order."""
    occupied: set[tuple[int, int]] = set()
    rows = []
    for r in range(n):
        cols = range(n) if r % 2 == 0 else range(n - 1, -1, -1)
        for c in cols:
            attacked = any((r + dr, c + dc) in occupied for dr, dc in KNIGHT_MOVES)
            placed = not attacked
            if placed:
                occupied.add((r, c))
            rows.append({"cell": (r, c), "occupied": placed})
    non_attacking = all(
        (r + dr, c + dc) not in occupied
        for (r, c) in occupied for dr, dc in KNIGHT_MOVES
    )
    return {
        "n": n,
        "occupied": sorted(occupied),
        "count": len(occupied),
        "non_attacking": non_attacking,
        "rows": rows,
    }


def verify() -> dict:
    rec = place_knights(8)
    return {"forge": "KnightForge", "paper": 24, "status": "pass" if rec["non_attacking"] else "fail",
            "occupied_count": rec["count"], "non_attacking": rec["non_attacking"]}
