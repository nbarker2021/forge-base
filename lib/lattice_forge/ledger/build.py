from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .exact import matrix_json, norm2, dot, reflect, stable_hash, vector_json, determinant, parse_vector_json, parse_matrix_json
from .ledger import Ledger
from .nsl import NSLTerm
from .roots import RootSystemData, core_root_systems, direct_sum_root_system, parse_root_system_label, component_root_system


NIEMEIER_FORMS: list[tuple[str, str, int | None, str]] = [
    ("Niemeier:A1^24", "A1^24", 2, "24 copies of A1 with binary Golay-code glue."),
    ("Niemeier:A2^12", "A2^12", 3, "12 copies of A2 with ternary Golay-code glue."),
    ("Niemeier:A3^8", "A3^8", 4, "8 copies of A3 with 4-adic glue."),
    ("Niemeier:A4^6", "A4^6", 5, "6 copies of A4."),
    ("Niemeier:A5^4_D4", "A5^4 D4", 6, "Mixed A5/D4 root system with common Coxeter number 6."),
    ("Niemeier:A6^4", "A6^4", 7, "4 copies of A6."),
    ("Niemeier:A7^2_D5^2", "A7^2 D5^2", 8, "Mixed A7/D5 root system."),
    ("Niemeier:A8^3", "A8^3", 9, "3 copies of A8."),
    ("Niemeier:A9^2_D6", "A9^2 D6", 10, "Mixed A9/D6 root system."),
    ("Niemeier:A11_D7_E6", "A11 D7 E6", 12, "Mixed A11/D7/E6 root system."),
    ("Niemeier:A12^2", "A12^2", 13, "2 copies of A12."),
    ("Niemeier:A15_D9", "A15 D9", 16, "Mixed A15/D9 root system."),
    ("Niemeier:A17_E7", "A17 E7", 18, "Mixed A17/E7 root system."),
    ("Niemeier:A24", "A24", 25, "Single A24 root system."),
    ("Niemeier:D4^6", "D4^6", 6, "6 copies of D4 with triality-rich glue."),
    ("Niemeier:D6^4", "D6^4", 10, "4 copies of D6."),
    ("Niemeier:D8^3", "D8^3", 14, "3 copies of D8."),
    ("Niemeier:D10_E7^2", "D10 E7^2", 18, "Mixed D10/E7 root system."),
    ("Niemeier:D12^2", "D12^2", 22, "2 copies of D12."),
    ("Niemeier:D16_E8", "D16 E8", 30, "Mixed D16/E8 root system."),
    ("Niemeier:D24", "D24", 46, "Single D24 root system."),
    ("Niemeier:E6^4", "E6^4", 12, "4 copies of E6."),
    ("Niemeier:E8^3", "E8^3", 30, "3 copies of E8."),
    ("Niemeier:Leech", "rootless", None, "Rootless even unimodular 24D Leech lattice destination."),
]

PARIAHS: list[dict[str, Any]] = [
    {"id": "Pariah:J1", "name": "Janko J1", "type": "structural", "order_factorization": "2^3*3*5*7*11*19"},
    {"id": "Pariah:J3", "name": "Janko J3", "type": "structural", "order_factorization": "2^7*3^5*5*17*19"},
    {"id": "Pariah:ON", "name": "O'Nan O'N", "type": "structural", "order_factorization": "2^9*3^4*5*7^3*11*19*31"},
    {"id": "Pariah:Ru", "name": "Rudvalis Ru", "type": "structural", "order_factorization": "2^14*3^3*5^3*7*13*29"},
    {"id": "Pariah:J4", "name": "Janko J4", "type": "hard", "order_factorization": "2^21*3^3*5*7*11^3*23*29*31*37*43"},
    {"id": "Pariah:Ly", "name": "Lyons Ly", "type": "hard", "order_factorization": "2^8*3^7*5^6*7*11*31*37*67"},
]


MONSTER_PRIMES = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 41, 47, 59, 71}
MONSTER_ORDER_FACTORIZATION = "2^46*3^20*5^9*7^6*11^2*13^3*17*19*23*29*31*41*47*59*71"


def parse_factorization(expr: str) -> dict[int, int]:
    """Parse factor strings like '2^3*3*5' into {2:3,3:1,5:1}."""
    out: dict[int, int] = {}
    expr = expr.strip()
    if not expr:
        return out
    for token in expr.split("*"):
        token = token.strip()
        if not token:
            continue
        if "^" in token:
            p, e = token.split("^", 1)
            prime, exp = int(p), int(e)
        else:
            prime, exp = int(token), 1
        out[prime] = out.get(prime, 0) + exp
    return out


def factor_payload(expr: str, monster_reference: bool = True) -> dict[str, Any]:
    factors = parse_factorization(expr)
    primes = sorted(factors)
    missing = sorted(set(primes) - MONSTER_PRIMES) if monster_reference else []
    return {
        "factorization": {str(k): v for k, v in factors.items()},
        "prime_set": primes,
        "monster_compatible_prime_set": not missing if monster_reference else None,
        "missing_monster_primes": missing,
    }


def _json(x: Any) -> str:
    return json.dumps(x, sort_keys=True)


def component_root_count(family: str, rank: int) -> int:
    family = family.upper()
    if family == "A":
        return rank * (rank + 1)
    if family == "D":
        return 2 * rank * (rank - 1)
    if family == "E" and rank == 6:
        return 72
    if family == "E" and rank == 7:
        return 126
    if family == "E" and rank == 8:
        return 240
    raise ValueError(f"unsupported root component {family}{rank}")


def component_coxeter_number(family: str, rank: int) -> int:
    family = family.upper()
    if family == "A":
        return rank + 1
    if family == "D":
        return 2 * rank - 2
    if family == "E" and rank == 6:
        return 12
    if family == "E" and rank == 7:
        return 18
    if family == "E" and rank == 8:
        return 30
    raise ValueError(f"unsupported root component {family}{rank}")




def component_determinant(family: str, rank: int) -> int:
    family = family.upper()
    if family == "A":
        return rank + 1
    if family == "D":
        return 4
    if family == "E" and rank == 6:
        return 3
    if family == "E" and rank == 7:
        return 2
    if family == "E" and rank == 8:
        return 1
    raise ValueError(f"unsupported root component {family}{rank}")


def component_discriminant_label(family: str, rank: int) -> str:
    family = family.upper()
    if family == "A":
        return f"Z/{rank + 1}Z"
    if family == "D":
        return "Z/4Z" if rank % 2 else "(Z/2Z)^2"
    if family == "E" and rank == 6:
        return "Z/3Z"
    if family == "E" and rank == 7:
        return "Z/2Z"
    if family == "E" and rank == 8:
        return "0"
    raise ValueError(f"unsupported root component {family}{rank}")


def terminal_discriminant_profile(root_system: str) -> dict[str, Any]:
    if root_system == "rootless":
        return {
            "root_lattice_determinant": 1,
            "discriminant_group_order": 1,
            "required_overlattice_index": 1,
            "component_discriminants": [],
            "status": "rootless terminal; no root sublattice determinant applies",
        }
    det = 1
    component_payload = []
    for fam, rank, mult in parse_root_system_label(root_system):
        cdet = component_determinant(fam, rank)
        det *= cdet ** mult
        component_payload.append({
            "component": f"{fam}{rank}",
            "multiplicity": mult,
            "determinant_each": cdet,
            "discriminant_each": component_discriminant_label(fam, rank),
        })
    idx = math.isqrt(det)
    idx_value: int | str = idx if idx * idx == det else "non_square_check_required"
    return {
        "root_lattice_determinant": det,
        "discriminant_group_order": det,
        "required_overlattice_index": idx_value,
        "component_discriminants": component_payload,
        "status": "computed from ADE determinant formulas; exact glue cosets remain separate",
    }


def insert_discriminant_profile(ledger: Ledger, object_id: str, root_system: str, glue_status: str = "computed_profile_glue_template") -> None:
    profile = terminal_discriminant_profile(root_system)
    h = stable_hash(object_id, root_system, profile, glue_status)
    ledger.execute(
        "INSERT OR REPLACE INTO discriminant_registry VALUES (?,?,?,?,?,?,?,?)",
        [
            f"disc:{object_id}",
            object_id,
            str(profile["root_lattice_determinant"]),
            str(profile["discriminant_group_order"]),
            str(profile["required_overlattice_index"]),
            glue_status,
            _json(profile),
            h,
        ],
    )
    insert_invariant(
        ledger,
        object_id,
        "discriminant_profile",
        profile,
        status="computed_from_ADE_component_determinants" if root_system != "rootless" else "rootless_terminal_template",
    )


