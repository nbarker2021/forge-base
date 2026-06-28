"""Source-grounded transport obligations for the CMPLX-R30 proof surface."""
from __future__ import annotations

from typing import Any

from .chart_codec_d4 import verify_chart_codec_d4
from .g2_f4_t5_conjugate import verify_conjugate_triple
from .jordan_j3 import verify_j3o_axioms
from .ledger.build import (
    NIEMEIER_FORMS,
    component_coxeter_number,
    terminal_discriminant_profile,
)
from .ledger.roots import parse_root_system_label


CLASSIFICATIONS = frozenset(
    {
        "demonstrated",
        "bounded_local",
        "bounded_external",
        "registered_landing_forms",
        "open",
    }
)


def transport_obligations() -> list[dict[str, str]]:
    """Return the four transport layers with explicit proof boundaries."""
    return [
        {
            "id": "LCR_TO_D4_AXIS_SHEET",
            "source_object": "{0,1}^3 LCR chart state",
            "target_object": "D4-style (axis, sheet) token",
            "map": "ANTIPODAL_LABEL[state], SHEET_SIGN[state]",
            "preserved_quantity": "lossless recovery of all eight chart states",
            "failure_condition": "two chart states share one (axis, sheet) token",
            "witness": "verify_chart_codec_d4",
            "classification": "demonstrated",
            "proof_boundary": "finite codec; does not derive a cold-start token from depth N",
        },
        {
            "id": "D4_TO_J3O_DIAGONAL_CARRIER",
            "source_object": "LCR diagonal chart state and shell strata",
            "target_object": "J3(O) diagonal and trace-2 idempotent carrier",
            "map": "(L,C,R) -> diag(L,C,R)",
            "preserved_quantity": "trace strata, diagonal idempotency, LR/Weyl permutation",
            "failure_condition": "Jordan idempotency or LR permutation preservation fails",
            "witness": "verify_j3o_axioms",
            "classification": "demonstrated",
            "proof_boundary": "diagonal carrier is finite; broader F4 transport is not implied automatically",
        },
        {
            "id": "J3O_TO_G2_F4_T5A_ROUTE",
            "source_object": "J3(O) chart carrier",
            "target_object": "G2 -> F4 -> T5A conjugate route",
            "map": "conjugate_triple_route(N, enumeration_bit_fn)",
            "preserved_quantity": "bounded paired route metadata across at most three named stages",
            "failure_condition": "bounded route exceeds three stages or is mistaken for a depth-only readout",
            "witness": "verify_conjugate_triple",
            "classification": "bounded_local",
            "proof_boundary": "local oracle-backed classifier exists; it does not derive the bit from depth N",
        },
        {
            "id": "EXCEPTIONAL_ROUTE_TO_NIEMEIER_LANDING_FORMS",
            "source_object": "exceptional-group route metadata",
            "target_object": "rank-24 Niemeier and Leech landing-form registry",
            "map": "registered terminal IDs and component product sheets",
            "preserved_quantity": "named terminal root-system metadata",
            "failure_condition": "landing form is treated as computation without a proved fingerprint map",
            "witness": "ledger.build.NIEMEIER_FORMS and lookup cache registry",
            "classification": "registered_landing_forms",
            "proof_boundary": "landing forms are registered targets, not automatic proof closure",
        },
    ]


def verify_niemeier_landing_registry() -> dict[str, Any]:
    """Report registered rank-24 targets without claiming a computed lift."""
    return {
        "status": "registered_only",
        "landing_form_count": len(NIEMEIER_FORMS),
        "fingerprint_map_proved": False,
        "proof_boundary": "registered terminal targets; no proved fingerprint-to-landing map",
    }


