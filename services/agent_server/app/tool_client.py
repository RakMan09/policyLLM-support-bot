from __future__ import annotations

from typing import Any

import httpx


class ToolClient:
    """Allowlisted, schema-constrained tool client.

    This client only exposes supported tool operations, preventing free-form commands.
    """

    def __init__(self, base_url: str, timeout_s: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout_s) as client:
            response = client.post(f"{self.base_url}{path}", json=payload)
            response.raise_for_status()
            return response.json()

    def lookup_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/tools/lookup_order", payload)

    def get_policy(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/tools/get_policy", payload)

    def check_eligibility(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/tools/check_eligibility", payload)

    def compute_refund(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/tools/compute_refund", payload)

    def create_return(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/tools/create_return", payload)

    def create_label(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/tools/create_label", payload)

    def create_escalation(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/tools/create_escalation", payload)
