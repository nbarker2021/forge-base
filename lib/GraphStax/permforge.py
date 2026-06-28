"""
GraphStax PermForge — Superpermutation scheduler + C-enumeration normal form.

THE C-TERM NORMAL FORM
----------------------
The C term is ALWAYS dependent on the act of a requested enumeration into a
state. C is not a standing value: it is produced when an enumeration request
fires against a window. In normal form:

    Γ(s) = π_C( enum(r_i, W) )

where
    W      = the (L,C,R) window (flat 3-bit chain, unobserved)
    r_i    = enumeration request i — a cursor position on the superpermutation
             string (which ordering of the window's slots is being read NOW)
    enum   = the act of enumeration: collapses the flat chain into one of the
             8 chart states (the 2×2×2 cube)
    π_C    = projection onto the LR-podal invariant of the enumerated state

No request, no C. The request IS the observation; the superpermutation cursor
is the supervisor of which enumeration is currently being requested.

THE SUPERPERMUTATION CLAIM (N = D)
----------------------------------
A dimensional action graph for dimension N is the set of all N! orderings in
which N slots can be read off the tape. Serializing this graph naively costs
N·N! symbols (each permutation written out in full). A superpermutation is the
minimal string containing every permutation of N symbols as a substring — the
FULL COMPRESSION of the dimensional action graph onto a 1D tape, achieved by
maximal overlap sharing between consecutive enumeration requests.

    superperm(N) = compress( ActionGraph(D = N) )

The system reads dimensions via tape in slots; walking the superpermutation
IS visiting every possible dimensional reading exactly once, minimally.

THE n=4 → n=5 SPLIT (4D object → full 8D space)
------------------------------------------------
n=4:  24 permutations (= D4 root count = 24-cell vertices, the unique
      self-dual regular 4-polytope). Minimal superpermutation is UNIQUE,
      length 33, and PALINDROMIC — its own mirror. No chirality, no torsion:
      the 4D enumeration schedule has one canonical form.

n=5:  120 permutations. Minimal length 153, and there are EXACTLY 8 minimal
      solutions: 1 palindrome + 7 symmetry-broken "trees". 8 solutions =
      8 dimensions = the E8 lane count. The 4D object's schedule, lifted one
      symbol, demands the full 8D ambient space.

      The reversal involution (the SAME LR-podal involution that defines the
      gluon Γ) acts on the octad with 4 fixed points + 2 swapped pairs —
      the same orbit type as the 8 chart states under swap_LR (4 Lie
      conjugates fixed + 2 chiral pairs). Computed below at import time as
      N5_REVERSAL_ORBIT; this is a structural observation, recorded for the
      validation pass.

      Torsor effect: among the 8 minimals there is no canonical choice beyond
      the palindrome — the solution set is a homogeneous space under the
      symmetry action (relabeling × reversal). Choosing one solution = fixing
      a gauge. This is the GR torsor structure of the dimensional lift.

Donor provenance: schedule-spine primitives (n=4..8 supervisor cursors);
n=5 octad data (1_palindrome_7_trees layout, minimals found 2014).
Superpermutation strings are SUPERVISOR CURSORS — never ribbon content.
"""
import hashlib
import json
import math
from itertools import permutations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ─── Lookup tables (import-time, read-only) ────────────────────────────────────

# n=4: the unique minimal superpermutation. 33 chars, palindromic.
# Covers all 24 permutations of {1,2,3,4}.
SUPERPERM_N4: str = "123412314231243121342132413214321"
N4_LENGTH: int = 33
N4_PERM_COUNT: int = 24

