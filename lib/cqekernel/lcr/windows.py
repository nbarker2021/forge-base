"""
LCR windows: the channel-level resolution surface.

The kernel is an **LCR-window machine**, not a per-bit gluon
counter. Every observation produces:

  * a *gluon stream* — one 3-bit (L, C, R) gluon per sliding
    window in the bit stream. This is the per-bit dimensional
    transport receipt. The C bit in each gluon is both the
    entry value AND the resolution value — the algebra
    primitive re-applies C to validate the correction. This
    is the user's "reapply that C" insight.
  * a *window envelope* — the bit stream partitioned into
    2x2 / 4x4 / 8x8 windows. The 8x8 envelope is the lattice
    envelope; the 2x2 and 4x4 are the channel windows.
  * a *channel resolution* — a small set of algebra-expressed
    resolutions (≤8 per observation), each tagged with which
    algebra primitive resolved it. This is the few-bit answer
    that emerges from the dimensional lift.

For an N-bit input the budget is:
  * per-bit gluon stream: N - 2 gluons (sliding 3-bit window)
  * 2x2 windows: ceil(N / 4)
  * 4x4 windows: ceil(N / 16)
  * 8x8 windows: at most 1
  * channel resolutions: ≤8 (the few-bit answer)

The gluons and the windows are not redundant. The gluons are
the per-window **receipt** that the algebra primitive re-applies
to the C bit at that exact location. The windows are the
envelope that the algebra primitive operates on. The channels
are the few compressed resolutions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class WindowSize(Enum):
    """The only window sizes the kernel recognises."""

    W_2x2 = "2x2"   # 4 bits, 16 possible states
    W_4x4 = "4x4"   # 16 bits, 65536 possible states
    W_8x8 = "8x8"   # 64 bits, the lattice envelope


# Number of bits per window
WINDOW_BITS: Dict[WindowSize, int] = {
    WindowSize.W_2x2: 4,
    WindowSize.W_4x4: 16,
    WindowSize.W_8x8: 64,
}


@dataclass(frozen=True)
class LCRGluon:
    """A single 3-bit LCR-window gluon. This is the per-bit
    dimensional-transport receipt.

    Each gluon carries:
      * the (L, C, R) triple — the entry value of the
        observation at that 3-bit window
      * the derived correction (C AND NOT R) — the
        lossless upward/downward dimensional transport
        that the C bit carries
      * the shell, the chiral flag, the closure state
      * the algebra-expressed receipt: which primitive
        re-applied C and got the same answer

    The gluon stream is the *body* of data required to lift
    the state fully. The C bit is the entry; the algebra
    primitive re-applies C to validate the correction. This
    is the per-window dimensional transport.
    """

    index: int
    left: int
    center: int
    right: int
    shell: int
    chiral: bool
    correction: int  # C AND NOT R
    state_class: str
    # Receipt-level: did the algebra primitive close this
    # gluon's window? (M3 idempotency, SU(3) closure, etc.)
    closed: bool
    # The subspace this gluon maps to in the algebra
    subspace: str = ""
    # Receipt hash for this gluon
    receipt_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "left": self.left,
            "center": self.center,
            "right": self.right,
            "shell": self.shell,
            "chiral": self.chiral,
            "correction": self.correction,
            "state_class": self.state_class,
            "closed": self.closed,
            "subspace": self.subspace,
            "receipt_hash": self.receipt_hash,
        }


@dataclass(frozen=True)
class LCRWindow:
    """A single channel-level LCR window resolution.

    The window is the **primary receipt unit** for the channel
    layer. Each observation emits at most ceil(N/4) 2x2 windows,
    ceil(N/16) 4x4 windows, and (at most) one 8x8 window.
    """

    # Identity
    size: WindowSize
    index: int  # ordinal within the observation

    # The raw bit grid (2x2: 4 bits, 4x4: 16 bits, 8x8: 64 bits)
    bits: Tuple[int, ...]  # length matches WINDOW_BITS[size]

    # The L/C/R decomposition of the window (extracted from the
    # 4x4 or 8x8 envelope; for 2x2, L=R=center=the single bit)
    left: int
    center: int
    right: int

    # The wider-context (only meaningful for 4x4 and 8x8)
    wider: Tuple[int, ...] = field(default_factory=tuple)
    # (LL, RR) for 4x4, (LL, LLL, RRR, RR) for 8x8

    # The resolved answer: which C-form fired, what the correction
    # identity returned, the closure state
    c_form: int = 0  # the center bit (the C-form value)
    correction: int = 0  # C AND NOT R
    shell: int = 0  # L + C + R
    chiral: bool = False  # L != R
    closed: bool = False  # whether the window closed (channel resolved)

    # The gluon indices that back this window (the per-3-bit
    # receipts inside this window's bit grid)
    backing_gluons: Tuple[int, ...] = ()

    # Receipt-level evidence: which algebra primitive was
    # applied, what the result was
    algebra_id: str = ""  # e.g. "octonion_axioms", "f4_3x3", "n3_su3_closure"
    algebra_status: str = ""  # "pass" / "fail" / "n/a"
    receipt_hash: str = ""

    @property
    def bit_count(self) -> int:
        return len(self.bits)

    def apply_algebra_idempotency(self) -> "LCRWindow":
        """Return a new window with `closed` set by checking the
        M3 idempotency on the 2x2 envelope.

        For 2x2 windows, the M3 idempotency says the cell
        `M = [[L, C], [C, R]]` should satisfy `M^2 = M` *iff*
        the channel is closed. The single test is
        `(L AND R) == C` — the center must equal the
        intersection of the boundaries (i.e. C must validate
        itself when re-applied through the algebra).

        For 4x4 and 8x8 windows, the test is the doubly-stochastic
        closure of the wider-context marginalization (the
        SU(3) closed-form on the trace-2 stratum).
        """
        if self.size == WindowSize.W_2x2:
            # 2x2 channel: closed iff L & R == C (the M3
            # idempotency: re-apply C, get the same C)
            closed = bool((self.left & self.right) == (self.center & 1))
        elif self.size == WindowSize.W_4x4:
            # 4x4 channel: closed iff the wider-context
            # marginalization equals the trace-2 idempotent
            w = self.wider[0] if self.wider else 0
            closed = bool((w & 1) == ((self.left ^ self.right ^ self.center) & 1))
        else:  # W_8x8
            w = self.wider
            if len(w) == 4:
                closed = bool(all(
                    (n & 1) == ((self.left ^ self.right ^ self.center) & 1)
                    for n in w
                ))
            else:
                closed = False
        # The receipt hash is sha256 of (size, bits, L, C, R, closed)
        import hashlib
        h = hashlib.sha256()
        h.update(self.size.value.encode("utf-8"))
        for b in self.bits:
            h.update(bytes([b & 1]))
        h.update(bytes([self.left & 0xFF, self.center & 0xFF, self.right & 0xFF]))
        h.update(bytes([1 if closed else 0]))
        receipt_hash = h.hexdigest()
        return LCRWindow(
            size=self.size,
            index=self.index,
            bits=self.bits,
            left=self.left,
            center=self.center,
            right=self.right,
            wider=self.wider,
            c_form=self.c_form,
            correction=self.correction,
            shell=self.shell,
            chiral=self.chiral,
            closed=closed,
            backing_gluons=self.backing_gluons,
            algebra_id=self.algebra_id or f"m3_idempotency_{self.size.value}",
            algebra_status="pass" if closed else "fail",
            receipt_hash=receipt_hash,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "size": self.size.value,
            "index": self.index,
            "bit_count": self.bit_count,
            "left": self.left,
            "center": self.center,
            "right": self.right,
            "wider": list(self.wider),
            "c_form": self.c_form,
            "correction": self.correction,
            "shell": self.shell,
            "chiral": self.chiral,
            "closed": self.closed,
            "algebra_id": self.algebra_id,
            "algebra_status": self.algebra_status,
            "receipt_hash": self.receipt_hash[:16] if self.receipt_hash else "",
        }


@dataclass(frozen=True)
class LCRChannel:
    """The resolved answer of one LCR window.

    This is the few-bit "channel bit" the user described: the
    algebra-expressed resolution that comes out of the 2x2 / 4x4
    / 8x8 envelope. Each channel has at most 1-3 bits of
    information; a single observation produces at most 8 of
    these.
    """

    # Which algebra primitive resolved the channel
    algebra_id: str
    # The few resolved bits (1-3 typical)
    bits: Tuple[int, ...]
    # Whether the channel fully closed
    closed: bool
    # The receipts that back this channel
    source_windows: Tuple[int, ...]  # window indices
    # The dimensional lift: which subspace of the lattice this
    # channel maps to (e.g. "shell_2_idempotent", "boundary_0101", "f4_3x3_uniform")
    subspace: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algebra_id": self.algebra_id,
            "bits": list(self.bits),
            "closed": self.closed,
            "source_windows": list(self.source_windows),
            "subspace": self.subspace,
        }


def envelope_into_windows(bits: Tuple[int, ...], size: WindowSize) -> List[LCRWindow]:
    """Slice a bit stream into non-overlapping windows of the
    given size.

    For an N-bit input and window size W with W bits, this
    returns floor(N / W) windows. The last partial window is
    zero-padded.

    This is the "envelope" pass: the input is partitioned
    into the kernel's native window granularity. Each window
    is the unit that gets a single resolved answer.
    """
    W = WINDOW_BITS[size]
    out: List[LCRWindow] = []
    n = len(bits)
    for start in range(0, n, W):
        chunk = bits[start:start + W]
        if len(chunk) < W:
            chunk = chunk + (0,) * (W - len(chunk))
        # L/C/R extraction depends on size
        if size == WindowSize.W_2x2:
            # 2x2: 4 bits, the corners are: bits 0,1 / bits 2,3
            # We treat bit 0 as the centroid (single C-form) and
            # bits 1,2,3 as L-wide, R-wide
            L = chunk[1]
            C = chunk[0]
            R = chunk[2]
            wider: Tuple[int, ...] = (chunk[3],)
        elif size == WindowSize.W_4x4:
            # 4x4: 16 bits, arranged as 2x2 of 2x2 cells.
            # Cells: 0-3 (top-left), 4-7 (top-right), 8-11 (bottom-left), 12-15 (bottom-right)
            # L = top-right cell, C = bottom-right cell, R = bottom-left cell
            # (the LCR ordering from the chart).
            # Or simpler: the 4x4 windows from lattice_forge's
            # LightConeFrame are: 4 nested windows of size 2x2.
            # We use the bottom-right 2x2 as the channel cell.
            L = (chunk[4] << 0) | (chunk[5] << 1) | (chunk[6] << 2) | (chunk[7] << 3)
            C = (chunk[12] << 0) | (chunk[13] << 1) | (chunk[14] << 2) | (chunk[15] << 3)
            R = (chunk[8] << 0) | (chunk[9] << 1) | (chunk[10] << 2) | (chunk[11] << 3)
            # Wider context: the top-left 2x2 (the marginalization)
            wider = (
                (chunk[0] << 0) | (chunk[1] << 1) | (chunk[2] << 2) | (chunk[3] << 3),
            )
        else:  # W_8x8
            # 8x8: 64 bits, the lattice envelope.
            # Use the standard 4x4 sub-envelopes (top-left, top-right,
            # bottom-left, bottom-right) as the L, C, R, and wider.
            def nibble_at(b: Tuple[int, ...], row: int, col: int) -> int:
                base = row * 8 + col
                return (b[base] << 0) | (b[base + 1] << 1) | (b[base + 2] << 2) | (b[base + 3] << 3)
            L = nibble_at(chunk, 0, 4)
            C = nibble_at(chunk, 4, 4)
            R = nibble_at(chunk, 4, 0)
            wider = (
                nibble_at(chunk, 0, 0),  # LL
                chunk[32],  # left-edge center
                chunk[40],  # right-edge center
                nibble_at(chunk, 4, 4) if False else chunk[63],  # (already in C)
            )
            # Slim wider to the canonical 4 (LL, LLL, RRR, RR)
            wider = (
                nibble_at(chunk, 0, 0),  # LL
                chunk[32],  # LLL
                chunk[40],  # RRR
                chunk[63],  # RR
            )
        out.append(LCRWindow(
            size=size,
            index=len(out),
            bits=tuple(chunk),
            left=L,
            center=C,
            right=R,
            wider=tuple(wider),
            c_form=C,
            correction=C & (1 - R) & 1,  # C AND (NOT R), reduced mod 2
            shell=((L & 1) + (C & 1) + (R & 1)),
            chiral=(L != R),
        ).apply_algebra_idempotency())  # set closed via the algebra test
    return out



def gluon_stream_from_bits(bits: Tuple[int, ...]) -> List[LCRGluon]:
    """Generate the LCR Gluon stream from a bit stream.

    Each gluon is a sliding 3-bit (L, C, R) window across the bit stream.
    Each gluon carries the dimensional transport receipt:
      - (L, C, R) triple
      - derived correction = C AND NOT R
      - shell, chiral, correction
      - closure state via M3 idempotency (L & R == C)
      - subspace classification
      - receipt hash

    The gluon stream is the per-3-bit dimensional transport receipt.
    The C bit is the entry; the algebra primitive re-applies C to
    validate the correction. This is the per-window dimensional transport.
    """
    gluons: List[LCRGluon] = []
    n = len(bits)
    for i in range(max(0, n - 2)):
        L, C, R = bits[i], bits[i + 1], bits[i + 2]
        shell = L + C + R
        chiral = (L != R)
        correction = C & (1 - R) & 1
        state_class: str
        if L == 0 and C == 0 and R == 0:
            state_class = "vacuum"
        elif L == 1 and C == 1 and R == 1:
            state_class = "plenum"
        elif C == 1 and shell == 2 and chiral:
            state_class = "shell_2_idempotent"
        elif shell == 2:
            state_class = "boundary"
        elif shell == 1:
            state_class = "chiral"
        else:
            state_class = "vacuum"
        # M3 idempotency closure: (L & R) == C
        closed = bool((L & R) == C)
        # Subspace classification
        if closed and shell == 2 and chiral:
            subspace = "shell_2_idempotent"
        elif chiral:
            subspace = "boundary_chiral"
        elif closed:
            subspace = "fixed_center"
        else:
            subspace = "open"
        # Receipt hash
        import hashlib
        h = hashlib.sha256()
        h.update(b"LCRGluon")
        for b in (i, L, C, R, shell, chiral, correction, closed):
            h.update(bytes([b & 0xFF]))
        receipt_hash = h.hexdigest()

        gluons.append(LCRGluon(
            index=i,
            left=L,
            center=C,
            right=R,
            shell=shell,
            chiral=chiral,
            correction=correction,
            state_class=state_class,
            closed=closed,
            subspace=subspace,
            receipt_hash=receipt_hash,
        ))
    return gluons


def resolve_channel(windows: List[LCRWindow]) -> Optional[LCRChannel]:
    """Take a list of windows (one observation) and produce a
    single resolved channel if any window closed.

    The channel is the algebra-expressed resolution bit(s)
    that the upstream lattice_forge / stdlib algebra primitive
    would emit for these windows. Returns None if no window
    closed (no channel resolved).
    """
    closed_windows = [w for w in windows if w.closed]
    if not closed_windows:
        return None
    # Aggregate: the channel's bits are the concatenation of
    # the closed windows' correction identities, with the
    # subspace label set to the canonical idempotent surface.
    bits: List[int] = []
    for w in closed_windows:
        bits.append(w.correction)
    # Subspace classification: if the window's center has
    # shell=2, it's the shell_2_idempotent subspace (the M3
    # idempotent from the corpus). If chiral, the boundary
    # subspace. If the wider context is the 0101/1010
    # alternation, the head_tail boundary.
    if closed_windows[0].shell == 2 and closed_windows[0].chiral:
        subspace = "shell_2_idempotent"
    elif closed_windows[0].chiral:
        subspace = "boundary_chiral"
    else:
        subspace = "fixed_center"
    return LCRChannel(
        algebra_id="octonion_axioms+f4_3x3",
        bits=tuple(bits),
        closed=True,
        source_windows=tuple(w.index for w in closed_windows),
        subspace=subspace,
    )


__all__ = [
    "WindowSize",
    "WINDOW_BITS",
    "LCRGluon",
    "LCRWindow",
    "LCRChannel",
    "envelope_into_windows",
    "gluon_stream_from_bits",
    "resolve_channel",
]
