"""
rule30_block_extractor.py — Block-addressed Rule 30 center-bit extractor.

Sits on top of `Rule30Checkpoints` (block_tower.py). The extractor's
contract is:
  * Build phase: O(N * width) one-shot construction of the checkpoint
    store to max_depth.
  * Query phase: O(base_page * width) per `nth_bit` call, independent of
    depth (so long as depth <= max_depth). Range reads of contiguous
    depths reuse a single anchor row and cost O((end - start) * width).

This is the honest block-addressed I/O design: the previous version tried
to predict 64-bit futures from a 3-bit (L,C,R) key, which is information-
theoretically impossible for Rule 30's full-entropy center column. The
correct role of the block tower is to *amortize* read cost across the
N-bit ribbon, not to compress it below the Shannon floor.

Complexity summary:
  query_time(n)       = O(base_page * width(n))
  range_time(start,end) = O((end - start) * width(end))
  build_time(N)       = O(N * width(N))
  storage(N)          = O(N / base_page) rows
"""
from __future__ import annotations

import time
from typing import Any

from .block_tower import Rule30Checkpoints, _rule30_step, rule30_center_column
from .tools import MDHGTool, MORSRTool, SpeedlightTool


class Rule30BlockExtractor:
    """Block-addressed Rule 30 center-bit reader."""

    def __init__(
        self,
        max_depth: int = 4096,
        base_page: int = 64,
        max_level: int = 3,
        *,
        forge: Any = None,
    ):
        self.max_depth = max_depth
        self.base_page = base_page
        self.max_level = max_level
        self._forge = forge
        self._speedlight = SpeedlightTool()
        self._build_seconds = 0.0
        self._cache_payload = {"max_depth": max_depth, "base_page": base_page}
        self._store = self._build_store()

    def _build_store(self) -> Rule30Checkpoints:
        cache_hit = self._speedlight.invoke(
            op="get",
            namespace="block_tower",
            payload=self._cache_payload,
        )
        t0 = time.perf_counter()
        store = Rule30Checkpoints(
            max_depth=self.max_depth,
            base_page=self.base_page,
            max_level=self.max_level,
        )
        self._build_seconds = time.perf_counter() - t0
        store_info = store.info()
        store_info["cache_hit"] = bool(cache_hit.get("hit"))
        self._speedlight.invoke(
            op="put",
            namespace="block_tower",
            payload=self._cache_payload,
            value=store_info,
        )
        MDHGTool().invoke(
            key=f"lf/block_tower/{self.max_depth}/{self.base_page}",
            metadata=store_info,
            page=self.max_depth // max(1, self.base_page),
            block=self.base_page,
        )
        return store

    @property
    def store_info(self) -> dict[str, Any]:
        info = self._store.info()
        info["build_seconds"] = self._build_seconds
        return info

    def _record_solver(self, *, operation: str, elapsed_s: float, shannon_residue: float = 0.0) -> None:
        if self._forge is None:
            return
        self._forge.record_solver_event(
            operation=operation,
            landauer_cost=elapsed_s,
            shannon_residue=shannon_residue,
        )

    def nth_bit(self, n: int) -> dict[str, Any]:
        """Return the Rule 30 center bit at depth n (1-indexed)."""
        if n < 1:
            raise ValueError("n must be >= 1")
        if n > self.max_depth:
            raise ValueError(
                f"n={n} exceeds max_depth={self.max_depth}; rebuild with a "
                f"larger store."
            )
        t0 = time.perf_counter()
        bit = self._store.center_bit_at(n)
        elapsed = time.perf_counter() - t0
        anchor = self._store.nearest_checkpoint_at_or_before(n)
        status = "pass"
        self._record_solver(
            operation="regime_a_nth_bit",
            elapsed_s=elapsed,
            shannon_residue=0.0,
        )
        return {
            "n": n,
            "bit": bit,
            "anchor_depth": anchor,
            "replay_steps": n - anchor,
            "elapsed_s": elapsed,
            "method": "block_tower_checkpoint",
            "status": status,
            "build_seconds": self._build_seconds,
        }

    def bit_range(self, start: int, end: int) -> dict[str, Any]:
        """Return Rule 30 center bits from depth start..end (inclusive)."""
        if start < 1 or end < start:
            raise ValueError(f"invalid range start={start} end={end}")
        if end > self.max_depth:
            raise ValueError(
                f"end={end} exceeds max_depth={self.max_depth}"
            )
        t0 = time.perf_counter()
        anchor = self._store.nearest_checkpoint_at_or_before(start)
        row = self._store.row_at(anchor)
        center = self._store._center
        bits: list[int] = []
        depth = anchor
        while depth < start - 1:
            row = _rule30_step(row)
            depth += 1
        while depth < end:
            row = _rule30_step(row)
            depth += 1
            bits.append(row[center])
        elapsed = time.perf_counter() - t0
        self._record_solver(
            operation="regime_a_bit_range",
            elapsed_s=elapsed,
            shannon_residue=0.0,
        )
        return {
            "start": start,
            "end": end,
            "length": len(bits),
            "bits": bits,
            "anchor_depth": anchor,
            "elapsed_s": elapsed,
            "method": "block_tower_checkpoint",
            "build_seconds": self._build_seconds,
        }


