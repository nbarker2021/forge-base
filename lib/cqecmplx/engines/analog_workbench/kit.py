from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Iterable

COLOR_FAMILIES = [
    "red", "green", "blue", "white", "black", "clear", "grey_gradient", "neon"
]

TOOL_CLASSES = [
    "notebook", "loose_paper", "gradient_page", "index_card", "string", "token",
    "sticker", "pen_marker", "clear_sleeve", "tab_divider", "dice", "playing_card",
    "balsa_edge", "receipt_sheet", "proof_tree_sheet", "obligation_sheet"
]

TOOL_PURPOSES = {
    "notebook": "Bound color-domain container for stable state, receipts, proof paths, and obligations.",
    "loose_paper": "Live readout substrate; begins grey and receives gradient state before binding.",
    "gradient_page": "Pre-oriented page where book color is read in relation to another color or boundary.",
    "index_card": "Decision probe for continue/new-page, proof/obligation, binding route, and next action.",
    "string": "Meso-layer carrier for edge, bond, braid, knot, transport path, or page-to-page bridge.",
    "token": "Movable local state body; can mark C, branch, node, active object, or local cell.",
    "sticker": "Fixed local marker for state tags, proof tags, closure marks, or receipt anchors.",
    "pen_marker": "Color trace tool for route, correction, entry, exit, boundary, and readout marks.",
    "clear_sleeve": "Reversible overlay for non-destructive tests, dry-erase routes, and comparisons.",
    "tab_divider": "Physical navigation marker for papers, colors, appendices, examples, and tool families.",
    "dice": "Scaled probability boundary operator used only at legal uncertainty points.",
    "playing_card": "Binary/permutation operator with red-black polarity, suits, ranks, faces, and jokers.",
    "balsa_edge": "Rigid physical lattice edge, axis, frame, spacing rule, or transport relation.",
    "receipt_sheet": "Recoverable log of what happened, what moved, colors used, and closure status.",
    "proof_tree_sheet": "Manual proof dependency surface: axioms, lemmas, formalism, and proof edges.",
    "obligation_sheet": "Open black/shadow state ledger for unresolved routes and deferred proof requirements.",
}

COLOR_PURPOSES = {
    "red": "Primary quark-color carrier; active red state movement.",
    "green": "Primary quark-color carrier; active green state movement.",
    "blue": "Primary quark-color carrier; active blue state movement.",
    "white": "Visible proof continuation, accepted route, exposed carrier.",
    "black": "Obligation, shadow state, unresolved remainder, deferred branch.",
    "clear": "Overlay, reversible comparison, non-destructive active readout.",
    "grey_gradient": "Unresolved loose substrate; must receive at least three-color gradient.",
    "neon": "Podal high-energy, collision-active, boundary-active, or urgent comparison state.",
}

@dataclass(frozen=True)
class KitObject:
    object_id: str
    color: str
    tool_class: str
    copy_index: int
    mode: str
    purpose: str


def build_eightfold_kit(copies: int = 8) -> Dict[str, object]:
    """Build an eightfold manifest for every color and every tool class.

    The manifest is the digital equivalent of the physical package bill of materials.
    Each color/tool pair has `copies` objects so all eight visible readout slots can
    be instantiated at once.
    """
    objects: List[KitObject] = []
    for color in COLOR_FAMILIES:
        for tool in TOOL_CLASSES:
            for i in range(1, copies + 1):
                objects.append(
                    KitObject(
                        object_id=f"{color}:{tool}:{i:02d}",
                        color=color,
                        tool_class=tool,
                        copy_index=i,
                        mode="loose_or_bound_by_use",
                        purpose=TOOL_PURPOSES[tool],
                    )
                )
    return {
        "kit_name": "Analog Forge Workbook Kit",
        "version": "0.1.0",
        "copies_per_color_tool": copies,
        "color_families": COLOR_FAMILIES,
        "tool_classes": TOOL_CLASSES,
        "color_purposes": COLOR_PURPOSES,
        "tool_purposes": TOOL_PURPOSES,
        "object_count": len(objects),
        "objects": [asdict(o) for o in objects],
    }


def count_by_color(manifest: Dict[str, object]) -> Dict[str, int]:
    counts = {c: 0 for c in COLOR_FAMILIES}
    for obj in manifest.get("objects", []):
        counts[obj["color"]] += 1
    return counts


def count_by_tool(manifest: Dict[str, object]) -> Dict[str, int]:
    counts = {t: 0 for t in TOOL_CLASSES}
    for obj in manifest.get("objects", []):
        counts[obj["tool_class"]] += 1
    return counts
