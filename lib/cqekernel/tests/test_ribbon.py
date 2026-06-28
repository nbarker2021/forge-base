"""Unit tests for the 8-slot ribbon layer."""

import unittest
from cqekernel.ribbon.slot import (
    SLOT_NAMES,
    arity_report,
    make_ribbon,
    make_slot,
)
from cqekernel.ribbon.hydrate import hydrate
from cqekernel.ribbon.transport import verify_ribbon_hash
from cqekernel.carrier.binary_boundary import make_frame
from cqekernel.carrier.fourbit import from_bytes
from cqekernel.carrier.lcr import gluon_from_lcr
from cqekernel import ObservedRequest, RequestMode


class TestRibbon(unittest.TestCase):
    def test_empty_ribbon(self):
        rb = make_ribbon(source_hash="s", created_by_request="r")
        self.assertEqual(rb.arity, 0)
        rep = arity_report(rb)
        self.assertEqual(rep.filled, [])
        self.assertEqual(set(rep.missing), set(SLOT_NAMES))
        self.assertFalse(rep.is_complete)

    def test_full_ribbon(self):
        slots = {k: make_slot(k, {"v": 1}) for k in SLOT_NAMES}
        rb = make_ribbon(source_hash="s", created_by_request="r", slots=slots)
        self.assertEqual(rb.arity, 8)
        rep = arity_report(rb)
        self.assertTrue(rep.is_complete)
        self.assertEqual(set(rep.proof_bearing), {"C", "L", "R", "B", "A"})
        self.assertEqual(rep.obligated, [])

    def test_partial_ribbon_obligations(self):
        slots = {"C": make_slot("C", 1), "A": make_slot("A", "x")}
        rb = make_ribbon(source_hash="s", created_by_request="r", slots=slots)
        rep = arity_report(rb)
        # C and A are obligated slots when missing
        self.assertIn("L", rep.obligated)
        self.assertIn("R", rep.obligated)
        self.assertIn("B", rep.obligated)
        self.assertFalse(rep.is_complete)

    def test_hydrate_produces_full_8(self):
        req = ObservedRequest(raw_text="hi", mode=RequestMode.AUDIT)
        frame = make_frame(payload=b"hi", source_type="text", adapter="TextAdapter")
        carrier = from_bytes(frame.sha256, b"hi")
        gluons = [gluon_from_lcr(i, (1, 0, 1) if i % 2 == 0 else (0, 1, 0)) for i in range(8)]
        ribbon = hydrate(req, frame, carrier, gluons)
        self.assertEqual(ribbon.arity, 8)
        self.assertEqual(set(ribbon.slots.keys()), set(SLOT_NAMES))
        self.assertTrue(verify_ribbon_hash(ribbon))

    def test_ribbon_hash_changes_with_provenance(self):
        # The ribbon hash depends on slot *identity* (name, hash,
        # source_kind, provenance, status) and source_hash — NOT on
        # slot value. Changing a slot's value should NOT change the
        # ribbon hash. Changing its provenance SHOULD.
        slots = {k: make_slot(k, {"v": 1}) for k in SLOT_NAMES}
        rb1 = make_ribbon(source_hash="s", created_by_request="r", slots=slots)
        slots2 = {k: make_slot(k, {"v": 1}) for k in SLOT_NAMES}
        slots2["C"] = make_slot("C", {"v": 2})  # value change: must NOT change hash
        rb2 = make_ribbon(source_hash="s", created_by_request="r", slots=slots2)
        self.assertEqual(rb1.ribbon_hash, rb2.ribbon_hash)
        # Change provenance: SHOULD change hash
        slots3 = {k: make_slot(k, {"v": 1}, provenance="X") for k in SLOT_NAMES}
        rb3 = make_ribbon(source_hash="s", created_by_request="r", slots=slots3)
        self.assertNotEqual(rb1.ribbon_hash, rb3.ribbon_hash)


if __name__ == "__main__":
    unittest.main()