def verify_niemeier_root_shell_profiles() -> dict[str, Any]:
    """Verify the bounded ADE profile map without claiming overlattice glue."""
    rootful = []
    rootless = []
    for terminal_id, root_system, declared_h, _note in NIEMEIER_FORMS:
        if root_system == "rootless":
            rootless.append(terminal_id)
            continue
        components = parse_root_system_label(root_system)
        component_h = {
            component_coxeter_number(family, rank)
            for family, rank, _multiplicity in components
        }
        profile = terminal_discriminant_profile(root_system)
        rootful.append(
            {
                "terminal_id": terminal_id,
                "root_system": root_system,
                "rank": sum(rank * multiplicity for _family, rank, multiplicity in components),
                "declared_coxeter_number": declared_h,
                "component_coxeter_numbers": sorted(component_h),
                "discriminant_profile": profile,
            }
        )
    all_rootful_ranks_are_24 = all(row["rank"] == 24 for row in rootful)
    all_declared_coxeter_numbers_match = all(
        row["component_coxeter_numbers"] == [row["declared_coxeter_number"]]
        for row in rootful
    )
    all_required_indices_are_integral = all(
        isinstance(row["discriminant_profile"]["required_overlattice_index"], int)
        for row in rootful
    )
    return {
        "status": (
            "pass"
            if (
                len(rootful) == 23
                and len(rootless) == 1
                and all_rootful_ranks_are_24
                and all_declared_coxeter_numbers_match
                and all_required_indices_are_integral
            )
            else "fail"
        ),
        "rootful_terminal_count": len(rootful),
        "rootless_terminal_count": len(rootless),
        "all_rootful_ranks_are_24": all_rootful_ranks_are_24,
        "all_declared_coxeter_numbers_match": all_declared_coxeter_numbers_match,
        "all_required_indices_are_integral": all_required_indices_are_integral,
        "exact_glue_cosets_proved": False,
        "scope": "bounded ADE root-shell and discriminant profiles only",
        "rootful_profiles": rootful,
        "rootless_terminals": rootless,
    }


def verify_niemeier_direct_sum_index_one_landings() -> dict[str, Any]:
    """Identify terminals whose root shell is already even unimodular."""
    terminal_ids = sorted(
        terminal_id
        for terminal_id, root_system, _declared_h, _note in NIEMEIER_FORMS
        if root_system != "rootless"
        and terminal_discriminant_profile(root_system)["required_overlattice_index"] == 1
    )
    return {
        "status": "pass" if terminal_ids == ["Niemeier:E8^3"] else "fail",
        "terminal_ids": terminal_ids,
        "exact_at_root_shell_level": terminal_ids == ["Niemeier:E8^3"],
        "semantic_landing_from_n_proved": False,
        "scope": (
            "determinant-one direct-sum root-shell landing only; "
            "does not derive a terminal from N"
        ),
    }


def verify_transport_obligations(max_depth: int = 4096) -> dict[str, Any]:
    """Verify local witnesses and keep wider lifts visibly open."""
    rows = transport_obligations()
    required = {
        "id",
        "source_object",
        "target_object",
        "map",
        "preserved_quantity",
        "failure_condition",
        "witness",
        "classification",
        "proof_boundary",
    }
    all_rows_have_required_fields = all(required <= set(row) for row in rows)
    valid_classifications = all(row["classification"] in CLASSIFICATIONS for row in rows)

    local_witness_results = {
        "LCR_TO_D4_AXIS_SHEET": verify_chart_codec_d4(max_depth=max_depth),
        "D4_TO_J3O_DIAGONAL_CARRIER": verify_j3o_axioms(),
        "J3O_TO_G2_F4_T5A_ROUTE": verify_conjugate_triple(max_depth=min(max_depth, 256)),
        "EXCEPTIONAL_ROUTE_TO_NIEMEIER_LANDING_FORMS": verify_niemeier_landing_registry(),
    }
    local_witnesses_pass = all(
        result["status"] in {"pass", "registered_only"}
        for result in local_witness_results.values()
    )
    demonstrated_count = sum(row["classification"] == "demonstrated" for row in rows)
    open_lift_count = len(rows) - demonstrated_count
    all_lifts_demonstrated = open_lift_count == 0
    status = (
        "pass_with_open_lifts"
        if all_rows_have_required_fields and valid_classifications and local_witnesses_pass
        else "fail"
    )
    return {
        "status": status,
        "row_count": len(rows),
        "demonstrated_count": demonstrated_count,
        "open_lift_count": open_lift_count,
        "all_rows_have_required_fields": all_rows_have_required_fields,
        "valid_classifications": valid_classifications,
        "local_witnesses_pass": local_witnesses_pass,
        "all_lifts_demonstrated": all_lifts_demonstrated,
        "local_witness_results": local_witness_results,
        "rows": rows,
    }
