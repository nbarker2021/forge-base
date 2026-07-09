"""
The ``Kernel`` class.

This is the central object that wires the kernel primitives into a
single API. It owns the ledger, the snapshot store, the receipt
store, the firmware registry, and the active policy.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from .request import ObservedRequest, RequestMode
from .status import (
    EvidenceStatus,
    ReceiptStatus,
    KernelPolicyError,
)
from .policy import Policy

from ..adapters import adapter_for
from ..carrier.binary_boundary import (
    BinaryBoundaryFrame,
    make_frame,
    verify_frame,
)
from ..carrier.correction import correction_table
from ..carrier.cform import CForm, cform_from_gluon
from ..carrier.fourbit import FourBitCarrier, from_bytes
from ..lcr import (
    LCRChannel,
    LCRGluon,
    LCRWindow,
    LocalGluon,
    WindowSize,
    admit,
    envelope_into_windows,
    gluon_stream_from_bits,
    resolve_channel,
)
from ..firmware.abi import DefaultFirmwareABI, FirmwareABI
from ..firmware.registry import FirmwareRegistry
from ..ledger.event import EVENT_TYPES, Event
from ..ledger.receipt import Receipt
from ..ledger.replay import ReplayResult, replay
from ..ledger.snapshot import (
    list_snapshots,
    make_snapshot,
    read_snapshot,
    write_snapshot,
)
from ..ledger.store import EventStore
from ..lcr import (
    LCRChannel,
    LCRGluon,
    LCRWindow,
    WindowSize,
    envelope_into_windows,
    gluon_stream_from_bits,
    resolve_channel,
)
from ..projection.boundary_aperture import detect_from_gluons
from ..projection.closure import close_cone
from ..projection.eversion import evert
from ..projection.light_cone import open_cone
from ..projection.observer_frame import check_governance, four_frames
from ..ribbon.hydrate import hydrate
from ..ribbon.slot import arity_report
from ..ribbon.transport import verify_ribbon_hash
from ..storage import paths
from ..storage.json_store import ReceiptStore
from ..verification.socratic import wrap
from ..workbook.workbook_engine import check_protocol, default_workbook


class Kernel:
    """The CQE/CMPLX kernel.

    The kernel enforces the carrier, request, receipt, boundary,
    replay, and status rules. It is a stdlib-only, source-bound
    C-form runtime.

    The observation pipeline follows the canonical wrapping order:

      1. Request (observation) → hashed immediately
      2. Binary boundary frame → stable substrate
      3. 4-bit carrier → canonical nibble encoding
      4. LCR Gluon stream (capital G = observer-specific C terms)
         derived from boundary frame's bit stream
      5. LCR envelope: 2x2 / 4x4 / 8x8 windows (non-overlapping)
      6. Channel resolution → few-bit answer from closed windows
      7. Asymmetric admissibility gate on each gluon
      8. C-form from each gluon
      9. Correction surface (local C ∧ ¬R table)
      10. Hydrated ribbon (8 slots, arity report)
      11. Optional firmware bridge (lattice_forge)
      12. Observer frames + boundary apertures
      13. Closure + eversion (obligations)
      14. Snapshot (replayable)
      15. Socratic wrapper

    The kernel's own writes to ``.cqe/workspace`` are always allowed.
    """

    def __init__(
        self,
        *,
        policy: Optional[Policy] = None,
        anchor: Optional[str] = None,
        firmware: Optional[FirmwareABI] = None,
        split_bias: int = 1,
    ):
        self.policy = policy or Policy.strict()
        self.anchor = anchor or paths.anchor()
        self.workspace = paths.workspace(self.anchor)
        self.receipts_path = self.workspace / "receipts.jsonl"
        self.events = EventStore(self.workspace / "events.jsonl")
        self.receipts = ReceiptStore(self.receipts_path)
        self.snapshots_dir = paths.ensure_snapshots(self.workspace)
        self.obligations_path = self.workspace / "obligations" / "obligations.jsonl"
        # Create registry first, then default ABI with registry
        self.firmware_registry = FirmwareRegistry()
        self.firmware = firmware or DefaultFirmwareABI(self.firmware_registry)
        self.split_bias = split_bias
        if self.split_bias not in (1, 2, 4, 8):
            raise ValueError("split_bias must be one of {1,2,4,8}")

        self.obligations_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        event_type: str,
        payload: Dict[str, Any],
        input_hash: str,
        output_hash: str,
        *,
        request_id: Optional[str] = None,
        evidence_class: EvidenceStatus = EvidenceStatus.KERNEL_PRIMITIVE,
    ) -> Receipt:
        """Emit an event and a corresponding receipt."""
        if event_type not in EVENT_TYPES:
            raise KernelPolicyError(f"unknown event type: {event_type}")

        ev = Event(
            event_type=event_type,
            payload=payload,
            request_id=request_id,
            input_hash=input_hash,
            output_hash=output_hash,
        )
        self.events.append(ev)

        r = Receipt.new(
            event_type=event_type,
            input_hash=input_hash,
            output_hash=output_hash,
            status=ReceiptStatus.PASS,
            evidence_class=evidence_class,
            payload=payload,
            request_id=request_id,
        )
        self.receipts.append(r)
        return r

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def observe(
        self,
        payload: Union[str, bytes, Dict[str, Any], List[Dict[str, Any]]],
        *,
        mode: Union[RequestMode, str] = RequestMode.READ_ONLY,
        source_type: str = "auto",
        observer_id: Optional[str] = None,
        extra_policy: Optional[Dict[str, Any]] = None,
    ) -> ObservationResult:
        """Observe a payload. The pipeline follows the canonical
        wrapping order:

          1. Request (observation) → hashed immediately
          2. Binary boundary frame → stable substrate
          3. 4-bit carrier → canonical nibble encoding
          4. LCR Gluon stream (capital G = observer-specific C terms)
             derived from boundary frame's bit stream
          5. LCR envelope: 2x2 / 4x4 / 8x8 windows (non-overlapping)
          6. Channel resolution → few-bit answer from closed windows
          7. Asymmetric admissibility gate on each gluon
          8. C-form from each gluon
          9. Correction surface (local C ∧ ¬R table)
          10. Hydrated ribbon (8 slots, arity report)
          11. Optional firmware bridge (lattice_forge)
          12. Observer frames + boundary apertures
          13. Closure + eversion (obligations)
          14. Snapshot (replayable)
          15. Socratic wrapper

        The kernel's own writes to ``.cqe/workspace`` are always allowed.
        The strict ``Policy`` is enforced against *external* operations.
        """
        # 1. request — the observation IS the request, hashed immediately
        # Keep raw_bytes for lossless roundtrip of bytes payloads
        if isinstance(payload, bytes):
            raw_bytes = payload
            raw = payload.decode("utf-8", errors="replace")
        elif isinstance(payload, (dict, list)):
            raw_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
            raw = raw_bytes.decode("utf-8")
        else:
            raw = str(payload)
            raw_bytes = raw.encode("utf-8")

        policy_dict = dict(self.policy.to_dict())
        if extra_policy:
            policy_dict.update(extra_policy)

        req = ObservedRequest(
            raw_text=raw,
            source_type=source_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            observer_id=observer_id,
            mode=mode.value if isinstance(mode, RequestMode) else mode,
            policy=policy_dict,
            raw_hash=hashlib.sha256(raw_bytes).hexdigest(),
            raw_bytes=raw_bytes,  # preserve original bytes for lossless roundtrip
        )

        self._emit(
            "REQUEST_OBSERVED",
            {"request_id": req.request_id, "raw_hash": req.raw_hash,
             "mode": req.mode.value, "source_type": req.source_type},
            input_hash=req.raw_hash, output_hash=req.raw_hash,
            request_id=req.request_id,
        )

        # 2. binary boundary frame — the initial envelope
        frame = make_frame(
            payload=req.raw_bytes,
            source_type=req.source_type,
            adapter="auto",
        )
        assert verify_frame(frame), "frame self-verify failed"
        self._emit(
            "BOUNDARY_FRAME_CREATED",
            {"frame_id": frame.frame_id, "sha256": frame.sha256,
             "byte_count": frame.byte_count, "adapter": frame.adapter},
            input_hash=req.raw_hash, output_hash=frame.sha256,
            request_id=req.request_id,
        )

        # 3. 4-bit carrier — canonical nibble encoding of boundary frame
        carrier = from_bytes(frame.sha256, req.raw_bytes)
        self._emit(
            "FOURBIT_ENCODED",
            {"carrier_id": carrier.carrier_id, "head_4bit": carrier.head_4bit,
             "tail_4bit": carrier.tail_4bit, "canonical_hash": carrier.canonical_hash,
             "nibble_count": carrier.nibble_count},
            input_hash=frame.sha256, output_hash=carrier.canonical_hash,
            request_id=req.request_id,
        )

        # 4. LCR Gluon stream (capital G = observer-specific C terms porting upwards)
        # Derived from the boundary frame's bit stream (sliding 3-bit windows)
        # This is the per-3-bit dimensional transport receipt.
        # frame.sha256 is hex; convert to bits
        sha256_bytes = bytes.fromhex(frame.sha256)
        bit_stream = tuple(
            (b >> i) & 1 for b in sha256_bytes for i in range(7, -1, -1)
        )[: len(req.raw_bytes) * 8] or tuple(
            int(bit) for n in carrier.nibbles for bit in n
        )
        gluons: List[LCRGluon] = gluon_stream_from_bits(bit_stream)

        # Emit the LCR Gluon stream receipt
        self._emit(
            "LCR_GLUON_STREAM",
            {
                "gluon_count": len(gluons),
                "first_gluon": gluons[0].to_dict() if gluons else None,
                "last_gluon": gluons[-1].to_dict() if gluons else None,
            },
            input_hash=frame.sha256, output_hash=frame.sha256,
            request_id=req.request_id,
        )

        # 5. LCR envelope: 2x2 / 4x4 / 8x8 windows (non-overlapping)
        # The bit stream is partitioned into non-overlapping windows.
        lcr_windows: List[LCRWindow] = []
        for size in (WindowSize.W_2x2, WindowSize.W_4x4, WindowSize.W_8x8):
            lcr_windows.extend(envelope_into_windows(bit_stream, size))

        # 6. Channel resolution → few-bit answer from closed windows
        lcr_channel = resolve_channel(lcr_windows)

        # Emit LCR envelope receipt
        self._emit(
            "LCR_ENVELOPE",
            {
                "window_counts": {
                    "2x2": sum(1 for w in lcr_windows if w.size == WindowSize.W_2x2),
                    "4x4": sum(1 for w in lcr_windows if w.size == WindowSize.W_4x4),
                    "8x8": sum(1 for w in lcr_windows if w.size == WindowSize.W_8x8),
                },
                "closed_count": sum(1 for w in lcr_windows if w.closed),
                "channel": lcr_channel.to_dict() if lcr_channel else None,
            },
            input_hash=frame.sha256, output_hash=frame.sha256,
            request_id=req.request_id,
        )

        # 8. C-form from each gluon
        # We map LCRGluon → LocalGluon for C-form generation
        local_gluons = [LocalGluon(
            index=g.index,
            left=g.left,
            center=g.center,
            right=g.right,
            shell=g.shell,
            gluon=g.center,  # the C term
            rule90=g.left ^ g.right,
            rule30=g.center ^ (g.left ^ g.right) ^ (g.left & g.right),
            correction=g.correction,
            state_class=g.state_class,
        ) for g in gluons]

        # 7. Asymmetric admissibility gate on each gluon (using LocalGluon)
        admission_results = [admit(g) for g in local_gluons]
        admitted = sum(1 for ar in admission_results if ar.admitted)
        class_counts: Dict[str, int] = {}
        for ar in admission_results:
            class_counts[ar.admission_class.value] = (
                class_counts.get(ar.admission_class.value, 0) + 1
            )
        self._emit(
            "ADMISSION_SPLIT",
            {"gluon_count": len(local_gluons),
             "admitted_count": admitted,
             "class_counts": class_counts,
             "head_gluon": local_gluons[0].index if local_gluons else None,
             "tail_gluon": local_gluons[-1].index if local_gluons else None},
            input_hash=frame.sha256, output_hash=frame.sha256,
            request_id=req.request_id,
        )

        cforms = [cform_from_gluon(g, carrier.canonical_hash) for g in local_gluons]
        self._emit(
            "C_FORM_CREATED",
            {"cform_count": len(cforms),
             "first_cform": cforms[0].to_dict() if cforms else None,
             "last_cform": cforms[-1].to_dict() if cforms else None},
            input_hash=frame.sha256,
            output_hash=cforms[0].canonical_hash if cforms else carrier.canonical_hash,
            request_id=req.request_id,
        )

        # 9. Correction surface (local C ∧ ¬R table)
        ct = correction_table()
        self._emit(
            "CORRECTION_COMPUTED",
            {"correction_table_size": len(ct),
             "first_correction": ct[0].to_dict() if ct else None},
            input_hash=cforms[0].canonical_hash if cforms else carrier.canonical_hash,
            output_hash=frame.sha256,
            request_id=req.request_id,
        )

        # 10. Hydrated ribbon (8 slots, arity report)
        ribbon = hydrate(req, frame, carrier, local_gluons)
        rep = arity_report(ribbon)
        if "O" in ribbon.slots and rep.obligated:
            ribbon.slots["O"].value["obligations"] = list(rep.obligated)
        assert verify_ribbon_hash(ribbon), "ribbon self-verify failed"
        self._emit(
            "RIBBON_CREATED",
            {"ribbon_id": ribbon.ribbon_id, "ribbon_hash": ribbon.ribbon_hash,
             "arity": ribbon.arity, "is_complete": rep.is_complete},
            input_hash=frame.sha256, output_hash=ribbon.ribbon_hash,
            request_id=req.request_id,
        )

        # 11. Optional firmware bridge (lattice_forge)
        # The bridge NEVER raises; a missing lattice_forge produces
        # a stdlib fallback payload stamped with EXTERNAL_REQUIRED.
        try:
            from ..firmware import lattice_forge_bridge
            mr_result = lattice_forge_bridge.manage_ribbon(req.raw_bytes)
            lc_result = lattice_forge_bridge.light_cone(
                req.raw_bytes, split_bias=self.split_bias, tick=0
            )
        except Exception as e:
            mr_result = None
            lc_result = None
            firmware_bridge_error = repr(e)
        else:
            firmware_bridge_error = None
        firmware_status = "OK" if (
            mr_result and mr_result.status == "OK"
            and lc_result and lc_result.status == "OK"
        ) else "EXTERNAL_REQUIRED"
        if firmware_status == "OK":
            evidence_class = EvidenceStatus.FIRMWARE_BACKED
            firmware_payload = {
                "managed_ribbon": mr_result.payload,
                "light_cone": lc_result.payload,
            }
        else:
            evidence_class = EvidenceStatus.KERNEL_PRIMITIVE
            firmware_payload = {
                "status": "EXTERNAL_REQUIRED",
                "split_bias": self.split_bias,
                "bridge_error": firmware_bridge_error,
                "managed_ribbon_status": mr_result.status if mr_result else None,
                "light_cone_status": lc_result.status if lc_result else None,
            }
        self._emit(
            "FIRMWARE_CALLED",
            {
                "bridge": "lattice_forge",
                "firmware_status": firmware_status,
                "split_bias": self.split_bias,
                **firmware_payload,
            },
            input_hash=ribbon.ribbon_hash,
            output_hash=(mr_result.payload.get("output_hash") if mr_result
                         and mr_result.status == "OK" else ribbon.ribbon_hash),
            request_id=req.request_id,
            evidence_class=evidence_class,
        )

        # 12. Observer frames + boundary apertures
        frames = four_frames(carrier.canonical_hash, selected_index=0,
                             obligation_id_prefix=f"obl:{req.request_id[:8]}")
        # Use the gluons for aperture detection (they carry L/C/R/correction)
        local_gluons_for_aperture = [LocalGluon(
            index=g.index,
            left=g.left,
            center=g.center,
            right=g.right,
            shell=g.shell,
            gluon=g.center,
            rule90=g.left ^ g.right,
            rule30=g.center ^ (g.left ^ g.right) ^ (g.left & g.right),
            correction=g.correction,
            state_class=g.state_class,
        ) for g in gluons]
        apertures = detect_from_gluons(local_gluons_for_aperture, tail_4bit=carrier.tail_4bit)
        cone = open_cone(
            source_c=carrier.canonical_hash,
            frames=frames,
            projection_depth=0,
            apertures=[a.aperture_id for a in apertures],
        )
        self._emit(
            "FRAME_PROJECTED",
            {"frame_count": len(frames),
             "governance_ok": check_governance(frames),
             "selected": [f.frame_name for f in frames if f.selected],
             "latent": [f.frame_name for f in frames if f.latent]},
            input_hash=ribbon.ribbon_hash, output_hash=carrier.canonical_hash,
            request_id=req.request_id,
        )
        self._emit(
            "BOUNDARY_APERTURE_DETECTED",
            {"aperture_count": len(apertures),
             "kinds": sorted({a.kind for a in apertures})},
            input_hash=carrier.canonical_hash, output_hash=carrier.canonical_hash,
            request_id=req.request_id,
        )
        cl = close_cone(cone)
        ev = evert(cone)
        self._emit(
            "OBLIGATION_CREATED",
            {"closed": cl.closed, "notes": cl.notes,
             "eversion_count": len(ev.obligations),
             "obligations": ev.obligations},
            input_hash=carrier.canonical_hash, output_hash=carrier.canonical_hash,
            request_id=req.request_id,
        )
        # Persist the obligations ledger file (the kernel's own state).
        with self.obligations_path.open("a", encoding="utf-8") as f:
            for ob in ev.obligations:
                f.write(json.dumps({
                    "obligation_id": ob,
                    "source_request_id": req.request_id,
                    "source_carrier_hash": carrier.canonical_hash,
                    "status": "OPEN",
                }, sort_keys=True, separators=(",", ":")) + "\n")

        # 14. Snapshot (replayable)
        snap = make_snapshot(
            request_id=req.request_id,
            source_hash=req.raw_hash,
            carrier_hash=carrier.canonical_hash,
            ribbon_hash=ribbon.ribbon_hash,
            ledger_hash=self.events.hash_chain(),
        )
        write_snapshot(self.snapshots_dir, snap)
        self._emit(
            "SNAPSHOT_CREATED",
            {"snapshot_id": snap.snapshot_id,
             "parent": snap.parent_snapshot},
            input_hash=ribbon.ribbon_hash, output_hash=snap.snapshot_id,
            request_id=req.request_id,
        )

        # 15. Socratic wrapper
        socratic = [q.to_dict() for q in wrap(ribbon.ribbon_id)]

        return ObservationResult(
            request=req,
            frame=frame,
            carrier=carrier,
            gluons=gluons,
            cforms=cforms,
            ribbon_hash=ribbon.ribbon_hash,
            arity=ribbon.arity,
            snapshot_id=snap.snapshot_id,
            socratic=socratic,
            lcr_windows=lcr_windows,
            lcr_channel=lcr_channel,
            extras={
                "admission_class_counts": class_counts,
                "admitted_count": admitted,
                "aperture_count": len(apertures),
                "closure_closed": cl.closed,
                "frame_governance_ok": check_governance(frames),
            },
        )

    # ------------------------------------------------------------------
    # Verification / Replay / Introspection
    # ------------------------------------------------------------------

    def verify_kernel(self) -> Dict[str, Any]:
        """Run the falsifier suite and return the report."""
        from ..verification.verifier import verify
        v = verify()
        # Augment with the stdlib algebra checks
        from ..algebra import (
            verify_j3o_axioms,
            verify_n3_su3_closure,
            verify_octonion_axioms,
        )
        algebra_reports = {
            "octonion": verify_octonion_axioms(),
            "j3o": verify_j3o_axioms(),
            "su3_closure": verify_n3_su3_closure(),
        }
        # Augment with the lattice_forge diff if available
        try:
            from ..firmware import algebra_bridge
            diff = algebra_bridge.diff_all()
        except Exception as e:
            diff = {"available": False, "error": repr(e)}
        v_dict = v.to_dict()
        v_dict["algebra_stdlib"] = algebra_reports
        v_dict["algebra_diff"] = diff
        return v_dict

    def workbook_check(self) -> Dict[str, Any]:
        """Check the default workbook protocol."""
        return check_protocol(default_workbook())

    def firmware_manifest(self) -> Dict[str, Any]:
        """Return a manifest of all known firmware packs."""
        base_list = self.firmware_registry.manifest()
        base = {item.get("pack_id", f"pack_{i}"): item for i, item in enumerate(base_list)}
        try:
            from ..firmware import lattice_forge_bridge
            lf = lattice_forge_bridge.manifest()
            base["lattice_forge_bridge"] = lf
        except Exception as e:
            base["lattice_forge_bridge"] = {"error": repr(e)}
        return base

    def replay(self, snapshot_id: str) -> ReplayResult:
        """Replay a snapshot by re-observing its source_hash as a probe."""
        res = replay(self.snapshots_dir, snapshot_id, rebuild=None, ledger=self.events)
        self._emit(
            "REPLAY_VERIFIED",
            {"snapshot_id": snapshot_id, "passed": res.passed,
             "expected_hash": res.expected_hash,
             "actual_hash": res.actual_hash},
            input_hash=snapshot_id, output_hash=res.actual_hash,
        )
        return res

    def list_snapshots(self) -> List[str]:
        return list_snapshots(self.snapshots_dir)

    def get_snapshot(self, snapshot_id: str) -> "Snapshot":
        """Load a snapshot by id."""
        from ..ledger.snapshot import read_snapshot
        return read_snapshot(self.snapshots_dir, snapshot_id)

    def receipts_for_request(self, request_id: str) -> List[Receipt]:
        """Return all receipts for a given request."""
        return [r for r in self.receipts.all()
                if r.request_id == request_id]

    def receipts_for_snapshot(self, snapshot_id: str) -> List[Receipt]:
        """Return receipts for a given snapshot."""
        return [r for r in self.receipts.all()
                if r.payload.get("snapshot_id") == snapshot_id]

    def obligations_for_request(self, request_id: str) -> List[Dict[str, Any]]:
        """Read the obligations ledger file for a given request."""
        obligations = []
        if self.obligations_path.exists():
            with self.obligations_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    ob = json.loads(line)
                    if ob.get("source_request_id") == request_id:
                        obligations.append(ob)
        return obligations

    def observe_packet(self, packet: Dict[str, Any]) -> ObservationResult:
        """Observe a JSON host packet."""
        op = packet.get("op", "observe")
        payload = packet.get("payload", "")
        mode = packet.get("mode", "READ_ONLY")
        return self.observe(payload, mode=mode, source_type="host_packet")

    def dispatch(self, firmware_call: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Lane-C dispatch: forward a call to the firmware ABI.

        Convenience pass-through used by the typed-kernel surface
        (see ``cqekernel.lcr.typed_kernel.TypedKernel.dispatch``).
        The first argument may be either a bare method name
        (default target ``lattice_forge``) or a
        ``"target.method"`` string. The call is gated by
        ``allow_firmware``; the C-lane gate
        (``allow_center_dispatch``) is checked by the typed
        wrapper, not here, so this method is safe to call
        directly from non-typed hosts.
        """
        if not self.policy.allow_firmware:
            from .errors import KernelPolicyError
            raise KernelPolicyError(
                "policy forbids firmware (set allow_firmware=True to "
                "enable firmware dispatch)"
            )
        if "." in firmware_call:
            target, method = firmware_call.split(".", 1)
        else:
            target, method = "lattice_forge", firmware_call
        return self.firmware_registry.call(target, method, payload)

    def cqe_info(self) -> Dict[str, Any]:
        """Return detailed CQE primitive info."""
        return {
            "kernel_d4_token_fields": [
                "index", "pode", "antipode", "orbit", "sheet",
                "spin_vignette", "cartan_slot", "time_polarity", "write_record"
            ],
            "lattice_forge_manifest": self.firmware_manifest(),
            "algebra_primitives": {
                "octonion": "Fano-plane 8D normed division algebra",
                "j3o": "27-dim exceptional Jordan algebra J3(O)",
                "f4_su3": "S3 permutations on 3-fundamental, 8x8 Rule 30 closed-form",
            },
            "kernel_version": "0.1.0",
        }


# ----------------------------------------------------------------------
# Observation result
# ----------------------------------------------------------------------

from dataclasses import dataclass

@dataclass
class ObservationResult:
    """The full result of a single observation."""

    request: ObservedRequest
    frame: BinaryBoundaryFrame
    carrier: FourBitCarrier
    gluons: List[LCRGluon]          # capital G = observer-specific C terms
    cforms: List[CForm]
    ribbon_hash: str
    arity: int
    snapshot_id: Optional[str]
    socratic: List[Dict[str, Any]]
    lcr_windows: List[LCRWindow]    # 2x2/4x4/8x8 envelope
    lcr_channel: Optional[LCRChannel]
    extras: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "frame": self.frame.to_dict(),
            "carrier": self.carrier.to_dict(),
            "gluon_count": len(self.gluons),
            "cform_count": len(self.cforms),
            "ribbon_hash": self.ribbon_hash,
            "arity": self.arity,
            "snapshot_id": self.snapshot_id,
            "socratic": list(self.socratic),
            "lcr_windows": [w.to_dict() for w in self.lcr_windows],
            "lcr_channel": self.lcr_channel.to_dict() if self.lcr_channel else None,
            "extras": dict(self.extras),
        }