"""
Policy system.

The kernel is policy-governed. Every operation consults the active
policy before performing any side effect. The default policy is strict
and source-bound: nothing is read from or written to the host, and
external compute is forbidden.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict


_DEFAULTS: Dict[str, Any] = {
    "allow_firmware": False,
    "allow_external_io": False,
    "allow_mutation": False,
    "allow_compute": False,
    "allow_conjectural_output": False,
    "require_receipts": True,
    "require_replay": True,
    "allow_host_write": False,
    # L/C/R typed-kernel lane gates (added 2026-06-24).
    # The L lane is data in/out (adapter/reader/writer).
    # The C lane is the control plane (kernel/dispatcher).
    # The R lane is the outward surface (receipts/projections).
    # All three default to False under Policy.strict() so the
    # kernel is type-strict by default.
    "allow_left_io": False,
    "allow_center_dispatch": False,
    "allow_right_emit": False,
}


@dataclass
class Policy:
    """Strict-by-default policy for kernel operations.

    The Policy has two layers of gates:

    1. The *original* eight gates (allow_firmware, allow_external_io,
       allow_mutation, allow_compute, allow_conjectural_output,
       require_receipts, require_replay, allow_host_write) gate
       *what kind of work* the kernel may do.

    2. The *new* three-lane gates (allow_left_io,
       allow_center_dispatch, allow_right_emit) gate *which lane*
       of the typed-kernel contract (L/C/R) is permitted for a
       given operation. They are enforced by ``TypedKernel.check_lane``.

    A working system must grant at least one lane per operation
    it wants to run. ``Policy.strict()`` denies all eight original
    gates and all three new lane gates.
    """

    allow_firmware: bool = False
    allow_external_io: bool = False
    allow_mutation: bool = False
    allow_compute: bool = False
    allow_conjectural_output: bool = False
    require_receipts: bool = True
    require_replay: bool = True
    allow_host_write: bool = False
    # L/C/R typed-kernel lane gates.
    allow_left_io: bool = False
    allow_center_dispatch: bool = False
    allow_right_emit: bool = False
    extras: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def strict(cls) -> "Policy":
        """Return the canonical strict default policy."""
        return cls(**_DEFAULTS)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Policy":
        """Build a policy from a dict; unknown keys go to ``extras``."""
        kwargs: Dict[str, Any] = {}
        extras: Dict[str, Any] = {}
        for k, v in data.items():
            if k in _DEFAULTS:
                kwargs[k] = v
            else:
                extras[k] = v
        kwargs["extras"] = extras
        return cls(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    def check(self, action: str) -> None:
        """Consult the policy. Raises ``KernelPolicyError`` on violation.

        Actions (original eight):
          "firmware"     -> requires ``allow_firmware``
          "external_io"  -> requires ``allow_external_io``
          "mutation"     -> requires ``allow_mutation``
          "compute"      -> requires ``allow_compute``
          "conjecture"   -> requires ``allow_conjectural_output``
          "host_write"   -> requires ``allow_host_write``

        Actions (new three-lane gates, raised by ``TypedKernel``):
          "left_io"          -> requires ``allow_left_io``
          "center_dispatch"  -> requires ``allow_center_dispatch``
          "right_emit"       -> requires ``allow_right_emit``
        """
        from .errors import KernelPolicyError

        table = {
            # original eight
            "firmware": self.allow_firmware,
            "external_io": self.allow_external_io,
            "mutation": self.allow_mutation,
            "compute": self.allow_compute,
            "conjecture": self.allow_conjectural_output,
            "host_write": self.allow_host_write,
            # new L/C/R typed-kernel lane gates
            "left_io": self.allow_left_io,
            "center_dispatch": self.allow_center_dispatch,
            "right_emit": self.allow_right_emit,
        }
        if action not in table:
            raise KernelPolicyError(f"unknown policy action: {action!r}")
        if not table[action]:
            raise KernelPolicyError(
                f"policy forbids {action!r} (strict defaults in effect)"
            )
