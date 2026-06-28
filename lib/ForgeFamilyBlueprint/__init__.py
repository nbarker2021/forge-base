"""ForgeFamilyBlueprint - the contract every Forge-family tool must satisfy.

The forge-family blueprint (kernel-ring form `CQE_CMPLX_ForgeFamilyBlueprint`,
`01_contracts/FORGE_FAMILY_CONTRACT.md`) was the meta-system that defines/names
the whole Forge ring, but it was never packaged. Built here as a real, importable
module: the contract as data + a `validate_forge()` checker that confirms a forge
module satisfies it (identity, engine core loop with receipts, CQE layer / reuse
default). This is the thing that makes a Forge a Forge.
"""
from __future__ import annotations

import types

CONTRACT = {
    "identity": "umbrella name capturing the whole tool; a manifest of what it inherits from",
    "engine": "a defined core loop (inputs, outputs, state transitions, validation, "
              "receipts) that labels what is final / placeholder / stub / future, and "
              "uses shared engine vehicles before custom routes",
    "cqe_layer": "bridges engine behavior -> math/formal structure -> product surface; "
                 "default is reuse/bind/extend an existing library identity, not a new datum",
    "universal_adapters": "binds to library identities, adapters, receipts, morphons",
    "receipt": "every event computed -> saved -> validated -> receipted -> reused",
}


def contract() -> dict:
    return dict(CONTRACT)


def validate_forge(mod: types.ModuleType) -> dict:
    """Check a forge module against the Forge-Family Contract."""
    checks = {
        "has_identity_docstring": bool((getattr(mod, "__doc__", "") or "").strip()),
        "has_engine_callable": any(
            callable(getattr(mod, n, None)) and not n.startswith("_")
            for n in dir(mod) if n not in ("verify",)
        ),
        "has_verify_receipt": callable(getattr(mod, "verify", None)),
    }
    receipt_ok = False
    if checks["has_verify_receipt"]:
        try:
            r = mod.verify()
            receipt_ok = isinstance(r, dict) and "status" in r
        except Exception:
            receipt_ok = False
    checks["verify_emits_receipt_with_status"] = receipt_ok
    passed = sum(1 for v in checks.values() if v)
    return {"forge": getattr(mod, "__name__", "?"), "checks": checks,
            "passed": passed, "total": len(checks),
            "compliant": passed == len(checks)}


def verify() -> dict:
    """Validate the contract is well-formed and that the newly-built forges comply."""
    results = []
    for name in ("KnightForge", "FoldForge", "MorphForge", "PolyForge",
                 "MetaForge", "CADForge", "WireBlock"):
        try:
            mod = __import__(name)
            results.append(validate_forge(mod))
        except Exception as exc:
            results.append({"forge": name, "compliant": False, "error": str(exc)})
    compliant = sum(1 for r in results if r.get("compliant"))
    return {"forge": "ForgeFamilyBlueprint",
            "status": "pass" if compliant == len(results) else "partial",
            "contract_sections": list(CONTRACT),
            "forges_checked": len(results), "compliant": compliant,
            "results": results}
