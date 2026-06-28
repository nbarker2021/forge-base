from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any
import hashlib

Pixel = Tuple[int, int, int, int]  # RGBA 0..255

@dataclass
class Frame:
    width: int
    height: int
    pixels: List[List[Pixel]]
    label: str = "frame"
    phase: int = 0

    def validate(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Frame width/height must be positive")
        if len(self.pixels) != self.height:
            raise ValueError("Pixel row count does not match height")
        for row in self.pixels:
            if len(row) != self.width:
                raise ValueError("Pixel column count does not match width")
            for px in row:
                if len(px) != 4 or any(not isinstance(v, int) or v < 0 or v > 255 for v in px):
                    raise ValueError(f"Invalid RGBA pixel: {px}")

    def digest(self) -> str:
        self.validate()
        h = hashlib.sha256()
        h.update(self.label.encode())
        h.update(bytes([self.width % 256, self.height % 256, self.phase % 256]))
        for row in self.pixels:
            for px in row:
                h.update(bytes(px))
        return h.hexdigest()[:16]

    def copy_with(self, pixels: List[List[Pixel]], label: str | None = None, phase: int | None = None) -> "Frame":
        f = Frame(width=len(pixels[0]) if pixels else 0, height=len(pixels), pixels=pixels, label=label or self.label, phase=self.phase if phase is None else phase)
        f.validate()
        return f

    def to_dict(self) -> Dict[str, Any]:
        return {"width": self.width, "height": self.height, "label": self.label, "phase": self.phase, "digest": self.digest(), "pixels": self.pixels}


def make_demo_frame(width: int = 8, height: int = 8, phase: int = 0, label: str = "demo") -> Frame:
    pixels: List[List[Pixel]] = []
    for y in range(height):
        row = []
        for x in range(width):
            r = (x * 32 + phase * 17) % 256
            g = (y * 32 + phase * 29) % 256
            b = ((x + y) * 16 + phase * 41) % 256
            row.append((r, g, b, 255))
        pixels.append(row)
    return Frame(width, height, pixels, label=label, phase=phase)


def lcr_from_pixel(px: Pixel) -> tuple[int, int, int]:
    r, g, b, a = px
    # boundary-binary L/C/R: luminance-left, color-center, alpha/right-presence
    l = 1 if r >= g else 0
    c = 1 if max(r, g, b) >= 128 else 0
    rr = 1 if a >= 128 and b >= r else 0
    return l, c, rr


def color_name(px: Pixel) -> str:
    r, g, b, a = px
    if a < 64:
        return "clear"
    # preserve saturated quark-color identity even at low luminance
    if r >= g and r >= b and r - max(g, b) > 24:
        return "red"
    if g >= r and g >= b and g - max(r, b) > 24:
        return "green"
    if b >= r and b >= g and b - max(r, g) > 24:
        return "blue"
    lum = (r + g + b) / 3
    if lum < 48:
        return "black"
    if lum > 210:
        return "white"
    return "grey"


def frame_to_worldforge_nodes(frame: Frame, prefix: str = "px") -> Dict[str, Any]:
    frame.validate()
    nodes = []
    edges = []
    for y, row in enumerate(frame.pixels):
        for x, px in enumerate(row):
            node_id = f"{prefix}_{frame.phase}_{y}_{x}"
            L, C, R = lcr_from_pixel(px)
            nodes.append({
                "id": node_id,
                "kind": "pixel_block",
                "label": f"{x},{y}",
                "x": x,
                "y": y,
                "phase": frame.phase,
                "rgba": px,
                "lcr": {"L": L, "C": C, "R": R, "Gamma": C},
                "color_state": color_name(px),
            })
            if x > 0:
                edges.append({"source": f"{prefix}_{frame.phase}_{y}_{x-1}", "target": node_id, "kind": "horizontal_adjacency"})
            if y > 0:
                edges.append({"source": f"{prefix}_{frame.phase}_{y-1}_{x}", "target": node_id, "kind": "vertical_adjacency"})
    return {"frame": frame.to_dict(), "nodes": nodes, "edges": edges}
