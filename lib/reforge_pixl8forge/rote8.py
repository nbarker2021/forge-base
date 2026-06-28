from __future__ import annotations
from .frames import Frame, Pixel
from typing import List


def _transpose(p):
    return [list(row) for row in zip(*p)]

def _rot90(p):
    return [list(row) for row in zip(*p[::-1])]

def _rot180(p):
    return [row[::-1] for row in p[::-1]]

def _rot270(p):
    return [list(row) for row in zip(*p)][::-1]

def _flip_x(p):
    return [row[::-1] for row in p]

def _flip_y(p):
    return p[::-1]

def _anti_transpose(p):
    # transpose across anti-diagonal
    return _rot180(_transpose(p))


def rote8(frame: Frame, phase: int) -> Frame:
    """Rote8: 8-way D4 orientation transposition for clean frame orientation."""
    frame.validate()
    k = phase % 8
    p: List[List[Pixel]] = frame.pixels
    if k == 0: out = [row[:] for row in p]
    elif k == 1: out = _rot90(p)
    elif k == 2: out = _rot180(p)
    elif k == 3: out = _rot270(p)
    elif k == 4: out = _flip_x(p)
    elif k == 5: out = _flip_y(p)
    elif k == 6: out = _transpose(p)
    else: out = _anti_transpose(p)
    return Frame(width=len(out[0]), height=len(out), pixels=out, label=f"{frame.label}:rote8:{k}", phase=k)
