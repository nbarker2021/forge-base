"""
Binary Boundary Adapter (BBA)
==============================

Takes the last N bits of any binary sequence — unaltered — and produces
the HEAD and TAIL Lie conjugate states that bound it, along with a full
structural characterisation of the interior.

The adapter never modifies the input.  It identifies the natural attractor
boundaries of the sequence within the lattice-forge framework and reports
what the framework sees at every interior position.

Primary interface
-----------------
    result = adapt(data)            # list, bytes, int, hex/binary string
    BinaryBoundaryAdapter(window=16).adapt(data)   # stateful / streaming

Outputs
-------
    head          — entry Lie conjugate (the rest state the sequence came from)
    tail          — exit  Lie conjugate (the rest state the sequence is heading to)
    matched       — True if head and tail are on the same oloid circle
    arc_type      — 'closed_arc' | 'crossing_arc'
    matching_tail — what tail would need to be for a closed arc
    cascade_dist  — {0: n_equilibrium, 1: n_linear, 2: n_carry}
    interior      — per-position structural record
    summary       — aggregate statistics

Cascade levels
--------------
    0  state already at Lie conjugate attractor — bar at rest, no computation
    1  C=0 or (C=1 and R=1)  — any linear CA (Rule 90 family) suffices
    2  C=1 and R=0           — frustrated bond / carry; correction sum needed

Physical interpretation
-----------------------
    L = fermionic read wire  (antisymmetric, negative spin, reads data)
    C = gluon               (centroid invariant + live color mediator, superposed)
    R = bosonic write wire   (symmetric, positive spin, writes data)

    Lie conjugate (L=R): read-write balance — the bar is at zero, the
    rollout of this digit is complete, carry resolved.

    Correction firing (C=1, R=0): gluon active but write channel silent —
    the frustrated bond that no linear rule can explain; only Rule 30
    handles this correctly via NOT(L) when C=1.

    The cascade level of a window measures its carry density: how deeply
    inside an active digit rollout the sequence currently sits.

Citation
--------
    T_WRAP     (Theorem C, Paper 15): ≤3 S3 steps to Lie conjugate, always.
    T_EMISSION (Theorem A, Paper 15): bit = NOT(L) if C=1 else L XOR R.
    T_BIJECTIVE (Paper 01)          : both spin states in shell=2 forward tape.
    Paper 16 (this submission)      : The Digit Rollout — universality argument.
"""

from __future__ import annotations

from typing import Any

