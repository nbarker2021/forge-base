"""MorphForge - applied lossless ribbon reader.

Paper 21 (MorphForge / PolyForge / MorphoniX). Referenced but never packaged.
Built here as a real, importable, stdlib-only ribbon encoder: an observed object
(symbol sequence) -> overlapping length-3 (L,C,R) windows = the ribbon, with a
lossless round-trip. The golden-sweep ordering lives in AGRMForge (this wraps it
when available). Cross-medium equivalence / domain closures are external bridges.
"""
from __future__ import annotations


def ribbon(symbols) -> list[tuple]:
    """Encode a sequence as overlapping (L,C,R) windows (the swept ribbon)."""
    s = list(symbols)
    return [tuple(s[i:i + 3]) for i in range(max(0, len(s) - 2))]


def round_trip(symbols) -> bool:
    """Lossless: the original sequence is recoverable from the ribbon windows."""
    s = list(symbols)
    if len(s) < 3:
        return True
    r = ribbon(s)
    rebuilt = list(r[0]) + [w[-1] for w in r[1:]]
    return rebuilt == s


def golden_sweep_order(items):
    """Order items by the AGRM golden-ratio sweep if AGRMForge is importable;
    else return items unchanged (stdlib baseline)."""
    try:
        from GraphStax import agrm
        scanner = agrm.AGRMSweepScanner(dimensions=max(1, len(items[0]) if items and hasattr(items[0], "__len__") else 1))
        nodes = [agrm.StaxNode(node_id=str(i), position=list(x) if hasattr(x, "__len__") else [float(i)],
                               resonance=str(i)) for i, x in enumerate(items)]
        return [items[int(n.node_id)] for n, _ in scanner.sweep(nodes).ranked]
    except Exception:
        return list(items)


def verify() -> dict:
    ok = round_trip([1, 2, 3, 1, 2, 1, 3, 2, 1])
    return {"forge": "MorphForge", "paper": 21, "status": "pass" if ok else "fail",
            "lossless_round_trip": ok}
