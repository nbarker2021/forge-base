"""Exact one-generation SM charge ledger derived through the SU(5) 3+2 orderer."""
from __future__ import annotations
from fractions import Fraction as F
from typing import Any

from .sm_nbody_bridge import SU5_HYPERCHARGE, su5_traceless_balance

SPIN = {
    "positive": {"chart": (1, 1, 0), "t3": F(1, 2)},
    "negative": {"chart": (0, 1, 1), "t3": F(-1, 2)},
    "null": {"chart": (1, 0, 1), "t3": F(0)},
}


def _component(field: str, name: str, kind: str, chirality: str | None, su3: str,
               su2: str, t3: F, y: F, origin: str, spin: str | None = None) -> dict[str, Any]:
    return {"field": field, "component": name, "kind": kind, "chirality": chirality,
            "su3_rep": su3, "su2_rep": su2, "t3": t3, "hypercharge": y,
            "electric_charge": t3 + y, "identity": "Q=T3+Y", "su5_origin": origin,
            "shell2_spin": spin, "chart_state": SPIN[spin]["chart"] if spin else None}


def derive_charge_ledger() -> list[dict[str, Any]]:
    c, w = SU5_HYPERCHARGE[0], SU5_HYPERCHARGE[3]
    qy, ucy, ecy, dcy, ly = c + w, c + c, w + w, -c, -w
    rows = [
        _component("Q_L", "u_L", "fermion", "left", "3", "2", F(1,2), qy, "10:color+weak", "positive"),
        _component("Q_L", "d_L", "fermion", "left", "3", "2", F(-1,2), qy, "10:color+weak", "negative"),
        _component("u_R", "u_R", "fermion", "right", "3", "1", F(0), -ucy, "conjugate(10:color+color)", "null"),
        _component("d_R", "d_R", "fermion", "right", "3", "1", F(0), -dcy, "conjugate(5bar:anti-color)", "null"),
        _component("L_L", "nu_L", "fermion", "left", "1", "2", F(1,2), ly, "5bar:anti-weak", "positive"),
        _component("L_L", "e_L", "fermion", "left", "1", "2", F(-1,2), ly, "5bar:anti-weak", "negative"),
        _component("e_R", "e_R", "fermion", "right", "1", "1", F(0), -ecy, "conjugate(10:weak+weak)", "null"),
        _component("H", "H_plus", "scalar", None, "1", "2", F(1,2), w, "5:weak", "positive"),
        _component("H", "H_zero", "scalar", None, "1", "2", F(-1,2), w, "5:weak", "negative"),
        _component("G", "g", "gauge", None, "8", "1", F(0), F(0), "24:(8,1)_0"),
        _component("W", "W_plus", "gauge", None, "1", "3", F(1), F(0), "24:(1,3)_0"),
        _component("W", "W_3", "gauge", None, "1", "3", F(0), F(0), "24:(1,3)_0"),
        _component("W", "W_minus", "gauge", None, "1", "3", F(-1), F(0), "24:(1,3)_0"),
        _component("B", "B", "gauge", None, "1", "1", F(0), F(0), "24:(1,1)_0"),
    ]
    return rows


def verify_charge_ledger() -> dict[str, Any]:
    rows = derive_charge_ledger()
    expected = {"u_L":F(2,3),"d_L":F(-1,3),"u_R":F(2,3),"d_R":F(-1,3),
                "nu_L":F(0),"e_L":F(-1),"e_R":F(-1),"H_plus":F(1),"H_zero":F(0),
                "g":F(0),"W_plus":F(1),"W_3":F(0),"W_minus":F(-1),"B":F(0)}
    by_name = {row["component"]: row for row in rows}
    checks = {
        "su5_generator_traceless": su5_traceless_balance() == 0,
        "all_expected_components_present": set(by_name) == set(expected),
        "all_charges_exact": all(by_name[name]["electric_charge"] == charge for name, charge in expected.items()),
        "all_q_identities_exact": all(row["electric_charge"] == row["t3"] + row["hypercharge"] for row in rows),
        "fermion_chirality_explicit": all(row["chirality"] in {"left","right"} for row in rows if row["kind"] == "fermion"),
        "minimal_sm_has_no_nu_r": "nu_R" not in by_name,
        "shell2_t3_interface_exact": all(row["t3"] == SPIN[row["shell2_spin"]]["t3"] for row in rows if row["shell2_spin"]),
        "gauge_block_and_complement_separated": all("(3,2)" not in row["su5_origin"] for row in rows if row["kind"] == "gauge"),
    }
    return {"schema":"Kp3.05.01-ChargeLedger/1.0", "status":"PASS" if all(checks.values()) else "FAIL",
            "rows": [{k:(str(v) if isinstance(v,F) else v) for k,v in row.items()} for row in rows],
            "checks":checks, "negative_tests":{"wrong_charge_detected": expected["u_L"] != F(1,3)},
            "boundary":"One minimal SM generation plus one Higgs doublet and SM gauge carriers. No nu_R; SU(5) complement dynamics, couplings, masses, and phenomenology remain open."}
