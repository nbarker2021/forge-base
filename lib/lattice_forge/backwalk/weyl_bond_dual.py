from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterator, Literal

from ..chart_codec_d4 import ANTIPODAL_LABEL, CHART_STATES, SHEET_SIGN
from ..ledger.exact import stable_hash
from ..substrate_map import WEYL_13_TABLE, route, shell
from .schema import WorkStore

# Exceptional tower (rank order). E6 is the categorical middle hub.
EXCEPTIONAL_GROUPS: tuple[str, ...] = ("G2", "F4", "E6", "E7", "E8")
MIDDLE_GROUP: str = "E6"
TOP_GROUPS: frozenset[str] = frozenset({"E7", "E8"})
BOTTOM_GROUPS: frozenset[str] = frozenset({"G2", "F4"})
MIDDLE_AXIS: int = 2
MIDDLE_CHART_INDICES: tuple[int, ...] = (2, 5)
QUADRANT_COUNT: int = 4

Direction = Literal["construct_in", "read_out"]
Pole = Literal["podal", "antipodal", "top", "bottom", "middle"]


def chart_axis(chart_idx: int) -> int:
    return ANTIPODAL_LABEL[CHART_STATES[chart_idx]]


# D4 antipodal quadrants: one axis = one search domain (2 chart vertices each).
QUADRANT_CHART_INDICES: dict[int, tuple[int, ...]] = {
    axis: tuple(i for i in range(8) if chart_axis(i) == axis)
    for axis in range(QUADRANT_COUNT)
}


def chart_sheet(chart_idx: int) -> int:
    return SHEET_SIGN[CHART_STATES[chart_idx]]


def dual_depth(chart_idx: int) -> int:
    """Distance from center axis (2) on the 4-axis D4 antipodal ladder."""
    return abs(chart_axis(chart_idx) - MIDDLE_AXIS)


def group_pole(group: str) -> Pole:
    if group == MIDDLE_GROUP:
        return "middle"
    if group in TOP_GROUPS:
        return "top"
    if group in BOTTOM_GROUPS:
        return "bottom"
    return "middle"


def chart_pole(chart_idx: int) -> Pole:
    """Sheet 0 = lower shell (bottom/podal); sheet 1 = upper (top/antipodal)."""
    return "antipodal" if chart_sheet(chart_idx) else "podal"


def nearest_middle_chart(chart_idx: int) -> int:
    """Route chart state toward the center doublet (axis 2)."""
    axis = chart_axis(chart_idx)
    if axis == MIDDLE_AXIS:
        return chart_idx
    # Step sheet toward middle: pick middle index with matching shell preference when possible.
    candidates = list(MIDDLE_CHART_INDICES)
    if len(candidates) == 1:
        return candidates[0]
    return min(candidates, key=lambda t: abs(shell(t) - shell(chart_idx)))


def mirror_chart(chart_idx: int) -> int:
    """Weyl involution partner (linked oloid antipode on 8-state chart)."""
    return WEYL_13_TABLE[chart_idx]


@dataclass(frozen=True)
class WeylBondBatchSpec:
    batch_id: str
    wave_id: str
    direction: Direction
    dual_depth: int
    source_group: str
    target_group: str
    quadrant: int
    lane_octet: bool = False  # if False, only lanes in quadrant (2 chart states)


def iter_batch_specs(
    *,
    include_read_out: bool = True,
    quadrant: int | None = None,
) -> Iterator[WeylBondBatchSpec]:
    """Generate bounded batches; optional single-quadrant search (2 lanes per depth slice)."""
    quadrants = (quadrant,) if quadrant is not None else range(QUADRANT_COUNT)
    for q in quadrants:
        if q < 0 or q >= QUADRANT_COUNT:
            raise ValueError(f"quadrant must be 0..{QUADRANT_COUNT - 1}, got {q}")
        for src in EXCEPTIONAL_GROUPS:
            for tgt in EXCEPTIONAL_GROUPS:
                directions: tuple[Direction, ...] = (
                    ("construct_in", "read_out") if include_read_out else ("construct_in",)
                )
                for direction in directions:
                    for depth in range(3):
                        if not _lanes_for_quadrant_depth(q, depth):
                            continue
                        wave = f"q{q}:{direction}_d{depth}"
                        batch_id = f"{wave}:{src}:{tgt}"
                        yield WeylBondBatchSpec(
                            batch_id=batch_id,
                            wave_id=wave,
                            direction=direction,
                            dual_depth=depth,
                            source_group=src,
                            target_group=tgt,
                            quadrant=q,
                            lane_octet=False,
                        )