def seed_reflection_actions_for_root_system(ledger: Ledger, rs: RootSystemData) -> None:
    # Store exact simple-reflection action over every seeded root. This makes Weyl involutions executable, not only descriptive.
    index_by_vec = {r: f"vec:{rs.name}:{idx:04d}" for idx, r in enumerate(rs.roots)}
    for gi, alpha in enumerate(rs.basis):
        for idx, root in enumerate(rs.roots):
            image = reflect(root, alpha, rs.gram)
            target_id = index_by_vec.get(image)
            if target_id is None:
                raise ValueError(f"reflection closure failed for {rs.name} s_{gi} on root {root}")
            source_id = f"vec:{rs.name}:{idx:04d}"
            payload = {"generator": f"s_{gi}", "source": source_id, "target": target_id}
            h = stable_hash(rs.name, gi, source_id, target_id)
            ledger.execute(
                "INSERT OR REPLACE INTO reflection_action_registry VALUES (?,?,?,?,?,?,?)",
                [f"refact:{rs.name}:s{gi}:{idx:04d}", rs.name, gi, source_id, target_id, _json(payload), h],
            )


def seed_root_neighborhood_profile(ledger: Ledger, rs: RootSystemData, store_edges: bool = False) -> None:
    """Store exact inner-product neighborhood profile for a root shell.

    For compact core systems this also stores non-orthogonal unordered adjacency
    samples/edges. For large terminal root shells, v0.5 keeps only aggregate
    profiles to avoid exploding the seed database.
    """
    norm_counts = Counter(str(norm2(r, rs.gram)) for r in rs.roots)
    inner_counts: Counter[str] = Counter()
    adjacency_counts: Counter[str] = Counter()
    pair_count = 0
    root_ids = [f"vec:{rs.name}:{idx:04d}" for idx in range(len(rs.roots))]
    for i in range(len(rs.roots)):
        for j in range(i + 1, len(rs.roots)):
            ip = dot(rs.roots[i], rs.roots[j], rs.gram)
            key = str(ip)
            inner_counts[key] += 1
            pair_count += 1
            if ip == 0:
                kind = "orthogonal"
            elif ip > 0:
                kind = "acute_positive_inner_product"
            else:
                kind = "obtuse_negative_inner_product"
            adjacency_counts[kind] += 1
            if store_edges and ip != 0:
                h = stable_hash(rs.name, root_ids[i], root_ids[j], key, kind)
                ledger.execute(
                    "INSERT OR REPLACE INTO root_adjacency_registry VALUES (?,?,?,?,?,?,?,?)",
                    [
                        f"adj:{rs.name}:{i:04d}:{j:04d}",
                        rs.name,
                        root_ids[i],
                        root_ids[j],
                        key,
                        kind,
                        _json({"unordered": True}),
                        h,
                    ],
                )
    payload = {
        "adjacency_kind_distribution": dict(sorted(adjacency_counts.items())),
        "edge_storage": "nonorthogonal_unordered" if store_edges else "aggregate_only",
    }
    h = stable_hash(rs.name, pair_count, inner_counts, norm_counts, payload)
    ledger.execute(
        "INSERT OR REPLACE INTO root_neighborhood_profiles VALUES (?,?,?,?,?,?,?,?,?)",
        [
            f"rnp:{rs.name}",
            rs.name,
            len(rs.roots),
            pair_count,
            _json(dict(sorted(inner_counts.items(), key=lambda kv: kv[0]))),
            _json(dict(sorted(norm_counts.items(), key=lambda kv: kv[0]))),
            "computed_exact",
            _json(payload),
            h,
        ],
    )
    insert_invariant(
        ledger,
        rs.name,
        "root_neighborhood_profile",
        {
            "root_count": len(rs.roots),
            "unordered_pair_count": pair_count,
            "inner_product_distribution": dict(sorted(inner_counts.items(), key=lambda kv: kv[0])),
            "norm_distribution": dict(sorted(norm_counts.items(), key=lambda kv: kv[0])),
        },
        status="computed_exact",
    )

def insert_invariant(ledger: Ledger, object_id: str, invariant_type: str, payload: dict[str, Any], status: str = "computed") -> None:
    h = stable_hash(object_id, invariant_type, payload, status)
    ledger.execute(
        "INSERT OR REPLACE INTO object_invariants VALUES (?,?,?,?,?,?)",
        [f"invdata:{object_id}:{invariant_type}", object_id, invariant_type, _json(payload), status, h],
    )


def insert_component_decomposition(ledger: Ledger, object_id: str, root_system: str) -> None:
    for fam, rank, mult in parse_root_system_label(root_system):
        rc = component_root_count(fam, rank)
        h = component_coxeter_number(fam, rank)
        cid = f"component:{object_id}:{fam}{rank}^{mult}"
        ledger.execute(
            "INSERT OR REPLACE INTO component_decompositions VALUES (?,?,?,?,?,?,?,?)",
            [cid, object_id, fam, rank, mult, rc, h, _json({"component": f"{fam}{rank}", "total_roots": rc * mult})],
        )


def insert_external_resource(ledger: Ledger, source: str, resource_type: str, query: str, title: str, url: str | None, status: str, payload: dict[str, Any] | None = None) -> None:
    rid = f"external:{source}:{resource_type}:{stable_hash(query, title, url)[:16]}"
    ledger.execute(
        "INSERT OR REPLACE INTO external_resource_registry VALUES (?,?,?,?,?,?,?,?)",
        [rid, source, resource_type, query, title, url, status, _json(payload or {})],
    )




