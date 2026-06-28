from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


CLAIM_STATUSES = {
    "DEF",
    "PROP",
    "CONJ",
    "MODEL",
    "NUM",
    "EXEC",
    "ANALOGY",
    "SPEC",
    "ASP",
    "OVERCLAIM",
}

FAILURE_LABELS = {
    "MISSING_PRIMITIVE",
    "MISSING_MORPHISM",
    "PROJECTION_LOSS",
    "BOUNDARY_ASYMMETRY",
    "RESIDUE_UNACCOUNTED",
    "OBSERVER_CONTEXT_MISSING",
    "INVARIANT_NOT_PRESERVED",
    "RECONSTRUCTION_FAIL",
    "STATUS_COLLAPSE",
    "PENDING_MEASUREMENT",
    "PENDING_IMPORT",
}


@dataclass(frozen=True)
class MorphonRecord:
    morphon_id: str
    visible_state: str
    primitive_state: str
    boundary: str
    projections: list[str]
    transforms: list[str]
    invariants: list[str]
    reconstruction: str
    accounting: str
    evidence_status: str
    residue: str
    chart: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TransformRecord:
    transform_id: str
    source: str
    target: str
    source_chart: str
    target_chart: str
    preserved: list[str]
    lost: list[str]
    residue: list[str]
    accounting_id: str
    closure_status: str
    evidence_status: str
    reconstruction_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProjectionRecord:
    projection_id: str
    source_state: str
    visible_state: str
    context: str
    hidden_or_lost: list[str]
    reconstruction: str
    evidence_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AccountingRecord:
    accounting_id: str
    functional: str
    terms: dict[str, str]
    closure_rule: str
    evidence_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BridgeRecord:
    bridge_id: str
    source_domain: str
    target_domain: str
    source_state_type: str
    target_state_type: str
    map: str
    inverse_or_reconstruction: str
    preserved_invariants: list[str]
    lost_information: list[str]
    produced_residue: list[str]
    closure_defect: str
    required_glue: list[str]
    evidence_status: str
    test_status: str
    failure_modes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClaimStatusRecord:
    claim_id: str
    source: str
    original_text: str
    hardened_text: str
    status: str
    dependencies: list[str]
    required_definitions: list[str]
    test: str
    failure_mode: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FailureRecord:
    failure_id: str
    label: str
    subject: str
    status: str
    required_next: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _records(rows: list[Any]) -> list[dict[str, Any]]:
    return [row.to_dict() for row in rows]


