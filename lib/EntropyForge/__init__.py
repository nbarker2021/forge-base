"""EntropyForge — Rule 30 center-column entropy with VOA partition receipts.

Distilled from product_entropy (historical_pastworks) into the forge ring.
Paper binding: CQE-paper-12 (CA Prediction Surface). The paper-bound object
is the canonical single-cell Rule 30 center column; the seeded engine is the
product surface built on top of it.

Adjudicated divergence from the source product: product_entropy seeded only
the syndrome chain while always evolving the canonical single-cell state.
EntropyForge seeds the CA initial window itself (SHA-256 expanded), so
distinct seeds give distinct streams. canonical=True preserves the
paper-bound single-cell object.

Stdlib only.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

RULE_NUMBER = 30
MONSTER_SCALAR = 47 * 59 * 71  # 196883

# VOA seed partition Z(q) = 2q^0 + 6q^5: 2 vacua + 6 excited states
VOA_PARTITION = {0: 2, 5: 6}

CHART_STATES: list[tuple[int, int, int]] = [
    (L, C, R) for L in (0, 1) for C in (0, 1) for R in (0, 1)
]

TRUE_VACUA = {(0, 0, 0), (1, 1, 1)}

# D4 antipodal axes: each axis pairs a state with its bitwise complement
ANTIPODAL_LABEL: dict[tuple[int, int, int], int] = {
    (0, 0, 0): 0, (1, 1, 1): 0,
    (1, 0, 0): 1, (0, 1, 1): 1,
    (0, 1, 0): 2, (1, 0, 1): 2,
    (0, 0, 1): 3, (1, 1, 0): 3,
}


def rule30_bit(L: int, C: int, R: int) -> int:
    """Rule 30 local rule: L XOR (C OR R)."""
    return L ^ (C | R)


def voa_weight(state: tuple[int, int, int]) -> int:
    """VOA conformal weight: 0 for true vacua (L=C=R), 5 otherwise."""
    L, C, R = state
    return 0 if L == C == R else 5


def voa_sector_of(state: tuple[int, int, int]) -> str:
    return "vacuum" if voa_weight(state) == 0 else "excited"


def xor_debias(bits: list[int]) -> list[int]:
    """XOR adjacent disjoint pairs: halves length, strips first-order bias."""
    return [bits[i] ^ bits[i + 1] for i in range(0, len(bits) - 1, 2)]


def pack_bits(bits: list[int]) -> bytes:
    out = bytearray()
    for i in range(len(bits) // 8):
        b = 0
        for j in range(8):
            b = (b << 1) | bits[i * 8 + j]
        out.append(b)
    return bytes(out)


def voa_checksum(chart_sequence: list[tuple[int, int, int]],
                 seed_hash: str = "", block_index: int = 0) -> str:
    """Compact VOA syndrome: weight counts + D4 axis counts, chained to seed."""
    weight_counts: dict[int, int] = {}
    axis_counts = [0, 0, 0, 0]
    for s in chart_sequence:
        w = voa_weight(s)
        weight_counts[w] = weight_counts.get(w, 0) + 1
        axis_counts[ANTIPODAL_LABEL[s]] += 1
    payload = (f"VOA:{len(chart_sequence)}:{weight_counts.get(0, 0)}"
               f":{weight_counts.get(5, 0)}:{axis_counts}"
               f":{MONSTER_SCALAR}:{sorted(VOA_PARTITION.items())}"
               f":{seed_hash}:{block_index}")
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


class CenterColumnEngine:
    """Rule 30 on a growing tape; emits center bits and center chart states.

    canonical=True (no seed): single 1-cell start — the paper-bound object.
    Seeded: initial window = 256 bits expanded from SHA-256(seed).
    """

    def __init__(self, seed: Optional[bytes] = None):
        self.canonical = seed is None
        if seed is None:
            self.seed_hash = "canonical"
            self._state = [1]
            self._offset = 0
        else:
            if len(seed) < 16:
                raise ValueError("seed must be at least 16 bytes")
            self.seed_hash = hashlib.sha256(seed).hexdigest()[:32]
            window = b"".join(
                hashlib.sha256(seed + bytes([i])).digest() for i in range(8)
            )
            self._state = [(window[i // 8] >> (7 - i % 8)) & 1 for i in range(256)]
            if not any(self._state):
                self._state[128] = 1
            self._offset = 128
        self.center_bits: list[int] = []
        self.chart_states: list[tuple[int, int, int]] = []

    def step(self) -> int:
        old = self._state
        n = len(old)
        off = self._offset
        C = old[off]
        L = old[off - 1] if off > 0 else 0
        R = old[off + 1] if off + 1 < n else 0
        self.chart_states.append((L, C, R))
        new = [0] * (n + 2)
        for i in range(n + 2):
            li = old[i - 2] if 0 <= i - 2 < n else 0
            ci = old[i - 1] if 0 <= i - 1 < n else 0
            ri = old[i] if i < n else 0
            new[i] = li ^ (ci | ri)
        self._state = new
        self._offset = off + 1
        bit = new[self._offset]
        self.center_bits.append(bit)
        return bit

    def run(self, steps: int) -> list[int]:
        while len(self.center_bits) < steps:
            self.step()
        return self.center_bits[:steps]


@dataclass(frozen=True)
class EntropyBlock:
    """Random bytes plus the VOA syndrome proof of their generation window."""
    bytes_data: bytes
    size_bytes: int
    block_index: int
    syndrome_id: str
    seed_hash: str
    weight_counts: dict[int, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        import base64
        return {
            "bytes_b64": base64.b64encode(self.bytes_data).decode("ascii"),
            "size_bytes": self.size_bytes,
            "block_index": self.block_index,
            "syndrome_id": self.syndrome_id,
            "seed_hash": self.seed_hash,
            "weight_counts": {str(k): v for k, v in self.weight_counts.items()},
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EntropyBlock":
        import base64
        return cls(
            bytes_data=base64.b64decode(d["bytes_b64"]),
            size_bytes=d["size_bytes"],
            block_index=d["block_index"],
            syndrome_id=d["syndrome_id"],
            seed_hash=d["seed_hash"],
            weight_counts={int(k): v for k, v in d.get("weight_counts", {}).items()},
        )


class EntropyForgeEngine:
    """Seeded Rule 30 entropy blocks with verifiable VOA syndromes."""

    def __init__(self, seed: Optional[bytes] = None):
        self._seed = seed if seed is not None else secrets.token_bytes(32)
        self._engine = CenterColumnEngine(self._seed)
        self._block_index = 0
        self._consumed = 0

    @property
    def seed_hash(self) -> str:
        return self._engine.seed_hash

    def generate_block(self, size_bytes: int = 64) -> EntropyBlock:
        bits_needed = size_bytes * 16          # debias halves, pack needs 8x
        start = self._consumed
        self._engine.run(start + bits_needed)
        bits = self._engine.center_bits[start:start + bits_needed]
        window = self._engine.chart_states[start:start + bits_needed]
        self._consumed += bits_needed
        data = pack_bits(xor_debias(bits))[:size_bytes]
        weight_counts: dict[int, int] = {}
        for s in window:
            w = voa_weight(s)
            weight_counts[w] = weight_counts.get(w, 0) + 1
        block = EntropyBlock(
            bytes_data=data,
            size_bytes=len(data),
            block_index=self._block_index,
            syndrome_id=voa_checksum(window, self._engine.seed_hash, self._block_index),
            seed_hash=self._engine.seed_hash,
            weight_counts=weight_counts,
        )
        self._block_index += 1
        return block

    def blocks(self, size_bytes: int = 64, count: int = 1) -> Iterator[EntropyBlock]:
        for _ in range(count):
            yield self.generate_block(size_bytes)


def verify_block(block: EntropyBlock,
                 chart_window: list[tuple[int, int, int]]) -> bool:
    """Client-side check: recompute the syndrome from the chart window."""
    return voa_checksum(chart_window, block.seed_hash, block.block_index) == block.syndrome_id


# ─── Finite verifier (paper-bound claims, CQE-paper-12) ─────────────────────

def _independent_center_column(steps: int) -> list[int]:
    """Textbook dict-based Rule 30 from a single cell — independent of
    CenterColumnEngine's list representation, for dual-implementation
    agreement."""
    cells: dict[int, int] = {0: 1}
    out: list[int] = []
    lo = hi = 0
    for _ in range(steps):
        new: dict[int, int] = {}
        for p in range(lo - 1, hi + 2):
            L = cells.get(p - 1, 0)
            C = cells.get(p, 0)
            R = cells.get(p + 1, 0)
            v = L ^ (C | R)
            if v:
                new[p] = v
        cells = new
        lo -= 1
        hi += 1
        out.append(cells.get(0, 0))
    return out


def verify() -> dict[str, Any]:
    """Run the 10 finite checks that bind EntropyForge to CQE-paper-12."""
    checks: dict[str, bool] = {}

    # 1. Rule 30 formula matches Wolfram code 30 on all 8 states
    checks["rule30_formula_matches_wolfram_code_30"] = all(
        rule30_bit(L, C, R) == ((30 >> ((L << 2) | (C << 1) | R)) & 1)
        for (L, C, R) in CHART_STATES
    )

    # 2. VOA partition is exactly Z(q) = 2q^0 + 6q^5
    weights: dict[int, int] = {}
    for s in CHART_STATES:
        w = voa_weight(s)
        weights[w] = weights.get(w, 0) + 1
    checks["voa_partition_is_2q0_plus_6q5"] = weights == VOA_PARTITION

    # 3. Monster scalar factorization
    checks["monster_scalar_is_47_59_71"] = MONSTER_SCALAR == 196883 == 47 * 59 * 71

    # 4. D4 antipodal axes: 4 axes, 2 states each, complement pairs
    axes: dict[int, list[tuple[int, int, int]]] = {}
    for s, a in ANTIPODAL_LABEL.items():
        axes.setdefault(a, []).append(s)
    checks["d4_antipodal_axes_partition"] = (
        len(axes) == 4
        and all(len(v) == 2 for v in axes.values())
        and all(tuple(1 - b for b in v[0]) == v[1] for v in axes.values())
    )

    # 5. Dual-implementation agreement on the canonical center column
    eng = CenterColumnEngine()
    engine_bits = eng.run(512)
    checks["center_column_dual_implementation_agreement"] = (
        engine_bits == _independent_center_column(512)
    )

    # 6. No period p <= 256 in the first 2048 canonical center bits
    eng2 = CenterColumnEngine()
    bits2048 = eng2.run(2048)
    def has_period(seq: list[int], p: int) -> bool:
        return all(seq[i] == seq[i + p] for i in range(len(seq) - p))
    checks["center_column_no_period_up_to_256_in_2048"] = not any(
        has_period(bits2048, p) for p in range(1, 257)
    )

    # 7. Debiased canonical stream density within 5% of 1/2
    deb = xor_debias(bits2048)
    density = sum(deb) / len(deb)
    checks["debiased_density_within_tolerance"] = abs(density - 0.5) <= 0.05

    # 8. Syndrome determinism and window sensitivity
    win = eng2.chart_states[:1024]
    checks["voa_syndrome_deterministic_and_window_sensitive"] = (
        voa_checksum(win) == voa_checksum(win)
        and voa_checksum(win) != voa_checksum(win[:512])
    )

    # 9. Seed separation: distinct seeds give distinct streams; same seed repeats
    a1 = EntropyForgeEngine(b"seed-alpha-0123456789abcdef").generate_block(64)
    a2 = EntropyForgeEngine(b"seed-alpha-0123456789abcdef").generate_block(64)
    b1 = EntropyForgeEngine(b"seed-beta--0123456789abcdef").generate_block(64)
    checks["seeded_streams_repeat_and_separate"] = (
        a1.bytes_data == a2.bytes_data
        and a1.syndrome_id == a2.syndrome_id
        and a1.bytes_data != b1.bytes_data
    )

    # 10. Block round-trip + client-side syndrome verification
    eng3 = EntropyForgeEngine(b"roundtrip-seed-0123456789abcdef")
    blk = eng3.generate_block(32)
    window = eng3._engine.chart_states[:32 * 16]
    rt = EntropyBlock.from_dict(blk.to_dict())
    checks["block_roundtrip_and_client_verify"] = (
        rt.bytes_data == blk.bytes_data
        and verify_block(rt, window)
    )

    return {
        "forge": "EntropyForge",
        "paper": "CQE-paper-12",
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2))
