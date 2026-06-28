"""
PixelForge AVI — a real video file encoder, stdlib only.

Writes uncompressed RGB24 AVI (RIFF / 'DIB ' frames): no codecs, no deps,
plays in Windows Media Player, VLC, browsers-with-plugins, everything.
Frame data is bottom-up BGR rows padded to 4 bytes — byte-identical to the
BMP pixel layout, so the encoder is pure container framing around the
pictures we already make. e8lossless end-to-end: what you hash is what
plays.

decode_avi() reads our own files back to Pictures — the decoder half, so
data -> pixels -> video -> pixels -> data is a provable roundtrip.
"""
from __future__ import annotations

import struct
from typing import List, Tuple

from PixelForge.picture import Picture


def _frame_bytes(p: Picture) -> bytes:
    """Bottom-up BGR, rows padded to 4 — the DIB layout."""
    w, h = p.width, p.height
    pad = b"\x00" * ((4 - (w * 3) % 4) % 4)
    rows = []
    for y in range(h - 1, -1, -1):
        row = bytearray()
        for x in range(w):
            r, g, b = p.get(x, y)
            row += bytes((b, g, r))
        rows.append(bytes(row) + pad)
    return b"".join(rows)


def write_avi(frames: List[Picture], path: str, fps: int = 30) -> str:
    """Encode Pictures into an uncompressed AVI at the requested rate."""
    if not frames:
        raise ValueError("no frames")
    w, h = frames[0].width, frames[0].height
    payloads = [_frame_bytes(p) for p in frames]
    fsize = len(payloads[0])

    # ── headers ──────────────────────────────────────────────────────────────
    avih = struct.pack("<14I",
        int(1_000_000 / fps), fsize * fps, 0, 0x10,      # usec/frame, rate, pad, HASINDEX
        len(frames), 0, 1, fsize, w, h, 0, 0, 0, 0)
    strh = (b"vids" + b"DIB " + struct.pack("<10I",
            0, 0, 0, 1, fps, 0, len(frames), fsize, 0xFFFFFFFF, 0)
            + struct.pack("<4H", 0, 0, w, h))
    strf = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, fsize,
                       2835, 2835, 0, 0)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return tag + struct.pack("<I", len(data)) + data + (b"\x00" * (len(data) % 2))

    def lst(tag: bytes, data: bytes) -> bytes:
        return chunk(b"LIST", tag + data)

    hdrl = lst(b"hdrl", chunk(b"avih", avih)
               + lst(b"strl", chunk(b"strh", strh) + chunk(b"strf", strf)))

    movi_frames = b"".join(chunk(b"00db", pl) for pl in payloads)
    movi = lst(b"movi", movi_frames)

    # idx1: offsets relative to the start of 'movi' tag data
    idx = bytearray()
    off = 4
    for pl in payloads:
        idx += b"00db" + struct.pack("<III", 0x10, off, len(pl))
        off += 8 + len(pl) + (len(pl) % 2)
    idx1 = chunk(b"idx1", bytes(idx))

    body = b"AVI " + hdrl + movi + idx1
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", len(body)) + body)
    return path


def decode_avi(path: str) -> Tuple[List[Picture], int]:
    """Read an AVI written by write_avi() back into Pictures + fps.
    The decoder half of the codec — proves the container is lossless."""
    raw = open(path, "rb").read()
    if raw[:4] != b"RIFF" or raw[8:12] != b"AVI ":
        raise ValueError("not an AVI")
    # main header (first 'avih' chunk)
    i = raw.find(b"avih")
    usec, = struct.unpack_from("<I", raw, i + 8)
    fps = round(1_000_000 / usec)
    nframes, = struct.unpack_from("<I", raw, i + 8 + 16)
    # dimensions from strf BITMAPINFOHEADER
    j = raw.find(b"strf")
    w, h = struct.unpack_from("<ii", raw, j + 12)
    # frames: every 00db chunk
    frames: List[Picture] = []
    k = 0
    row_w = w * 3 + ((4 - (w * 3) % 4) % 4)
    while True:
        k = raw.find(b"00db", k)
        if k < 0 or len(frames) >= nframes:
            break
        size, = struct.unpack_from("<I", raw, k + 4)
        data = raw[k + 8:k + 8 + size]
        if len(data) == size and size == row_w * h:
            p = Picture(w, h)
            for y in range(h):
                src = data[(h - 1 - y) * row_w:(h - 1 - y) * row_w + w * 3]
                for x in range(w):
                    b_, g_, r_ = src[x * 3], src[x * 3 + 1], src[x * 3 + 2]
                    p.set(x, y, (r_, g_, b_))
            frames.append(p)
        k += 8 + size
    return frames, fps
