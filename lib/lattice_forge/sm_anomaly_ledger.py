"""Exact anomaly ledger derived from the Kp3.05.01 physical charge ledger."""
from __future__ import annotations

from fractions import Fraction as F
from typing import Any, Iterable

from .sm_charge_ledger import derive_charge_ledger


def derive_left_handed_weyl_multiplets(
    rows: Iterable[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Collapse component rows and conjugate physical right-handed fermions.

    Anomalies are summed over left-handed Weyl fields.  A physical right-handed
    field therefore enters with conjugate color representation and -Y.
    """
    source = list(rows if rows is not None else derive_charge_ledger())
    multiplets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in source:
        if row["kind"] != "fermion" or row["field"] in seen:
            continue
        seen.add(row["field"])
        right = row["chirality"] == "right"
        color_dim = 3 if row["su3_rep"] == "3" else 1
        weak_dim = 2 if row["su2_rep"] == "2" else 1
        multiplets.append(
            {
                "field": f'{row["field"]}^c' if right else row["field"],
                "su3_rep": "bar3" if right and row["su3_rep"] == "3" else row["su3_rep"],
                "su2_rep": row["su2_rep"],
                "color_dim": color_dim,
                "weak_dim": weak_dim,
                "hypercharge": -row["hypercharge"] if right else row["hypercharge"],
                "basis_operation": "right-handed conjugation" if right else "identity",
            }
        )
    return multiplets


def _t_su3(rep: str) -> F:
    return F(1, 2) if rep in {"3", "bar3"} else F(0)


def _t_su2(rep: str) -> F:
    return F(1, 2) if rep == "2" else F(0)


def anomaly_sums(multiplets: Iterable[dict[str, Any]]) -> dict[str, F | int]:
    sums: dict[str, F | int] = {
        "SU3_cubed": F(0),
        "SU3_SU3_U1": F(0),
        "SU2_SU2_U1": F(0),
        "U1_cubed": F(0),
        "gravity_gravity_U1": F(0),
        "SU2_doublet_count": 0,
    }
    cubic_sign = {"3": 1, "bar3": -1, "1": 0}
    for m in multiplets:
        y, cd, wd = m["hypercharge"], m["color_dim"], m["weak_dim"]
        sums["SU3_cubed"] += wd * cubic_sign[m["su3_rep"]]
        sums["SU3_SU3_U1"] += wd * _t_su3(m["su3_rep"]) * y
        sums["SU2_SU2_U1"] += cd * _t_su2(m["su2_rep"]) * y
        sums["U1_cubed"] += cd * wd * y**3
        sums["gravity_gravity_U1"] += cd * wd * y
        if m["su2_rep"] == "2":
            sums["SU2_doublet_count"] += cd
    return sums


def verify_anomaly_cancellation(
    multiplets: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fields = list(multiplets if multiplets is not None else derive_left_handed_weyl_multiplets())
    sums = anomaly_sums(fields)
    checks = {
        "left_handed_basis_complete": {m["field"] for m in fields}
        == {"Q_L", "u_R^c", "d_R^c", "L_L", "e_R^c"},
        "su3_cubed_zero": sums["SU3_cubed"] == 0,
        "su3_squared_u1_zero": sums["SU3_SU3_U1"] == 0,
        "su2_squared_u1_zero": sums["SU2_SU2_U1"] == 0,
        "u1_cubed_zero": sums["U1_cubed"] == 0,
        "mixed_gravity_u1_zero": sums["gravity_gravity_U1"] == 0,
        "su2_global_doublet_parity_even": sums["SU2_doublet_count"] % 2 == 0,
    }
    encode = lambda value: str(value) if isinstance(value, F) else value
    return {
        "schema": "Kp3.05.02-AnomalyLedger/1.0",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "basis": [{k: encode(v) for k, v in m.items()} for m in fields],
        "sums": {k: encode(v) for k, v in sums.items()},
        "checks": checks,
        "boundary": (
            "Exact one-generation local gauge and mixed anomaly cancellation in the minimal "
            "Standard Model left-handed Weyl basis, plus the even SU(2)-doublet global check. "
            "This does not establish anomaly freedom for nonminimal fields or quantum gravity."
        ),
    }
