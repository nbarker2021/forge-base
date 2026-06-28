"""
L/C/R typed kernel: three-lane contract for the cqekernel.

Identity: this module is the typed surface of the **LCRKernel** layer
of the CQE / LCR / CMPLX-1T identity chain. The substrate is
**CQEEngine** (Cartan Quadratic Equivalence); the product line is
**CMPLX-1T** (pronounced "Complexity"). See IDENTITY.md at the repo
root for the full chain with citations.

This module promotes the L, C, R bits of the 3-tuple from algebraic
identity to *operational role*. The algebra is unchanged. What
changes is the type contract: every kernel operation now declares
which lane it lives in, and the policy gates enforce the lane split
explicitly.

Three lanes, three roles, three Protocol classes:

  * L = data in / data out.  ``LAdapter``     (left:  reader/writer)
  * C = control plane.       ``CKernel``      (center: dispatcher)
  * R = outward surface.     ``RChannel``     (right:  projector)

The default ``Policy.strict()`` denies all three lanes. A working
system must explicitly grant at least one lane per operation.

This file is strictly additive. The 8 LCR states, the gate, the
ribbon, the master_ribbon, the firmware ABI, and every forge keep
working unchanged under the new types.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Lane identity
# ---------------------------------------------------------------------------


class Lane(str, Enum):
    """The three operational lanes of the typed kernel.

    Algebraically, L/C/R are the three bits of the LCR triple. In
    the typed contract, L/C/R are the three *lanes* a kernel
    operation can live in.
    """

    L = "L"  # data in / data out (reader / writer / adapter)
    C = "C"  # control plane (kernel, policy, firmware, workbook)
    R = "R"  # outward surface (receipts, snapshots, projections)

    @property
    def role(self) -> str:
        return {
            Lane.L: "adapter",
            Lane.C: "kernel",
            Lane.R: "channel",
        }[self]

    @property
    def policy_action(self) -> str:
        """The Policy.check() action key that gates this lane."""
        return {
            Lane.L: "left_io",
            Lane.C: "center_dispatch",
            Lane.R: "right_emit",
        }[self]

    @property
    def policy_field(self) -> str:
        """The Policy dataclass field that gates this lane."""
        return {
            Lane.L: "allow_left_io",
            Lane.C: "allow_center_dispatch",
            Lane.R: "allow_right_emit",
        }[self]


# ---------------------------------------------------------------------------
# LCR triple lane classifier
# ---------------------------------------------------------------------------


def lane_of_lcr(lcr: "tuple[int, int, int] | list[int]") -> Lane:
    """Map an (L, C, R) triple to its *dominant* lane under the typed
    contract.

    This is a *classifier*, not a gate decision. The asymmetric gate
    (in ``carrier.lcr``) still produces ``AdmissionClass`` values; this
    function answers a different question: which lane owns this
    triple from the perspective of the typed-kernel contract?

    Heuristic (intentionally simple, intentionally auditable):
      * L == R != C   -> boundary pair, dominant lane is the one
                         whose value is the "lone" bit (the head/tail
                         signal). If C is the lone bit, the carrier
                         is C (C owns the head/tail). Otherwise
                         the boundary is L=R and the dominant lane
                         is the boundary itself (Lane.L).
      * L == R == C   -> all three bits agree: pure C (the kernel
                         admitted the value, so the center owns it).
      * L != R        -> chiral pair, the disagreement lives in the
                         L and R bits, so the dominant lane is C
                         (the C bit arbitrates the disagreement).

    The classifier is used for *type-aware error messages* and
    *obligation reporting*, not for any policy decision. Policy
    decisions always come from the asymmetric gate.
    """
    L, C, R = int(lcr[0]), int(lcr[1]), int(lcr[2])
    if L == R and C != L:
        # boundary pair. C is the lone bit. The carrier is C.
        return Lane.C
    if L == R and C == L:
        # uniform: all three agree. C arbitrated admission; C owns.
        return Lane.C
    # L != R: the disagreement is in the L/R bits, C arbitrates.
    return Lane.C


def lane_role_string(lcr: "tuple[int, int, int] | list[int]") -> str:
    """Return a human-readable string for the lane of an LCR triple.

    Used in receipts, error messages, and the typed-kernel spec doc.
    """
    lane = lane_of_lcr(lcr)
    return f"{lane.value} ({lane.role})"


# ---------------------------------------------------------------------------
# Lane permission record (a typed receipt, not a financial one)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LaneGrant:
    """An explicit, audited grant of a lane to a single operation.

    The grant is *content-addressed* by the operation name and lane,
    so a host can persist its grants and re-verify them on every
    kernel boot.
    """

    operation: str
    lane: Lane
    granted: bool
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "lane": self.lane.value,
            "lane_role": self.lane.role,
            "granted": self.granted,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# L-adapter Protocol: data in / data out
# ---------------------------------------------------------------------------


@runtime_checkable
class LAdapter(Protocol):
    """The L-lane: data in / data out.

    An ``LAdapter`` takes a source from outside the kernel and
    produces a canonical ``BinaryBoundaryFrame`` (and vice versa
    for the R side of the contract: it can take a kernel result
    and project it back into the external shape).

    Everything the kernel reads or writes goes through an L adapter.
    No kernel primitive reads or writes the host filesystem, the
    network, a database, or a vector store directly. The L lane is
    the *only* allowed path to the outside.

    Existing adapters that already satisfy this contract:
      * ``bytes_adapter.adapt``  (raw bytes -> frame)
      * ``json_adapter.adapt``   (JSON object -> frame)
      * ``csv_adapter.adapt``    (CSV -> frame)
      * ``text.adapt``           (str -> frame)
      * ``filesystem.adapt``     (path -> manifest frame)
      * ``host_packet.adapt``    (host packet -> frame)

    They are already Protocol-compatible; the type label makes
    that explicit.
    """

    def adapt(self, source: Any) -> Any:  # returns BinaryBoundaryFrame
        ...


# ---------------------------------------------------------------------------
# C-kernel Protocol: control plane
# ---------------------------------------------------------------------------


@runtime_checkable
class CKernel(Protocol):
    """The C-lane: control plane.

    A ``CKernel`` arbitrates *what runs*, in *what order*, under
    *what policy*, and emits a ``Receipt`` for every dispatch.

    Three things are gated by the C lane:
      1. Mode changes (READ_ONLY -> AUDIT, LOOKUP_ONLY -> COMPUTE_IF_NEEDED)
      2. Firmware dispatch (``lattice_forge``, ``oloid_geometry``, etc.)
      3. Workbook step execution (the analog workbook protocol)

    A working C kernel never reads or writes the outside (that is
    the L lane's job) and never produces outward artifacts (that
    is the R lane's job). It *only* dispatches.

    The existing ``Kernel`` class already satisfies this contract.
    The Protocol label makes it explicit. The shape below matches
    the actual ``cqekernel.Kernel`` public API: ``observe``,
    ``observe_packet``, ``firmware_manifest``, ``cqe_info``,
    ``replay``, ``verify_kernel``, ``workbook_check``,
    ``dispatch``, ``get_snapshot``, ``list_snapshots``.
    """

    def observe(self, payload: Any, **kwargs: Any) -> Any: ...

    def observe_packet(self, packet: Dict[str, Any]) -> Any: ...

    def dispatch(self, firmware_call: str, payload: Dict[str, Any]) -> Any: ...

    def firmware_manifest(self) -> Dict[str, Any]: ...

    def cqe_info(self) -> Dict[str, Any]: ...

    def replay(self, snapshot_id: str) -> Any: ...

    def verify_kernel(self) -> Dict[str, Any]: ...

    def workbook_check(self) -> Dict[str, Any]: ...

    def get_snapshot(self, snapshot_id: str) -> Any: ...

    def list_snapshots(self) -> Any: ...


# ---------------------------------------------------------------------------
# R-channel Protocol: outward surface
# ---------------------------------------------------------------------------


@runtime_checkable
class RChannel(Protocol):
    """The R-lane: outward surface.

    An ``RChannel`` is the *only* thing the customer, the
    frontpage, the showcase, the validation report, and the
    whitepaper ever see. It takes kernel results and projects them
    into outward artifacts:

      * ``emit(receipt)``           -> a receipt chain entry
      * ``project(snapshot)``       -> a snapshot, a projection, a
                                        HTML card, a JSON manifest,
                                        a PDF, or a PNG
      * ``publish(whitepaper)``     -> a whitepaper or frontpage link

    A working R channel never reads the outside (that is L) and
    never dispatches (that is C). It only emits and projects.
    """

    def emit(self, receipt: Any) -> None: ...

    def project(self, snapshot: Any) -> Any: ...


# ---------------------------------------------------------------------------
# TypedKernel: a thin policy-enforcing wrapper around the existing Kernel
# ---------------------------------------------------------------------------


@dataclass
class TypedKernel:
    """The typed-kernel surface: a policy-enforcing lane check.

    This is the *entry point* a host uses to declare a typed
    operation. It does *not* replace the existing ``Kernel``
    class. It wraps it with three lane checks, each one gated by
    a single Policy field.

    Usage:

        from cqekernel import Kernel
        from cqekernel.lcr.typed_kernel import TypedKernel, Lane

        k = Kernel()
        tk = TypedKernel(kernel=k, policy=k.policy)

        # default Policy.strict() denies all three lanes
        tk.check_lane("observe_audit", Lane.L)   # raises KernelPolicyError
        tk.check_lane("observe_audit", Lane.C)   # raises KernelPolicyError
        tk.check_lane("observe_audit", Lane.R)   # raises KernelPolicyError

        # grant a single lane, operation is now allowed
        from cqekernel import Policy
        open_policy = Policy.strict().grant(Lane.C, "observe_audit")
        tk2 = TypedKernel(kernel=k, policy=open_policy)
        tk2.check_lane("observe_audit", Lane.C)   # passes
        tk2.check_lane("observe_audit", Lane.R)   # still denied

    The TypedKernel does not call into the kernel. It only
    enforces the lane gate. The actual observation happens in
    the regular Kernel after the gate passes.
    """

    kernel: Any  # the existing Kernel instance (forward-declared as Any to avoid import cycle)
    policy: Any  # the Policy dataclass instance

    def check_lane(self, operation: str, lane: Lane) -> LaneGrant:
        """Check whether ``operation`` is allowed to run on ``lane``.

        Raises ``KernelPolicyError`` if denied. Returns a
        ``LaneGrant`` with ``granted=True`` if allowed.
        """
        if not isinstance(lane, Lane):
            raise TypeError(f"lane must be a Lane enum, got {type(lane).__name__}")
        allowed = bool(getattr(self.policy, lane.policy_field, False))
        if not allowed:
            # Local import to avoid a circular dependency at module load.
            from ..core.errors import KernelPolicyError
            raise KernelPolicyError(
                f"policy forbids lane {lane.value!r} ({lane.role}) for "
                f"operation {operation!r} (set {lane.policy_field}=True "
                f"to grant this lane)"
            )
        return LaneGrant(
            operation=operation,
            lane=lane,
            granted=True,
            reason=f"granted by {lane.policy_field}=True",
        )

    def dispatch(self, firmware_call: str, payload: Dict[str, Any]) -> Any:
        """Lane-C dispatch: forward a call to the kernel's firmware ABI.

        Convenience pass-through that lets a host write
        ``tk.dispatch("lattice_forge", "verify_j3", payload)`` without
        reaching past the typed surface. The actual dispatch is
        delegated to the wrapped kernel's firmware ABI; this method
        is here so the typed surface exposes the same call shape.
        """
        from ..core.errors import KernelPolicyError
        if not self.policy.allow_center_dispatch:
            raise KernelPolicyError(
                "policy forbids center_dispatch (set "
                "allow_center_dispatch=True to grant the C lane)"
            )
        if not bool(getattr(self.policy, "allow_firmware", False)):
            raise KernelPolicyError(
                "policy forbids firmware (set allow_firmware=True to "
                "enable firmware dispatch from the C lane)"
            )
        # The real Kernel exposes firmware_registry + firmware ABI.
        # For ergonomic dispatch, split the first positional arg
        # into (target, method) if it's a "<target>.<method>" string.
        call = firmware_call
        if "." in call:
            target, method = call.split(".", 1)
        else:
            target, method = "lattice_forge", call
        registry = getattr(self.kernel, "firmware_registry", None)
        if registry is None:
            raise KernelPolicyError("kernel has no firmware_registry; cannot dispatch")
        return registry.call(target, method, payload)

    def grants(self) -> List[LaneGrant]:
        """Return the set of currently-granted lanes, in the order L, C, R.

        Useful for boot-time auditing: print the grant table and
        confirm a host is not running with all three lanes open
        (the most dangerous configuration).
        """
        out: List[LaneGrant] = []
        for lane in (Lane.L, Lane.C, Lane.R):
            out.append(
                LaneGrant(
                    operation="*",
                    lane=lane,
                    granted=bool(getattr(self.policy, lane.policy_field, False)),
                    reason=(
                        f"set by {lane.policy_field}"
                        if getattr(self.policy, lane.policy_field, False)
                        else f"denied (default; {lane.policy_field}=False)"
                    ),
                )
            )
        return out


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------


__all__ = [
    "Lane",
    "LaneGrant",
    "LAdapter",
    "CKernel",
    "RChannel",
    "TypedKernel",
    "lane_of_lcr",
    "lane_role_string",
]