def _lanes_for_depth(depth: int) -> list[int]:
    return [i for i in range(8) if dual_depth(i) == depth]


def _compose_path_payload(src_g: str, tgt_g: str) -> dict[str, Any]:
    path: list[str] = []
    if src_g != MIDDLE_GROUP:
        path.append(src_g)
    if MIDDLE_GROUP not in (src_g, tgt_g):
        path.append(MIDDLE_GROUP)
    if tgt_g != MIDDLE_GROUP and tgt_g not in path:
        path.append(tgt_g)
    return {"exceptional_path": path, "middle_group": MIDDLE_GROUP}


def _lanes_for_quadrant_depth(quadrant: int, depth: int) -> list[int]:
    return [i for i in QUADRANT_CHART_INDICES[quadrant] if dual_depth(i) == depth]


def materialize_weyl_bond_batch(
    store: WorkStore,
    spec: WeylBondBatchSpec,
    *,
    max_rows: int,
    mirror_oloid: bool = True,
) -> dict[str, Any]:
    """Write bonded Weyl chamber rows for one batch; returns stats."""
    if spec.lane_octet:
        lanes = [i for i in range(8) if dual_depth(i) == spec.dual_depth]
    else:
        lanes = _lanes_for_quadrant_depth(spec.quadrant, spec.dual_depth)
    rows = 0
    path_meta = _compose_path_payload(spec.source_group, spec.target_group)
    path_meta["quadrant"] = spec.quadrant
    path_meta["quadrant_chart_indices"] = list(QUADRANT_CHART_INDICES[spec.quadrant])

    for chart_src in lanes:
        if rows >= max_rows:
            break

        if spec.direction == "construct_in":
            chart_tgt = nearest_middle_chart(chart_src)
        else:
            # read_out: from middle hub state toward this lane
            chart_tgt = chart_src
            chart_src = nearest_middle_chart(chart_src)

        routing = route(chart_src, chart_tgt)
        bond_id = f"wb:{stable_hash(spec.batch_id, chart_src, chart_tgt, spec.direction)[:32]}"
        payload = {
            **path_meta,
            "wave_id": spec.wave_id,
            "direction": spec.direction,
            "dual_depth": spec.dual_depth,
            "chart_src": chart_src,
            "chart_tgt": chart_tgt,
            "chart_src_label": routing.get("source_label"),
            "chart_tgt_label": routing.get("target_label"),
            "weyl_routing": routing,
            "group_pole_src": group_pole(spec.source_group),
            "group_pole_tgt": group_pole(spec.target_group),
            "chart_pole_src": chart_pole(chart_src),
            "chart_pole_tgt": chart_pole(chart_tgt),
            "mirror_oloid": False,
        }
        store.insert_weyl_bond(
            bond_id=bond_id,
            batch_id=spec.batch_id,
            wave_id=spec.wave_id,
            quadrant=spec.quadrant,
            lane_index=chart_src,
            pole=f"{chart_pole(chart_src)}|{chart_pole(chart_tgt)}",
            source_group=spec.source_group,
            target_group=spec.target_group,
            chart_src=chart_src,
            chart_tgt=chart_tgt,
            middle_chart=nearest_middle_chart(chart_src),
            depth_from_middle=spec.dual_depth,
            bond_kind="weyl_chamber_bond",
            evidence_level="exact",
            payload=payload,
        )
        rows += 1

        if mirror_oloid and rows < max_rows:
            m_src = mirror_chart(chart_src)
            m_tgt = mirror_chart(chart_tgt)
            if m_src != chart_src or m_tgt != chart_tgt:
                m_route = route(m_src, m_tgt)
                m_id = f"wb:{stable_hash(spec.batch_id, m_src, m_tgt, 'mirror')[:32]}"
                store.insert_weyl_bond(
                    bond_id=m_id,
                    batch_id=spec.batch_id,
                    wave_id=spec.wave_id,
                    quadrant=spec.quadrant,
                    lane_index=m_src,
                    pole=f"{chart_pole(m_src)}|{chart_pole(m_tgt)}",
                    source_group=spec.source_group,
                    target_group=spec.target_group,
                    chart_src=m_src,
                    chart_tgt=m_tgt,
                    middle_chart=nearest_middle_chart(m_src),
                    depth_from_middle=spec.dual_depth,
                    bond_kind="weyl_chamber_bond_mirror",
                    evidence_level="exact",
                    payload={**payload, "mirror_oloid": True, "weyl_routing": m_route},
                )
                rows += 1

    store.flush()
    return {"batch_id": spec.batch_id, "rows_written": rows, "lanes": len(lanes)}
