"""
PixelForge Video — video is just a lot of pixels moving.

A video is layers of pictures, superposed, with movement CALCULATED — not
re-rendered. Each Layer carries a picture and a motion function t -> (dx, dy);
each frame transports the layer's pixels by toroidal translation (the torus
chart again: pixels wrap, none created, none destroyed — the pixel multiset
is CONSERVED per layer, the e8lossless property made literal) and superposes
the layers by blending.

Per-frame governance reuses the existing machinery unchanged: an 8-vector is
read from the frame (mean wires, emission mean, carry density, motion
magnitude...) and fed to FrameStream, which applies the parity/entropy
transition law and emits the deterministic artifact. Same layers + same
motions = same frames = same hashes, forever.

Stdlib only. Nothing new — adjusting.
"""
from __future__ import annotations

import hashlib
from typing import Any, Callable, Dict, List, Optional, Tuple

from PixelForge.frame import FrameStream
from PixelForge.picture import Picture
from PixelForge.rgb import pixel_carry, pixel_emission

Motion = Callable[[int], Tuple[int, int]]    # frame index -> (dx, dy) pixels


def translate_toroidal(p: Picture, dx: int, dy: int) -> Picture:
    """Move every pixel by (dx, dy) on the torus. Lossless transport:
    the pixel multiset is conserved — movement, not mutation."""
    w, h = p.width, p.height
    out = Picture(w, h)
    dx %= w
    dy %= h
    row_bytes = w * 3
    for y in range(h):
        src_y = (y - dy) % h
        src = p.buf[src_y * row_bytes:(src_y + 1) * row_bytes]
        shifted = src[-dx * 3:] + src[:-dx * 3] if dx else src
        out.buf[y * row_bytes:(y + 1) * row_bytes] = shifted
    return out


class Layer:
    def __init__(self, picture: Picture, motion: Optional[Motion] = None,
                 alpha: float = 1.0):
        self.picture = picture
        self.motion = motion or (lambda t: (0, 0))
        self.alpha = max(0.0, min(1.0, alpha))


class VideoSynth:
    """Layers + motion -> frames. Superposition is blending; movement is
    toroidal transport; governance is the existing FrameStream."""

    def __init__(self, width: int, height: int, fps: float = 24.0,
                 background: Tuple[int, int, int] = (0, 0, 0),
                 parity_rule: str = "free",
                 entropy_slack: float = 0.08):
        # entropy_slack: moving content fluctuates frame statistics both
        # ways; the default tolerates ordinary motion while still recording
        # large entropy jumps as obligations (set 0.0 for the strict law).
        self.width, self.height, self.fps = int(width), int(height), fps
        self.background = background
        self.layers: List[Layer] = []
        self.stream = FrameStream(fps=fps, projection="standard",
                                  parity_rule=parity_rule,
                                  entropy_slack=entropy_slack)

    def add_layer(self, picture: Picture, motion: Optional[Motion] = None,
                  alpha: float = 1.0) -> "VideoSynth":
        self.layers.append(Layer(picture, motion, alpha))
        return self

    # ── frame synthesis ──────────────────────────────────────────────────────
    def _compose(self, t: int) -> Picture:
        frame = Picture.solid(self.width, self.height, self.background)
        for layer in self.layers:
            dx, dy = layer.motion(t)
            moved = translate_toroidal(layer.picture, dx, dy)
            frame = frame.blend(moved, layer.alpha)
        return frame

    def _frame_e8(self, pic: Picture, t: int) -> List[float]:
        """Read the frame's 8-vector: the three wires' means, emission mean,
        carry density, motion magnitude, layer count, time phase."""
        n = pic.width * pic.height
        step = max(1, n // 256)                  # sampled read, deterministic
        sr = sg = sb = se = sc = 0
        count = 0
        for i in range(0, n, step):
            x, y = i % pic.width, i // pic.width
            r, g, b = pic.get(x, y)
            sr += r; sg += g; sb += b
            se += pixel_emission(r, g, b)
            sc += pixel_carry(r, g, b)
            count += 1
        mv = sum(abs(l.motion(t)[0]) + abs(l.motion(t)[1]) for l in self.layers)
        return [sr / count / 255, sg / count / 255, sb / count / 255,
                se / count / 255, sc / count / 8,
                min(1.0, mv / max(1, self.width)),
                len(self.layers) / 8.0,
                (t % 256) / 256.0]

    def render(self, n_frames: int) -> Dict[str, Any]:
        """Synthesize n frames; every frame governed through FrameStream."""
        pics: List[Picture] = []
        for t in range(n_frames):
            pic = self._compose(t)
            pics.append(pic)
            self.stream.add_state(self._frame_e8(pic, t),
                                  metadata={"frame_hash": pic.content_hash(),
                                            "t": t})
        h = hashlib.sha256()
        for p in pics:
            h.update(p.content_hash().encode())
        return {
            "frames": pics,
            "video_hash": h.hexdigest()[:16],
            "artifact": {k: v for k, v in self.stream.artifact().items()
                         if k != "frames"},
            "governance": self.stream.stats(),
        }

    @staticmethod
    def write_sequence(frames: List[Picture], directory: str,
                       fmt: str = "bmp") -> List[str]:
        from pathlib import Path
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        out = []
        for i, p in enumerate(frames):
            path = str(d / f"frame_{i:04d}.{fmt}")
            (p.to_bmp if fmt == "bmp" else p.to_ppm)(path)
            out.append(path)
        return out