# ---------------------------------------------------------------------------
# Verification + benchmarking
# ---------------------------------------------------------------------------

def verify_extractor(max_depth: int = 4096) -> dict[str, Any]:
    """Compare the extractor against brute-force Rule 30 at many depths."""
    extractor = Rule30BlockExtractor(max_depth=max_depth)
    bf = rule30_center_column(max_depth)

    sample = sorted({
        *[1, 2, 3, 10, 50, 63, 64, 65, 100, 127, 128, 200, 255, 256, 500, 1000],
        *range(1, max_depth + 1, max(1, max_depth // 256)),
        max_depth - 1, max_depth,
    })
    sample = [d for d in sample if 1 <= d <= max_depth]

    mismatches = []
    for n in sample:
        r = extractor.nth_bit(n)
        if r["bit"] != bf[n - 1]:
            mismatches.append({"n": n, "expected": bf[n - 1], "got": r["bit"]})

    if mismatches:
        MORSRTool().invoke(
            failure_kind="verify_extractor",
            context={"mismatch_count": len(mismatches), "max_depth": max_depth},
        )

    range_result = extractor.bit_range(1, min(256, max_depth))
    expected_range = bf[:len(range_result["bits"])]
    range_matches = sum(
        1 for a, b in zip(range_result["bits"], expected_range) if a == b
    )
    mismatch_rate = (
        len(mismatches) / len(sample) if sample else 0.0
    )

    return {
        "status": "pass" if not mismatches and range_matches == len(expected_range) else "fail",
        "max_depth": max_depth,
        "sample_count": len(sample),
        "individual_mismatch_count": len(mismatches),
        "individual_mismatches": mismatches[:10],
        "range_total": len(expected_range),
        "range_matches": range_matches,
        "range_match_rate": range_matches / len(expected_range) if expected_range else 0.0,
        "mismatch_rate": mismatch_rate,
    }


def benchmark_extractor(depths: list[int] | None = None) -> dict[str, Any]:
    """Benchmark per-query latency vs. depth. With the block-tower store,
    query time should be roughly constant in n (bounded by base_page)."""
    if depths is None:
        depths = [64, 256, 1024, 4096]

    max_d = max(depths)
    extractor = Rule30BlockExtractor(max_depth=max_d)
    results = []
    for n in depths:
        N_TRIALS = 20
        t0 = time.perf_counter()
        for _ in range(N_TRIALS):
            extractor.nth_bit(n)
        elapsed = (time.perf_counter() - t0) / N_TRIALS
        results.append({
            "n": n,
            "avg_query_s": elapsed,
        })

    if len(results) >= 2 and results[0]["avg_query_s"] > 0:
        ratio = results[-1]["avg_query_s"] / results[0]["avg_query_s"]
    else:
        ratio = None
    return {
        "results": results,
        "max_over_min_ratio": ratio,
        "method": "block_tower_checkpoint",
    }


if __name__ == "__main__":
    import json
    print("Verifying extractor at max_depth=4096...")
    v = verify_extractor(4096)
    print(json.dumps(
        {k: v[k] for k in v if k != "individual_mismatches"},
        indent=2,
    ))
    if v["individual_mismatches"]:
        print("Mismatches:")
        for m in v["individual_mismatches"]:
            print(f"  {m}")

    print("\nBenchmarking [64, 256, 1024, 4096]...")
    b = benchmark_extractor([64, 256, 1024, 4096])
    for r in b["results"]:
        print(f"  n={r['n']:>5}: {r['avg_query_s']*1000:.4f} ms/query")
    print(f"  ratio(max/min) = {b['max_over_min_ratio']:.3f}")
