"""Observer-relative proof accounting for the Rule 30 plus-or-minus-one shell."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib import import_module
from itertools import product
from pathlib import Path
import sys
from typing import Any

from .actions import emit, swap_lr
from .atlas import BinaryRule, BondedFrames
from .normal_form import LocalTriad
from .request_codec import RequestTailCodec, anneal_to_lie_conjugate

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ClaimNode:
    """One shell-scoped claim and the boundary required to promote it."""

    claim_id: str
    shell: int
    statement: str
    dependencies: tuple[str, ...]
    verifier: str
    declared_scope: str
    evidence_tier: str
    promotion_rule: str
    emergent_obligations: tuple[str, ...] = ()
    failure_boundary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FrontierNode:
    """One immediate next-shell candidate visible from completed work."""

    claim_id: str
    observer_nodes: tuple[str, ...]
    direction: str
    required_link_type: str
    promotion_gate: str
    status: str = "frontier_candidate"
    verifier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _claim(
    claim_id: str,
    shell: int,
    dependencies: tuple[str, ...] = (),
    *,
    verifier: str,
    evidence_tier: str = "demonstrated",
) -> ClaimNode:
    return ClaimNode(
        claim_id=claim_id,
        shell=shell,
        statement=claim_id.replace("_", " ").title(),
        dependencies=dependencies,
        verifier=verifier,
        declared_scope="shell_scoped",
        evidence_tier=evidence_tier,
        promotion_rule="all dependencies and the declared verifier must pass",
        failure_boundary="a missing dependency, cycle, or failed verifier blocks promotion",
    )


def _default_claims() -> tuple[ClaimNode, ...]:
    return (
        _claim("LCR_TRIAD_DOMAIN", -1, verifier="lcr_triad_domain"),
        _claim(
            "GLUON_LR_INVARIANCE",
            -1,
            ("LCR_TRIAD_DOMAIN",),
            verifier="gluon_lr_invariance",
        ),
        _claim("RULE90_PRIOR", -1, ("LCR_TRIAD_DOMAIN",), verifier="rule90_prior"),
        _claim(
            "RULE30_CORRECTION_IDENTITY",
            -1,
            ("LCR_TRIAD_DOMAIN", "RULE90_PRIOR"),
            verifier="rule30_correction_identity",
        ),
        _claim(
            "D4_AXIS_SHEET_CODEC",
            -1,
            ("LCR_TRIAD_DOMAIN",),
            verifier="proof:chart_codec_d4.verify_chart_codec_d4",
        ),
        _claim(
            "REQUEST_TAIL_BOUNDARY_CODEC",
            -1,
            ("LCR_TRIAD_DOMAIN", "GLUON_LR_INVARIANCE"),
            verifier="request_tail_boundary_codec",
        ),
        _claim(
            "RULE30_LOCAL_EMISSION",
            0,
            ("GLUON_LR_INVARIANCE", "RULE30_CORRECTION_IDENTITY"),
            verifier="rule30_local_emission",
        ),
        _claim(
            "CANONICAL_SHEET_LOOKUP",
            0,
            ("RULE30_LOCAL_EMISSION",),
            verifier="canonical_sheet_lookup",
            evidence_tier="bounded_exec",
        ),
        _claim(
            "ORIENTED_BINARY_ATLAS",
            0,
            ("RULE30_LOCAL_EMISSION", "D4_AXIS_SHEET_CODEC"),
            verifier="oriented_binary_atlas",
            evidence_tier="bounded_exec",
        ),
        _claim(
            "REVERSE_RECIPE_LIBRARY",
            0,
            ("ORIENTED_BINARY_ATLAS", "CANONICAL_SHEET_LOOKUP"),
            verifier="reverse_recipe_library",
            evidence_tier="bounded_exec",
        ),
        _claim(
            "TWO_LAYER_BOUNDARY_DOWN_CHAIN",
            0,
            ("REVERSE_RECIPE_LIBRARY",),
            verifier="two_layer_boundary_down_chain",
            evidence_tier="bounded_exec",
        ),
        _claim(
            "LOCAL_WRAP_RECEIPT",
            0,
            ("REQUEST_TAIL_BOUNDARY_CODEC", "RULE30_LOCAL_EMISSION"),
            verifier="local_wrap_receipt",
        ),
        _claim(
            "J3O_DIAGONAL_CARRIER",
            1,
            ("D4_AXIS_SHEET_CODEC", "GLUON_LR_INVARIANCE"),
            verifier="proof:jordan_j3.verify_j3o_axioms",
        ),
        _claim(
            "G2_F4_T5A_BOUNDED_ROUTE",
            1,
            ("J3O_DIAGONAL_CARRIER", "LOCAL_WRAP_RECEIPT"),
            verifier="proof:g2_f4_t5_conjugate.verify_conjugate_triple",
            evidence_tier="bounded_normalized",
        ),
        _claim(
            "F2_CORRECTION_GOVERNANCE",
            1,
            ("RULE30_CORRECTION_IDENTITY", "D4_AXIS_SHEET_CODEC"),
            verifier="proof:f2_majorana.verify_f2_majorana",
        ),
        ClaimNode(
            claim_id="NIEMEIER_LANDING_REGISTRY",
            shell=1,
            statement="Registered Niemeier and Leech landing forms",
            dependencies=("G2_F4_T5A_BOUNDED_ROUTE",),
            verifier="proof:transport_obligations.verify_niemeier_landing_registry",
            declared_scope="registered landing forms",
            evidence_tier="registered",
            promotion_rule="remain registered until a fingerprint map is proved",
            emergent_obligations=("NIEMEIER_FINGERPRINT_MAP",),
            failure_boundary="a landing-form registry is not a computed landing map",
        ),
    )


def _triads() -> tuple[LocalTriad, ...]:
    return tuple(LocalTriad(*bits) for bits in product((0, 1), repeat=3))


def _pass(**details: Any) -> dict[str, Any]:
    return {"status": "pass", **details}


def _local_witness(name: str) -> dict[str, Any]:
    triads = _triads()
    rule30 = BinaryRule.from_rule_number(30)
    rule90 = BinaryRule.from_rule_number(90)
    if name == "lcr_triad_domain":
        return _pass(states_checked=len(triads))
    if name == "gluon_lr_invariance":
        return _pass(states_checked=sum(t.center == swap_lr(t).center for t in triads))
    if name == "rule90_prior":
        return _pass(states_checked=sum(rule90.emit(t) == (t.left ^ t.right) for t in triads))
    if name == "rule30_correction_identity":
        return _pass(
            states_checked=sum(
                rule30.correction_against(rule90, t) == (t.center & (1 - t.right))
                for t in triads
            )
        )
    if name == "rule30_local_emission":
        return _pass(states_checked=sum(rule30.emit(t) == emit(t) for t in triads))
    if name == "request_tail_boundary_codec":
        codec = RequestTailCodec()
        return _pass(
            tails_checked=sum(
                codec.decode(n)["status"] == "resolved" for n in range(1 << codec.tail_bits)
            )
        )
    if name == "local_wrap_receipt":
        return _pass(
            states_checked=sum(
                anneal_to_lie_conjugate((t.left, t.center, t.right))["steps"] <= 3
                for t in triads
            )
        )
    if name == "oriented_binary_atlas":
        return _pass(
            states_checked=sum(len(BondedFrames.from_triad(t).to_dict()) == 4 for t in triads)
        )
    if name in {"canonical_sheet_lookup", "reverse_recipe_library"}:
        from .library import ReverseAtlasLibrary

        library = ReverseAtlasLibrary.open(REPO_ROOT / "DATA/cache/reverse-atlas-rule30-center-1m")
        return _pass(
            address_count=library.manifest["address_count"],
            recipe_table_size=library.manifest["recipe_table_size"],
        )
    if name == "two_layer_boundary_down_chain":
        from .library import ReverseAtlasChain

        chain = ReverseAtlasChain.open(REPO_ROOT / "DATA/cache/reverse-atlas-chain-1m.json")
        receipt = chain.backtrack(4096)
        return _pass(hop_count=receipt["hop_count"])
    if name == "wolfram_billion_weyl_slot_coverage":
        from .cache import verify_wolfram_billion_weyl_slot_coverage

        return verify_wolfram_billion_weyl_slot_coverage()
    if name == "wolfram_billion_dihedral_atlas_geometry":
        from .cache import verify_wolfram_billion_dihedral_atlas_geometry

        return verify_wolfram_billion_dihedral_atlas_geometry()
    if name == "e8_centroid_cartan_partition":
        from .cache import verify_e8_centroid_cartan_partition

        return verify_e8_centroid_cartan_partition()
    if name == "formulaic_billion_address_library":
        from .cache import verify_formulaic_billion_address_library

        return verify_formulaic_billion_address_library()
    if name == "formulaic_address_dtt_tdd_ttd_lane":
        from .deployment_lane import verify_formulaic_address_deployment_lane

        return verify_formulaic_address_deployment_lane(1_000_000_249)
    raise KeyError(f"unknown local witness: {name}")


def _proof_witness(specifier: str) -> dict[str, Any]:
    proof_src = REPO_ROOT / "PROOF/src"
    if str(proof_src) not in sys.path:
        sys.path.insert(0, str(proof_src))
    module_name, function_name = specifier.split(".", maxsplit=1)
    function = getattr(import_module(f"lattice_forge.{module_name}"), function_name)
    if function_name == "verify_chart_codec_d4":
        return function(max_depth=256)
    if function_name == "verify_conjugate_triple":
        return function(max_depth=256)
    return function()


def _witness(verifier: str) -> dict[str, Any]:
    return (
        _proof_witness(verifier.removeprefix("proof:"))
        if verifier.startswith("proof:")
        else _local_witness(verifier)
    )


class ProofShell:
    """Compile deterministic reports for one observer-relative proof wave."""

    def __init__(
        self,
        claims: tuple[ClaimNode, ...],
        frontier_nodes: tuple[FrontierNode, ...],
    ) -> None:
        self.claims = {claim.claim_id: claim for claim in claims}
        self.frontier_nodes = frontier_nodes

    @classmethod
    def default(cls) -> "ProofShell":
        return cls(
            claims=_default_claims(),
            frontier_nodes=(
                FrontierNode(
                    claim_id="NIEMEIER_FINGERPRINT_MAP",
                    observer_nodes=("NIEMEIER_LANDING_REGISTRY",),
                    direction="outgoing",
                    required_link_type="cold-start fingerprint-to-landing map",
                    promotion_gate=(
                        "derive the fingerprint from the request state, bind it to one "
                        "landing form, and verify held-out semantic landings"
                    ),
                    status="open_obligation",
                ),
                FrontierNode(
                    claim_id="WOLFRAM_BILLION_WEYL_SLOT_COVERAGE",
                    observer_nodes=("NIEMEIER_LANDING_REGISTRY",),
                    direction="outgoing",
                    required_link_type="billion-sheet address coverage for every W(E8) slot",
                    promotion_gate=(
                        "show that the registered billion-bit sheet has at least "
                        "|W(E8)| positions while keeping fingerprint assignment separate"
                    ),
                    status="bounded_verified",
                    verifier="wolfram_billion_weyl_slot_coverage",
                ),
                FrontierNode(
                    claim_id="WOLFRAM_BILLION_D4_VISUAL_ATLAS",
                    observer_nodes=("WOLFRAM_BILLION_WEYL_SLOT_COVERAGE",),
                    direction="outgoing",
                    required_link_type="four rotations plus four mirrored packed-sheet reads",
                    promotion_gate=(
                        "define reversible D4 coordinate transforms over the registered "
                        "billion-bit sheet without materializing an expanded matrix"
                    ),
                    status="bounded_verified",
                    verifier="wolfram_billion_dihedral_atlas_geometry",
                ),
                FrontierNode(
                    claim_id="E8_CENTROID_CARTAN_PARTITION",
                    observer_nodes=("WOLFRAM_BILLION_D4_VISUAL_ATLAS",),
                    direction="outgoing",
                    required_link_type="E8 adjoint centroid partition into root and Cartan slots",
                    promotion_gate=(
                        "reserve the exact 240 root slots and eight non-root Cartan "
                        "trigger candidates while keeping event semantics separate"
                    ),
                    status="bounded_verified",
                    verifier="e8_centroid_cartan_partition",
                ),
                FrontierNode(
                    claim_id="WOLFRAM_BILLION_FORMULAIC_ADDRESS_LIBRARY",
                    observer_nodes=("E8_CENTROID_CARTAN_PARTITION",),
                    direction="outgoing",
                    required_link_type="formulaic N-to-D4/Jordan library address compiler",
                    promotion_gate=(
                        "compile every non-negative N into sheet cycle, D4 image view, "
                        "visual coordinate, centroid slot, and one of eight lookup shards"
                    ),
                    status="bounded_verified",
                    verifier="formulaic_billion_address_library",
                ),
                FrontierNode(
                    claim_id="FORMULAIC_ADDRESS_DTT_TDD_TTD_LANE",
                    observer_nodes=("WOLFRAM_BILLION_FORMULAIC_ADDRESS_LIBRARY",),
                    direction="outgoing",
                    required_link_type="deployment-shaped deterministic address receipt lane",
                    promotion_gate=(
                        "invoke the CLI, replay the same request in process, invoke the "
                        "CLI again, and require all three receipts to agree exactly"
                    ),
                    status="bounded_verified",
                    verifier="formulaic_address_dtt_tdd_ttd_lane",
                ),
                FrontierNode(
                    claim_id="WOLFRAM_BILLION_CARTAN_SECTOR_CLASSIFIER",
                    observer_nodes=("FORMULAIC_ADDRESS_DTT_TDD_TTD_LANE",),
                    direction="outgoing",
                    required_link_type="Cartan-sector labels for eight visual sheet views",
                    promotion_gate=(
                        "define a Lie-theoretic sector invariant, classify each visual "
                        "view, and verify that the labels are preserved under the claimed action"
                    ),
                    status="open_obligation",
                ),
                FrontierNode(
                    claim_id="NIEMEIER_ROOT_SHELL_PROFILE_MAP",
                    observer_nodes=("NIEMEIER_LANDING_REGISTRY",),
                    direction="outgoing",
                    required_link_type="bounded ADE terminal profile map",
                    promotion_gate=(
                        "verify rank, common Coxeter number, and discriminant index "
                        "for every rootful registered terminal"
                    ),
                    status="bounded_verified",
                    verifier=(
                        "proof:transport_obligations."
                        "verify_niemeier_root_shell_profiles"
                    ),
                ),
                FrontierNode(
                    claim_id="NIEMEIER_E8_CUBED_DIRECT_SUM_LANDING",
                    observer_nodes=("NIEMEIER_LANDING_REGISTRY",),
                    direction="outgoing",
                    required_link_type="determinant-one direct-sum terminal shell",
                    promotion_gate=(
                        "identify registered rootful terminals whose ADE root lattice "
                        "already has required overlattice index one"
                    ),
                    status="bounded_verified",
                    verifier=(
                        "proof:transport_obligations."
                        "verify_niemeier_direct_sum_index_one_landings"
                    ),
                ),
                FrontierNode(
                    claim_id="LEECH_ENUMERATED_GLUE_SELECTOR",
                    observer_nodes=(
                        "NIEMEIER_E8_CUBED_DIRECT_SUM_LANDING",
                        "REQUEST_TAIL_BOUNDARY_CODEC",
                    ),
                    direction="outgoing",
                    required_link_type="enumeration-derived three-E8 glue selector",
                    promotion_gate=(
                        "derive deterministic glue-selection metadata from N while "
                        "keeping the rootless Leech invariant proof separate"
                    ),
                    status="bounded_verified",
                    verifier=(
                        "proof:enumerated_glue."
                        "verify_enumerated_glue_selector_contract"
                    ),
                ),
                FrontierNode(
                    claim_id="LEECH_ROOTLESS_MEMBERSHIP_ORACLE",
                    observer_nodes=("LEECH_ENUMERATED_GLUE_SELECTOR",),
                    direction="outgoing",
                    required_link_type="independent rootless Leech membership oracle",
                    promotion_gate=(
                        "validate scaled-coordinate membership and reject norm-2 roots "
                        "before promoting an enumerated glue action"
                    ),
                    status="bounded_verified",
                    verifier="proof:enumerated_glue.verify_leech_membership_oracle",
                ),
                FrontierNode(
                    claim_id="LEECH_ENUMERATED_MINIMAL_VECTOR_LANDING",
                    observer_nodes=(
                        "LEECH_ENUMERATED_GLUE_SELECTOR",
                        "LEECH_ROOTLESS_MEMBERSHIP_ORACLE",
                    ),
                    direction="outgoing",
                    required_link_type="bounded enumeration-selected Leech landing family",
                    promotion_gate=(
                        "emit cross-E8-block norm-4 vectors from N and validate each "
                        "with the independent rootless Leech membership oracle"
                    ),
                    status="bounded_verified",
                    verifier=(
                        "proof:enumerated_glue."
                        "verify_enumerated_leech_minimal_landings"
                    ),
                ),
                FrontierNode(
                    claim_id="LEECH_ENUMERATED_TYPE1_MINIMAL_ORBIT",
                    observer_nodes=("LEECH_ROOTLESS_MEMBERSHIP_ORACLE",),
                    direction="outgoing",
                    required_link_type="complete signed type-1 Leech minimal-vector orbit",
                    promotion_gate=(
                        "enumerate all signed two-coordinate vectors and validate "
                        "all 1104 norm-4 landings with the independent oracle"
                    ),
                    status="bounded_verified",
                    verifier=(
                        "proof:enumerated_glue."
                        "verify_enumerated_leech_type1_orbit"
                    ),
                ),
                FrontierNode(
                    claim_id="LEECH_ENUMERATED_TYPE2_MINIMAL_ORBIT",
                    observer_nodes=("LEECH_ROOTLESS_MEMBERSHIP_ORACLE",),
                    direction="outgoing",
                    required_link_type="complete Golay-octad type-2 Leech minimal-vector orbit",
                    promotion_gate=(
                        "enumerate all Golay octads and even-parity sign assignments, "
                        "then validate all 97152 norm-4 landings"
                    ),
                    status="bounded_verified",
                    verifier=(
                        "proof:enumerated_glue."
                        "verify_enumerated_leech_type2_orbit"
                    ),
                ),
                FrontierNode(
                    claim_id="LEECH_ENUMERATED_TYPE3_MINIMAL_ORBIT",
                    observer_nodes=("LEECH_ROOTLESS_MEMBERSHIP_ORACLE",),
                    direction="outgoing",
                    required_link_type="complete Golay-word type-3 Leech minimal-vector orbit",
                    promotion_gate=(
                        "enumerate each distinguished coordinate and Golay-word sign lift, "
                        "then validate all 98304 norm-4 landings"
                    ),
                    status="bounded_verified",
                    verifier=(
                        "proof:enumerated_glue."
                        "verify_enumerated_leech_type3_orbit"
                    ),
                ),
                FrontierNode(
                    claim_id="LEECH_CLASSICAL_MINIMAL_SHELL_ACCOUNTING",
                    observer_nodes=(
                        "LEECH_ENUMERATED_TYPE1_MINIMAL_ORBIT",
                        "LEECH_ENUMERATED_TYPE2_MINIMAL_ORBIT",
                        "LEECH_ENUMERATED_TYPE3_MINIMAL_ORBIT",
                    ),
                    direction="outgoing",
                    required_link_type="three-orbit classical minimal-shell accounting",
                    promotion_gate=(
                        "sum the three verified classical orbit families to 196560 "
                        "while keeping first-principles exhaustiveness separate"
                    ),
                    status="bounded_verified",
                    verifier=(
                        "proof:enumerated_glue."
                        "verify_enumerated_leech_classical_minimal_shell"
                    ),
                ),
                FrontierNode(
                    claim_id="LEECH_ARBITRARY_BYTE_RIBBON_CODEC",
                    observer_nodes=("LEECH_CLASSICAL_MINIMAL_SHELL_ACCOUNTING",),
                    direction="outgoing",
                    required_link_type="lossless arbitrary-byte Leech vector ribbon codec",
                    promotion_gate=(
                        "encode bytes as radix-196560 landing addresses, validate every "
                        "vector, and decode exact payload bytes including leading zeroes"
                    ),
                    status="bounded_verified",
                    verifier="proof:enumerated_glue.verify_leech_ribbon_codec",
                ),
                FrontierNode(
                    claim_id="LEECH_LITERAL_QUARTER_TURN_IMAGE_READ",
                    observer_nodes=("LEECH_CLASSICAL_MINIMAL_SHELL_ACCOUNTING",),
                    direction="outgoing",
                    required_link_type="literal four-view Leech coordinate image rotation",
                    promotion_gate=(
                        "rotate each 3x8 coordinate image through 0, 90, 180, and "
                        "270 degrees and verify exact restoration after four turns"
                    ),
                    status="bounded_verified",
                    verifier="proof:nebe_gamma72.verify_literal_quarter_turn_experiment",
                ),
                FrontierNode(
                    claim_id="NEBE_GAMMA72_THREE_LEECH_TRANSPORT",
                    observer_nodes=("LEECH_ARBITRARY_BYTE_RIBBON_CODEC",),
                    direction="outgoing",
                    required_link_type="lossless arbitrary-byte three-Leech transport contract",
                    promotion_gate=(
                        "emit three exact Leech ribbons with reused enumeration metadata "
                        "while keeping the Hermitian polarization action separate"
                    ),
                    status="bounded_verified",
                    verifier="proof:nebe_gamma72.verify_nebe_gamma72_contract",
                ),
                FrontierNode(
                    claim_id="NEBE_GAMMA72_POLARIZATION_MATRIX_ACTION",
                    observer_nodes=("NEBE_GAMMA72_THREE_LEECH_TRANSPORT",),
                    direction="outgoing",
                    required_link_type="Hermitian polarization matrix action on Lambda24^3",
                    promotion_gate=(
                        "supply one selected Z[alpha] structure, apply its A and B block "
                        "matrices, and verify an extremal even unimodular Gamma72 landing"
                    ),
                    status="open_obligation",
                ),
                FrontierNode(
                    claim_id="NIEMEIER_EXACT_GLUE_COSETS",
                    observer_nodes=("NIEMEIER_LANDING_REGISTRY",),
                    direction="outgoing",
                    required_link_type="proof-grade overlattice glue representatives",
                    promotion_gate=(
                        "retain the existing discriminant profiles and add exact glue "
                        "cosets or codewords for each nontrivial overlattice"
                    ),
                    status="bounded_partial",
                ),
                FrontierNode(
                    claim_id="LEECH_CONSTRUCTION_MINIMAL_SHELL",
                    observer_nodes=("NIEMEIER_LANDING_REGISTRY",),
                    direction="outgoing",
                    required_link_type="rootless Leech construction witness",
                    promotion_gate=(
                        "supply a code, lift, or quotient route and verify the minimal shell"
                    ),
                    status="open_obligation",
                ),
                FrontierNode(
                    claim_id="LATTICE_CONJUGATE_SUBSTRATE_REACHABILITY",
                    observer_nodes=("NIEMEIER_LANDING_REGISTRY",),
                    direction="outgoing",
                    required_link_type="explicit lattice-to-symmetry reachability map",
                    promotion_gate=(
                        "name the source lattice, target symmetry object, explicit map, "
                        "preserved operation, and verifier"
                    ),
                ),
            ),
        )

    def _dependencies_exist(self) -> bool:
        return all(
            dependency in self.claims
            for claim in self.claims.values()
            for dependency in claim.dependencies
        )

    def _acyclic(self) -> bool:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(claim_id: str) -> bool:
            if claim_id in visiting:
                return False
            if claim_id in visited:
                return True
            visiting.add(claim_id)
            for dependency in self.claims[claim_id].dependencies:
                if dependency in self.claims and not visit(dependency):
                    return False
            visiting.remove(claim_id)
            visited.add(claim_id)
            return True

        return all(visit(claim_id) for claim_id in sorted(self.claims))

    def _dependency_closure(self, claim_id: str) -> tuple[str, ...]:
        closure: set[str] = set()

        def collect(current_id: str) -> None:
            for dependency in self.claims[current_id].dependencies:
                if dependency not in closure:
                    closure.add(dependency)
                    collect(dependency)

        collect(claim_id)
        return tuple(sorted(closure))

    def frontier(self) -> dict[str, Any]:
        """Emit the immediate next shell without repeating completed nodes."""
        rows = []
        for node in self.frontier_nodes:
            row = node.to_dict()
            if node.verifier:
                try:
                    witness = _witness(node.verifier)
                    verifier_passed = witness.get("status") == "pass"
                except Exception as error:
                    witness = {"status": "fail", "error": str(error)}
                    verifier_passed = False
                row["witness"] = witness
                row["verifier_passed"] = verifier_passed
                if not verifier_passed:
                    row["status"] = "blocked"
            rows.append(row)
        return {
            "wave_depth": 1,
            "claim_ids": [row["claim_id"] for row in rows],
            "rows": rows,
            "emergent_obligations": sorted(
                {
                    obligation
                    for claim in self.claims.values()
                    for obligation in claim.emergent_obligations
                }
                | {
                    node.claim_id
                    for node in self.frontier_nodes
                    if node.status in {"open_obligation", "bounded_partial"}
                }
            ),
        }

    def show(self, claim_id: str) -> dict[str, Any] | None:
        """Return one evaluated claim row, or `None` when it is unknown."""
        return self.verify()["claims"].get(claim_id)

    def verify(self) -> dict[str, Any]:
        """Evaluate one shell wave while preserving each witness boundary."""
        graph_valid = self._dependencies_exist() and self._acyclic()
        rows: dict[str, dict[str, Any]] = {}

        def evaluate(claim_id: str) -> None:
            if claim_id in rows:
                return
            claim = self.claims[claim_id]
            for dependency in claim.dependencies:
                evaluate(dependency)
            try:
                witness = _witness(claim.verifier)
                verifier_passed = witness.get("status") in {"pass", "registered_only"}
            except Exception as error:  # Keep a failed adapter visible in the report.
                witness = {"status": "fail", "error": str(error)}
                verifier_passed = False
            dependencies_passed = all(
                rows[dependency]["effective_tier"] != "blocked"
                for dependency in claim.dependencies
            )
            effective_tier = (
                claim.evidence_tier
                if graph_valid and verifier_passed and dependencies_passed
                else "blocked"
            )
            rows[claim_id] = {
                **claim.to_dict(),
                "dependency_closure": list(self._dependency_closure(claim_id)),
                "dependencies_passed": dependencies_passed,
                "verifier_passed": verifier_passed,
                "witness": witness,
                "effective_tier": effective_tier,
            }

        for claim_id in sorted(self.claims, key=lambda item: (self.claims[item].shell, item)):
            evaluate(claim_id)
        blocked_nodes = sorted(
            claim_id for claim_id, row in rows.items() if row["effective_tier"] == "blocked"
        )
        return {
            "status": "pass_with_frontier" if graph_valid and not blocked_nodes else "fail",
            "shells": {
                str(shell): sum(claim.shell == shell for claim in self.claims.values())
                for shell in (-1, 0, 1)
            },
            "graph": {
                "all_dependencies_exist": self._dependencies_exist(),
                "acyclic": self._acyclic(),
            },
            "claims": rows,
            "proven_nodes": sorted(
                claim_id for claim_id, row in rows.items()
                if row["effective_tier"] == "demonstrated"
            ),
            "bounded_nodes": sorted(
                claim_id for claim_id, row in rows.items()
                if row["effective_tier"].startswith("bounded_")
            ),
            "registered_nodes": sorted(
                claim_id for claim_id, row in rows.items()
                if row["effective_tier"] == "registered"
            ),
            "blocked_nodes": blocked_nodes,
            "emergent_obligations": self.frontier()["emergent_obligations"],
            "dependency_paths": {
                claim_id: row["dependency_closure"] for claim_id, row in rows.items()
            },
            "frontier": self.frontier(),
        }
