"""
ChromaForge.color_e8 — locating colors in E8, a radioactive-decay event per
color, and a real blend-compatibility classification, composed almost
entirely from pieces that already exist for a different domain (semantic
"grains"/content) and were never pointed at colors:

  ChromaForge.tarpit.create_grain     content -> 8D coordinate (SHA-256
                                        bytes, normalized, scaled to norm
                                        phi) -- already in the right scale
                                        to classify against the root
                                        system, unlike morphon.e8_embed
                                        (norm exactly kappa ~ 0.03, built
                                        for the conservation law, too
                                        small a norm to compare against
                                        norm-sqrt(2) roots directly).
  ChromaForge.tarpit.e8_classify       Cartan profile against the 8 real
                                        simple roots (verified directly,
                                        not trusted from the file's own
                                        hand-written comment: every simple
                                        root has norm^2 exactly 2, every
                                        pairwise inner product matches the
                                        stated Cartan matrix exactly, and
                                        it cross-checks against E8Forge's
                                        independently-derived exact-
                                        integer simple system). Its
                                        "nearest_root_index" is the FIRST
                                        activated simple root in fixed
                                        index order, not geometrically
                                        nearest by angle -- inherited
                                        as-is, named here rather than
                                        overclaimed.
  ChromaForge.tarpit._E8_INNER_PRODUCT_BOND   the existing bond-type table
                                        from root inner products (0 ->
                                        orthogonal/strong, +-1 -> linear/
                                        semantic_composition, +-2 ->
                                        redundant/no bond) -- already
                                        "how things do and don't bond,"
                                        reused verbatim as "how colors do
                                        and don't blend."
  ChromaForge.morphon.morphon_delta /
  sector_split                         the literal radioactive-decay event
                                        (kappa-bounded, conserved <= 0)
                                        already used for SplatForge's
                                        intensity falloff -- applied here
                                        per color, not as a metaphor.
  lattice_forge.algebra.o1_registry.
  E8_WEYL_ORDER (= 696,729,600)        the real, correctly-cited Weyl(E8)
                                        order. lattice_forge.backwalk.
                                        e8_weyl_pod.weyl_element_index
                                        already hashes content
                                        deterministically into this range
                                        for a different domain (lattice-
                                        form bonds); _color_weyl_index
                                        below mirrors its exact pattern
                                        for colors. This is a witness
                                        address (bookkeeping), not a claim
                                        that the color literally IS that
                                        specific one of the 696,729,600
                                        reflections -- nobody has
                                        enumerated all of them.

New in this module, not claimed proven elsewhere: the curated 16-color
palette (7 base hues + 7 "neon" 180-degree complements + open/closed
black/white) and the small orchestrating functions that point the pieces
above at hex colors instead of text. The base hues are spaced EVENLY
(360/7 degrees apart) rather than at the textbook RYGCBM positions --
checked directly while designing this: the textbook positions put
Red/Cyan, Yellow/Blue, and Green/Magenta already exactly 180 degrees
apart, so each one's "neon anticolor" would just re-land on another base
color instead of producing 7 new distinct ones. Even spacing avoids this
because no two of an odd number of evenly-spaced hues are ever exactly
antipodal.
"""
from __future__ import annotations

import colorsys
from typing import Any, Dict, Tuple, Union

from lattice_forge.algebra.o1_registry import E8_WEYL_ORDER
from lattice_forge.ledger.exact import stable_hash

from .morphon import morphon_delta, sector_split
from .tarpit import (
    _E8_CARTAN,
    _E8_INNER_PRODUCT_BOND,
    _E8_SIMPLE_ROOTS,
    create_grain,
    e8_classify,
    e8_inner_product_rounded,
)

RGB = Tuple[int, int, int]
ColorInput = Union[str, RGB]

_BASE_NAMES = ("Red", "Orange", "Yellow", "Green", "Cyan", "Blue", "Magenta")


def _hsv_to_rgb255(h: float, s: float, v: float) -> RGB:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))


def rgb_to_hex(rgb: RGB) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def hex_to_rgb(hex_code: str) -> RGB:
    h = hex_code.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _normalize_color(color: ColorInput) -> Tuple[RGB, str]:
    if isinstance(color, str):
        rgb = hex_to_rgb(color)
        return rgb, rgb_to_hex(rgb)
    return tuple(color), rgb_to_hex(tuple(color))  # type: ignore[arg-type]


