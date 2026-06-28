"""AuthenticaForge — 5-term lattice authentication codes with CRT closure.

Distilled from product_authentica (historical_pastworks) into the forge ring.
Paper binding: CQE-paper-08 (Lattice Closure). The code lattice is
[1, 3, 7, 21, 137]: product 1*3*7*21 = 441, sum 441 + 137 = 578 = 2 * 17^2,
digital root DR(578) = 2. A code is lattice-closed when

    d1*d2*d3*d4 + d5 == 0 (mod 17)   and   DR(d1*d2*d3*d4 + d5) == 2,

which by CRT (gcd(9, 17) = 1) is exactly  sum == 119 (mod 153).

Adjudicated corrections to the source product:
  1. The global mutable sequence counter (thread lock) is removed; the
     sequence is an explicit parameter. Same inputs, same code — the Event
     Law determinism requirement.
  2. Structural finding: the check digit (DR + sum mod 17) mod 10 equals 2
     for EVERY lattice-valid code, so it is constant and not an independent
     third check; it only detects corruption of itself. Recorded as a fact;
     unforgeability rests on the HMAC layer alone.
  3. FastAPI/SDK layers stay product-side.

Stdlib only.
"""
from __future__ import annotations

import base64
import hashlib
import hmac as hmac_mod
from typing import Any, Optional

FIVE_TERM_LATTICE = (1, 3, 7, 21, 137)
LATTICE_PRODUCT = 1 * 3 * 7 * 21          # 441
LATTICE_SUM = LATTICE_PRODUCT + 137       # 578 = 2 * 17^2
LATTICE_MODULUS = 17
LATTICE_DIGITAL_ROOT = 2
CRT_RESIDUE = 119                          # unique x in [0,153): x%17==0, DR(x)==2
CRT_MODULUS = 9 * 17                       # 153


def digital_root(n: int) -> int:
    """Iterated digit sum; closed form 1 + (n-1) % 9 for n > 0."""
    if n == 0:
        return 0
    return 9 if n % 9 == 0 else n % 9


def is_lattice_closed(d1: int, d2: int, d3: int, d4: int, d5: int) -> bool:
    """The pure offline check: works on a calculator."""
    s = d1 * d2 * d3 * d4 + d5
    return s % LATTICE_MODULUS == 0 and digital_root(s) == LATTICE_DIGITAL_ROOT


def _derive_digit(seed: int, lattice_term: int, position: int) -> int:
    if seed in FIVE_TERM_LATTICE:
        return seed
    return max(1, min(9, (seed * 31 + lattice_term * 17 + position * 13) % 9 + 1))


