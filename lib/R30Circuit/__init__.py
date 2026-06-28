"""R30Circuit - the reversible 3-qubit Rule 30 quantum circuit (lost thread S5).

Barker Supplement S5 (Quantum Circuit Implementation) described the reversible
unitary `U_R30` but it was never packaged. Built here as a real, importable,
stdlib-only classical-reversible simulation:

    U_R30 |L,C,R>|t> = |L,C,R> |t XOR f(L,C,R)>,   f = L XOR (C OR R)  (Rule 30)

Gate sequence (4 qubits: 3 neighborhood + 1 target):
    CNOT(L->t); CNOT(C->t); CNOT(R->t); Toffoli(C,R->t)
because  f = L XOR C XOR R XOR (C AND R) = L XOR (C OR R).

The 1+8+8+1 Cayley-Dickson lift (8 inputs -> 8 outputs, vacuum + identity) is the
unistochastic tree; the measured-physics quantum claim is the external bridge.
"""
from __future__ import annotations


def rule30(L: int, C: int, R: int) -> int:
    return L ^ (C | R)


def apply_u_r30(L: int, C: int, R: int, t: int = 0) -> tuple[int, int, int, int]:
    """Reversible Rule 30 gate: CNOTs + Toffoli onto the target qubit."""
    t ^= L            # CNOT(L -> t)
    t ^= C            # CNOT(C -> t)
    t ^= R            # CNOT(R -> t)
    t ^= (C & R)      # Toffoli(C,R -> t)
    return (L, C, R, t)


def is_reversible() -> bool:
    """U_R30 is a permutation of the 16 four-qubit basis states."""
    outs = [apply_u_r30((s >> 3) & 1, (s >> 2) & 1, (s >> 1) & 1, s & 1)
            for s in range(16)]
    return len(set(outs)) == 16


def reproduces_rule30() -> bool:
    """With t=0 the target ends as exactly the Rule 30 output."""
    return all(apply_u_r30(L, C, R, 0)[3] == rule30(L, C, R)
               for L in (0, 1) for C in (0, 1) for R in (0, 1))


def cd_tree() -> dict:
    """The Cayley-Dickson 1+8+8+1 tree counts for the 3-qubit lift."""
    inputs = [(L, C, R) for L in (0, 1) for C in (0, 1) for R in (0, 1)]   # 8
    outputs = sorted({apply_u_r30(L, C, R, 0)[3] for (L, C, R) in inputs}) # bits
    return {"vacuum": 1, "inputs": len(inputs), "outputs_tree": len(inputs),
            "identity": 1, "total_1_8_8_1": 1 + 8 + 8 + 1, "bit_values": outputs}


def verify() -> dict:
    rev, repro = is_reversible(), reproduces_rule30()
    return {"forge": "R30Circuit", "paper": 9,
            "status": "pass" if rev and repro else "fail",
            "reversible_16_states": rev,
            "reproduces_rule30": repro,
            "cd_tree": cd_tree()["total_1_8_8_1"],
            "note": "reversible circuit exact; measured-physics quantum claim is external"}
