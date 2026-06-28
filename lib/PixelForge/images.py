"""
PixelForge Images — real image decoders, pure stdlib.

read_png(): a true PNG decoder built on zlib (stdlib): chunk parse, all five
scanline filters (None/Sub/Up/Average/Paeth), 8-bit gray / gray+alpha /
RGB / RGBA / palette, non-interlaced. Alpha composites over black.
read_bmp(): inverse of Picture.to_bmp (24-bit BI_RGB).
load_image(): dispatch by magic bytes.

Real pictures in, Pictures out — the doorway for the saved-image database.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Optional

from PixelForge.picture import Picture


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def read_png(path: str) -> Picture:
    raw = Path(path).read_bytes()
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    w = h = bit_depth = color_type = 0
    palette = b""
    idat = bytearray()
    i = 8
    while i < len(raw):
        ln, typ = struct.unpack_from(">I4s", raw, i)
        data = raw[i + 8:i + 8 + ln]
        if typ == b"IHDR":
            w, h, bit_depth, color_type, _comp, _filt, interlace = \
                struct.unpack(">IIBBBBB", data)
            if bit_depth != 8 or interlace:
                raise ValueError("png decoder supports 8-bit non-interlaced only")
        elif typ == b"PLTE":
            palette = data
        elif typ == b"IDAT":
            idat += data
        elif typ == b"IEND":
            break
        i += 12 + ln
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    stride = w * channels
    flat = zlib.decompress(bytes(idat))

    # unfilter
    out = bytearray(h * stride)
    prev = bytearray(stride)
    pos = 0
    for y in range(h):
        f = flat[pos]; pos += 1
        line = bytearray(flat[pos:pos + stride]); pos += stride
        if f == 1:    # Sub
            for x in range(channels, stride):
                line[x] = (line[x] + line[x - channels]) & 0xFF
        elif f == 2:  # Up
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 0xFF
        elif f == 3:  # Average
            for x in range(stride):
                a = line[x - channels] if x >= channels else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 0xFF
        elif f == 4:  # Paeth
            for x in range(stride):
                a = line[x - channels] if x >= channels else 0
                c = prev[x - channels] if x >= channels else 0
                line[x] = (line[x] + _paeth(a, prev[x], c)) & 0xFF
        out[y * stride:(y + 1) * stride] = line
        prev = line

    pic = Picture(w, h)
    for y in range(h):
        row = out[y * stride:(y + 1) * stride]
        for x in range(w):
            k = x * channels
            if color_type == 2:
                r, g, b = row[k], row[k + 1], row[k + 2]
            elif color_type == 6:
                a = row[k + 3]
                r = row[k] * a // 255
                g = row[k + 1] * a // 255
                b = row[k + 2] * a // 255
            elif color_type == 0:
                r = g = b = row[k]
            elif color_type == 4:
                a = row[k + 1]
                r = g = b = row[k] * a // 255
            else:  # palette
                pi = row[k] * 3
                r, g, b = palette[pi], palette[pi + 1], palette[pi + 2]
            pic.set(x, y, (r, g, b))
    return pic


def read_bmp(path: str) -> Picture:
    raw = Path(path).read_bytes()
    if raw[:2] != b"BM":
        raise ValueError("not a BMP")
    off, = struct.unpack_from("<I", raw, 10)
    hdr, w, h, _planes, bpp, comp = struct.unpack_from("<IiiHHI", raw, 14)
    if bpp != 24 or comp != 0:
        raise ValueError("bmp reader supports 24-bit BI_RGB only")
    flip = h > 0
    h = abs(h)
    row_w = (w * 3 + 3) & ~3
    pic = Picture(w, h)
    for y in range(h):
        src_y = (h - 1 - y) if flip else y
        base = off + src_y * row_w
        for x in range(w):
            b, g, r = raw[base + x * 3], raw[base + x * 3 + 1], raw[base + x * 3 + 2]
            pic.set(x, y, (r, g, b))
    return pic


def load_image(path: str) -> Optional[Picture]:
    """Decode any supported real image file to a Picture (None if unsupported)."""
    try:
        head = Path(path).open("rb").read(8)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return read_png(path)
        if head[:2] == b"BM":
            return read_bmp(path)
    except Exception:
        return None
    return None
