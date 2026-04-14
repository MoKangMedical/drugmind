"""
MediPharma API client for DrugMind.
"""

from __future__ import annotations

import os
from typing import Any

import httpx


class MediPharmaClient:
    """Thin HTTP client around the MediPharma REST surface."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 45.0,
    ):
        env_base_url = (
            os.getenv("MEDI_PHARMA_BASE_URL", "").strip()
            or os.getenv("MEDIPHARMA_BASE_URL", "").strip()
        )
        env_api_key = (
            os.getenv("MEDI_PHARMA_API_KEY", "").strip()
            or os.getenv("MEDIPHARMA_API_KEY", "").strip()
        )
        self.base_url = (base_url if base_url is not None else env_base_url).strip().rstrip("/")
        self.api_key = (api_key if api_key is not None else env_api_key).strip()
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    def describe(self) -> dict[str, Any]:
        return {
            "provider": "medi_pharma",
            "enabled": self.enabled,
            "base_url": self.base_url,
            "features": [
                "health",
                "target_discovery",
                "virtual_screening",
                "molecule_generation",
                "admet_predict",
                "admet_batch",
                "lead_optimization",
                "pipeline_run",
                "knowledge_report",
                "ecosystem_overview",
            ],
        }

    def probe_status(self) -> dict[str, Any]:
        if not self.enabled:
            return {
                "status": "not_configured",
                "provider": "medi_pharma",
                "base_url": "",
                "health": None,
            }
        try:
            payload = self.health()
            return {
                "status": "ready",
                "provider": "medi_pharma",
                "base_url": self.base_url,
                "health": payload,
            }
        except Exception as exc:
            return {
                "status": "error",
                "provider": "medi_pharma",
                "base_url": self.base_url,
                "error": str(exc),
            }

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def discover_targets(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/targets/discover", json=payload)

    def run_screening(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/screening/run", json=payload)

    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/generate", json=payload)

    def predict_admet(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/admet/predict", json=payload)

    def batch_predict_admet(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/admet/batch", json=payload)

    def optimize(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/optimize", json=payload)

    def run_pipeline(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/pipeline/run", json=payload)

    def knowledge_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/knowledge/report", json=payload)

    def ecosystem(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/ecosystem")

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("MEDI_PHARMA_BASE_URL 未配置")

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        with httpx.Client(timeout=self.timeout) as client:
            response = client.request(
                method.upper(),
                f"{self.base_url}{path}",
                json=json,
                params=params,
                headers=headers or None,
            )
            response.raise_for_status()
            return response.json()
