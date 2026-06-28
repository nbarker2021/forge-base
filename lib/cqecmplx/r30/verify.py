"""Production verification report."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .actions import idempotent_at_c, lcr_cycle, swap_lr
from .atlas import BinaryRule
from .cache import ExtendedMemoryManifest, InMemorySheetCache
from .library import ReverseAtlasChain, ReverseAtlasLibrary
from .normal_form import EvidenceClass, LocalTriad
from .proof_shell import ProofShell
from .request_codec import REQUEST_TAIL_BITS, RequestTailCodec, classify_triad
from .solver import CmplxR30Solver


def verify_product(
    manifest_path: Path = Path("extended_memory/manifest.json"),
    reverse_library_path: Path = Path("DATA/cache/reverse-atlas-rule30-center-1m"),
    projected_reverse_library_path: Path = Path(
        "DATA/cache/reverse-atlas-projected-rule30-from-center-ribbon-1m"
    ),
    reverse_chain_path: Path = Path("DATA/cache/reverse-atlas-chain-1m.json"),
) -> dict[str, Any]:
    """Run the lean runtime's bounded product checks."""
    triads = [
        LocalTriad(left, center, right)
        for left in (0, 1)
        for center in (0, 1)
        for right in (0, 1)
    ]
    local_closure = all(idempotent_at_c(triad) for triad in triads)
    lr_centroid_fixed = all(swap_lr(triad).center == triad.center for triad in triads)
    three_placement_identity = all(lcr_cycle(triad) == triad for triad in triads)
    rule90 = BinaryRule.from_rule_number(90)
    all_projectors_reconstruct = all(
        projector.emit(triad)
        == rule90.emit(triad) ^ projector.correction_against(rule90, triad)
        for rule_number in range(256)
        for projector in (BinaryRule.from_rule_number(rule_number),)
        for triad in triads
    )
    rule30 = BinaryRule.from_rule_number(30)
    rule30_correction_is_c_and_not_r = all(
        rule30.correction_against(rule90, triad)
        == triad.center & (1 - triad.right)
        for triad in triads
    )
    solver = CmplxR30Solver(InMemorySheetCache.from_bits("101100"))
    exact = solver.solve(2)
    route = solver.solve(7)
    manifest = ExtendedMemoryManifest.load(manifest_path).status()
    reverse_library = ReverseAtlasLibrary.open(reverse_library_path)
    reverse_receipt = reverse_library.lookup(4096)
    projected_reverse_library = ReverseAtlasLibrary.open(projected_reverse_library_path)
    projected_reverse_receipt = projected_reverse_library.lookup(4096)
    reverse_chain = ReverseAtlasChain.open(reverse_chain_path)
    backtrack_receipt = reverse_chain.backtrack(4096)
    backtrack_chain = {
        "loaded": True,
        "path": str(reverse_chain.path),
        "hop_count": backtrack_receipt["hop_count"],
        "lookup_exact": (
            backtrack_receipt["evidence"] == "reverse_chain_exact"
            and all(
                hop["receipt"]["evidence"] == "reverse_library_exact"
                for hop in backtrack_receipt["hops"]
            )
        ),
    }
    projected_chain = {
        "loaded": True,
        "path": str(projected_reverse_library.path),
        "address_count": projected_reverse_library.manifest["address_count"],
        "recipe_table_size": projected_reverse_library.manifest["recipe_table_size"],
        "unique_observed_recipe_count": projected_reverse_library.manifest[
            "unique_observed_recipe_count"
        ],
        "lookup_receipt_exact": (
            projected_reverse_receipt["evidence"] == "reverse_library_exact"
        ),
    }
    required_reverse_library = {
        "loaded": True,
        "path": str(reverse_library.path),
        "address_count": reverse_library.manifest["address_count"],
        "recipe_table_size": reverse_library.manifest["recipe_table_size"],
        "unique_observed_recipe_count": reverse_library.manifest[
            "unique_observed_recipe_count"
        ],
        "lookup_complexity": reverse_library.manifest["lookup_complexity"],
        "lookup_receipt_exact": reverse_receipt["evidence"] == "reverse_library_exact",
        "projected_chain": projected_chain,
        "backtrack_chain": backtrack_chain,
    }
    request_codec = RequestTailCodec()
    all_request_tails_close = all(
        receipt["head"]["state"][0] == receipt["head"]["state"][2]
        and receipt["tail"]["state"][0] == receipt["tail"]["state"][2]
        and receipt["head"]["anneal_steps"] <= 3
        and receipt["tail"]["anneal_steps"] <= 3
        for n in range(1 << REQUEST_TAIL_BITS)
        for receipt in (request_codec.decode(n),)
    )
    overlap = classify_triad((0, 1, 0))
    proof_shell = ProofShell.default().verify()
    enumerated_request_tail_codec = {
        "tail_bits": REQUEST_TAIL_BITS,
        "tails_checked": 1 << REQUEST_TAIL_BITS,
        "all_65536_tails_close": all_request_tails_close,
        "lookup_table_entries": 0,
        "complexity": "O(1) for fixed 16-bit request tail",
        "rest_and_correction_facets_independent": (
            overlap["lie_conjugate"]
            and overlap["correction_fires"]
            and overlap["geometry_level"] == 0
            and overlap["emission_level"] == 2
        ),
        "scope": (
            "Exact local boundary framing for the request token generated by N. "
            "This is not an Nth-bit semantic landing."
        ),
    }
    checks = {
        "exact_materialized_receipt": exact.evidence is EvidenceClass.MATERIALIZED_EXACT,
        "unhydrated_address_routed": (
            route.evidence is EvidenceClass.REGISTERED_ROUTE
            and route.bit is None
            and route.root_template == "K6:t1"
            and not route.continuation_verified
        ),
        "lr_centroid_fixed": lr_centroid_fixed,
        "three_placement_identity": three_placement_identity,
        "manifest_schema": manifest["schema_version"] == 1,
        "all_256_projectors_reconstruct": all_projectors_reconstruct,
        "rule30_correction_is_c_and_not_r": rule30_correction_is_c_and_not_r,
        "required_reverse_library": (
            required_reverse_library["address_count"] == 1_000_000
            and required_reverse_library["recipe_table_size"] == 8
            and required_reverse_library["unique_observed_recipe_count"] == 8
            and required_reverse_library["lookup_receipt_exact"]
            and projected_chain["address_count"] == 1_000_000
            and projected_chain["recipe_table_size"] == 8
            and projected_chain["unique_observed_recipe_count"] == 8
            and projected_chain["lookup_receipt_exact"]
            and backtrack_chain["hop_count"] == 2
            and backtrack_chain["lookup_exact"]
        ),
        "enumerated_request_tail_codec": (
            enumerated_request_tail_codec["all_65536_tails_close"]
            and enumerated_request_tail_codec["rest_and_correction_facets_independent"]
        ),
        "proof_shell": proof_shell["status"] == "pass_with_frontier",
    }
    return {
        "status": "pass" if local_closure and all(checks.values()) else "fail",
        "checks": checks,
        "local_closure": {
            "all_8_binary_triads": local_closure,
            "predicate": "center(S)=center(swap_LR(S)) and emit(S)=emit(LCR_cycle(S))",
            "scope": "local binary triads under literal rho^3 identity",
        },
        "oriented_binary_atlas": {
            "all_256_projectors_reconstruct": all_projectors_reconstruct,
            "rule30_correction_is_c_and_not_r": rule30_correction_is_c_and_not_r,
            "negative_observation_lane": -1,
            "scope": "all radius-1 Boolean truth tables over oriented LCR reads",
        },
        "required_reverse_library": required_reverse_library,
        "enumerated_request_tail_codec": enumerated_request_tail_codec,
        "proof_shell": proof_shell,
        "cross_sheet_continuation_proved": False,
        "proof_boundary": (
            "Local closure is universal for literal LCR cycling. "
            "Cross-sheet continuation requires an independently verified rule."
        ),
    }