# n=5: all 8 minimal superpermutations ("the octad"). 153 chars each.
# Layout: index 0 = the palindrome; indices 1-7 = the seven trees.
# Covers all 120 permutations of {1,2,3,4,5}.
N5_OCTAD: Tuple[str, ...] = (
    "123451234152341253412354123145231425314235142315423124531243512431524312543121345213425134215342135421324513241532413524132541321453214352143251432154321",
    "123451234152341253412354123145231425314235142315423124531243512431524312543121354213524135214352134521325413251432513425132451321543215342153241532145321",
    "123451234152341253412354123145231425314235142315421352413521435213452135421534215432154231245321453241532451325413251432513425132453124351243152431254312",
    "123451234152341253412354123145213425134215342135421345214352145321452314253142351423154231245312435124315243125432154325143254132451324153241352413254312",
    "123451234152341253412354132541352413542134521342513421534213541231452314253142351423154231245321435214325143215432145324153245132453124351243152431254312",
    "123451234152341253412354132514325134251324513254135241354213541231452134521435214532154321534215324153214523142531423514231542312453124351243152431254312",
    "123451324513425134521354213524135214352134512341523412534123541231452314253142351423154231245312435124315243125432153421532415321453215432514325413254312",
    "123451324153241352413254132451342513452134512341523412534123541231452314253142351423154213542153421543214532143521432514321542312453124351243152431254312",
)
SUPERPERM_N5: str = N5_OCTAD[0]      # the palindrome
N5_LENGTH: int = 153
N5_PERM_COUNT: int = 120
N5_OCTAD_LAYOUT: str = "1_palindrome_7_trees"


def _canon(s: str) -> str:
    """Canonical relabeling: first-seen symbols → 1,2,3,..."""
    m: Dict[str, str] = {}
    out: List[str] = []
    nxt = 1
    for ch in s:
        if ch not in m:
            m[ch] = str(nxt)
            nxt += 1
        out.append(m[ch])
    return "".join(out)


def _reversal_orbit(octad: Tuple[str, ...]) -> Dict[int, int]:
    """Where reversal+relabel sends each octad member. Computed at import."""
    canon_index = {_canon(s): i for i, s in enumerate(octad)}
    return {i: canon_index.get(_canon(s[::-1]), -1) for i, s in enumerate(octad)}


# The reversal involution's action on the octad.
# Result: {0:0, 1:1, 2:5, 3:7, 4:4, 5:2, 6:6, 7:3}
#   → 4 fixed points (0,1,4,6) + 2 swapped pairs (2↔5, 3↔7).
# Same orbit type as the 8 chart states under swap_LR:
#   4 Lie conjugates fixed + 2 chiral pairs.
N5_REVERSAL_ORBIT: Dict[int, int] = _reversal_orbit(N5_OCTAD)

N5_REVERSAL_FIXED: Tuple[int, ...] = tuple(
    i for i, j in N5_REVERSAL_ORBIT.items() if i == j
)
N5_REVERSAL_PAIRS: Tuple[Tuple[int, int], ...] = tuple(
    (i, j) for i, j in N5_REVERSAL_ORBIT.items() if i < j
)


# ─── External record loading (n=6..8 from field data, walk-up search) ─────────

_PKG_DIR = Path(__file__).resolve().parent

def _find_superperm_data() -> Optional[Path]:
    """Locate field superpermutation records by walking up from this package.
    Looks for CMPLX-PartsFactory-main/data/superpermutations."""
    for base in (_PKG_DIR, *_PKG_DIR.parents):
        cand = base / "CMPLX-PartsFactory-main" / "data" / "superpermutations"
        if cand.is_dir():
            return cand
    return None

_DATA_DIR: Optional[Path] = _find_superperm_data()
_RECORD_CACHE: Dict[int, Optional[Dict[str, Any]]] = {}


def load_record(n: int) -> Optional[Dict[str, Any]]:
    """Load a superpermutation record. n=4,5 from embedded tables; n=6..8
    from field data if locatable (provenance_class='record', not minimal)."""
    if n in _RECORD_CACHE:
        return _RECORD_CACHE[n]
    rec: Optional[Dict[str, Any]] = None
    if n == 4:
        rec = {"n": 4, "status": "validated", "superpermutation": SUPERPERM_N4,
               "length": N4_LENGTH, "permutation_count": N4_PERM_COUNT,
               "palindrome": True, "provenance_class": "minimal"}
    elif n == 5:
        rec = {"n": 5, "status": "validated", "superpermutation": SUPERPERM_N5,
               "length": N5_LENGTH, "permutation_count": N5_PERM_COUNT,
               "alternates": list(N5_OCTAD), "octad_layout": N5_OCTAD_LAYOUT,
               "provenance_class": "minimal"}
    elif _DATA_DIR is not None:
        path = _DATA_DIR / f"n{n}.json"
        if path.is_file():
            rec = json.loads(path.read_text(encoding="utf-8"))
    _RECORD_CACHE[n] = rec
    return rec


