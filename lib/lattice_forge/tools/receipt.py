"""Receipt port adapter (slot-01)."""
from __future__ import annotations

from typing import Any, Optional

from .base import PortTool, _get_morphon_provider


class ReceiptTool(PortTool):
    port = "receipt"
    part_id = "receipt-chain"

    @classmethod
    def available(cls) -> bool:
        prov = _get_morphon_provider(cls.port)
        if prov is not None:
            return True
        try:
            from cmplx.receipt.chain import ReceiptChain  # noqa: F401

            return True
        except Exception:
            return False

    def invoke(
        self,
        *,
        operation: str,
        payload: dict[str, Any],
        receipt_type: Optional[str] = None,
        atom_id: str = "",
        **_: Any,
    ) -> dict[str, Any]:
        if not self.available():
            return self.unavailable(operation=operation, payload=payload)

        body = {"forge_op": operation, **payload}
        prov = _get_morphon_provider(self.port)
        try:
            if prov is not None:
                result = prov.mint(
                    receipt_type=receipt_type or _infer_receipt_type(payload),
                    atom_id=atom_id or operation,
                    operation=f"forge_{operation}",
                    payload=body,
                )
                return {"available": True, "provenance": self.provenance(), "result": result}

            from cmplx.receipt.chain import ReceiptChain

            result = ReceiptChain().mint(
                receipt_type=receipt_type or _infer_receipt_type(payload),
                atom_id=atom_id or operation,
                operation=f"forge_{operation}",
                payload=body,
            )
            return {"available": True, "provenance": self.provenance(), "result": result}
        except Exception as exc:
            return self.unavailable(reason=str(exc), operation=operation, payload=payload)


def _infer_receipt_type(payload: dict[str, Any]) -> str:
    try:
        from cmplx.receipt.types import ReceiptType
    except Exception:
        return "PROCESS"
    status = str(payload.get("status", ""))
    if status == "fail":
        return ReceiptType.GATE.value
    if status.startswith("pass"):
        return ReceiptType.PROCESS.value
    return ReceiptType.PROCESS.value