def binding_digit(d1: int, d2: int, d3: int, d4: int, sequence: int) -> int:
    """The computed 5th digit closing the lattice.

    Solves sum == CRT_RESIDUE (mod CRT_MODULUS) with sum = product + d5:
    d5 = 119 + 153*m - product for an m derived deterministically from the
    sequence. Distinct sequences in [0, 997) give distinct m (37 is
    invertible mod the prime 997), hence distinct codes.
    """
    product = d1 * d2 * d3 * d4
    min_m = max(0, (product - CRT_RESIDUE) // CRT_MODULUS + 1)
    m = min_m + (sequence * 37 + 137) % 997
    d5 = CRT_RESIDUE + CRT_MODULUS * m - product
    if d5 < 1:
        d5 = CRT_RESIDUE + CRT_MODULUS * (min_m + 1) - product
    return d5


def generate_code(manufacturer_id: int, product_line_id: int, facility_id: int,
                  production_date: int, sequence: int,
                  secret: Optional[str] = None) -> dict[str, Any]:
    """Generate a lattice-closed code. Fully deterministic in its inputs."""
    d1 = _derive_digit(manufacturer_id, FIVE_TERM_LATTICE[0], 0)
    d2 = _derive_digit(product_line_id, FIVE_TERM_LATTICE[1], 1)
    d3 = _derive_digit(facility_id, FIVE_TERM_LATTICE[2], 2)
    d4 = _derive_digit(production_date, FIVE_TERM_LATTICE[3], 3)
    d5 = binding_digit(d1, d2, d3, d4, sequence)
    s = d1 * d2 * d3 * d4 + d5
    check_digit = (digital_root(s) + s % LATTICE_MODULUS) % 10  # constant 2 when valid
    code = f"AUTH-{d1:03d}-{d2:03d}-{d3:03d}-{d4:03d}-{d5:03d}-{check_digit}"
    out: dict[str, Any] = {
        "code": code,
        "digits": [d1, d2, d3, d4, d5],
        "check_digit": check_digit,
        "lattice_sum": s,
        "digital_root": digital_root(s),
        "lattice_closed": is_lattice_closed(d1, d2, d3, d4, d5),
        "qr_payload": qr_encode(code),
    }
    if secret:
        out["hmac"] = hmac_mod.new(secret.encode(), code.encode(),
                                   hashlib.sha256).hexdigest()[:16]
    return out


def verify_code(code: str, secret: Optional[str] = None,
                hmac_sig: Optional[str] = None) -> dict[str, Any]:
    """Verify a code: lattice closure, digital root, optional HMAC."""
    parts = code.strip().upper().split("-")
    if len(parts) != 7 or parts[0] != "AUTH":
        return {"authentic": False, "error": "parse failed"}
    try:
        d1, d2, d3, d4, d5 = (int(p) for p in parts[1:6])
    except ValueError:
        return {"authentic": False, "error": "parse failed"}
    s = d1 * d2 * d3 * d4 + d5
    lattice_ok = s % LATTICE_MODULUS == 0
    dr_ok = digital_root(s) == LATTICE_DIGITAL_ROOT
    hmac_ok = None
    if secret and hmac_sig:
        expected = hmac_mod.new(secret.encode(), code.encode(),
                                hashlib.sha256).hexdigest()[:16]
        hmac_ok = hmac_mod.compare_digest(expected, hmac_sig)
    checks = [lattice_ok, dr_ok] + ([hmac_ok] if hmac_ok is not None else [])
    return {
        "authentic": all(checks),
        "lattice_check": lattice_ok,
        "dr_check": dr_ok,
        "hmac_ok": hmac_ok,
        "lattice_sum": s,
        "method": "server_signed" if hmac_ok is not None else "offline_math",
    }


def qr_encode(code: str) -> str:
    """Encode the full canonical code string.

    The source product packed fixed 3-digit fields, but d5 is unbounded
    (that is what separates batch sequences), so its decoder corrupted any
    code with a 4+ digit d5. Encoding the canonical string round-trips for
    every valid code.
    """
    return "authentica://v/" + base64.b32encode(code.encode()).decode().rstrip("=")


def qr_decode(payload: str) -> str:
    if not payload.startswith("authentica://v/"):
        return payload
    enc = payload[len("authentica://v/"):]
    pad = (-len(enc)) % 8
    return base64.b32decode(enc + "=" * pad).decode()


# ─── Finite verifier (paper-bound claims, CQE-paper-08) ─────────────────────

def verify() -> dict[str, Any]:
    """Run the 10 finite checks that bind AuthenticaForge to CQE-paper-08."""
    checks: dict[str, bool] = {}

    # 1. Lattice constants close: 441 + 137 = 578 = 2 * 17^2, DR 2, 0 mod 17
    checks["lattice_constants_close"] = (
        LATTICE_PRODUCT == 441
        and LATTICE_SUM == 578 == 2 * 17 ** 2
        and LATTICE_SUM % 17 == 0
        and digital_root(LATTICE_SUM) == 2
    )

    # 2. Digital root closed form matches iterated digit sum on 1..10000
    def dr_iter(n: int) -> int:
        while n >= 10:
            n = sum(int(c) for c in str(n))
        return n
    checks["digital_root_closed_form"] = all(
        digital_root(n) == dr_iter(n) for n in range(1, 10001)
    )

    # 3. CRT: x%17==0 and DR(x)==2 has the unique solution 119 in [0, 153)
    sols = [x for x in range(CRT_MODULUS)
            if x % 17 == 0 and digital_root(x) == 2]
    checks["crt_unique_residue_119_mod_153"] = sols == [CRT_RESIDUE]

    # 4. Every valid sum has digital root 2: DR(119 + 153m) == 2 for m in 0..999
    checks["valid_sums_always_dr_2"] = all(
        digital_root(CRT_RESIDUE + CRT_MODULUS * m) == 2 for m in range(1000)
    )

    # 5. Binding digit closes the lattice for all d1..d4 in 1..9 (6561 cases)
    checks["binding_digit_closes_all_6561"] = all(
        is_lattice_closed(a, b, c, d, binding_digit(a, b, c, d, sequence=5))
        for a in range(1, 10) for b in range(1, 10)
        for c in range(1, 10) for d in range(1, 10)
    )

    # 6. Tamper detection: any d5 shift by 1..16 breaks the mod-17 identity
    base = generate_code(3, 7, 21, 260612, sequence=42)
    d1, d2, d3, d4, d5 = base["digits"]
    checks["d5_perturbation_detected_up_to_16"] = all(
        not is_lattice_closed(d1, d2, d3, d4, d5 + delta)
        for delta in range(1, 17)
    )

    # 7. Structural finding: check digit is constant 2 for valid codes
    cds = {generate_code(m, 7, 21, 260612, sequence=m)["check_digit"]
           for m in range(1, 200)}
    checks["check_digit_constant_2_for_valid_codes"] = cds == {2}

    # 8. Generation is deterministic; distinct sequences below 997 separate
    a = generate_code(3, 7, 21, 260612, sequence=42)
    b = generate_code(3, 7, 21, 260612, sequence=42)
    batch = {generate_code(3, 7, 21, 260612, sequence=s)["code"]
             for s in range(500)}
    checks["deterministic_and_500_batch_unique"] = (
        a["code"] == b["code"] and len(batch) == 500
    )

    # 9. QR payload round-trips
    checks["qr_payload_roundtrip"] = qr_decode(qr_encode(a["code"])) == a["code"]

    # 10. End-to-end: generated code verifies offline and with HMAC;
    #     wrong HMAC fails
    signed = generate_code(3, 7, 21, 260612, sequence=7, secret="k1")
    good = verify_code(signed["code"], secret="k1", hmac_sig=signed["hmac"])
    bad = verify_code(signed["code"], secret="k1", hmac_sig="0" * 16)
    plain = verify_code(signed["code"])
    checks["end_to_end_verify_and_hmac_gate"] = (
        good["authentic"] and plain["authentic"] and not bad["authentic"]
    )

    return {
        "forge": "AuthenticaForge",
        "paper": "CQE-paper-08",
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2))