def superperm(n: int) -> str:
    """Validated superpermutation string for n. Raises if unavailable."""
    rec = load_record(n)
    if rec is None or str(rec.get("status", "")).lower() != "validated":
        raise ValueError(f"superpermutation n={n} not available/validated")
    sp = rec.get("superpermutation") or rec.get("superperm")
    if not sp:
        raise ValueError(f"superpermutation n={n} record has no string")
    return str(sp)


# ─── Coverage verification (pure functions) ───────────────────────────────────

def coverage_check(s: str, n: int) -> bool:
    """True when every permutation of 1..n appears as a length-n substring."""
    if len(s) < n:
        return False
    needed = {"".join(p) for p in permutations(str(i) for i in range(1, n + 1))}
    found = {s[i:i + n] for i in range(len(s) - n + 1)}
    return needed <= found


def coverage_checksum(s: str, n: int) -> str:
    """Stable short checksum of the coverage set."""
    perms = sorted("".join(p) for p in permutations(str(i) for i in range(1, n + 1)))
    covered = sorted({s[i:i + n] for i in range(len(s) - n + 1)})
    payload = json.dumps({"perms": perms, "covered": covered}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ─── The C-term enumeration normal form ───────────────────────────────────────

def enumeration_request(cursor: int, n: int = 4) -> Dict[str, Any]:
    """One enumeration request r_i: the act that produces C.

    The supervisor cursor at position i requests the reading of one slot
    (the digit) within the currently active permutation window (the length-n
    substring ending at the cursor). This is the normal-form decomposition:

        request   = (cursor, active_window)
        enum      = the window IS the enumerated ordering of slot reads
        slot      = which dimension/slot the tape reads NOW

    C exists only as a product of this request — Γ(s) = π_C(enum(r_i, W)).
    """
    s = superperm(n)
    i = cursor % len(s)
    slot = int(s[i])
    win_start = max(0, i - n + 1)
    window = s[win_start:i + 1]
    is_full_perm = len(set(window)) == n and len(window) == n
    return {
        "cursor":         i,
        "slot":           slot,                  # the dimension being read NOW
        "window":         window,                # the active enumeration
        "is_permutation": is_full_perm,          # window enumerates all n slots
        "n":              n,
        "normal_form":    "Γ(s) = π_C(enum(r_i, W)) — no request, no C",
    }


def c_normal_form(L: int, C: int, R: int, cursor: int, n: int = 4) -> Dict[str, Any]:
    """The full expression: an (L,C,R) window enumerated by request r_cursor.

    The flat 3-bit chain (L,C,R) only becomes a chart state when an
    enumeration request fires. The returned record carries both halves:
    the request (from the superpermutation supervisor) and the enumerated
    state with its T_EMISSION product.
    """
    from GraphStax.rule30 import profile
    req = enumeration_request(cursor, n=n)
    state = (L, C, R)
    p = profile(state)
    return {
        "request":       req,
        "state":         state,
        "gluon":         p["gluon"],             # Γ(s) = C — exists because r fired
        "emission_bit":  p["emission_bit"],
        "emission_path": p["emission_path"],
        "state_class":   p["state_class"],
        "expression":    f"Γ({state}) = π_C(enum(r_{req['cursor']}, W)) = {p['gluon']}",
    }


# ─── Supervisor cursor / scheduler ────────────────────────────────────────────

class SuperPermScheduler:
    """Walks a superpermutation as a supervisor cursor, dispatching slot reads.

    Given n items (services, ribbon slots, dimensions), the schedule visits
    them in superpermutation order — every possible ordering of the n items
    appears exactly once as a contiguous block, with maximal overlap between
    consecutive orderings. This IS the compressed dimensional action graph.

    The cursor string is never content: it is the supervisor of which
    enumeration request fires next.
    """

    def __init__(self, n: int = 4):
        self.n = n
        self._s = superperm(n)
        self._cursor = 0

    def step(self) -> Dict[str, Any]:
        """Advance one position; return the enumeration request fired."""
        req = enumeration_request(self._cursor, n=self.n)
        self._cursor += 1
        return req

    def reset(self) -> None:
        self._cursor = 0

    def schedule(self, items: List[Any]) -> Iterable[Tuple[int, Any]]:
        """Yield (cursor, item) pairs for one full pass of the cursor string.
        items must have length n; item k-1 is dispatched when slot k fires."""
        if len(items) != self.n:
            raise ValueError(f"need exactly {self.n} items, got {len(items)}")
        for i, ch in enumerate(self._s):
            yield i, items[int(ch) - 1]

    def walk(self, length: Optional[int] = None) -> Iterable[int]:
        """Yield slot numbers from the cursor string (cyclic if length > len)."""
        s = self._s
        limit = len(s) if length is None else int(length)
        for i in range(limit):
            yield int(s[i % len(s)])

    @property
    def length(self) -> int:
        return len(self._s)

    @property
    def cursor(self) -> int:
        return self._cursor

    def status(self) -> Dict[str, Any]:
        return {"n": self.n, "length": len(self._s), "cursor": self._cursor,
                "palindrome": self._s == self._s[::-1]}


# ─── The dimensional claims (computed exhibits) ───────────────────────────────

def action_graph_compression(n: int) -> Dict[str, Any]:
    """The N=D compression claim, with numbers.

    The dimensional action graph at D=n has n! vertices (orderings of n slot
    reads). Naive serialization costs n·n! symbols. The superpermutation is
    the minimal covering walk — full compression via overlap sharing.
    """
    sp = superperm(n)
    perm_count = math.factorial(n)
    naive = n * perm_count
    return {
        "n":                  n,
        "dimension_D":        n,
        "action_graph_vertices": perm_count,      # n! orderings
        "naive_serialization":   naive,           # n·n! symbols
        "superperm_length":      len(sp),
        "compression_ratio":     round(naive / len(sp), 4),
        "coverage_valid":        coverage_check(sp, n),
        "claim": (
            f"superperm({n}) is the full compression of ActionGraph(D={n}): "
            f"{perm_count} dimensional readings serialized in {len(sp)} tape "
            f"symbols instead of {naive} (ratio {naive / len(sp):.2f}x), "
            "as the system reads dimensions via tape in slots."
        ),
    }


def dimensional_split() -> Dict[str, Any]:
    """The n=4 → n=5 split exhibit: 4D object → full 8D space + torsor.

    All quantities computed from the embedded tables at call time.
    Structural correspondences are recorded as observations for the
    validation pass — not as validated claims.
    """
    n4_palindrome = SUPERPERM_N4 == SUPERPERM_N4[::-1]
    octad_palindromes = [i for i, s in enumerate(N5_OCTAD) if s == s[::-1]]

    return {
        "n4": {
            "permutations":   N4_PERM_COUNT,       # 24 = D4 roots = 24-cell vertices
            "minimal_length": N4_LENGTH,
            "solution_count": 1,                    # unique minimal
            "palindromic":    n4_palindrome,        # self-mirror: no torsion
            "geometry":       "24 permutations = 24 D4 roots = 24-cell (4D, self-dual)",
        },
        "n5": {
            "permutations":   N5_PERM_COUNT,        # 120
            "minimal_length": N5_LENGTH,
            "solution_count": len(N5_OCTAD),        # 8 = E8 lane count
            "octad_layout":   N5_OCTAD_LAYOUT,      # 1 palindrome + 7 trees
            "palindrome_indices": octad_palindromes,
            "reversal_orbit": dict(N5_REVERSAL_ORBIT),
            "reversal_fixed": list(N5_REVERSAL_FIXED),   # 4 fixed
            "reversal_pairs": [list(p) for p in N5_REVERSAL_PAIRS],  # 2 pairs
            "geometry":       "8 minimal solutions = 8 dimensions = E8 lanes",
        },
        "split": {
            "statement": (
                "The n=4→n=5 split is the dimensional lift: the 4D object "
                "(24-cell / D4, unique self-mirrored schedule) demands the "
                "full 8D space (octad of schedules = E8 lanes) when one more "
                "symbol enters the enumeration."
            ),
            "torsor": (
                "The 8 minimals form a homogeneous space under relabeling × "
                "reversal — no canonical origin among them. Choosing one is a "
                "gauge choice: the GR torsor effect of the lift."
            ),
            "gluon_correspondence": (
                "Reversal acts on the octad with 4 fixed + 2 swapped pairs — "
                "the same orbit type as the 8 chart states under swap_LR "
                "(4 Lie conjugates fixed + 2 chiral pairs), the involution "
                "that defines the gluon Γ(s)=C. Recorded as structural "
                "observation pending validation."
            ),
        },
    }


# ═══════════════════════════════════════════════════════════════════════
# Paper 32 machinery — the N+1 chart walk and the n=8 record attempt
# Methods: classic recursive construction; lower bound of Houston-Pantone-
# Vatter (2014, formalizing the anonymous 2011 bound); upper-bound
# construction of Egan (2018, building on Houston's 2014 minimality break
# at n=6); record data curated per Johnston; n=5 minimality by Chaffin.
# Nothing reinvented — their methods, carried inside this format.
# ═══════════════════════════════════════════════════════════════════════

def lower_bound(n: int) -> int:
    """L(n) ≥ n! + (n−1)! + (n−2)! + n − 3  (Houston–Pantone–Vatter form).
    Valid for n ≥ 3; for n < 3 the trivial values are exact."""
    if n < 3:
        return (1, 1, 3)[n] if n <= 2 else 0
    return (math.factorial(n) + math.factorial(n - 1)
            + math.factorial(n - 2) + n - 3)


def chart_walk_upper(n: int) -> int:
    """The classic recursive-construction length: Σ_{k=1}^{n} k!.
    This is the pure N→N+1 chart walk — each lift visits every permutation
    of the previous scale and threads the new symbol through it."""
    return sum(math.factorial(k) for k in range(1, n + 1))


def egan_upper(n: int) -> int:
    """Egan's construction length: n! + (n−1)! + (n−2)! + (n−3)! + n − 3.
    Beats the chart walk from n=7 on; equals it at n=6 (873)."""
    if n < 4:
        return chart_walk_upper(n)
    return (math.factorial(n) + math.factorial(n - 1) + math.factorial(n - 2)
            + math.factorial(n - 3) + n - 3)


def visit_order(s: str, n: int) -> List[str]:
    """The permutations of 1..n in first-visit order along s — the sequence
    of local charts the cursor enters."""
    seen: List[str] = []
    seen_set: set = set()
    for i in range(len(s) - n + 1):
        w = s[i:i + n]
        if len(set(w)) == n and w not in seen_set and all(c.isdigit() for c in w):
            seen.append(w)
            seen_set.add(w)
    return seen


def recursive_step(s_n: str, n: int) -> str:
    """One N→N+1 lift of the classic construction.

    For each permutation p visited by s_n (in visit order), emit the block
    p·(n+1)·p, then merge consecutive blocks with maximal overlap. The new
    symbol n+1 is threaded through every local chart of scale n — this is
    the dimensional lift made literal: the chart at scale n becomes the
    sheet of the (n+1)-cursor.
    """
    perms = visit_order(s_n, n)
    sym = str(n + 1)
    blocks = [p + sym + p for p in perms]
    out = blocks[0]
    for b in blocks[1:]:
        k = min(len(out), len(b) - 1)
        while k > 0 and out[-k:] != b[:k]:
            k -= 1
        out += b[k:]
    return out


def recursive_construction(n: int) -> str:
    """Walk the full chart ladder 1 → n. Length is Σ_{k=1}^{n} k! at every
    rung (verified by the Paper 32 verifier)."""
    s = "1"
    for k in range(1, n):
        s = recursive_step(s, k)
    return s


def verify_record(n: int) -> Dict[str, Any]:
    """Verify a shipped superpermutation record against full coverage and
    the bounds ladder. This is the verifier — it validates the string,
    not the provenance claims."""
    rec = load_record(n)
    if rec is None:
        return {"n": n, "status": "missing"}
    sp = str(rec.get("superpermutation") or "")
    valid = coverage_check(sp, n) if sp else False
    return {
        "n":               n,
        "status":          rec.get("status"),
        "length":          len(sp),
        "coverage_valid":  valid,
        "lower_bound":     lower_bound(n),
        "chart_walk":      chart_walk_upper(n),
        "egan_upper":      egan_upper(n),
        "meets_egan":      len(sp) <= egan_upper(n),
        "gap_to_lower":    len(sp) - lower_bound(n),
        "provenance":      rec.get("provenance_class"),
    }


def n8_attempt() -> Dict[str, Any]:
    """The Paper 32 n=8 exhibit, executed live.

    1. Build the chart-walk construction 1→8 (Σk! = 46233) and verify
       full coverage of all 40320 permutations.
    2. Verify the shipped n=8 record (46205) — full coverage check.
    3. Confirm 46205 = egan_upper(8) exactly: the record IS Egan's
       construction length.
    4. Report the residual: egan_upper(n) − lower_bound(n) = (n−3)!,
       so at n=8 the open window below the best construction is 5! = 120.
    """
    built = recursive_construction(8)
    built_valid = coverage_check(built, 8)

    rec = verify_record(8)

    return {
        "chart_walk": {
            "length":          len(built),
            "expected":        chart_walk_upper(8),     # 46233
            "matches":         len(built) == chart_walk_upper(8),
            "coverage_valid":  built_valid,
        },
        "record": rec,                                   # shipped 46205
        "egan_construction": {
            "formula":         "n! + (n-1)! + (n-2)! + (n-3)! + n - 3",
            "value":           egan_upper(8),            # 46205
            "record_is_egan":  rec.get("length") == egan_upper(8),
            "saves_vs_chart_walk": chart_walk_upper(8) - egan_upper(8),  # 28
        },
        "open_window": {
            "lower_bound":     lower_bound(8),           # 46085
            "gap":             egan_upper(8) - lower_bound(8),           # 120
            "gap_identity":    "(n-3)! = 5! = 120",
            "note": (
                "Search has closed part of this window at smaller n "
                "(n=6: −1 below the formula; n=7: −2). At n=8 the window "
                "of width (n−3)! = 120 below the Egan construction is open."
            ),
        },
    }


def power_of_ten_walk() -> Dict[str, Any]:
    """The scale ladder N=1..8: each N+1 solve walks up the power-of-ten
    scale, and every effect in the complexity of finding the minimal lives
    inside the local charts (the length-n windows).

    Columns per rung:
      length        — best available (minimal for n≤5, record for n≥6)
      log10         — the power-of-ten position
      solutions     — count of minimals where known (1 at n=4, 8 at n=5)
      chart_status  — what the local charts admit at this scale
      mdhg_level    — the sheet hierarchy rung the cursor occupies
    """
    mdhg = ("grain", "dust", "triad", "block", "cluster",
            "domain", "region", "planet", "universe")
    best = {1: 1, 2: 3, 3: 9, 4: 33, 5: 153}
    solutions = {1: 1, 2: 1, 3: 2, 4: 1, 5: 8}
    chart_notes = {
        1: "trivial — a single chart",
        2: "one overlap, forced",
        3: "weight-1/2 edges only; 2 minimals",
        4: "UNIQUE minimal, palindromic — no torsion at 4D",
        5: "octad: 1 palindrome + 7 trees = 8 = E8 lanes; minimality proven by exhaustive search",
        6: "minimality open below 872; chart walk 873 broken by SAT search −1",
        7: "construction 5908; search reached 5906; window open",
        8: "Egan construction 46205; window of (n−3)!=120 above lower bound open",
    }
    rungs = []
    for n in range(1, 9):
        if n <= 5:
            length = best[n]
        else:
            rec = load_record(n)
            length = int(rec["length"]) if rec else egan_upper(n)
        rungs.append({
            "n":            n,
            "length":       length,
            "log10":        round(math.log10(length), 4) if length > 0 else 0.0,
            "lower_bound":  lower_bound(n),
            "chart_walk":   chart_walk_upper(n),
            "egan_upper":   egan_upper(n),
            "solutions":    solutions.get(n, "open"),
            "chart_status": chart_notes[n],
            "mdhg_level":   mdhg[n - 1],
        })
    return {
        "claim": (
            "Solving each N+1 is one rung up the power-of-ten ladder "
            "(log10 grows by ~log10(n) per rung — factorial walk). All "
            "effects in minimal-finding complexity are chart-local: the "
            "uniqueness at n=4, the octad at n=5, and the open search "
            "windows at n≥6 are properties of what the length-n windows "
            "(the local charts) admit, not of the global string."
        ),
        "rungs": rungs,
    }


# ─── Module-level singleton + forwarding ──────────────────────────────────────

scheduler = SuperPermScheduler(n=4)

def step() -> Dict[str, Any]:
    return scheduler.step()

def walk(length: Optional[int] = None) -> Iterable[int]:
    return scheduler.walk(length)