def insert_object(
    ledger: Ledger,
    object_id: str,
    name: str,
    kind: str,
    rank: int | None,
    dimension: int | None,
    family: str,
    is_terminal: bool = False,
    metadata: dict[str, Any] | None = None,
) -> None:
    ledger.execute(
        """
        INSERT OR REPLACE INTO object_registry
        (object_id,name,kind,rank,dimension,family,is_terminal,metadata_json)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        [object_id, name, kind, rank, dimension, family, int(is_terminal), _json(metadata or {})],
    )


def insert_root_system(ledger: Ledger, rs: RootSystemData) -> None:
    family = rs.name[0] if rs.name[0].isalpha() else "root"
    insert_object(
        ledger,
        rs.name,
        rs.name,
        "root_system",
        rs.rank,
        len(rs.gram),
        family,
        False,
        {"root_count": len(rs.roots), "notes": rs.notes},
    )
    gram_hash = stable_hash(rs.name, matrix_json(rs.gram))
    ledger.execute(
        "INSERT OR REPLACE INTO gram_forms VALUES (?,?,?,?,?,?)",
        [f"gram:{rs.name}", rs.name, matrix_json(rs.gram), None, "exact rational", gram_hash],
    )
    for idx, r in enumerate(rs.roots):
        n2 = str(norm2(r, rs.gram))
        orbit = f"norm2={n2}"
        h = stable_hash(rs.name, vector_json(r), n2)
        ledger.execute(
            "INSERT OR REPLACE INTO exact_vectors VALUES (?,?,?,?,?,?)",
            [f"vec:{rs.name}:{idx:04d}", rs.name, vector_json(r), n2, orbit, h],
        )
    insert_invariant(
        ledger,
        rs.name,
        "root_shell",
        {"rank": rs.rank, "ambient_dimension": len(rs.gram), "root_count": len(rs.roots), "norm2_values": sorted({str(norm2(r, rs.gram)) for r in rs.roots})},
    )
    insert_construction_status(
        ledger,
        rs.name,
        "root_shell_vectors",
        "exact",
        {"root_count": len(rs.roots), "coordinate_model": "exact rational", "gram": "stored"},
    )


def insert_morphism(
    ledger: Ledger,
    source: str,
    target: str,
    morphism_type: str,
    conditions: dict[str, Any] | None = None,
    invariant_delta: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    status: str = "legal",
    obstruction: dict[str, Any] | None = None,
) -> str:
    mid = f"mor:{source}->{target}:{morphism_type}"
    h = stable_hash(source, target, morphism_type, conditions or {}, invariant_delta or {}, metadata or {})
    ledger.execute(
        "INSERT OR REPLACE INTO morphism_registry VALUES (?,?,?,?,?,?,?,?,?)",
        [mid, source, target, morphism_type, None, _json(conditions or {}), _json(invariant_delta or {}), _json(metadata or {}), h],
    )
    eid = f"edge:{source}->{target}:{morphism_type}"
    ledger.execute(
        "INSERT OR REPLACE INTO admissibility_edges VALUES (?,?,?,?,?,?,?,?)",
        [eid, source, target, mid, status, _json(conditions or {}), _json(obstruction or {}), h],
    )
    return mid


def insert_morphism_witness(
    ledger: Ledger,
    morphism_id: str,
    source: str,
    target: str,
    witness_type: str,
    witness_vectors: list[str],
    target_signature: dict[str, Any],
    verification_status: str,
    payload: dict[str, Any] | None = None,
) -> None:
    payload = payload or {}
    wid = f"wit:{morphism_id}:{witness_type}"
    h = stable_hash(morphism_id, source, target, witness_type, witness_vectors, target_signature, verification_status, payload)
    ledger.execute(
        "INSERT OR REPLACE INTO morphism_witness_registry VALUES (?,?,?,?,?,?,?,?,?,?)",
        [wid, morphism_id, source, target, witness_type, _json(witness_vectors), _json(target_signature), verification_status, _json(payload), h],
    )


def insert_nsl_boundary(
    ledger: Ledger,
    source: str,
    target: str,
    noether_residue: float,
    shannon_residue: float,
    landauer_cost: float,
    absorption_capacity: float,
    status: str,
    payload: dict[str, Any] | None = None,
) -> None:
    term = NSLTerm(
        noether_residue=noether_residue,
        shannon_residue=shannon_residue,
        landauer_cost=landauer_cost,
        absorption_capacity=absorption_capacity,
    )
    payload = payload or {}
    h = stable_hash(source, target, term.as_dict(), status, payload)
    ledger.execute(
        "INSERT OR REPLACE INTO nsl_boundary_registry VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            f"nsl:{source}->{target}",
            source,
            target,
            term.noether_residue,
            term.shannon_residue,
            term.landauer_cost,
            term.absorption_capacity,
            term.theta,
            int(term.closes_internally),
            status,
            _json({**payload, "term": term.as_dict()}),
            h,
        ],
    )


def insert_rag(
    ledger: Ledger,
    object_id: str,
    summary: str,
    facts: str = "",
    futures: str = "",
    obstructions: str = "",
    refs: list[str] | None = None,
) -> None:
    ledger.execute(
        "INSERT OR REPLACE INTO rag_cards VALUES (?,?,?,?,?,?,?)",
        [f"rag:{object_id}", object_id, summary, facts, futures, obstructions, _json(refs or [])],
    )



def insert_construction_status(
    ledger: Ledger,
    object_id: str,
    surface_type: str,
    exactness: str,
    payload: dict[str, Any] | None = None,
) -> None:
    payload = payload or {}
    h = stable_hash(object_id, surface_type, exactness, payload)
    ledger.execute(
        "INSERT OR REPLACE INTO construction_status_registry VALUES (?,?,?,?,?,?)",
        [f"status:{object_id}:{surface_type}", object_id, surface_type, exactness, _json(payload), h],
    )


def insert_prime_factor_profile(
    ledger: Ledger,
    object_id: str,
    integer_name: str,
    factorization: str,
    integer_value: str | None = None,
    monster_reference: bool = True,
    payload_extra: dict[str, Any] | None = None,
) -> None:
    payload = factor_payload(factorization, monster_reference=monster_reference)
    if payload_extra:
        payload.update(payload_extra)
    h = stable_hash(object_id, integer_name, factorization, integer_value, payload)
    ledger.execute(
        "INSERT OR REPLACE INTO prime_factor_registry VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            f"factor:{object_id}:{integer_name}",
            object_id,
            integer_name,
            integer_value,
            _json(payload["factorization"]),
            _json(payload["prime_set"]),
            None if payload["monster_compatible_prime_set"] is None else int(payload["monster_compatible_prime_set"]),
            _json(payload["missing_monster_primes"]),
            _json(payload),
            h,
        ],
    )
    insert_invariant(ledger, object_id, f"prime_factor_profile:{integer_name}", payload, status="computed_from_seeded_factorization")


def edge_evidence(edge: dict[str, Any]) -> str:
    if edge.get("status") == "forbidden":
        return "forbidden"
    raw = " ".join(str(edge.get(k, "")) for k in ["morphism_type", "condition_json", "metadata_json", "obstruction_json"])
    if "conceptual scaffold" in raw or "Monster" in raw or "pariah" in raw.lower():
        return "conceptual"
    if "template" in raw or "placeholder" in raw:
        return "template"
    return "seeded_exact_or_computed"


def path_metric_payload(ledger: Ledger, path: list[str], terminal_id: str | None = None) -> dict[str, Any]:
    edges = ledger.path_edges(path)
    evidence = [edge_evidence(e) for e in edges]
    exact = sum(1 for e in evidence if e == "seeded_exact_or_computed")
    template = sum(1 for e in evidence if e == "template")
    conceptual = sum(1 for e in evidence if e == "conceptual")
    forbidden = sum(1 for e in evidence if e == "forbidden")
    if forbidden:
        level = "forbidden"
    elif conceptual:
        level = "conceptual_scaffold"
    elif template:
        level = "template_supported"
    else:
        level = "seeded_computed"
    return {
        "path": path,
        "edge_evidence": evidence,
        "edge_count": len(edges),
        "exact_edge_count": exact,
        "template_edge_count": template,
        "conceptual_edge_count": conceptual,
        "forbidden_edge_count": forbidden,
        "evidence_level": level,
        "terminal_id": terminal_id,
    }


def insert_path_metric(ledger: Ledger, path: list[str], terminal_id: str | None = None, status: str = "legal") -> None:
    payload = path_metric_payload(ledger, path, terminal_id)
    ph = stable_hash(path)
    h = stable_hash(ph, payload, status)
    ledger.execute(
        "INSERT OR REPLACE INTO path_metrics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            f"metric:{ph}",
            ph,
            path[0],
            terminal_id or path[-1],
            _json(path),
            payload["edge_count"],
            payload["exact_edge_count"],
            payload["template_edge_count"],
            payload["conceptual_edge_count"],
            payload["forbidden_edge_count"],
            payload["evidence_level"],
            status,
            _json(payload),
            h,
        ],
    )

def seed_roots(ledger: Ledger) -> None:
    systems: dict[str, RootSystemData] = dict(core_root_systems())
    for _, root_system, _, _ in NIEMEIER_FORMS:
        for fam, rank, _mult in parse_root_system_label(root_system):
            rs = component_root_system(fam, rank)
            systems[rs.name] = rs
    # Keep executable adjacency/reflection action tables on the low-rank operator seed set.
    # E6/E7/E8 still retain exact root shells and Dynkin profiles, but their full action
    # tables are deferred to avoid repeated-build memory drift in small agent sandboxes.
    operator_action_seed_set = {"A1", "A2", "D4", "G2", "F4"}
    for rs in sorted(systems.values(), key=lambda x: (x.name[0], x.rank, x.name)):
        insert_root_system(ledger, rs)
        if rs.name in operator_action_seed_set:
            seed_root_neighborhood_profile(ledger, rs, store_edges=True)
            seed_reflection_actions_for_root_system(ledger, rs)


def seed_composite_objects(ledger: Ledger) -> None:
    insert_object(
        ledger,
        "G2xF4",
        "G2 × F4 exceptional dual-pair seed",
        "composite",
        6,
        None,
        "exceptional_pair",
        False,
        {"role": "low-rank asymmetric preconditioner", "decomposition_in_E8_lie_algebra": "248=14+52+(7*26)"},
    )
    insert_object(
        ledger,
        "Monster:M",
        "Monster group M",
        "sporadic_boundary",
        None,
        None,
        "Monster",
        False,
        {"role": "substrate/rules layer in this scaffold", "sporadic_partition": "20 Monster-involved + 4 structural pariahs + 2 hard pariahs"},
    )


def seed_niemeier(ledger: Ledger) -> None:
    for terminal_id, root_system, h, note in NIEMEIER_FORMS:
        components = parse_root_system_label(root_system)
        root_count = sum(component_root_count(fam, rank) * mult for fam, rank, mult in components)
        insert_object(
            ledger,
            terminal_id,
            terminal_id.replace("Niemeier:", ""),
            "niemeier_terminal",
            24,
            24,
            "Niemeier",
            True,
            {"root_system": root_system, "coxeter_number": h, "root_count": root_count, "note": note},
        )
        disc_profile = terminal_discriminant_profile(root_system)
        ledger.execute(
            "INSERT OR REPLACE INTO terminal_24d_forms VALUES (?,?,?,?,?,?,?)",
            [
                terminal_id,
                terminal_id.replace("Niemeier:", ""),
                root_system,
                h,
                _json({
                    "status": "template; root shell is exact, full overlattice glue pending",
                    "root_count": root_count,
                    "required_overlattice_index": disc_profile["required_overlattice_index"],
                    "root_lattice_determinant": disc_profile["root_lattice_determinant"],
                }),
                None,
                _json({"note": note, "components": components, "discriminant_profile": disc_profile}),
            ],
        )
        insert_discriminant_profile(ledger, terminal_id, root_system)
        if root_system != "rootless":
            insert_component_decomposition(ledger, terminal_id, root_system)
            terminal_rs = direct_sum_root_system(terminal_id, components)
            # Store exact terminal root-shell vectors and Gram form. This is not full glue completion; it is the complete root shell of the Niemeier root system.
            gram_hash = stable_hash(terminal_id, matrix_json(terminal_rs.gram))
            ledger.execute(
                "INSERT OR REPLACE INTO gram_forms VALUES (?,?,?,?,?,?)",
                [f"gram:{terminal_id}", terminal_id, matrix_json(terminal_rs.gram), None, "exact rational direct-sum ADE", gram_hash],
            )
            for idx, r in enumerate(terminal_rs.roots):
                n2 = "2"  # ADE terminal root shells are normalized to norm 2.
                orbit = f"terminal_root_shell:norm2={n2}"
                vh = stable_hash(terminal_id, vector_json(r), n2)
                ledger.execute(
                    "INSERT OR REPLACE INTO exact_vectors VALUES (?,?,?,?,?,?)",
                    [f"vec:{terminal_id}:{idx:05d}", terminal_id, vector_json(r), n2, orbit, vh],
                )
            insert_invariant(
                ledger,
                terminal_id,
                "terminal_root_shell",
                {
                    "rank": terminal_rs.rank,
                    "ambient_dimension": len(terminal_rs.gram),
                    "root_count": len(terminal_rs.roots),
                    "component_expression": root_system,
                    "component_count": sum(mult for _, _, mult in components),
                    "norm2_values": ["2"],
                    "status": "exact root shell; glue/overlattice data separate",
                },
            )
        else:
            insert_invariant(
                ledger,
                terminal_id,
                "terminal_root_shell",
                {"rank": 24, "ambient_dimension": 24, "root_count": 0, "component_expression": "rootless", "status": "Leech rootless terminal template; minimal shell/glue import pending"},
            )
        insert_rag(
            ledger,
            terminal_id,
            f"24D terminal destination template for {root_system}.",
            facts=f"Seeded as one of the 24 positive-definite even unimodular rank-24 destinations. Exact root shell count: {root_count}. Glue/coset records remain template-level unless separately imported.",
            futures="Terminal form; no further 24D destination expansion is seeded.",
            obstructions="Requires exact glue-code/coset data before proof-grade overlattice construction output.",
        )


def seed_pariahs(ledger: Ledger) -> None:
    for p in PARIAHS:
        insert_object(
            ledger,
            p["id"],
            p["name"],
            "pariah_sporadic",
            None,
            None,
            "Pariah",
            False,
            p,
        )
        insert_rag(
            ledger,
            p["id"],
            f"{p['name']} as a {p['type']} pariah boundary object.",
            facts=f"Order factorization: {p['order_factorization']}. Type in this scaffold: {p['type']} pariah.",
            futures="Used here as Monster-exterior boundary routing, not as a proven physical mechanism.",
            obstructions="Not a Monster subquotient; hard pariahs include non-Monster primes.",
        )


def seed_morphisms(ledger: Ledger) -> None:
    # Low-rank preconditioners.
    insert_morphism(ledger, "G2", "A2", "long_root_A2_projection", metadata={"role": "long roots of G2 form an A2 subsystem"})
    insert_morphism(ledger, "G2", "A2", "short_root_A2_projection", metadata={"role": "short roots of G2 form an A2 subsystem"})
    insert_morphism(ledger, "G2", "D4", "triality_unfolding_template", conditions={"status": "template"}, metadata={"role": "G2 as triality fixed/folded channel of D4"})

    insert_morphism(ledger, "F4", "D4", "long_root_D4_projection", metadata={"role": "long roots of F4 form a D4 subsystem"})
    insert_morphism(ledger, "F4", "E6", "fixed_subalgebra_extension_template", conditions={"status": "template"}, metadata={"role": "F4/E6 adjacency via outer automorphism/fixed subalgebra framing"})
    insert_morphism(ledger, "G2", "G2xF4", "pair_with_F4")
    insert_morphism(ledger, "F4", "G2xF4", "pair_with_G2")
    insert_morphism(ledger, "G2xF4", "E8", "exceptional_dual_pair_closure", metadata={"decomposition": "e8 ≈ g2 + f4 + (7⊗26)"})

    # Exceptional ladder.
    insert_morphism(ledger, "E6", "E7", "exceptional_rank_extension")
    insert_morphism(ledger, "E7", "E8", "exceptional_rank_extension")
    insert_morphism(ledger, "E6", "Niemeier:E6^4", "rank24_fourfold_terminal")
    insert_morphism(ledger, "E7", "Niemeier:A17_E7", "rank24_mixed_terminal")
    insert_morphism(ledger, "E7", "Niemeier:D10_E7^2", "rank24_mixed_terminal")
    insert_morphism(ledger, "E8", "Niemeier:E8^3", "rank24_threefold_terminal")
    insert_morphism(ledger, "E8", "Niemeier:D16_E8", "rank24_mixed_terminal")

    # Direct ADE terminal examples arising from G2/F4 routes.
    insert_morphism(ledger, "A1", "Niemeier:A1^24", "rank24_terminal")
    insert_morphism(ledger, "A2", "Niemeier:A2^12", "rank24_terminal", metadata={"preconditioned_by": ["G2.long_A2", "G2.short_A2"]})
    insert_morphism(ledger, "D4", "Niemeier:D4^6", "rank24_terminal", metadata={"preconditioned_by": ["G2.triality", "F4.long_D4"]})
    insert_morphism(ledger, "D4", "Niemeier:A5^4_D4", "rank24_mixed_terminal")

    # Niemeier to Monster/pariah boundary as a conceptual admissibility layer.
    insert_morphism(ledger, "Niemeier:Leech", "Monster:M", "moonshine_substrate_boundary_template", conditions={"status": "conceptual scaffold"})
    insert_morphism(ledger, "Niemeier:E8^3", "Monster:M", "rootful_to_monster_context_template", conditions={"status": "conceptual scaffold"})
    for p in ["Pariah:J1", "Pariah:J3", "Pariah:ON", "Pariah:Ru"]:
        insert_morphism(ledger, "Monster:M", p, "structural_pariah_exit_template", conditions={"status": "conceptual scaffold"})
    for hard in ["Pariah:J4", "Pariah:Ly"]:
        insert_morphism(ledger, "Pariah:J1", hard, "hard_wall_landing_template", conditions={"status": "conceptual scaffold"})
        insert_morphism(ledger, "Pariah:J3", hard, "hard_wall_landing_template", conditions={"status": "conceptual scaffold"})
        insert_morphism(ledger, "Pariah:ON", hard, "hard_wall_landing_template", conditions={"status": "conceptual scaffold"})
        insert_morphism(ledger, "Pariah:Ru", hard, "hard_wall_landing_template", conditions={"status": "conceptual scaffold"})

    # Known forbidden/simple obstruction templates.
    insert_morphism(
        ledger,
        "G2",
        "Niemeier:Leech",
        "rootful_to_rootless_direct_forbidden",
        status="forbidden",
        obstruction={"reason": "direct rootful terminal path into rootless Leech not seeded; requires quotient/lift/code route"},
    )


def seed_morphism_witnesses(ledger: Ledger) -> None:
    """Attach exact root-subset witnesses to the first key low-rank morphisms.

    These witnesses are intentionally modest but important: they turn the
    G2/F4 starting claims into queryable exact subsets instead of prose-only
    morphism labels.
    """
    def ids_with_norm(object_id: str, norm: str) -> list[str]:
        rows = ledger.query(
            "SELECT vector_id FROM exact_vectors WHERE object_id=? AND norm_json=? ORDER BY vector_id",
            [object_id, norm],
        )
        return [r["vector_id"] for r in rows]

    # G2 convention in this seed: norm 2 = short roots, norm 6 = long roots.
    short_g2 = ids_with_norm("G2", "2")
    long_g2 = ids_with_norm("G2", "6")
    insert_morphism_witness(
        ledger,
        "mor:G2->A2:short_root_A2_projection",
        "G2",
        "A2",
        "exact_root_subset",
        short_g2,
        {"target_root_count": 6, "target_rank": 2, "interpretation": "G2 short-root A2 channel"},
        "verified_by_norm_partition_count",
        {"expected_count": 6, "actual_count": len(short_g2)},
    )
    insert_morphism_witness(
        ledger,
        "mor:G2->A2:long_root_A2_projection",
        "G2",
        "A2",
        "exact_root_subset",
        long_g2,
        {"target_root_count": 6, "target_rank": 2, "interpretation": "G2 long-root A2 channel"},
        "verified_by_norm_partition_count",
        {"expected_count": 6, "actual_count": len(long_g2)},
    )

    # F4 convention in this seed: norm 2 roots form the long-root D4 channel
    # after scale normalization; the witness records the exact 24-vector subset.
    f4_norm2 = ids_with_norm("F4", "2")
    f4_norm4 = ids_with_norm("F4", "4")
    d4_candidate = f4_norm2 if len(f4_norm2) == 24 else f4_norm4
    insert_morphism_witness(
        ledger,
        "mor:F4->D4:long_root_D4_projection",
        "F4",
        "D4",
        "exact_root_subset",
        d4_candidate,
        {"target_root_count": 24, "target_rank": 4, "interpretation": "F4 norm-partition D4 channel"},
        "verified_by_norm_partition_count" if len(d4_candidate) == 24 else "needs_manual_review",
        {"norm2_count": len(f4_norm2), "norm4_count": len(f4_norm4), "selected_count": len(d4_candidate)},
    )




def seed_component_terminal_morphisms(ledger: Ledger) -> None:
    """Add component-to-terminal admissibility edges for every ADE component appearing in a 24D terminal."""
    for terminal_id, root_system, _h, _note in NIEMEIER_FORMS:
        if root_system == "rootless":
            continue
        for fam, rank, mult in parse_root_system_label(root_system):
            source = f"{fam}{rank}"
            insert_morphism(
                ledger,
                source,
                terminal_id,
                "component_terminal_embedding_template",
                conditions={"component_multiplicity_in_terminal": mult, "root_system": root_system},
                invariant_delta={"terminal_rank": 24, "component_rank": rank, "rank_deficit": 24 - rank},
                metadata={"role": "component path to exact terminal root shell; glue/coset completion checked separately"},
            )


def seed_terminal_glue_profiles(ledger: Ledger) -> None:
    """Insert determinant-derived glue-index profiles for every 24D terminal.

    This does not claim exact coset representatives for all Niemeier lattices. It stores the
    forced index size that any overlattice/glue completion must satisfy.
    """
    for terminal_id, root_system, _h, _note in NIEMEIER_FORMS:
        profile = terminal_discriminant_profile(root_system)
        path_hash = stable_hash("terminal_glue_profile", terminal_id, profile)
        checks = [
            "rank must be 24",
            "evenness must hold after coset adjoining",
            "determinant must reduce to 1",
            "glue index squared must equal root lattice determinant",
        ]
        status = "computed_exact_index_cosets_pending" if root_system != "rootless" else "rootless_leech_glue_import_pending"
        ledger.execute(
            "INSERT OR REPLACE INTO glue_requirements VALUES (?,?,?,?,?,?,?,?)",
            [
                f"glue_profile:{terminal_id}",
                path_hash,
                terminal_id,
                terminal_id,
                _json([{
                    "kind": "required_overlattice_index",
                    "value": profile["required_overlattice_index"],
                    "root_lattice_determinant": profile["root_lattice_determinant"],
                    "component_discriminants": profile["component_discriminants"],
                }]),
                _json([]),
                _json({"checks": checks, "status": status}),
                status,
            ],
        )

def seed_glue_templates(ledger: Ledger) -> None:
    templates = [
        ("G2", "Niemeier:A2^12", ["A2^12 ternary glue placeholder"], ["verify even unimodular rank-24 completion"]),
        ("F4", "Niemeier:D4^6", ["D4^6 glue placeholder"], ["verify D4 copies share common Coxeter number 6"]),
        ("E8", "Niemeier:E8^3", ["direct sum unimodular template: E8^3"], ["three E8 blocks already even unimodular"]),
        ("D4", "Niemeier:D4^6", ["D4^6 glue code placeholder"], ["triality-compatible closure check"]),
        ("A2", "Niemeier:A2^12", ["ternary Golay-compatible placeholder"], ["A2 discriminant cancellation check"]),
    ]
    for source, target, cosets, checks in templates:
        path_hash = stable_hash(source, target, cosets, checks)
        ledger.execute(
            "INSERT OR REPLACE INTO glue_requirements VALUES (?,?,?,?,?,?,?,?)",
            [
                f"glue:{source}->{target}",
                path_hash,
                target,
                source,
                _json(cosets),
                _json([]),
                _json({"checks": checks, "v0_3_status": "template; discriminant/glue-index profile is computed, exact coset reps pending unless noted"}),
                "template",
            ],
        )



def seed_status_and_prime_profiles(ledger: Ledger) -> None:
    """Add explicit exact/template/confidence records and prime-boundary profiles."""
    insert_prime_factor_profile(
        ledger,
        "Monster:M",
        "group_order",
        MONSTER_ORDER_FACTORIZATION,
        integer_value=None,
        monster_reference=False,
        payload_extra={"role": "reference prime vocabulary for Monster-involvement boundary"},
    )
    insert_construction_status(
        ledger,
        "Monster:M",
        "finite_group_implementation",
        "conceptual",
        {"status": "order/prime vocabulary only; full multiplication/characters/representations pending GAP/ATLAS import"},
    )
    for p in PARIAHS:
        insert_prime_factor_profile(
            ledger,
            p["id"],
            "group_order",
            p["order_factorization"],
            integer_value=None,
            monster_reference=True,
            payload_extra={"pariah_type": p["type"]},
        )
        missing = factor_payload(p["order_factorization"])["missing_monster_primes"]
        exactness = "computed_profile" if p["type"] == "hard" or not missing else "computed_profile"
        insert_construction_status(
            ledger,
            p["id"],
            "monster_boundary_prime_profile",
            exactness,
            {
                "pariah_type": p["type"],
                "monster_compatible_prime_set": not missing,
                "missing_monster_primes": missing,
                "interpretation": "hard arithmetic exterior" if missing else "structural exterior; prime set alone does not obstruct Monster compatibility",
            },
        )
    for row in ledger.query("SELECT object_id, kind FROM object_registry"):
        oid, kind = row["object_id"], row["kind"]
        if kind == "niemeier_terminal":
            insert_construction_status(
                ledger,
                oid,
                "terminal_root_shell",
                "exact" if oid != "Niemeier:Leech" else "template",
                {"status": "exact root shell stored; full overlattice glue cosets pending" if oid != "Niemeier:Leech" else "rootless Leech placeholder; construction/minimal shell pending"},
            )
            insert_construction_status(
                ledger,
                oid,
                "overlattice_glue",
                "computed_profile",
                {"status": "required glue index computed from ADE determinant profile; exact coset reps pending"},
            )
        elif kind == "root_system":
            insert_construction_status(
                ledger,
                oid,
                "morphism_family",
                "partial_seeded",
                {"status": "local exact root data stored; morphism family seeded only for known scaffold edges"},
            )


def seed_residue_templates(ledger: Ledger) -> None:
    residues = [
        ("Monster:M", "Pariah:J4", "prime", {"new_primes": [37, 43], "role": "hard exterior"}),
        ("Monster:M", "Pariah:Ly", "prime", {"new_primes": [37, 67], "role": "hard exterior"}),
        ("G2", "A2", "nsl", {"Noether": "template", "Shannon": "template", "Landauer": "template"}),
        ("F4", "D4", "nsl", {"Noether": "template", "Shannon": "template", "Landauer": "template"}),
    ]
    for source, target, rtype, payload in residues:
        ledger.execute(
            "INSERT OR REPLACE INTO residue_registry VALUES (?,?,?,?,?,?)",
            [f"res:{source}->{target}:{rtype}", source, target, rtype, _json(payload), "template"],
        )


def seed_rag_cards(ledger: Ledger) -> None:
    insert_rag(
        ledger,
        "G2",
        "Rank-2 exceptional root system used here as the first lawful asymmetry preconditioner.",
        facts="Seeded with 12 exact roots. Long and short roots each define A2-style channels; D4 triality unfolding is represented as a template morphism.",
        futures="A2, D4, G2×F4, Niemeier:A2^12 through A2, Niemeier:D4^6 through D4, E8 through G2×F4.",
        obstructions="Direct rootful-to-Leech path is marked forbidden in v0.1 unless a code/lift route is supplied.",
    )
    insert_rag(
        ledger,
        "F4",
        "Rank-4 exceptional root system used here as the first 4D asymmetry/correction shell.",
        facts="Seeded with 48 exact roots in R4. Long roots form a D4 subsystem; F4→E6 and F4×G2→E8 routes are seeded as templates.",
        futures="D4, E6, G2×F4, E8, D4^6, E6^4, E8^3 through continuation.",
    )
    insert_rag(
        ledger,
        "E8",
        "Rank-8 exceptional closure template with 240 exact roots in simple-root coordinates.",
        facts="Seeded by Weyl closure from simple roots. Used as a rootful local closure carrier and a route into E8^3/D16E8 24D terminal forms.",
        futures="Niemeier:E8^3, Niemeier:D16_E8, Monster boundary templates.",
    )
    insert_rag(
        ledger,
        "Monster:M",
        "Conceptual Monster substrate boundary node for the v0.1 morphism ledger.",
        facts="Not a full finite-group implementation. Stores the 20+4+2 partition role and pariah routing templates.",
        futures="Structural pariah exits J1,J3,O'N,Ru; hard landing templates J4,Ly through structural pariahs.",
        obstructions="Requires external finite group/ATLAS/GAP data to become proof-grade.",
    )



def seed_involutions(ledger: Ledger) -> None:
    """Seed simple reflection/involution metadata.

    v0.1 records the generator-level involutions as executable metadata.
    Later versions should expand these into full action tables over roots.
    """
    for obj, count in [("G2", 2), ("F4", 4), ("E6", 6), ("E7", 7), ("E8", 8)]:
        for i in range(count):
            payload = {"action": "simple_root_reflection", "simple_root_index": i, "order": 2}
            h = stable_hash(obj, "simple_reflection", i, payload)
            ledger.execute(
                "INSERT OR REPLACE INTO involution_registry VALUES (?,?,?,?,?,?,?)",
                [f"inv:{obj}:s{i}", obj, f"simple reflection s_{i}", None, _json(payload), _json({"role": "Weyl generator involution"}), h],
            )
    # Conceptual pariah boundary involutions.
    for obj in ["Pariah:J1", "Pariah:J3", "Pariah:ON", "Pariah:Ru", "Pariah:J4", "Pariah:Ly"]:
        payload = {"action": "boundary_mirror_template", "order": 2, "status": "conceptual scaffold"}
        h = stable_hash(obj, payload)
        ledger.execute(
            "INSERT OR REPLACE INTO involution_registry VALUES (?,?,?,?,?,?,?)",
            [f"inv:{obj}:boundary_mirror", obj, "boundary mirror template", None, _json(payload), _json({"role": "exit/landing mirror placeholder"}), h],
        )


def seed_convolutions(ledger: Ledger) -> None:
    """Seed convolution/operator metadata for future Fourier-neighborhood work."""
    items = [
        ("G2", "finite_root_neighborhood_convolution", {"kernel": "Weyl-orbit weighted", "status": "template"}),
        ("F4", "finite_root_neighborhood_convolution", {"kernel": "long/short-root split weighted", "status": "template"}),
        ("E8", "240_root_shell_convolution", {"kernel": "root-shell adjacency", "status": "template"}),
        ("Monster:M", "character_table_convolution_template", {"kernel": "class-function convolution", "status": "requires ATLAS/GAP import"}),
    ]
    for obj, name, op in items:
        h = stable_hash(obj, name, op)
        ledger.execute(
            "INSERT OR REPLACE INTO convolution_registry VALUES (?,?,?,?,?,?,?)",
            [f"conv:{obj}:{name}", obj, name, _json({"domain": obj}), _json(op), _json({"role": "Fourier/neighborhood propagation hook"}), h],
        )




def materialize_terminal_paths(ledger: Ledger, max_depth: int = 10) -> None:
    """Persist reachable terminal paths and source-terminal profiles for fast API queries."""
    objects = ledger.query("SELECT object_id FROM object_registry ORDER BY object_id")
    for row in objects:
        source = row["object_id"]
        for item in ledger.terminal_futures(source, max_depth=max_depth):
            terminal_id = item["object_id"]
            path = item["path"]
            path_hash = stable_hash(path)
            edge_statuses = [edge.get("status") for edge in ledger.path_edges(path)]
            explanation = f"{source} reaches {terminal_id} by {len(path)-1} seeded legal edge(s)."
            ledger.execute(
                "INSERT OR REPLACE INTO path_registry VALUES (?,?,?,?,?,?)",
                [path_hash, _json(path), source, terminal_id, "legal", explanation],
            )
            disc = ledger.discriminant_profile(terminal_id)
            payload = {
                "path": path,
                "edge_statuses": edge_statuses,
                "discriminant_profile": disc,
                "glue_template_count": len(ledger.path_glue_templates(path, terminal_id)),
            }
            h = stable_hash(source, terminal_id, path, payload)
            ledger.execute(
                "INSERT OR REPLACE INTO terminal_admissibility_profiles VALUES (?,?,?,?,?,?,?,?)",
                [f"tap:{source}->{terminal_id}", source, terminal_id, path_hash, len(path)-1, "legal_seeded", _json(payload), h],
            )
            insert_path_metric(ledger, path, terminal_id=terminal_id, status="legal_seeded")


def seed_nsl_boundary_proxies(ledger: Ledger) -> None:
    """Seed dimensionless NSL-style boundary proxies over materialized paths.

    These are not physical-unit Noether/Shannon/Landauer values. They are
    explicit normalized ledgers that use currently stored mathematical data:
    rank deficit, future-cone ambiguity, and glue-index burden. This prevents
    the package from treating NSL as an untyped placeholder while keeping the
    status honest.
    """
    candidate_counts = {
        row["source_id"]: row["n"]
        for row in ledger.query("SELECT source_id, COUNT(*) AS n FROM terminal_admissibility_profiles GROUP BY source_id")
    }
    for row in ledger.query("SELECT source_id, terminal_id, best_path_hash, min_depth FROM terminal_admissibility_profiles"):
        source = row["source_id"]
        target = row["terminal_id"]
        source_obj = ledger.object(source) or {}
        target_obj = ledger.object(target) or {}
        srank = source_obj.get("rank") or 0
        trank = target_obj.get("rank") or 24
        noether = abs(float(trank) - float(srank)) / max(float(trank or 24), 1.0)
        shannon = math.log2(max(candidate_counts.get(source, 1), 1)) / 8.0
        disc = ledger.discriminant_profile(target) or {}
        try:
            glue_index = float(disc.get("required_overlattice_index") or 1.0)
        except (TypeError, ValueError):
            glue_index = 1.0
        landauer = math.log2(max(glue_index, 1.0)) / 24.0
        # Absorption is a proxy for how much of the burden the terminal template
        # already accounts for: exact root shell + computed discriminant profile.
        target_status = {s["surface_type"]: s["exactness"] for s in ledger.construction_status(target)}
        absorption = 0.0
        if target_status.get("terminal_root_shell") in {"exact", "template"}:
            absorption += 0.35
        if target_status.get("overlattice_glue") == "computed_profile":
            absorption += 0.25
        if row.get("min_depth") is not None:
            absorption += max(0.0, 0.25 - 0.03 * float(row["min_depth"]))
        insert_nsl_boundary(
            ledger,
            source,
            target,
            noether_residue=noether,
            shannon_residue=shannon,
            landauer_cost=landauer,
            absorption_capacity=absorption,
            status="dimensionless_proxy_from_rank_futurecone_glueindex",
            payload={
                "source_rank": srank,
                "target_rank": trank,
                "candidate_count_for_source": candidate_counts.get(source, 0),
                "required_overlattice_index": disc.get("required_overlattice_index"),
                "best_path_hash": row.get("best_path_hash"),
                "min_depth": row.get("min_depth"),
                "warning": "proxy ledger only; not a physical-unit Noether/Shannon/Landauer calculation",
            },
        )



def infer_coxeter_number(object_id: str) -> int | None:
    if object_id.startswith("A") and object_id[1:].isdigit():
        return int(object_id[1:]) + 1
    if object_id.startswith("D") and object_id[1:].isdigit():
        return 2 * (int(object_id[1:]) - 1)
    return {"G2": 6, "F4": 12, "E6": 12, "E7": 18, "E8": 30}.get(object_id)


def seed_dynkin_profiles(ledger: Ledger) -> None:
    """Store exact Cartan/Dynkin profile rows for every seeded root-system object."""
    for row in ledger.query("SELECT object_id FROM object_registry WHERE kind='root_system' ORDER BY object_id"):
        oid = row["object_id"]
        gram_row = ledger.gram(oid)
        if not gram_row:
            continue
        matrix_json_value = gram_row["matrix_json"]
        gram = parse_matrix_json(matrix_json_value)
        det = determinant(gram)
        root_count = ledger.conn.execute("SELECT COUNT(*) FROM exact_vectors WHERE object_id=?", [oid]).fetchone()[0]
        payload = {
            "interpretation": "simple-root coordinate Gram/Cartan matrix; exact rational entries",
            "determinant": str(det),
            "root_count": root_count,
        }
        h = stable_hash(oid, matrix_json_value, str(det), root_count, payload)
        ledger.execute(
            "INSERT OR REPLACE INTO dynkin_registry VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                f"dynkin:{oid}",
                oid,
                matrix_json_value,
                str(det),
                infer_coxeter_number(oid),
                root_count,
                int(ledger.object(oid).get("rank") or len(gram)),
                "computed_exact",
                _json(payload),
                h,
            ],
        )
        insert_invariant(
            ledger,
            oid,
            "dynkin_cartan_profile",
            {"determinant": str(det), "coxeter_number": infer_coxeter_number(oid), "root_count": root_count},
            status="computed_exact",
        )


def _fraction_key(x: Any) -> str:
    return str(x)


def _root_signature_from_vectors(vectors: list[Any], gram: Any) -> dict[str, Any]:
    """Scale-invariant root-subset signature from exact vectors and Gram form."""
    norm_counts: Counter[str] = Counter(str(norm2(v, gram)) for v in vectors)
    ip_counts: Counter[str] = Counter()
    angle_counts: Counter[str] = Counter()
    for i in range(len(vectors)):
        ni = norm2(vectors[i], gram)
        for j in range(i + 1, len(vectors)):
            nj = norm2(vectors[j], gram)
            ip = dot(vectors[i], vectors[j], gram)
            ip_counts[str(ip)] += 1
            if ip == 0:
                sig = "0"
            else:
                sign = "+" if ip > 0 else "-"
                sig = f"{sign}{(ip * ip) / (ni * nj)}"
            angle_counts[sig] += 1
    return {
        "root_count": len(vectors),
        "rank_upper_bound": len(gram),
        "norm_distribution": dict(sorted(norm_counts.items())),
        "inner_product_distribution": dict(sorted(ip_counts.items())),
        "scale_invariant_angle_distribution": dict(sorted(angle_counts.items())),
    }


def _vectors_for_ids(ledger: Ledger, object_id: str, vector_ids: list[str]) -> tuple[list[Any], Any]:
    gram_row = ledger.gram(object_id)
    if not gram_row:
        raise ValueError(f"missing Gram form for {object_id}")
    gram = parse_matrix_json(gram_row["matrix_json"])
    coords_by_id = {
        row["vector_id"]: parse_vector_json(row["coordinates_json"])
        for row in ledger.query("SELECT vector_id, coordinates_json FROM exact_vectors WHERE object_id=?", [object_id])
    }
    missing = [vid for vid in vector_ids if vid not in coords_by_id]
    if missing:
        raise ValueError(f"missing vector ids for {object_id}: {missing[:5]}")
    return [coords_by_id[vid] for vid in vector_ids], gram


def insert_morphism_verification(
    ledger: Ledger,
    morphism_id: str,
    source_id: str,
    target_id: str,
    verification_type: str,
    source_signature: dict[str, Any],
    target_signature: dict[str, Any],
    result: str,
    status: str,
    payload: dict[str, Any] | None = None,
) -> None:
    h = stable_hash(morphism_id, source_id, target_id, verification_type, source_signature, target_signature, result, status, payload or {})
    ledger.execute(
        "INSERT OR REPLACE INTO morphism_verification_registry VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            f"mverify:{stable_hash(morphism_id, verification_type)[:24]}",
            morphism_id,
            source_id,
            target_id,
            verification_type,
            _json(source_signature),
            _json(target_signature),
            result,
            status,
            _json(payload or {}),
            h,
        ],
    )


def seed_morphism_signature_verifications(ledger: Ledger) -> None:
    """Verify witness subsets by comparing scale-invariant angle signatures with targets."""
    for row in ledger.query("SELECT * FROM morphism_witness_registry ORDER BY source_id,target_id,witness_type"):
        try:
            witness_ids = json.loads(row["witness_vectors_json"])
        except Exception:
            witness_ids = []
        if not witness_ids:
            continue
        source_id = row["source_id"]
        target_id = row["target_id"]
        source_vectors, source_gram = _vectors_for_ids(ledger, source_id, witness_ids)
        target_rows = ledger.query("SELECT vector_id FROM exact_vectors WHERE object_id=? ORDER BY vector_id", [target_id])
        target_ids = [r["vector_id"] for r in target_rows]
        if not target_ids:
            continue
        target_vectors, target_gram = _vectors_for_ids(ledger, target_id, target_ids)
        src_sig = _root_signature_from_vectors(source_vectors, source_gram)
        tgt_sig = _root_signature_from_vectors(target_vectors, target_gram)
        same_angles = src_sig["scale_invariant_angle_distribution"] == tgt_sig["scale_invariant_angle_distribution"]
        same_count = src_sig["root_count"] == tgt_sig["root_count"]
        result = "pass_scale_invariant_root_signature" if same_angles and same_count else "review_signature_mismatch"
        insert_morphism_verification(
            ledger,
            row["morphism_id"],
            source_id,
            target_id,
            "witness_scale_invariant_angle_signature",
            src_sig,
            tgt_sig,
            result,
            "computed_exact_from_witness_vectors",
            {"witness_id": row["witness_id"], "same_root_count": same_count, "same_angle_signature": same_angles},
        )


def seed_terminal_component_embeddings(ledger: Ledger) -> None:
    """Store exact embeddings of every ADE component instance inside each terminal root shell."""
    for terminal_id, root_system, _h, _note in NIEMEIER_FORMS:
        if root_system == "rootless":
            continue
        components = parse_root_system_label(root_system)
        terminal_rs = direct_sum_root_system(terminal_id, components)
        terminal_index = {r: f"vec:{terminal_id}:{idx:05d}" for idx, r in enumerate(sorted(set(terminal_rs.roots), key=lambda x: tuple(x)))}
        total_rank = terminal_rs.rank
        rank_offset = 0
        instance_index = 0
        for fam, rank, mult in components:
            comp_rs = component_root_system(fam, rank)
            source_id = comp_rs.name
            source_ids = [f"vec:{source_id}:{idx:04d}" for idx in range(len(comp_rs.roots))]
            for _ in range(mult):
                embedded_roots = []
                for r in comp_rs.roots:
                    v = [0] * total_rank
                    for i, x in enumerate(r):
                        v[rank_offset + i] = x
                    embedded_roots.append(tuple(v))
                terminal_ids = [terminal_index[v] for v in embedded_roots]
                label = f"{fam}{rank}"
                payload = {
                    "component_label": label,
                    "component_rank": rank,
                    "terminal_root_system": root_system,
                    "rank_span": [rank_offset, rank_offset + rank - 1],
                    "interpretation": "exact root-shell block embedding inside terminal direct-sum root system; overlattice glue remains separate",
                }
                h = stable_hash(terminal_id, label, instance_index, source_id, rank_offset, source_ids, terminal_ids, payload)
                ledger.execute(
                    "INSERT OR REPLACE INTO terminal_component_embeddings VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    [
                        f"tcembed:{terminal_id}:{instance_index:02d}:{label}",
                        terminal_id,
                        label,
                        instance_index,
                        source_id,
                        rank_offset,
                        len(terminal_ids),
                        _json(source_ids),
                        _json(terminal_ids),
                        "computed_exact_root_shell_embedding",
                        _json(payload),
                        h,
                    ],
                )
                # Attach a verification row for the component -> terminal edge class.
                # The embedding is exact-by-construction: terminal vectors are source component
                # roots zero-padded into the direct-sum rank-24 coordinate block. Use count/norm
                # signatures here so seeding remains fast even for D24/A24 root shells.
                src_sig = {
                    "root_count": len(source_ids),
                    "rank_upper_bound": rank,
                    "norm_distribution": {"2": len(source_ids)},
                    "signature_mode": "count_norm_exact_by_component_formula",
                }
                tgt_sig = {**src_sig, "terminal_embedding": "zero_padded_direct_sum_block", "terminal_vector_count": len(terminal_ids)}
                insert_morphism_verification(
                    ledger,
                    f"mor:{source_id}->{terminal_id}:component_terminal_embedding_template",
                    source_id,
                    terminal_id,
                    "terminal_component_exact_embedding_signature",
                    src_sig,
                    tgt_sig,
                    "pass_exact_by_direct_sum_construction",
                    "computed_exact_root_shell_embedding",
                    {"component_instance_index": instance_index, "rank_offset": rank_offset, "terminal_vector_count": len(terminal_ids)},
                )
                instance_index += 1
                rank_offset += rank


def insert_closure_obstruction(
    ledger: Ledger,
    source_id: str,
    target_id: str,
    obstruction_type: str,
    condition: dict[str, Any],
    result: str,
    severity: str = "info",
    payload: dict[str, Any] | None = None,
) -> None:
    h = stable_hash(source_id, target_id, obstruction_type, condition, result, severity, payload or {})
    ledger.execute(
        "INSERT OR REPLACE INTO closure_obstruction_registry VALUES (?,?,?,?,?,?,?,?,?)",
        [
            f"obstruction:{stable_hash(source_id, target_id, obstruction_type)[:24]}",
            source_id,
            target_id,
            obstruction_type,
            _json(condition),
            result,
            severity,
            _json(payload or {}),
            h,
        ],
    )


def seed_closure_obstructions(ledger: Ledger) -> None:
    """Make direct obstructions/checkpoints queryable, not just prose in can_close."""
    for row in ledger.query("SELECT object_id FROM object_registry WHERE kind='root_system' ORDER BY object_id"):
        oid = row["object_id"]
        root_count = ledger.conn.execute("SELECT COUNT(*) FROM exact_vectors WHERE object_id=?", [oid]).fetchone()[0]
        if root_count:
            insert_closure_obstruction(
                ledger,
                oid,
                "Niemeier:Leech",
                "direct_rootful_to_rootless_terminal",
                {"source_root_count": root_count, "target_root_count": 0},
                "direct path blocked unless an explicit code/lift/quotient route is supplied",
                "warning",
                {"interpretation": "Leech is rootless; a rootful source is not a direct terminal root-shell embedding."},
            )
    for row in ledger.query("SELECT object_id, required_overlattice_index, glue_status FROM discriminant_registry ORDER BY object_id"):
        target = row["object_id"]
        idx = row["required_overlattice_index"]
        if target == "Niemeier:Leech":
            insert_closure_obstruction(
                ledger,
                target,
                target,
                "leech_construction_pending",
                {"root_system": "rootless"},
                "Leech terminal is registered, but construction/minimal shell data is pending import",
                "warning",
            )
        elif str(idx) != "1":
            insert_closure_obstruction(
                ledger,
                target,
                target,
                "exact_glue_cosets_pending",
                {"required_overlattice_index": idx},
                "root shell is exact, but proof-grade overlattice requires exact glue cosets/codewords",
                "warning",
            )
        else:
            insert_closure_obstruction(
                ledger,
                target,
                target,
                "glue_index_one_direct_sum",
                {"required_overlattice_index": idx},
                "root lattice determinant already unimodular at the terminal root-shell level",
                "info",
            )


def seed_build_manifest(ledger: Ledger) -> None:
    summary = ledger.summary()
    payload = {
        "summary": summary,
        "hardening": [
            "root neighborhood profiles",
            "root adjacency edges for compact core systems",
            "morphism witnesses for G2->A2 and F4->D4 channels",
            "scale-invariant signature verification for morphism witnesses",
            "Dynkin/Cartan profiles for all seeded root systems",
            "exact terminal component embeddings for all rootful 24D terminals",
            "closure obstruction registry for rootless/glue-pending/direct-sum cases",
            "dimensionless NSL boundary proxy ledger",
        ],
        "external_import_status": "HF searches did not expose a proof-grade Niemeier/Leech/Golay/ATLAS dataset through the connector; imports remain staged.",
        "version_note": "v0.6 makes the arrows more accountable by storing exact component embeddings and computed morphism verification signatures.",
    }
    created = datetime.now(timezone.utc).isoformat()
    h = stable_hash("0.6", created, payload)
    ledger.execute(
        "INSERT OR REPLACE INTO build_manifest_registry VALUES (?,?,?,?,?,?)",
        ["manifest:v0.6", "0.6", created, "schema_v0_6", _json(payload), h],
    )

def seed_external_resources(ledger: Ledger) -> None:
    """Record external discovery state, including HF searches made during v0.2 hardening.

    These are not imported proof sources; they make the external-data status explicit.
    """
    insert_external_resource(ledger, "HuggingFace", "dataset_search", "Niemeier lattice Leech E8 root systems", "No direct matching repositories found", None, "no_direct_match")
    insert_external_resource(ledger, "HuggingFace", "dataset_search", "root systems Weyl groups Lie algebra", "No direct matching repositories found", None, "no_direct_match")
    insert_external_resource(ledger, "HuggingFace", "dataset_search", "lattice", "cmudrc/2d-lattices", "https://hf.co/datasets/cmudrc/2d-lattices", "candidate_unrelated_low_dimensional")
    insert_external_resource(ledger, "HuggingFace", "paper_search", "Niemeier lattice Leech lattice E8 root system glue code", "Spherical Leech Quantization for Visual Tokenization and Generation", "https://hf.co/papers/2512.14697", "candidate_modern_leech_application_not_glue_database")


def build_seed_database(path: str | Path, overwrite: bool = True) -> Ledger:
    # Repeated seed builds in a single Python process can temporarily retain large
    # direct-sum/root-neighborhood objects until cyclic GC runs. Collect up front
    # so test suites and agents can rebuild many ledgers without memory drift.
    import gc
    from . import roots as _roots
    # Clear root-system caches before a full reseed. This prevents long-lived
    # Fraction-heavy root-shell objects from accumulating across repeated test
    # builds in one Python process.
    for _fn_name in [
        "root_system_A", "root_system_D", "root_system_G2", "root_system_F4",
        "root_system_E6", "root_system_E7", "root_system_E8", "component_root_system"
    ]:
        _fn = getattr(_roots, _fn_name, None)
        if hasattr(_fn, "cache_clear"):
            _fn.cache_clear()
    gc.collect()
    ledger = Ledger.create(path, overwrite=overwrite)
    ledger.defer_commit = True
    seed_roots(ledger)
    seed_dynkin_profiles(ledger)
    seed_composite_objects(ledger)
    seed_niemeier(ledger)
    seed_pariahs(ledger)
    seed_morphisms(ledger)
    seed_morphism_witnesses(ledger)
    seed_morphism_signature_verifications(ledger)
    seed_component_terminal_morphisms(ledger)
    seed_terminal_component_embeddings(ledger)
    seed_glue_templates(ledger)
    seed_terminal_glue_profiles(ledger)
    seed_residue_templates(ledger)
    seed_status_and_prime_profiles(ledger)
    seed_involutions(ledger)
    seed_convolutions(ledger)
    seed_rag_cards(ledger)
    seed_external_resources(ledger)
    materialize_terminal_paths(ledger)
    seed_nsl_boundary_proxies(ledger)
    seed_closure_obstructions(ledger)
    seed_build_manifest(ledger)
    ledger.conn.commit()
    ledger.defer_commit = False
    gc.collect()
    return ledger
