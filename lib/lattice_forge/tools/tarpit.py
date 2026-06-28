"""TarPit symbolic port adapter."""
from __future__ import annotations

from typing import Any

from .base import PortTool


class TarpitTool(PortTool):
    port = "symbolic"
    part_id = "tarpit-symbolic"

    @classmethod
    def available(cls) -> bool:
        return cls()._provider() is not None

    def invoke(
        self,
        *,
        method: str = "canonical_forms",
        form_name: str = "",
        payload: dict[str, Any] | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        prov = self._provider()
        if prov is None:
            return self.unavailable(method=method, form_name=form_name)

        try:
            if method == "canonical_forms":
                fn = getattr(prov, "canonical_forms", None) or getattr(prov, "list_forms", None)
                if fn is None:
                    return self.unavailable(reason="canonical_forms_unsupported")
                result = fn()
                return {
                    "available": True,
                    "provenance": self.provenance(),
                    "forms": result,
                }

            fn = getattr(prov, method, None)
            if fn is None:
                return self.unavailable(reason=f"unknown_method:{method}", method=method)
            call_payload = payload or {}
            call_payload.update(params)
            result = fn(**call_payload) if call_payload else fn(form_name) if form_name else fn()
            return {
                "available": True,
                "provenance": self.provenance(),
                "method": method,
                "form_name": form_name,
                "result": result,
            }
        except Exception as exc:
            return self.unavailable(reason=str(exc), method=method, form_name=form_name)

    @classmethod
    def label_syndrome(cls, syndrome_key: str) -> dict[str, Any]:
        """Return a canonical TarPit label for an ECC/shed syndrome key."""
        tool = cls()
        local_label = f"syndrome:{syndrome_key}"
        if not tool.available():
            return {
                "available": False,
                "canonical_label": local_label,
                "provenance": tool.provenance(),
            }
        result = tool.invoke(method="label_syndrome", form_name=syndrome_key)
        if result.get("available"):
            return result
        return {
            "available": False,
            "canonical_label": local_label,
            "provenance": tool.provenance(),
            "tarpit_fallback": True,
        }
