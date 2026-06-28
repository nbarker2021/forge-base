"""
PixelForge Picture — any picture from color blending over the LCR sheet.

A Picture is a width x height sheet of RGB pixels (= a sheet of 8-plane
ribbons). Construction is blending and emission only:

  solid()           one chart state everywhere
  gradient()        pure color blending between two states
  rule30_texture()  the emission law itself paints: each row emitted from
                    the previous by T_EMISSION across the sheet — texture
                    from the substrate, deterministic, seedable
  blend()           superpose any two pictures (the video primitive)

Derived channels (the math reading the picture back):
  emission_map()    per-pixel T_EMISSION shadow byte as grayscale
  carry_map()       per-pixel correction-firing density as grayscale

Output: PPM (P6) and BMP (24-bit BI_RGB) writers — stdlib only, viewable
anywhere. content_hash() makes every picture a crystallizable lib item.
"""
from __future__ import annotations

import hashlib
import struct
from typing import List, Optional, Tuple

from PixelForge.rgb import blend_rgb, pixel_carry, pixel_emission, _EMIT

Color = Tuple[int, int, int]


class Picture:
    """RGB24 pixel sheet. Logical content; any Surface realizes it."""

    def __init__(self, width: int, height: int,
                 buf: Optional[bytearray] = None):
        self.width = int(width)
        self.height = int(height)
        n = self.width * self.height * 3
        self.buf = buf if buf is not None else bytearray(n)
        if len(self.buf) != n:
            raise ValueError("buffer size mismatch")

    # ── constructors (blending IS picture-making) ────────────────────────────
    @classmethod
    def solid(cls, w: int, h: int, color: Color) -> "Picture":
        p = cls(w, h)
        r, g, b = color
        p.buf[:] = bytes((r, g, b)) * (w * h)
        return p

    @classmethod
    def gradient(cls, w: int, h: int, c0: Color, c1: Color,
                 horizontal: bool = True) -> "Picture":
        p = cls(w, h)
        for y in range(h):
            for x in range(w):
                t = (x / max(1, w - 1)) if horizontal else (y / max(1, h - 1))
                p.set(x, y, blend_rgb(c0, c1, t))
        return p

    @classmethod
    def rule30_texture(cls, w: int, h: int, fg: Color, bg: Color,
                       seed: int = 1) -> "Picture":
        """The emission law paints. Row 0 seeded deterministically; each
        next row's cell = T_EMISSION of the (L, C, R) window above it."""
        p = cls(w, h)
        row = [(seed >> (x % 31)) & 1 if x != w // 2 else 1 for x in range(w)]
        for y in range(h):
            for x in range(w):
                p.set(x, y, fg if row[x] else bg)
            row = [
                _EMIT[(row[(x - 1) % w], row[x], row[(x + 1) % w])]
                for x in range(w)
            ]
        return p

    # ── pixel access ─────────────────────────────────────────────────────────
    def get(self, x: int, y: int) -> Color:
        i = (y * self.width + x) * 3
        return (self.buf[i], self.buf[i + 1], self.buf[i + 2])

    def set(self, x: int, y: int, c: Color) -> None:
        i = (y * self.width + x) * 3
        self.buf[i], self.buf[i + 1], self.buf[i + 2] = c

    # ── superposition ────────────────────────────────────────────────────────
    def blend(self, other: "Picture", t: float) -> "Picture":
        """Superpose two equal-size pictures: out = self*(1-t) + other*t."""
        if (other.width, other.height) != (self.width, self.height):
            raise ValueError("blend requires equal dimensions")
        out = Picture(self.width, self.height)
        a, b, o = self.buf, other.buf, out.buf
        ti = int(t * 256)
        for i in range(len(a)):
            o[i] = (a[i] * (256 - ti) + b[i] * ti) >> 8
        return out

    def copy(self) -> "Picture":
        return Picture(self.width, self.height, bytearray(self.buf))

    def compare(self, other: "Picture") -> dict:
        """Per-channel byte difference against another picture of equal
        size — the GS-08 parity primitive: two backends producing the
        same splat buffer are compared directly via this, not assumed
        identical from matching code paths alone."""
        if (other.width, other.height) != (self.width, self.height):
            raise ValueError("compare requires equal dimensions")
        a, b = self.buf, other.buf
        max_delta = 0
        sum_delta = 0
        n = len(a)
        for i in range(n):
            d = a[i] - b[i]
            if d < 0:
                d = -d
            if d > max_delta:
                max_delta = d
            sum_delta += d
        return {
            "identical": max_delta == 0,
            "max_channel_delta": max_delta,
            "mean_channel_delta": round(sum_delta / n, 6) if n else 0.0,
        }

    # ── derived channels (the math reads the picture) ───────────────────────
    def emission_map(self) -> "Picture":
        out = Picture(self.width, self.height)
        for y in range(self.height):
            for x in range(self.width):
                e = pixel_emission(*self.get(x, y))
                out.set(x, y, (e, e, e))
        return out

    def carry_map(self) -> "Picture":
        out = Picture(self.width, self.height)
        for y in range(self.height):
            for x in range(self.width):
                c = pixel_carry(*self.get(x, y)) * 31   # 0..8 -> 0..248
                out.set(x, y, (c, c, c))
        return out

    # ── identity + output ────────────────────────────────────────────────────
    def content_hash(self) -> str:
        h = hashlib.sha256()
        h.update(struct.pack("<II", self.width, self.height))
        h.update(bytes(self.buf))
        return h.hexdigest()[:16]

    def to_ppm(self, path: str) -> str:
        with open(path, "wb") as f:
            f.write(f"P6\n{self.width} {self.height}\n255\n".encode())
            f.write(bytes(self.buf))
        return path

    def to_bmp(self, path: str) -> str:
        """24-bit BI_RGB bottom-up BMP — double-clickable on any OS."""
        w, h = self.width, self.height
        row_pad = (4 - (w * 3) % 4) % 4
        img_size = (w * 3 + row_pad) * h
        with open(path, "wb") as f:
            f.write(b"BM")
            f.write(struct.pack("<IHHI", 54 + img_size, 0, 0, 54))
            f.write(struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0,
                                img_size, 2835, 2835, 0, 0))
            pad = b"\x00" * row_pad
            for y in range(h - 1, -1, -1):          # bottom-up
                row = bytearray()
                for x in range(w):
                    r, g, b = self.get(x, y)
                    row += bytes((b, g, r))         # BGR order
                f.write(bytes(row) + pad)
        return path
