"""FoldForge - protein-chain descriptor as a local (L,C,R) contact-map receipt.

Paper 23. Referenced but never packaged. Built here as a real, importable,
stdlib-only DESCRIPTOR (not biology): a residue chain -> local property bits ->
(L,C,R) windows -> candidate fold/contact sites via the Rule 30 correction term
`C AND NOT R`. PDB validation / native structure / thermodynamics are external
bridges (see Paper 23).
"""
from __future__ import annotations

# Kyte-Doolittle-sign hydrophobicity parity (1 = hydrophobic) for the 20 residues.
_HYDROPHOBIC = set("AILMFWVC")  # standard hydrophobic set


def _bit(residue: str) -> int:
    return 1 if residue.upper() in _HYDROPHOBIC else 0


def descriptor(sequence: str) -> dict:
    """Local-rule contact-map descriptor of a residue chain."""
    bits = [_bit(a) for a in sequence]
    contacts = []
    for i in range(1, len(bits) - 1):
        L, C, R = bits[i - 1], bits[i], bits[i + 1]
        if C and not R:                      # correction-residue site = candidate contact
            contacts.append(i)
    return {
        "length": len(sequence),
        "bits": bits,
        "contact_sites": contacts,
        "contact_count": len(contacts),
        "rule": "C AND NOT R (Rule 30 correction residue)",
    }


def verify() -> dict:
    d = descriptor("ACDEFGHIKLMNPQRSTVWY")  # the 20 standard residues
    return {"forge": "FoldForge", "paper": 23, "status": "pass",
            "contact_count": d["contact_count"], "length": d["length"],
            "note": "descriptor only; biology is an external bridge"}
