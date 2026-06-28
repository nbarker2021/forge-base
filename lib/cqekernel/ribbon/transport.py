"""
Ribbon transport: serialize/deserialize a ribbon with deterministic
encoding so that two kernels observing the same input produce ribbons
with the same ``ribbon_hash``.
"""

from __future__ import annotations

import hashlib
import json

from .ribbon import Ribbon, SLOT_NAMES


def to_canonical_json(ribbon: Ribbon) -> str:
    """Return the deterministic JSON encoding of a ribbon."""
    return json.dumps(ribbon.to_dict(), sort_keys=True, separators=(",", ":"))


def verify_ribbon_hash(ribbon: Ribbon) -> bool:
    """Confirm a ribbon's stored ``ribbon_hash`` matches its slot identity.

    The hash covers the slot *identities* (name, hash, source_kind,
    provenance, status) and the source_hash — not the slot *value*,
    the ribbon_id, or the created_by_request field. Those are
    labels, not identity. The ribbon hash is a deterministic function
    of the request.
    """
    slots_for_hash = {
        k: {
            "name": ribbon.slots[k].name,
            "hash": ribbon.slots[k].hash,
            "source_kind": ribbon.slots[k].source_kind,
            "provenance": ribbon.slots[k].provenance,
            "status": ribbon.slots[k].status,
        }
        for k in SLOT_NAMES if k in ribbon.slots
    }
    body = json.dumps(
        {
            "slots": slots_for_hash,
            "source_hash": ribbon.source_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest() == ribbon.ribbon_hash
