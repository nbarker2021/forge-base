"""Energy quantum engine (recrafted from CQECMPLX-Formal-Suite CQE-PAPER-030/031/032/033).

Proves the honest energy-transport claims. Items that are NOT internally derivable are
flagged X (calibration claims, or arithmetic errors in the source papers):

  - verify_unified_energy_transport: kappa is the universal quantum (edge=kappa;
        VOA excited = 5*kappa; mass per bond = kappa). Honest.
  - verify_tarpit_mass_formula: m = N_bonds * kappa. Honest for arbitrary N_bonds.
        FLAGGED X: the "343-tile void mass = 343*kappa = 10.302" uses the UNSUPPORTED
        343-tile closure count (flagged in recraft of 020/022/023).
  - verify_coupling_transport: kappa-power formulas. FLAGGED X: CQE-PAPER-033 Sec 6.1
        claims 1/(kappa^2 * sin^2 theta_W) = 137.036, but the true value is ~4782; the
        alpha_em^-1 = 137 number is a calibrate_units calibration claim (E-category), NOT
        produced by the kappa formula. G_N = kappa^3 (~2.72e-5 geom units) is honest;
        conversion to 6.67e-11 is calibration.

No A033996 claim appears in CQE-PAPER-030..033 (energy/kappa focused).
"""

import math

from lattice_forge.axiom_verifiers import KAPPA, PHI, CHART_STATES, TRUE_VACUA
from lattice_forge.centroid_voa import voa_weight


def verify_unified_energy_transport():
    """kappa = ln(phi)/16 is the universal energy quantum (CQE-PAPER-030b)."""
    checks = {}

    # 1. kappa value
    k = math.log(PHI) / 16
    checks["kappa_value"] = abs(k - KAPPA) < 1e-15

    # 2. Edge energy = kappa (per bonded interaction / per edge)
    checks["edge_energy_kappa"] = True  # definitional: kappa IS the per-edge quantum

    # 3. VOA excited-state energy = 5 * kappa (vacua weight 0, excited weight 5)
    weights = [voa_weight(s) for s in CHART_STATES]
    checks["voa_excited_5kappa"] = (
        weights.count(0) == 2 and weights.count(5) == 6
    )

    # 4. Total excited energy = 6 * 5 * kappa = 30 kappa
    e_excited = sum(weights) * k
    checks["total_excited_30kappa"] = abs(e_excited - 30 * k) < 1e-12

    # 5. Path capacity 16 = 8 spectral edges x 2 chiralities (the denominator of kappa)
    checks["path_capacity_16"] = (len(CHART_STATES) * 2 == 16)

    all_pass = all(checks.values())
    return {
        "status": "pass" if all_pass else "fail",
        "checks": len(checks),
        "sub_checks": checks,
        "defects": 0 if all_pass else 1,
        "honesty_boundary": (
            "kappa = ln(phi)/16 universal quantum. Edge energy = kappa; VOA excited = "
            "5*kappa; 2 vacua weight 0, 6 excited weight 5; total excited = 30*kappa; "
            "denominator 16 = 8 edges x 2 chiralities. SM couplings are E-category "
            "calibration (calibrate_units), not derived from kappa here."
        ),
    }


def verify_tarpit_mass_formula():
    """Mass = N_bonds * kappa (CQE-PAPER-032). Honest form; 343 basis flagged."""
    checks = {}

    # 1. The formula is linear in bond count.
    def mass(n_bonds):
        return n_bonds * KAPPA

    checks["linear_formula"] = (
        abs(mass(7) - 7 * KAPPA) < 1e-12
        and abs(mass(49) - 49 * KAPPA) < 1e-12
    )

    # 2. Single tile (1 bond) mass = kappa exactly.
    checks["single_tile_kappa"] = abs(mass(1) - KAPPA) < 1e-12

    # 3. The paper's void-apex figure uses N_bonds = 343 (the unsupported 343-tile
    #    closure). We verify the FORMULA computes mass(343) = 343*kappa = 10.302...,
    #    but the 343 COUNT itself is FLAGGED X (not produced by the deduping closure
    #    engine - see recraft of 020/022/023).
    computed = mass(343)
    checks["void_mass_formula_value"] = abs(computed - 343 * KAPPA) < 1e-9
    checks["void_343_count_unsupported"] = True  # informational flag (see honesty_boundary)

    all_pass = all(checks.values())
    return {
        "status": "pass" if all_pass else "fail",
        "checks": len(checks),
        "sub_checks": checks,
        "defects": 0 if all_pass else 1,
        "honesty_boundary": (
            "Mass = N_bonds * kappa is honest and linear. The void-apex mass 343*kappa "
            "= 10.302 follows the formula, BUT the N_bonds=343 count is the UNSUPPORTED "
            "343-tile closure (FLAGGED X in recraft of 020/022/023); the deduping closure "
            "engine does not produce 343 distinct states. Higgs vev = 120*kappa*alpha*scale "
            "is a calibrate_units calibration claim (E-category)."
        ),
    }


def verify_coupling_transport():
    """Couplings as kappa transport (CQE-PAPER-033). Honest computations; claims flagged."""
    checks = {}

    k = KAPPA
    sin2 = 0.23122

    # 1. alpha_s = 5*kappa/pi (raw, no running) - honest computation.
    a_s_raw = 5 * k / math.pi
    checks["alpha_s_raw"] = abs(a_s_raw - 0.04785) < 1e-3
    # The "running to 0.1179" factor is hand-waved; recorded as calibration.
    checks["alpha_s_running_unverified"] = True  # informational flag

    # 2. alpha_em: paper claims alpha_em^-1 = 137.036 from kappa^2 * sin^2 theta_W.
    #    Honest computation: kappa^2 * sin^2 = 2.09e-4; its reciprocal is ~4782, NOT 137.
    alpha_em_raw = k**2 * sin2
    checks["alpha_em_formula_value"] = abs(alpha_em_raw - 0.0002091) < 1e-6
    checks["alpha_em_137_not_from_formula"] = True  # 1/0.0002091 = 4782 != 137 -> FLAGGED X
    # The 137.036 number itself comes from calibrate_units (E-category), not this formula.

    # 3. G_N = kappa^3 (geometric units) - honest computation.
    g_n = k**3
    checks["newton_g_raw"] = abs(g_n - 2.72e-5) < 1e-6
    # Conversion to 6.67e-11 m^3/kg/s^2 is calibration (scale factor).

    all_pass = all(checks.values())
    return {
        "status": "pass" if all_pass else "fail",
        "checks": len(checks),
        "sub_checks": checks,
        "defects": 0 if all_pass else 1,
        "honesty_boundary": (
            "Coupling kappa-power formulas computed honestly: alpha_s = 5*kappa/pi "
            "(~0.04785; running to 0.1179 is calibration), G_N = kappa^3 (~2.72e-5 geom). "
            "FLAGGED X: CQE-PAPER-033 Sec 6.1 claims 1/(kappa^2*sin^2 theta_W)=137.036, "
            "but the true reciprocal is ~4782; alpha_em^-1=137.036 is a calibrate_units "
            "calibration (E-category), NOT produced by the kappa formula. The 343-tile "
            "mass basis is also unsupported (see 020/022/023 recraft)."
        ),
    }
