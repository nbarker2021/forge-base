from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict
import random

@dataclass(frozen=True)
class DiceEvent:
    sides: int
    roll: int
    boundary_question: str
    interpretation: str

@dataclass(frozen=True)
class CardEvent:
    card: str
    color: str
    suit: str
    rank: str
    interpretation: str

SUITS = ["hearts", "diamonds", "clubs", "spades"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]


def roll_dice(boundary_question: str, sides: int = 6, seed: int | None = None) -> DiceEvent:
    rng = random.Random(seed)
    roll = rng.randint(1, sides)
    midpoint = (sides + 1) / 2
    interpretation = "possible_branch" if roll >= midpoint else "randomness_check"
    return DiceEvent(sides=sides, roll=roll, boundary_question=boundary_question, interpretation=interpretation)


def draw_card(seed: int | None = None) -> CardEvent:
    rng = random.Random(seed)
    suit = rng.choice(SUITS)
    rank = rng.choice(RANKS)
    color = "red" if suit in {"hearts", "diamonds"} else "black"
    if rank == "A":
        role = "one_or_eleven_entry"
    elif rank in {"J", "Q", "K"}:
        role = "witness_form"
    else:
        role = "ranked_setting"
    return CardEvent(card=f"{rank} of {suit}", color=color, suit=suit, rank=rank, interpretation=role)


def legal_binding(colors: List[str]) -> Tuple[bool, str]:
    """Simple initial binding test.

    Same-color and black/white/clear/grey-neon support relationships are accepted.
    Cross-RGB bindings are marked as legal only if at least three colors are present,
    representing a triadic gradient rather than arbitrary two-color binding.
    """
    unique = set(colors)
    if len(unique) == 1:
        return True, "self_similar_binding"
    if "clear" in unique:
        return True, "overlay_binding"
    if {"black", "white"}.issubset(unique):
        return True, "proof_obligation_podal_binding"
    if len(unique.intersection({"red", "green", "blue"})) >= 3:
        return True, "triadic_color_binding"
    return False, "unbound_obligation"


def string_relation(source: str, target: str, color: str, relation: str = "transport") -> Dict[str, str]:
    return {
        "source": source,
        "target": target,
        "color": color,
        "relation": relation,
        "meaning": "colored meso-layer carrier/braid/bond edge",
    }
