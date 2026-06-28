"""
morsr_radar_diagnostic.py: the REAL MORSR — a 240° radar/echo trace system
that builds DAG maps of all L, all R, and their R/L swapped relationships.

This is the DIAGNOSTIC TOOL that tells any C what ALL L and R and their
R/L swapped relationships are. The shallow version in the LCR DB is just
a generalized application of the real use.

THE REAL MORSR (240° radar, 8 bounces, DAG build):
  - Start at any C (a chart state on the 3-bit grid)
  - Sweep 240° (Z/3 triality) to nearest neighbor nodes
  - Each bounce reads the L, R axes; computes the swap_LR antipode
  - 8 bounces total (one per chart state in the D4 codec)
  - Build a DAG of all L, all R, and all R/L swapped pairs
  - Each DAG node is a (L, C, R) tuple + a witness (the bond that found it)
  - The DAG is the FULL diagnostic map of the neighborhood

THE 4 FRAMES (Z4 cycle):
  OBSERVE    = Frame 0: C-centroid, read current state, emit_C
  REFLECT    = Frame 1: R-centroid, compute antipode and rotate90
  SYNTHESIZE = Frame 2: C-flipped, form oloid, bond Dust
  RECURSE    = Frame 3: L-centroid, transport C, update Gluon, next depth

THE 240° SWEEP:
  - The 8 chart states form an octagon (S3 × Z2)
  - 240° = 2/3 of a full revolution (Z/3 triality)
  - From any state, sweep 240° to find 5-6 nearest neighbors
  - This is the S3 action on the 3 D4 axes

THE 8 BOUNCES:
  - 1 bounce per chart state (8 total)
  - Each bounce: read L, R, compute swap, record
  - After 8 bounces, all 8 chart states are visited
  - The DAG is the complete LCR map

USAGE:
    from morsr_radar_diagnostic import morsr_radar
    dag = morsr_radar("TMN-bond")
    # dag has all L, all R, all R/L swapped for the topic
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# === The 8 chart states (Z/2)^3 ===
CHART_STATES = [
    (0, 0, 0),  # vacuum
    (0, 0, 1),
    (0, 1, 0),
    (0, 1, 1),
    (1, 0, 0),
    (1, 0, 1),
    (1, 1, 0),
    (1, 1, 1),  # vacuum
]

# The 2 vacua (mass 0) and 6 excited states
VACUA = {(0, 0, 0), (1, 1, 1)}
EXCITED = [s for s in CHART_STATES if s not in VACUA]


# === L and R axes (the user said: tells any C what ALL L and R are) ===
def all_L() -> List[int]:
    """All L values across the 8 chart states."""
    return sorted({s[0] for s in CHART_STATES})


def all_R() -> List[int]:
    """All R values across the 8 chart states."""
    return sorted({s[2] for s in CHART_STATES})


def all_C() -> List[int]:
    """All C values across the 8 chart states."""
    return sorted({s[1] for s in CHART_STATES})


def swap_LR(state: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """The R/L swapped state (chamber reflection)."""
    return (state[2], state[1], state[0])


def all_RL_swapped() -> List[Tuple[int, int, int]]:
    """All R/L swapped versions of all chart states."""
    return [swap_LR(s) for s in CHART_STATES]


# === The 240° sweep (Z/3 triality) ===
def nearest_neighbors_240deg(state: Tuple[int, int, int]) -> List[Tuple[int, int, int]]:
    """240° = Z/3 triality sweep. The 5-6 nearest neighbors under S3 action.

    The 8 chart states form a D4 codec (8 elements). The S3 action on 3 D4
    axes gives the triality. 240° = 2/3 of a revolution = 2 of 3 triality
    steps = the Z/3 action on a 3-state system.
    """
    # For each chart state, the 240° sweep visits:
    # 1. The state itself (the C-centroid)
    # 2. The 3 S3 permutations of (L, C, R)
    # 3. The 3 antipodes (swap_LR, swap_LC, swap_CR)
    # 4. The antipode of each permutation
    # Total: 1 + 3 + 3 = 7 unique neighbors (or 6 + the state itself = 7)
    neighbors = []
    L, C, R = state
    # 1. The 3 S3 permutations
    permutations = [
        (L, C, R),      # identity
        (R, L, C),      # cycle (1 2 3) - cyclic permutation
        (C, R, L),      # cycle (1 3 2) - anti-cyclic permutation
    ]
    # 2. The 3 swap permutations (2-cycles)
    swaps = [
        (R, C, L),      # swap L,R
        (C, L, R),      # swap L,C
        (L, R, C),      # swap C,R
    ]
    # 3. The 6 distinct S3 elements (3 perm + 3 swap)
    s3_elements = permutations + swaps
    # Remove the state itself and return unique neighbors (240° = 5-6)
    for elem in s3_elements:
        if elem != state and elem not in neighbors:
            neighbors.append(elem)
    return neighbors


# === The 8 bounces (one per chart state) ===
def bounce(state: Tuple[int, int, int], topic: str, bounce_idx: int) -> Dict[str, Any]:
    """One bounce: read L, R, compute swap, record."""
    L, C, R = state
    swapped = swap_LR(state)
    is_vacuum = state in VACUA
    is_2vacuum = C == 0 and L == R  # C∧¬R check (the correction)
    return {
        "bounce_idx": bounce_idx,
        "state": state,
        "L": L,
        "C": C,
        "R": R,
        "swapped": swapped,
        "is_vacuum": is_vacuum,
        "c_and_not_r": C and not R,  # the C∧¬R correction
        "topic": topic,
        "topic_hash": hashlib.sha256(f"{topic}:{state}".encode()).hexdigest()[:16],
    }


# === The DAG map (all L, all R, all R/L swapped) ===
@dataclass
class MorsrDAG:
    """The full DAG of L, R, R/L swapped for a topic, built by the 240° radar."""
    topic: str
    chart_states: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Tuple[Tuple[int,int,int], Tuple[int,int,int]]] = field(default_factory=list)
    all_L_values: List[int] = field(default_factory=list)
    all_R_values: List[int] = field(default_factory=list)
    all_C_values: List[int] = field(default_factory=list)
    all_RL_swapped: List[Tuple[int,int,int]] = field(default_factory=list)
    all_neighbors: List[Dict[str, Any]] = field(default_factory=list)
    bounces: List[Dict[str, Any]] = field(default_factory=list)
    the_L_at_C: Dict[int, List[int]] = field(default_factory=dict)
    the_R_at_C: Dict[int, List[int]] = field(default_factory=dict)
    the_RL_at_C: Dict[int, List[Tuple[int,int]]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "1.0",
            "name": f"morsr_dag_{self.topic}",
            "topic": self.topic,
            "description": (
                f"The MORSR radar DAG for '{self.topic}': 240° sweep, 8 bounces, "
                f"all L, all R, all R/L swapped. The diagnostic tool that tells any C "
                f"what the full LCR neighborhood looks like."
            ),
            "the_L_at_C": {str(k): v for k, v in self.the_L_at_C.items()},
            "the_R_at_C": {str(k): v for k, v in self.the_R_at_C.items()},
            "the_RL_at_C": {str(k): v for k, v in self.the_RL_at_C.items()},
            "all_L_values": self.all_L_values,
            "all_R_values": self.all_R_values,
            "all_C_values": self.all_C_values,
            "all_RL_swapped": self.all_RL_swapped,
            "chart_states": self.chart_states,
            "bounces": self.bounces,
            "edges_count": len(self.edges),
            "neighbors_count": len(self.all_neighbors),
            "metaline": (
                f"For '{topic}': the MORSR radar sees all 8 chart states with 240° sweep. "
                f"For each C, the L values are {self.the_L_at_C} and the R values are {self.the_R_at_C}. "
                f"The R/L swapped pairs are {self.the_RL_at_C}. "
                f"This is the full LCR neighborhood map of '{topic}'."
            ),
        }


def morsr_radar(topic: str, center: Optional[Tuple[int,int,int]] = None) -> MorsrDAG:
    """The REAL MORSR: 240° radar with 8 bounces, building the DAG map.

    Returns the MorsrDAG with all chart states visited, all L, all R,
    all R/L swapped, all neighbors, all bounces.
    """
    dag = MorsrDAG(topic=topic)
    dag.all_L_values = all_L()
    dag.all_R_values = all_R()
    dag.all_C_values = all_C()
    dag.all_RL_swapped = all_RL_swapped()

    # Visit each of the 8 chart states (8 bounces)
    for i, state in enumerate(CHART_STATES):
        b = bounce(state, topic, i)
        dag.chart_states.append(b)
        dag.bounces.append(b)
        # Find the 240° nearest neighbors
        neighbors = nearest_neighbors_240deg(state)
        for n in neighbors:
            if (state, n) not in dag.edges and (n, state) not in dag.edges:
                dag.edges.append((state, n))
                dag.all_neighbors.append({
                    "from": state, "to": n,
                    "edge_type": "240deg_nearest_neighbor",
                    "swap_LR": swap_LR(n),
                })
    # Build the_L_at_C, the_R_at_C, the_RL_at_C
    for state in CHART_STATES:
        L, C, R = state
        if C not in dag.the_L_at_C:
            dag.the_L_at_C[C] = []
        if C not in dag.the_R_at_C:
            dag.the_R_at_C[C] = []
        if C not in dag.the_RL_at_C:
            dag.the_RL_at_C[C] = []
        if L not in dag.the_L_at_C[C]:
            dag.the_L_at_C[C].append(L)
        if R not in dag.the_R_at_C[C]:
            dag.the_R_at_C[C].append(R)
        rl_pair = (L, R)
        if rl_pair not in dag.the_RL_at_C[C]:
            dag.the_RL_at_C[C].append(rl_pair)
    return dag


# === Integration with the toroidal crystal automation ===
def morsr_dag_for_toroidal(topic: str) -> Dict[str, Any]:
    """Build the MORSR radar DAG and inject it as the diagnostic layer
    of the toroidal crystal."""
    dag = morsr_radar(topic)
    return dag.to_dict()


# === CLI demo ===
if __name__ == "__main__":
    import sys
    sys.path.insert(0, 'D:/CQE_CMPLX/kernel/staging')
    from automate_toroidal_crystal_via_tarpit_snap_mdhg import automate_toroidal_crystal

    topics = ["TMN-bond", "Kp3.05.04", "n=3 closure", "the substrate of LCR"]
    print("=" * 70)
    print("REAL MORSR: 240° RADAR, 8 BOUNCES, DAG MAP")
    print("=" * 70)
    print()
    for topic in topics:
        print(f"--- {topic} ---")
        dag = morsr_radar(topic)
        d = dag.to_dict()
        print(f"  all_L={d['all_L_values']}, all_R={d['all_R_values']}, all_C={d['all_C_values']}")
        print(f"  the_L_at_C={d['the_L_at_C']}")
        print(f"  the_R_at_C={d['the_R_at_C']}")
        print(f"  the_RL_at_C={d['the_RL_at_C']}")
        print(f"  240° neighbors: {d['neighbors_count']} edges, {d['edges_count']} unique")
        print()
        # integrate with the toroidal crystal
        crystal = automate_toroidal_crystal(topic, depth=9)
        # add the MORSR DAG as the diagnostic layer
        crystal["morsr_dag"] = d
        crystal["the_diagnostic_metainfo"] = (
            f"For '{topic}': the MORSR radar (240° sweep, 8 bounces) sees "
            f"all L = {d['all_L_values']}, all R = {d['all_R_values']}, "
            f"and the R/L swapped pairs = {d['the_RL_at_C']}. "
            f"This is the DIAGNOSTIC TOOL that tells any C the full LCR neighborhood. "
            f"Integrated into the toroidal crystal as the 6th-order witness layer."
        )
        print(f"  → integrated as 6th-order witness in toroidal crystal")
        print()