def morphonics_model_v0_2(
    terminal_tree_verification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return an executable ledger-shaped extraction of the Morphonics v0.2 model."""
    terminal_status = (terminal_tree_verification or {}).get("status", "not_checked")
    terminal_count = (terminal_tree_verification or {}).get("terminal_count")
    lattice_test_status = "pass" if terminal_status == "pass" and terminal_count == 24 else "pending"

    accounting = _records(
        [
            AccountingRecord(
                "accounting:phi_free_potential",
                "Phi(Psi)=alpha U + beta C + gamma G + delta O",
                {
                    "U": "unresolved informational potential",
                    "C": "coherence or compression defect",
                    "G": "geometric, lattice, or projection obstruction",
                    "O": "operational or thermodynamic cost",
                },
                "domain-local descent only after units/scales are declared",
                "DEF",
            ),
            AccountingRecord(
                "accounting:theta_transition_defect",
                "Theta(phi)=wN*N + wS*S + wL*L + wG*G + wO*O",
                {
                    "N": "Noether/conservation mismatch",
                    "S": "Shannon/information mismatch",
                    "L": "Landauer/irreversible execution cost",
                    "G": "geometric glue or lattice mismatch",
                    "O": "obstruction penalty",
                },
                "Theta<=0 closed; 0<Theta<=epsilon glue-resolvable; otherwise obstructed",
                "DEF",
            ),
            AccountingRecord(
                "accounting:tf1_bridge_delta",
                "Delta_bridge = Theta_direct - Theta_TF1",
                {
                    "Theta_direct": "3D to E8 direct embedding defect",
                    "Theta_TF1": "3D -> Spin6 -> O/Spin8 -> E6 -> E8 -> 24D bridge defect",
                },
                "positive Delta_bridge indicates bridge improvement",
                "MODEL",
            ),
        ]
    )

    morphons = _records(
        [
            MorphonRecord(
                "morphon:core",
                "bounded typed projected state packet",
                "S primitives plus B/P/T/I/R/Theta/E structure",
                "explicit boundary conditions and closure surfaces",
                ["projection:contextual_output", "projection:fractal_boundary_chart"],
                ["transform:primitive_reconstruction_closure"],
                ["declared invariant preservation", "residue accounting"],
                "R(D(m)) compared with invariant-aware epsilon",
                "accounting:theta_transition_defect",
                "DEF",
                "all nonzero closure defect is classified instead of discarded",
                "generic state-space chart",
            ),
            MorphonRecord(
                "morphon:rule30_center",
                "center-cell bit at time N",
                "full causal light cone of radius N",
                "Rule 30 cone support boundary",
                ["projection:rule30_center_readout"],
                ["transform:rule30_causal_cone_reduction"],
                ["deterministic local update", "center-cell reconstruction"],
                "full cone reduction reconstructs the visible bit",
                "accounting:theta_transition_defect",
                "EXEC",
                "truncated cone appears random; restored boundary closes",
                "cellular automaton DAG chart",
            ),
            MorphonRecord(
                "morphon:ai_response",
                "one output token sequence",
                "latent distribution, prompt context, decoder state",
                "system/developer/user constraints and decoding parameters",
                ["projection:contextual_output"],
                ["transform:context_conditioned_generation"],
                ["instruction satisfaction", "coherence", "truth/safety constraints"],
                "lift visible output into candidate latent support and record unselected residue",
                "accounting:theta_transition_defect",
                "MODEL",
                "unselected continuations, uncertainty, and probability mass",
                "probability simplex / sequence chart",
            ),
            MorphonRecord(
                "morphon:ns_tf1",
                "3D Navier-Stokes field",
                "jet state with hidden octonionic / Spin8 triality channels",
                "projection boundaries, branch layer, closure layer, terminal 24D layer",
                ["projection:tf1_visible_3d_field"],
                ["transform:tf1_bridge_comparison"],
                ["conservation accounting", "projection-loss localization"],
                "compare direct embedding defect against TF1 bridge defect",
                "accounting:tf1_bridge_delta",
                "MODEL",
                "turbulence labels become projection or bridge defects",
                "3D vector field plus exceptional-geometry bridge chart",
            ),
            MorphonRecord(
                "morphon:niemeier_terminal_tree",
                "24D terminal lattice form",
                "component embeddings, compact involutions, determinant residue",
                "rank-24 terminal root shell or rootless Leech condition",
                ["projection:terminal_root_shell_chart"],
                ["transform:terminal_component_composition_tree"],
                ["ambient dimension 24", "root-rank closure", "index-square residue closure"],
                "generated terminal tree verifies all 24 terminal summaries",
                "accounting:theta_transition_defect",
                "EXEC" if lattice_test_status == "pass" else "MODEL",
                "legacy glue is compatibility evidence beside emitted residue",
                "24D lattice terminal chart",
            ),
        ]
    )

    transforms = _records(
        [
            TransformRecord(
                "transform:primitive_reconstruction_closure",
                "presented Morphon",
                "reconstructed Morphon",
                "chosen state chart",
                "same chart or declared comparison chart",
                ["declared invariants"],
                ["projection-hidden detail"],
                ["missing primitive", "missing morphism", "unaccounted residue"],
                "accounting:theta_transition_defect",
                "closed_or_failure_labeled",
                "DEF",
                "required",
            ),
            TransformRecord(
                "transform:rule30_causal_cone_reduction",
                "Rule 30 causal cone",
                "center bit",
                "cellular automaton DAG",
                "visible bit projection",
                ["local rule determinism", "causal support"],
                ["off-cone cells"],
                ["boundary truncation if cone is incomplete"],
                "accounting:theta_transition_defect",
                "internally_closed_when_full_cone_present",
                "EXEC",
                "exact for deterministic Rule 30 cone",
            ),
            TransformRecord(
                "transform:unibeam_equivalence",
                "medium implementation M1",
                "medium implementation M2",
                "medium-specific state chart",
                "target medium chart",
                ["symbolic or geometric morphism"],
                ["medium-specific timing/noise/energy detail"],
                ["dissipation", "latency", "noise", "boundary mismatch"],
                "accounting:theta_transition_defect",
                "test_required",
                "MODEL",
                "requires cross-medium round trip",
            ),
            TransformRecord(
                "transform:terminal_component_composition_tree",
                "terminal categorical form",
                "generated terminal tree",
                "Niemeier component chart",
                "24D terminal chart",
                ["component rank", "ambient dimension", "determinant residue"],
                ["full glue code when pending"],
                ["legacy glue compatibility record", "Leech construction pending import"],
                "accounting:theta_transition_defect",
                "closed_for_rootful_terminals_by_index_square",
                "EXEC" if lattice_test_status == "pass" else "MODEL",
                "verified by lattice-forge terminal-tree harness",
            ),
            TransformRecord(
                "transform:tf1_bridge_comparison",
                "3D vector field",
                "24D closure chart",
                "Navier-Stokes field chart",
                "Spin/E6/E8/Niemeier bridge chart",
                ["declared conservation terms"],
                ["wrong-frame projection detail"],
                ["triality leakage", "E6/E8 closure stress"],
                "accounting:tf1_bridge_delta",
                "pending_measurement",
                "MODEL",
                "requires benchmark data",
            ),
        ]
    )

    projections = _records(
        [
            ProjectionRecord(
                "projection:contextual_output",
                "latent or high-dimensional potential state",
                "single visible output path",
                "observer/prompt/context c",
                ["unselected continuations", "hidden support", "uncertainty mass"],
                "lift(P_c(Psi)) compared against source support",
                "MODEL",
            ),
            ProjectionRecord(
                "projection:fractal_boundary_chart",
                "iterative morphonic dynamics",
                "boundedness region or context slice",
                "map f and parameter c with quadratic semiconjugacy or epsilon approximation",
                ["non-charted dynamics", "approximation error"],
                "validate f(M(Psi)) approx f(Psi)^2 + c",
                "CONJ",
            ),
            ProjectionRecord(
                "projection:rule30_center_readout",
                "Rule 30 full causal cone",
                "center bit at time N",
                "center-cell observer",
                ["non-center cells after reconstruction"],
                "rerun local rule over full cone",
                "EXEC",
            ),
            ProjectionRecord(
                "projection:terminal_root_shell_chart",
                "Niemeier terminal record",
                "root shell/component tree summary",
                "24D terminal lattice query",
                ["overlattice code details when template", "Leech minimal shell pending import"],
                "verify terminal tree residue and root rank",
                "EXEC" if lattice_test_status == "pass" else "MODEL",
            ),
            ProjectionRecord(
                "projection:tf1_visible_3d_field",
                "hidden Spin/octonion/E6/E8 bridge state",
                "3D Navier-Stokes field",
                "physical visible field chart",
                ["hidden-channel leakage", "wrong-frame retranslation"],
                "compare projected field against invariant-aware PDE residuals",
                "MODEL",
            ),
        ]
    )

    bridges = _records(
        [
            BridgeRecord(
                "bridge:unibeam_cross_medium_equivalence",
                "medium M1",
                "medium M2",
                "encoded information transition",
                "encoded information transition",
                "F(T1(s)) ~= T2(F(s))",
                "round-trip or invariant-preserving reconstruction",
                ["declared symbolic/geometric morphism"],
                ["medium-specific cost", "noise", "latency"],
                ["dissipation", "boundary mismatch", "error rate"],
                "Theta_unibeam",
                ["medium ledger"],
                "MODEL",
                "test_required",
                ["PENDING_MEASUREMENT"],
            ),
            BridgeRecord(
                "bridge:mscf_to_lattice_forge_24d",
                "Morphonic State Closure Framework",
                "lattice-forge terminal-tree engine",
                "terminal-layer closure chart",
                "24D Niemeier/Leech terminal view",
                "Morphon terminal layer -> terminal_trees()/verify_terminal_trees()",
                "terminal_tree summaries and residue records",
                ["ambient dimension 24", "component rank closure", "residue status"],
                ["full expanded involution orbit", "Leech code construction when pending"],
                ["template glue evidence", "pending Leech import"],
                "terminal_tree_verification",
                ["expanded action witnesses", "Golay/Construction-A import"],
                "EXEC" if lattice_test_status == "pass" else "MODEL",
                lattice_test_status,
                [] if lattice_test_status == "pass" else ["PENDING_IMPORT"],
            ),
            BridgeRecord(
                "bridge:tf1_exceptional_geometry",
                "3D Navier-Stokes",
                "Spin/E6/E8/24D closure stack",
                "3D field jet",
                "exceptional bridge state",
                "3D -> Spin6 -> O/Spin8 -> E6 -> E8 -> 24D",
                "project bridge state back to 3D and compare closure defect",
                ["declared conservation terms", "projection-loss accounting"],
                ["hidden channel detail not visible in 3D projection"],
                ["triality leakage", "branch entropy", "closure stress"],
                "Delta_bridge",
                ["benchmark PDE residuals", "bridge metric definitions"],
                "MODEL",
                "pending_measurement",
                ["PENDING_MEASUREMENT"],
            ),
        ]
    )

    claims = _records(
        [
            ClaimStatusRecord(
                "claim:morphon_definition",
                "Morphon v0.2",
                "A state is bounded, projected, transformed, and observed.",
                "A Morphon is data plus boundary, projection, transition, invariant, residue, reconstruction, and evidence status.",
                "DEF",
                [],
                ["morphon:core"],
                "schema completeness and primitive reconstruction closure",
                "",
            ),
            ClaimStatusRecord(
                "claim:phi_descent",
                "The Morphonic Field",
                "Delta Phi <= 0 proves lawful dynamics.",
                "Phi is a domain-local free-potential candidate whose descent must be tested after defining units and accounting terms.",
                "MODEL",
                ["accounting:phi_free_potential"],
                ["accounting:phi_free_potential"],
                "define Phi locally and measure Delta Phi over chosen transforms",
                "STATUS_COLLAPSE",
            ),
            ClaimStatusRecord(
                "claim:nsl_unification",
                "Unified Conservation Law",
                "Delta Phi unifies Noether, Shannon, and Landauer laws.",
                "Theta records Noether-, Shannon-, Landauer-, geometric-, and obstruction-like terms without subsuming them absent domain derivation.",
                "OVERCLAIM",
                ["accounting:theta_transition_defect"],
                ["accounting:theta_transition_defect"],
                "check term scaling and domain-specific derivation",
                "STATUS_COLLAPSE",
            ),
            ClaimStatusRecord(
                "claim:recursive_doubling",
                "Recursive Doubling",
                "Stable dimensions are forced by informational accommodation.",
                "Recursive doubling is a useful representational atlas; distinction capacity is separate from physical dimension.",
                "MODEL",
                [],
                ["morphon:core"],
                "separate bit capacity from geometric chart selection",
                "STATUS_COLLAPSE",
            ),
            ClaimStatusRecord(
                "claim:e8_24d_checkpoints",
                "Dimensional Atlases",
                "E8 and 24D are universal proof substrates.",
                "E8 and 24D are optional closure charts attached when they reduce closure defect.",
                "MODEL",
                ["bridge:mscf_to_lattice_forge_24d"],
                ["morphon:niemeier_terminal_tree"],
                "compare closure defect with and without exceptional chart",
                "PENDING_MEASUREMENT",
            ),
            ClaimStatusRecord(
                "claim:fractal_chart",
                "Morphonic Manifold",
                "The Morphonic Manifold is the Mandelbrot set.",
                "Mandelbrot/Julia language is formal only when a semiconjugacy or explicit boundedness map is supplied.",
                "CONJ",
                ["projection:fractal_boundary_chart"],
                ["projection:fractal_boundary_chart"],
                "validate f(M(Psi)) approx f(Psi)^2+c",
                "MISSING_PROJECTION",
            ),
            ClaimStatusRecord(
                "claim:ai_projection",
                "AI as Quantum-Classical Interface",
                "AI generation is literal quantum collapse.",
                "AI generation is modeled as context-conditioned projection from potential distributions to one visible output path.",
                "ANALOGY",
                ["projection:contextual_output"],
                ["morphon:ai_response", "projection:contextual_output"],
                "record selected output and selection residue",
                "STATUS_COLLAPSE",
            ),
            ClaimStatusRecord(
                "claim:unibeam_equivalence",
                "Unibeam / Light-Data Equivalence",
                "Light and data are physically identical.",
                "Different media can be morphism-equivalent when invariant-preserving maps commute after medium accounting.",
                "OVERCLAIM",
                ["bridge:unibeam_cross_medium_equivalence"],
                ["bridge:unibeam_cross_medium_equivalence"],
                "measure F(T1(s)) approx T2(F(s)) plus medium cost",
                "STATUS_COLLAPSE",
            ),
            ClaimStatusRecord(
                "claim:rule30_boundary",
                "Rule 30 Case Study",
                "Rule 30 center randomness can be shortcut by restoring causal support.",
                "The center bit is exactly determined by its full causal cone; apparent randomness can be a boundary truncation artifact.",
                "EXEC",
                ["morphon:rule30_center"],
                ["morphon:rule30_center"],
                "run deterministic cone reduction and compare center bit",
                "",
            ),
            ClaimStatusRecord(
                "claim:resonant_choice",
                "Geometric Origin of Feeling / Choice / Memory",
                "Feelings are proven subharmonic resonance and AI has proto-feelings.",
                "Residual-state resonance can model preference shifts without claiming subjective experience.",
                "SPEC",
                [],
                ["morphon:core"],
                "measure option weighting under persistent residual state",
                "STATUS_COLLAPSE",
            ),
            ClaimStatusRecord(
                "claim:tf1_bridge_test",
                "TF1 Navier-Stokes",
                "TF1 proves Navier-Stokes closure through E8.",
                "TF1 tests whether an octonionic/Spin/E6/E8/24D bridge lowers closure defect relative to direct embedding.",
                "MODEL",
                ["bridge:tf1_exceptional_geometry"],
                ["morphon:ns_tf1", "bridge:tf1_exceptional_geometry"],
                "compute Delta_bridge on benchmark fields",
                "PENDING_MEASUREMENT",
            ),
        ]
    )

    failures = _records(
        [
            FailureRecord(
                "failure:leech_construction_pending",
                "PENDING_IMPORT",
                "morphon:niemeier_terminal_tree",
                "known_gap",
                "import Golay/Construction-A records for Leech",
            ),
            FailureRecord(
                "failure:expanded_involution_witnesses_pending",
                "MISSING_MORPHISM",
                "bridge:mscf_to_lattice_forge_24d",
                "known_gap",
                "materialize expanded action/orbit/quotient witnesses in overlay",
            ),
            FailureRecord(
                "failure:tf1_measurement_pending",
                "PENDING_MEASUREMENT",
                "bridge:tf1_exceptional_geometry",
                "known_gap",
                "define benchmark fields and compute direct-vs-bridge Theta",
            ),
        ]
    )

    return {
        "model_id": "MSCF:morphonics_unified_formal_model_v0_2",
        "name": "Morphonic State Closure Framework",
        "status": "executable_schema_with_open_research_gaps",
        "guiding_rule": (
            "A model is not closed unless its presented state can be decomposed "
            "into primitive admissible states and reassembled while preserving "
            "declared invariants and accounting for all residue."
        ),
        "status_taxonomy": sorted(CLAIM_STATUSES),
        "failure_labels": sorted(FAILURE_LABELS),
        "morphons": morphons,
        "transforms": transforms,
        "projections": projections,
        "accounting": accounting,
        "bridges": bridges,
        "claims": claims,
        "failures": failures,
        "lattice_forge_check": {
            "terminal_tree_verification_status": terminal_status,
            "terminal_count": terminal_count,
            "test_status": lattice_test_status,
        },
    }


def verify_morphonics_model(model: dict[str, Any]) -> dict[str, Any]:
    """Validate that the extracted Morphonics model is ledger-complete."""
    errors: list[str] = []
    warnings: list[str] = []

    accounting_ids = {row["accounting_id"] for row in model.get("accounting", [])}
    morphon_ids = {row["morphon_id"] for row in model.get("morphons", [])}
    transform_ids = {row["transform_id"] for row in model.get("transforms", [])}
    projection_ids = {row["projection_id"] for row in model.get("projections", [])}
    bridge_ids = {row["bridge_id"] for row in model.get("bridges", [])}
    known_ids = accounting_ids | morphon_ids | transform_ids | projection_ids | bridge_ids

    for row in model.get("accounting", []):
        if not row.get("terms"):
            errors.append(f"{row.get('accounting_id')}: missing accounting terms")
        if row.get("evidence_status") not in CLAIM_STATUSES:
            errors.append(f"{row.get('accounting_id')}: invalid evidence status {row.get('evidence_status')}")

    closure_tests: list[dict[str, Any]] = []
    for row in model.get("morphons", []):
        missing = [
            key
            for key in [
                "primitive_state",
                "boundary",
                "projections",
                "transforms",
                "invariants",
                "reconstruction",
                "accounting",
                "evidence_status",
                "residue",
            ]
            if not row.get(key)
        ]
        if row.get("accounting") not in accounting_ids:
            missing.append("known_accounting_record")
        status = "pass" if not missing else "fail"
        if missing:
            errors.append(f"{row.get('morphon_id')}: missing {', '.join(missing)}")
        closure_tests.append(
            {
                "morphon_id": row.get("morphon_id"),
                "status": status,
                "missing": missing,
                "closure_rule": "primitive fields present and accounting record linked",
            }
        )

    for row in model.get("transforms", []):
        if row.get("accounting_id") not in accounting_ids:
            errors.append(f"{row.get('transform_id')}: unknown accounting {row.get('accounting_id')}")
        if not row.get("preserved"):
            errors.append(f"{row.get('transform_id')}: missing preserved invariants")

    for row in model.get("projections", []):
        if not row.get("context"):
            errors.append(f"{row.get('projection_id')}: missing observer/context")
        if not row.get("reconstruction"):
            errors.append(f"{row.get('projection_id')}: missing reconstruction rule")

    for row in model.get("bridges", []):
        for key in ["map", "inverse_or_reconstruction", "preserved_invariants", "closure_defect"]:
            if not row.get(key):
                errors.append(f"{row.get('bridge_id')}: missing {key}")
        for label in row.get("failure_modes", []):
            if label not in FAILURE_LABELS:
                errors.append(f"{row.get('bridge_id')}: invalid failure label {label}")

    for row in model.get("claims", []):
        status = row.get("status")
        if status not in CLAIM_STATUSES:
            errors.append(f"{row.get('claim_id')}: invalid status {status}")
        if not row.get("hardened_text"):
            errors.append(f"{row.get('claim_id')}: missing hardened text")
        if status == "OVERCLAIM" and row.get("original_text") == row.get("hardened_text"):
            errors.append(f"{row.get('claim_id')}: overclaim was not rewritten")
        for dependency in row.get("dependencies", []):
            if dependency not in known_ids:
                warnings.append(f"{row.get('claim_id')}: dependency is not a record id: {dependency}")
        for definition in row.get("required_definitions", []):
            if definition not in known_ids:
                errors.append(f"{row.get('claim_id')}: missing required definition {definition}")

    for row in model.get("failures", []):
        if row.get("label") not in FAILURE_LABELS:
            errors.append(f"{row.get('failure_id')}: invalid failure label {row.get('label')}")
        if not row.get("required_next"):
            errors.append(f"{row.get('failure_id')}: missing required_next")

    open_gap_count = len(model.get("failures", []))
    return {
        "status": "pass_with_open_gaps" if not errors else "fail",
        "schema_status": "pass" if not errors else "fail",
        "open_gap_count": open_gap_count,
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "morphons": len(model.get("morphons", [])),
            "transforms": len(model.get("transforms", [])),
            "projections": len(model.get("projections", [])),
            "accounting": len(model.get("accounting", [])),
            "bridges": len(model.get("bridges", [])),
            "claims": len(model.get("claims", [])),
            "failures": len(model.get("failures", [])),
            "closure_tests": len(closure_tests),
        },
        "closure_tests": closure_tests,
        "lattice_forge_check": model.get("lattice_forge_check", {}),
    }