from .centroid_voa import (
    anneal_to_lie_conjugate,
    voa_weight,
    LIE_CONJUGATES,
    TRUE_VACUA,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CIRCLE_F: frozenset = frozenset({(0, 1, 0), (1, 1, 1)})   # gluon-bound L=R
CIRCLE_P: frozenset = frozenset({(0, 0, 0), (1, 0, 1)})   # gluon-free  L=R

CORRECTION_FIRING: frozenset = frozenset(
    (L, C, R)
    for L in (0, 1) for C in (0, 1) for R in (0, 1)
    if C == 1 and R == 0
)

# Pre-built 256-rule lookup table.
# _RULE_TABLE[rule_number][k] where k = (L<<2)|(C<<1)|R
_RULE_TABLE: list[tuple[int, ...]] = [
    tuple((n >> k) & 1 for k in range(8))
    for n in range(256)
]


# ---------------------------------------------------------------------------
# Core formulas
# ---------------------------------------------------------------------------

def _emit(L: int, C: int, R: int) -> int:
    """T_EMISSION (Theorem A): shadow = NOT(L) if C=1 else L XOR R."""
    return (1 - L) if C == 1 else (L ^ R)


def _circle(state: tuple[int, int, int]) -> str:
    return "F" if state in CIRCLE_F else "P"


def _partner(state: tuple[int, int, int]) -> tuple[int, int, int]:
    """The other element on the same circle as the anneal target of `state`."""
    target = anneal_to_lie_conjugate(state)["final"]
    circle = CIRCLE_F if target in CIRCLE_F else CIRCLE_P
    for s in circle:
        if s != target:
            return s
    return target


def cascade_level(state: tuple[int, int, int]) -> int:
    """
    Cascade level: how deep in the fallback hierarchy this state sits.

    0 — already at Lie conjugate; bar at rest, rollout complete
    1 — linear CA sufficient (C=0 or C=1 and R=1)
    2 — carry / frustrated bond (C=1 and R=0); correction sum required
    """
    if state in LIE_CONJUGATES:
        return 0
    return 1


def emission_level(state: tuple[int, int, int]) -> int:
    """Return 2 when Rule 30's `C AND NOT(R)` correction fires, else 1."""
    return 2 if state in CORRECTION_FIRING else 1


def rules_consistent_with(state: tuple[int, int, int], shadow: int) -> int:
    """
    Count of the 256 CA rules whose output at `state` equals `shadow`.
    Always 128 (half agree, half disagree at any single state).
    Returned as a count so callers can verify the 128/128 split.
    """
    k = (state[0] << 2) | (state[1] << 1) | state[2]
    return sum(1 for n in range(256) if _RULE_TABLE[n][k] == shadow)


# ---------------------------------------------------------------------------
# Input normalisation
# ---------------------------------------------------------------------------

def _to_bits(data: Any, last_n: int | None = None) -> list[int]:
    """
    Normalise any binary-flavoured input to a list of {0, 1} integers.

    Accepted:
        list / tuple  — values coerced with & 1
        bytes         — big-endian bit expansion
        int  (≥ 0)    — big-endian bit expansion
        str           — hex string (contains a–f) or binary string (0/1 only)
    """
    if isinstance(data, (list, tuple)):
        bits = [int(b) & 1 for b in data]

    elif isinstance(data, (bytes, bytearray)):
        bits = []
        for byte in data:
            for shift in range(7, -1, -1):
                bits.append((byte >> shift) & 1)

    elif isinstance(data, int):
        if data < 0:
            raise ValueError("negative integers are not supported")
        if data == 0:
            bits = [0]
        else:
            tmp, bits = data, []
            while tmp:
                bits.append(tmp & 1)
                tmp >>= 1
            bits.reverse()

    elif isinstance(data, str):
        s = data.strip().lower().replace(" ", "").replace("0x", "").replace("_", "")
        if all(c in "0123456789abcdef" for c in s) and any(c in "abcdef" for c in s):
            val = int(s, 16)
            bits = [(val >> i) & 1 for i in range(len(s) * 4 - 1, -1, -1)]
        else:
            bits = [int(c) for c in s if c in ("0", "1")]
    else:
        raise TypeError(f"unsupported type: {type(data)!r}")

    if last_n is not None and len(bits) > last_n:
        bits = bits[-last_n:]
    return bits


# ---------------------------------------------------------------------------
# Core adaptation function
# ---------------------------------------------------------------------------

def adapt(data: Any, window: int = 16) -> dict[str, Any]:
    """
    Adapt any binary sequence into the lattice-forge framework.

    Takes the last `window` bits of `data`, unaltered.
    Returns the HEAD/TAIL boundaries and a full interior characterisation.

    Parameters
    ----------
    data   : list[int], bytes, int, hex string, or binary string
    window : number of tail bits to use (default 16, minimum 3)

    Returns
    -------
    dict with keys:
        bits, head, tail, head_circle, tail_circle,
        matched, arc_type, matching_tail,
        head_steps, tail_steps,
        interior, summary
    """
    bits = _to_bits(data, last_n=window)
    n = len(bits)
    if n < 3:
        raise ValueError(f"Binary Boundary Adapter requires at least 3 bits; got {n}")

    entry = (bits[0],  bits[1],  bits[2])
    exit_ = (bits[-3], bits[-2], bits[-1])

    head_ann = anneal_to_lie_conjugate(entry)
    tail_ann = anneal_to_lie_conjugate(exit_)

    head = head_ann["final"]
    tail = tail_ann["final"]
    hc   = _circle(head)
    tc   = _circle(tail)

    matched       = (hc == tc)
    arc_type      = "closed_arc" if matched else "crossing_arc"
    matching_tail = tail if matched else _partner(head)

    # Extend with one bit of boundary context from HEAD (left) and TAIL (right)
    # so every interior position has full (L, C, R) context.
    ext = [head[2]] + list(bits) + [tail[0]]

    interior: list[dict[str, Any]] = []
    voa_dist: dict[int, int]       = {}
    cascade_dist: dict[int, int]   = {0: 0, 1: 0}
    emission_dist: dict[int, int]  = {1: 0, 2: 0}
    lie_count = vacuum_count = corr_count = arch_total = 0

    for i in range(1, len(ext) - 1):
        L, C, R = ext[i - 1], ext[i], ext[i + 1]
        s = (L, C, R)

        shadow = _emit(L, C, R)
        w      = voa_weight(s)
        in_lie = s in LIE_CONJUGATES
        in_vac = s in TRUE_VACUA
        corr   = s in CORRECTION_FIRING
        ann    = anneal_to_lie_conjugate(s)
        cl     = cascade_level(s)
        el     = emission_level(s)

        voa_dist[w]      = voa_dist.get(w, 0) + 1
        cascade_dist[cl] = cascade_dist.get(cl, 0) + 1
        emission_dist[el] = emission_dist.get(el, 0) + 1
        if in_lie:  lie_count    += 1
        if in_vac:  vacuum_count += 1
        if corr:    corr_count   += 1
        arch_total += ann["steps"]

        interior.append({
            "pos":             i - 1,
            "state":           s,
            "L":               L,
            "C":               C,
            "R":               R,
            "shadow":          shadow,
            "voa_weight":      w,
            "in_lie":          in_lie,
            "in_vacuum":       in_vac,
            "carry":           corr,       # C=1 and R=0: frustrated bond
            "corr_fires":      corr,       # compatibility alias
            "anneal_steps":    ann["steps"],
            "anneal_target":   ann["final"],
            "cascade_level":   cl,
            "emission_level":  el,
        })

    shadow_seq = [p["shadow"] for p in interior]

    summary: dict[str, Any] = {
        "n_bits":             n,
        "head":               head,
        "tail":               tail,
        "head_circle":        hc,
        "tail_circle":        tc,
        "matched":            matched,
        "arc_type":           arc_type,
        "matching_tail":      matching_tail,
        "head_steps":         head_ann["steps"],
        "tail_steps":         tail_ann["steps"],
        # Cascade profile
        "cascade_dist":       cascade_dist,
        "emission_dist":      emission_dist,
        "carry_density":      corr_count / n,  # fraction needing correction
        "emission_linear_fraction": emission_dist[1] / n,
        "linear_fraction":    cascade_dist[1] / n,
        "equilibrium_fraction": cascade_dist[0] / n,
        # Structural counts
        "lie_contact_count":     lie_count,
        "lie_contact_fraction":  lie_count / n,
        "vacuum_count":          vacuum_count,
        "vacuum_fraction":       vacuum_count / n,
        "carry_count":           corr_count,
        "arch_mean":             arch_total / n,
        "voa_weight_dist":       voa_dist,
        "shadow_sequence":       shadow_seq,
        "entry_triad":           entry,
        "exit_triad":            exit_,
    }

    return {
        "bits":          bits,
        "head":          head,
        "tail":          tail,
        "head_circle":   hc,
        "tail_circle":   tc,
        "matched":       matched,
        "arc_type":      arc_type,
        "matching_tail": matching_tail,
        "head_steps":    head_ann["steps"],
        "tail_steps":    tail_ann["steps"],
        "interior":      interior,
        "summary":       summary,
    }


# ---------------------------------------------------------------------------
# Stateful class — for streaming or repeated adaptation
# ---------------------------------------------------------------------------

class BinaryBoundaryAdapter:
    """
    Stateful wrapper around `adapt()`.

    Useful when processing a stream of windows: each call to `.adapt()`
    records the result and exposes aggregate carry-density trends over time.

    Usage
    -----
        bba = BinaryBoundaryAdapter(window=16)
        r   = bba.adapt(data)
        bba.print_last()
        print(bba.carry_trend())
    """

    def __init__(self, window: int = 16) -> None:
        self.window   = window
        self._history: list[dict[str, Any]] = []

    def adapt(self, data: Any) -> dict[str, Any]:
        """Adapt `data` and record the result."""
        result = adapt(data, window=self.window)
        self._history.append(result)
        return result

    def last(self) -> dict[str, Any] | None:
        """Return the most recent adaptation result."""
        return self._history[-1] if self._history else None

    def carry_trend(self) -> dict[str, Any]:
        """
        Aggregate carry density across all adaptations so far.

        Returns the mean carry_density, the min, and the max,
        plus the arc_type distribution (closed vs crossing).
        """
        if not self._history:
            return {"n_adaptations": 0}

        densities  = [r["summary"]["carry_density"]  for r in self._history]
        arc_types  = [r["arc_type"]                   for r in self._history]
        closed     = sum(1 for a in arc_types if a == "closed_arc")

        return {
            "n_adaptations":       len(self._history),
            "mean_carry_density":  sum(densities) / len(densities),
            "min_carry_density":   min(densities),
            "max_carry_density":   max(densities),
            "closed_arc_count":    closed,
            "crossing_arc_count":  len(self._history) - closed,
            "closed_arc_fraction": closed / len(self._history),
        }

    def print_last(self) -> None:
        """Pretty-print the most recent adaptation."""
        r = self.last()
        if r is None:
            print("No adaptations yet.")
            return
        print_adaptation(r)

    def reset(self) -> None:
        """Clear adaptation history."""
        self._history.clear()


# ---------------------------------------------------------------------------
# Convenience entry points
# ---------------------------------------------------------------------------

def from_bytes(data: bytes, window: int = 16) -> dict[str, Any]:
    """Adapt the last `window` bits of a bytes object."""
    return adapt(data, window=window)


def from_hex(hex_str: str, window: int = 16) -> dict[str, Any]:
    """Adapt the last `window` bits of a hex-encoded string."""
    return adapt(hex_str, window=window)


def from_int(value: int, window: int = 16) -> dict[str, Any]:
    """Adapt the last `window` bits of a non-negative integer."""
    return adapt(value, window=window)


def from_file(path: str, window: int = 16) -> dict[str, Any]:
    """Adapt the last `window` bits of any file."""
    import pathlib
    return from_bytes(pathlib.Path(path).read_bytes(), window=window)


# ---------------------------------------------------------------------------
# Pretty printer
# ---------------------------------------------------------------------------

def print_adaptation(result: dict[str, Any]) -> None:
    s  = result["summary"]
    cd = s["cascade_dist"]

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║          BINARY BOUNDARY ADAPTER                        ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  input  ({s['n_bits']} bits): {''.join(str(b) for b in result['bits'])}")
    print()
    print(f"  HEAD  {result['head']}  circle={result['head_circle']}  "
          f"anneal={result['head_steps']} step{'s' if result['head_steps'] != 1 else ' '}")
    print(f"  TAIL  {result['tail']}  circle={result['tail_circle']}  "
          f"anneal={result['tail_steps']} step{'s' if result['tail_steps'] != 1 else ' '}")
    print()
    match_str = "✓ MATCHED" if result["matched"] else "✗ CROSSING"
    print(f"  arc type     : {result['arc_type']}  {match_str}")
    if not result["matched"]:
        print(f"  matching tail: {result['matching_tail']}  "
              f"(needed for closed arc)")
    print()
    print(f"  cascade      : "
          f"L0={cd[0]} equilibrium  "
          f"L1={cd[1]} linear-CA  "
          f"L2={cd[2]} carry/correction")
    print(f"  carry density: {s['carry_density']:.1%}  "
          f"({'high' if s['carry_density'] > 0.3 else 'low'} — "
          f"{'deep in active rollout' if s['carry_density'] > 0.3 else 'near equilibrium'})")
    print(f"  lie contacts : {s['lie_contact_count']}/{s['n_bits']}  "
          f"({s['lie_contact_fraction']:.1%})")
    print(f"  true vacua   : {s['vacuum_count']}/{s['n_bits']}  "
          f"({s['vacuum_fraction']:.1%})")
    print(f"  arch mean    : {s['arch_mean']:.2f}")
    print(f"  VOA dist     : {dict(sorted(s['voa_weight_dist'].items()))}")
    print()
    print(f"  shadow seq   : {''.join(str(b) for b in s['shadow_sequence'])}")
    print()
    print(f"  {'pos':>3}  {'L C R':5}  {'voa':>3}  {'shd':>3}  "
          f"{'lie':>3}  {'cry':>3}  {'ann':>3}  {'L#':>2}")
    print("  " + "─" * 42)
    for p in result["interior"]:
        print(
            f"  {p['pos']:3d}  {p['L']} {p['C']} {p['R']}  "
            f"  {p['voa_weight']:3d}  "
            f"{p['shadow']:3d}  "
            f"{'●' if p['in_lie'] else '·':>3}  "
            f"{'▲' if p['carry'] else '·':>3}  "
            f"{p['anneal_steps']:3d}  "
            f"{p['cascade_level']:2d}"
        )
    print("  " + "─" * 42)
    print("  L=fermionic read  C=gluon  R=bosonic write")
    print("  ● lie contact  ▲ carry (C=1,R=0)  L#=cascade level")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    USAGE = """\
Binary Boundary Adapter
Usage:
  python -m lattice_forge.binary_boundary_adapter <data> [window]

Arguments:
  data    hex string, binary string, or decimal integer
  window  number of tail bits to frame (default: 16)

Examples:
  python -m lattice_forge.binary_boundary_adapter deadbeefcafe1234
  python -m lattice_forge.binary_boundary_adapter 1011001001110100 16
  python -m lattice_forge.binary_boundary_adapter 0xff 8
  python -m lattice_forge.binary_boundary_adapter 12345 16
"""

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0)

    raw    = sys.argv[1]
    window = int(sys.argv[2]) if len(sys.argv) > 2 else 16

    # Accept plain decimal integers too
    try:
        raw_parsed: Any = raw
        if raw.lstrip("-").isdigit():
            raw_parsed = int(raw)
    except ValueError:
        pass

    try:
        result = adapt(raw_parsed, window=window)
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    print_adaptation(result)
