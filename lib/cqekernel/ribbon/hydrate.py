"""
Hydrate a ribbon from a request + carrier + gluons.

The hydration step turns a request observation and its derived
carrier / gluon stream into a first-class 8-slot ribbon. Slot
provenance is set from the input source; missing slots are recorded
as obligations on the resulting ribbon.
"""

from __future__ import annotations

from typing import Iterable, List

from ..carrier.binary_boundary import BinaryBoundaryFrame
from ..carrier.fourbit import FourBitCarrier
from ..carrier.lcr import LocalGluon
from ..core.request import ObservedRequest
from .slot import make_ribbon, make_slot


def hydrate(
    request: ObservedRequest,
    frame: BinaryBoundaryFrame,
    carrier: FourBitCarrier,
    gluons: Iterable[LocalGluon],
) -> "Ribbon":  # noqa: F821
    """Build a ribbon from a request, frame, carrier, and gluon stream."""
    gluon_list = list(gluons)
    shells = [g.shell for g in gluon_list]
    chiral = [g for g in gluon_list if g.left != g.right]
    boundary = [g for g in gluon_list if g.state_class == "boundary"]
    # Left-dominant: chiral pairs where the L bit is 1 (or boundary
    # sites where the L bit is 1). Right-dominant: the mirror.
    left_dominant = [g for g in chiral if g.left == 1]
    right_dominant = [g for g in chiral if g.right == 1]
    left_boundary = [g for g in boundary if g.left == 1]
    right_boundary = [g for g in boundary if g.right == 1]
    # shell-1 gluons are the chiral-pair chiral-pairs: each chiral
    # pair has L and R, so count them on each side.
    left_shell1 = [g for g in gluon_list if g.shell == 1 and g.left == 1]
    right_shell1 = [g for g in gluon_list if g.shell == 1 and g.right == 1]
    # Cumulative boundary side sums (L=R=fixed_center is shell 0 or 3,
    # excluded from chiral; boundary class is shell 2 with L=C=0,R=1
    # or L=C=1,R=0).
    left_sum = sum(g.left for g in gluon_list)
    right_sum = sum(g.right for g in gluon_list)

    # C — center (carrier canonical hash, the head 4-bit)
    c_slot = make_slot(
        "C",
        {
            "carrier_hash": carrier.canonical_hash,
            "head_4bit": carrier.head_4bit,
            "tail_4bit": carrier.tail_4bit,
            "nibble_count": carrier.nibble_count,
        },
        source_kind="carrier",
        provenance=f"frame:{frame.frame_id}",
    )
    # L — left boundary (counts of L-dominant gluons + cumulative L sum)
    l_slot = make_slot(
        "L",
        {
            "chiral_count": len(left_dominant),
            "boundary_count": len(left_boundary),
            "shell1_count": len(left_shell1),
            "left_sum": left_sum,
        },
        source_kind="gluon_stream",
        provenance=f"frame:{frame.frame_id}",
    )
    # R — right boundary (mirror of L)
    r_slot = make_slot(
        "R",
        {
            "chiral_count": len(right_dominant),
            "boundary_count": len(right_boundary),
            "shell1_count": len(right_shell1),
            "right_sum": right_sum,
        },
        source_kind="gluon_stream",
        provenance=f"frame:{frame.frame_id}",
    )
    # B — boundary rule (the correction identity, expressed)
    b_slot = make_slot(
        "B",
        "correction = C AND NOT R",
        source_kind="kernel_primitive",
        provenance="correction.correction_table",
    )
    # T — tool transform (the adapter that produced the frame)
    t_slot = make_slot(
        "T",
        {
            "adapter": frame.adapter,
            "adapter_version": frame.adapter_version,
            "source_type": frame.source_type,
        },
        source_kind="adapter",
        provenance=f"frame:{frame.frame_id}",
    )
    # O — obligation set (filled with arity report info)
    o_slot = make_slot(
        "O",
        {
            "shell_distribution": {
                "0": shells.count(0),
                "1": shells.count(1),
                "2": shells.count(2),
                "3": shells.count(3),
            },
            "obligations": [],  # filled by arity report
        },
        source_kind="arity",
        provenance="ribbon.arity_report",
    )
    # W — workbook analogue (the analog action set)
    w_slot = make_slot(
        "W",
        {
            "analog_actions": [
                "draw_2x2_grid",
                "place_tokens",
                "mark_color",
                "fold_tape",
                "record_notebook",
            ],
            "digital_twin": "ribbon.slots",
        },
        source_kind="workbook",
        provenance="workbook.analog_schema",
    )
    # A — anchor (request hash, frame hash, carrier hash)
    a_slot = make_slot(
        "A",
        {
            "request_id": request.request_id,
            "request_hash": request.raw_hash,
            "frame_id": frame.frame_id,
            "frame_hash": frame.sha256,
            "carrier_id": carrier.carrier_id,
            "carrier_hash": carrier.canonical_hash,
        },
        source_kind="provenance",
        provenance="kernel.observe",
    )

    return make_ribbon(
        source_hash=carrier.canonical_hash,
        created_by_request=request.request_id,
        slots={
            "C": c_slot, "L": l_slot, "R": r_slot, "B": b_slot,
            "T": t_slot, "O": o_slot, "W": w_slot, "A": a_slot,
        },
    )