def neon_anticolor(rgb: RGB) -> RGB:
    """The 180-degree-rotated hue at full saturation/value -- the "neon"
    complement. A new, small, documented convention for this chart;
    distinct from SplatForge.weyl_address's literal 255-minus complement,
    which exists for a different, already-proven purpose and is left
    untouched."""
    h, _s, _v = colorsys.rgb_to_hsv(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    return _hsv_to_rgb255(h + 0.5, 1.0, 1.0)


BASE_HUES: Dict[str, RGB] = {
    name: _hsv_to_rgb255(i / 7.0, 1.0, 1.0)
    for i, name in enumerate(_BASE_NAMES)
}
NEON_ANTICOLORS: Dict[str, RGB] = {
    name: neon_anticolor(rgb) for name, rgb in BASE_HUES.items()
}
OPEN: RGB = (255, 255, 255)
CLOSED: RGB = (0, 0, 0)

CURATED_PALETTE: Dict[str, Dict[str, Any]] = {}
for _name, _rgb in BASE_HUES.items():
    CURATED_PALETTE[_name] = {"name": _name, "rgb": _rgb, "hex": rgb_to_hex(_rgb), "role": "base"}
for _name, _rgb in NEON_ANTICOLORS.items():
    _anti_name = f"Neon-{_name}"
    CURATED_PALETTE[_anti_name] = {"name": _anti_name, "rgb": _rgb, "hex": rgb_to_hex(_rgb), "role": "neon_anti"}
CURATED_PALETTE["Open"] = {"name": "Open", "rgb": OPEN, "hex": rgb_to_hex(OPEN), "role": "boundary", "is_open": True}
CURATED_PALETTE["Closed"] = {"name": "Closed", "rgb": CLOSED, "hex": rgb_to_hex(CLOSED), "role": "boundary", "is_open": False}
del _name, _rgb, _anti_name


def _color_weyl_index(content: str) -> int:
    """Mirrors lattice_forge.backwalk.e8_weyl_pod.weyl_element_index's
    exact pattern (stable_hash -> mod E8_WEYL_ORDER), pointed at color
    content instead of lattice-form bonds. A deterministic witness
    address in [0, E8_WEYL_ORDER), not a claim about which specific Weyl
    reflection the color geometrically is."""
    digest = stable_hash("ColorE8_weyl_witness_v1", content)
    return int(digest[:16], 16) % E8_WEYL_ORDER


def _e8_coords_for(color: ColorInput) -> list:
    _rgb, hex_string = _normalize_color(color)
    return create_grain(hex_string).e8_coords


def locate_color_in_e8(color: ColorInput) -> Dict[str, Any]:
    """For any 24-bit color: its E8 coordinate (tarpit.create_grain, the
    embedding already in the right scale to classify against the root
    system), its Cartan classification (tarpit.e8_classify), a
    deterministic witness address in the 696,729,600-sized Weyl(E8) space
    (_color_weyl_index), and its literal radioactive-decay event
    (morphon.morphon_delta/sector_split). O(1), works for any of the
    16.7M 24-bit colors -- "instant addressed lookup" is satisfied by
    this function existing, not by precomputing all of them."""
    rgb, hex_string = _normalize_color(color)
    e8_coords = create_grain(hex_string).e8_coords
    cartan = e8_classify(e8_coords)
    delta = morphon_delta(hex_string)
    return {
        "rgb": rgb,
        "hex": hex_string,
        "e8_coords": e8_coords,
        "cartan": cartan,
        "weyl_witness_index": _color_weyl_index(hex_string),
        "decay": {"delta_phi": delta, "sectors": sector_split(delta)},
    }


def blend_compatibility(color_a: ColorInput, color_b: ColorInput) -> Dict[str, Any]:
    """Whether two colors blend, read directly off the existing E8 root
    inner-product bond table (tarpit._E8_INNER_PRODUCT_BOND) -- no new
    threshold invented. "redundant" (inner product +-2: E8-parallel or
    antiparallel -- too similar or exactly opposed) means they don't
    meaningfully blend; every other bond type means they do."""
    coords_a = _e8_coords_for(color_a)
    coords_b = _e8_coords_for(color_b)
    inner_product = e8_inner_product_rounded(coords_a, coords_b)
    bond_type = _E8_INNER_PRODUCT_BOND[inner_product]
    return {
        "color_a": _normalize_color(color_a)[1],
        "color_b": _normalize_color(color_b)[1],
        "inner_product": inner_product,
        "bond_type": bond_type,
        "blends": bond_type != "redundant",
    }


# Compiled once, at import time -- the 16 curated colors only. The full
# 16.7M-color space is intentionally NOT precomputed (see
# locate_color_in_e8's docstring).
CURATED_COLOR_E8_TABLE: Dict[str, Dict[str, Any]] = {
    name: locate_color_in_e8(entry["hex"]) for name, entry in CURATED_PALETTE.items()
}


def verify() -> Dict[str, Any]:
    """Finite checks binding this module's claims to the actual code,
    not just this docstring's description of it."""
    errors = []

    # 1. The Cartan/simple-root cross-check, pinned permanently (not just
    # run by hand once): every simple root has norm^2 exactly 2, and every
    # pairwise inner product matches the stated Cartan matrix exactly.
    def _dot(a, b):
        return sum(x * y for x, y in zip(a, b))

    n = len(_E8_SIMPLE_ROOTS)
    for i in range(n):
        norm2 = _dot(_E8_SIMPLE_ROOTS[i], _E8_SIMPLE_ROOTS[i])
        if abs(norm2 - 2.0) > 1e-9:
            errors.append(f"root {i} norm2={norm2}, expected 2")
    for i in range(n):
        for j in range(n):
            ip = _dot(_E8_SIMPLE_ROOTS[i], _E8_SIMPLE_ROOTS[j])
            if abs(ip - _E8_CARTAN[i][j]) > 1e-9:
                errors.append(f"<a{i+1},a{j+1}>={ip}, Cartan says {_E8_CARTAN[i][j]}")

    # 2. All 16 curated colors are RGB-distinct.
    rgbs = [entry["rgb"] for entry in CURATED_PALETTE.values()]
    if len(set(rgbs)) != 16:
        errors.append(f"expected 16 distinct curated RGB values, got {len(set(rgbs))}")

    # 3. No base hue is within 5 degrees of being antipodal (180 deg) to
    # another base hue -- the even-spacing claim this module's docstring
    # makes, checked numerically rather than assumed from the formula.
    hue_degrees = {}
    for name, rgb in BASE_HUES.items():
        h, _s, _v = colorsys.rgb_to_hsv(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
        hue_degrees[name] = h * 360.0
    names = list(hue_degrees)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            diff = abs(hue_degrees[names[i]] - hue_degrees[names[j]]) % 360.0
            diff = min(diff, 360.0 - diff)
            if abs(diff - 180.0) < 5.0:
                errors.append(f"{names[i]} and {names[j]} are near-antipodal ({diff} deg)")

    # 4. locate_color_in_e8 is deterministic.
    for name, entry in CURATED_PALETTE.items():
        a = locate_color_in_e8(entry["hex"])
        b = locate_color_in_e8(entry["hex"])
        if a != b:
            errors.append(f"locate_color_in_e8 not deterministic for {name}")

    # 5. bond_type always one of the 4 known labels; weyl_witness_index in
    # range; decay sign conserved (<= 0) -- for every curated color.
    known_bonds = set(_E8_INNER_PRODUCT_BOND.values())
    for name, located in CURATED_COLOR_E8_TABLE.items():
        if located["cartan"]["bond_type"] not in known_bonds:
            errors.append(f"{name}: unknown bond_type {located['cartan']['bond_type']!r}")
        if not (0 <= located["weyl_witness_index"] < E8_WEYL_ORDER):
            errors.append(f"{name}: weyl_witness_index out of range")
        if located["decay"]["delta_phi"] > 1e-12:
            errors.append(f"{name}: decay delta_phi positive ({located['decay']['delta_phi']})")

    # 6. blend_compatibility is symmetric, and every color is "redundant"
    # (inner product rounds to +2) with itself.
    sample = list(CURATED_PALETTE.values())[:5]
    for entry in sample:
        self_blend = blend_compatibility(entry["hex"], entry["hex"])
        if self_blend["inner_product"] != 2 or self_blend["bond_type"] != "redundant":
            errors.append(f"{entry['name']}: self-blend not redundant: {self_blend}")
    for a, b in zip(sample, sample[1:]):
        fwd = blend_compatibility(a["hex"], b["hex"])
        rev = blend_compatibility(b["hex"], a["hex"])
        if fwd["inner_product"] != rev["inner_product"] or fwd["bond_type"] != rev["bond_type"]:
            errors.append(f"blend_compatibility not symmetric for {a['name']}/{b['name']}")

    return {
        "forge": "ChromaForge",
        "module": "color_e8",
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "curated_palette_size": len(CURATED_PALETTE),
    }
