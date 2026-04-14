"""
Tamarind Bio API adapter for DrugMind.
"""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

import httpx


@dataclass
class TamarindJobEstimate:
    """Estimated cost/runtime for a biologics or structure job."""

    provider: str
    job_type: str
    seeds: int
    designs_per_seed: int
    scaffolds: list[str] = field(default_factory=list)
    total_designs: int = 0
    estimated_minutes: float = 0.0
    estimated_cost_usd: float = 0.0
    tier: str = "free"
    notes: list[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class TamarindClient:
    """Adapter around Tamarind Bio job submission and polling APIs."""

    DEFAULT_BASE_URL = "https://app.tamarind.bio/api/ppiscreenml"
    TERMINAL_STATUSES = {
        "completed",
        "complete",
        "succeeded",
        "success",
        "failed",
        "error",
        "cancelled",
        "canceled",
    }

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = (base_url or os.getenv("TAMARIND_BASE_URL", "").strip() or self.DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key or os.getenv("TAMARIND_API_KEY", "").strip()
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def describe(self) -> dict[str, Any]:
        return {
            "provider": "tamarind",
            "enabled": self.enabled,
            "base_url": self.base_url,
            "features": [
                "job_estimation",
                "tool_catalog",
                "submit_job",
                "list_jobs",
                "get_job",
                "get_result",
                "poll_job",
                "provider_status_probe",
            ],
        }

    def estimate_job(
        self,
        *,
        job_type: str,
        seeds: int,
        designs_per_seed: int,
        scaffolds: list[str] | None = None,
        complexity: str = "standard",
    ) -> dict[str, Any]:
        scaffolds = scaffolds or []
        total_designs = max(seeds, 1) * max(designs_per_seed, 1) * max(len(scaffolds), 1)
        minutes_per_design = {
            "light": 0.35,
            "standard": 0.75,
            "heavy": 1.6,
        }.get(complexity, 0.75)
        estimated_minutes = round(total_designs * minutes_per_design, 1)
        notes = [
            "Tamarind free tier should be reserved for high-value design batches.",
            "Large campaigns should separate exploratory and validation runs.",
        ]
        if total_designs > 500:
            notes.append("This campaign should be split into batched submissions to improve retry control.")
        estimate = TamarindJobEstimate(
            provider="tamarind",
            job_type=job_type,
            seeds=seeds,
            designs_per_seed=designs_per_seed,
            scaffolds=scaffolds,
            total_designs=total_designs,
            estimated_minutes=estimated_minutes,
            estimated_cost_usd=0.0,
            tier="free" if total_designs <= 200 else "managed",
            notes=notes,
        )
        return asdict(estimate)

    def list_available_tools(self) -> dict[str, Any]:
        if not self.enabled:
            return {"status": "not_configured", "provider": "tamarind", "tools": []}
        payload = self._request("GET", "/tools")
        tools = payload if isinstance(payload, list) else payload.get("tools", payload.get("data", []))
        return {
            "status": "ready",
            "provider": "tamarind",
            "tools": tools if isinstance(tools, list) else [tools],
        }

    def list_jobs(self, *, job_name: str = "", status: str = "", limit: int = 50) -> dict[str, Any]:
        if not self.enabled:
            return {"status": "not_configured", "provider": "tamarind", "jobs": []}
        params = {}
        if job_name:
            params["jobName"] = job_name
        if status:
            params["status"] = status
        payload = self._request("GET", "/jobs", params=params or None)
        jobs = self._normalize_job_records(payload)
        if limit:
            jobs = jobs[:limit]
        return {
            "status": "ready",
            "provider": "tamarind",
            "jobs": jobs,
        }

    def get_job(self, job_name: str) -> dict[str, Any]:
        if not self.enabled:
            return {"status": "not_configured", "provider": "tamarind", "job": None}
        payload = self._request("GET", "/jobs", params={"jobName": job_name})
        job = self._normalize_single_job(payload, expected_job_name=job_name)
        return {
            "status": "ready" if job else "not_found",
            "provider": "tamarind",
            "job": job,
        }

    def submit_job(
        self,
        *,
        job_name: str,
        job_type: str,
        settings: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        wait_for_completion: bool = False,
        poll_interval_seconds: int = 20,
        timeout_seconds: int = 900,
        include_result: bool = True,
    ) -> dict[str, Any]:
        payload = {
            "jobName": job_name,
            "jobType": job_type,
            "settings": settings,
        }
        if metadata:
            payload["metadata"] = metadata
        if inputs:
            payload["inputs"] = inputs

        if not self.enabled:
            return {
                "status": "not_configured",
                "provider": "tamarind",
                "job_name": job_name,
                "request": payload,
                "note": "TAMARIND_API_KEY 未配置，未发起真实提交。",
            }

        response_payload = self._request("POST", "/submit-job", json=payload)
        result = {
            "status": "submitted",
            "provider": "tamarind",
            "job_name": job_name,
            "job_type": job_type,
            "response": response_payload,
        }
        if wait_for_completion:
            result["poll"] = self.poll_job(
                job_name,
                interval_seconds=poll_interval_seconds,
                timeout_seconds=timeout_seconds,
                include_result=include_result,
            )
        return result

    def get_result(self, job_name: str, *, path: str = "") -> dict[str, Any]:
        if not self.enabled:
            return {"status": "not_configured", "provider": "tamarind", "result": None}
        payload = {"jobName": job_name}
        if path:
            payload["path"] = path
        result = self._try_result_endpoints(payload)
        return {
            "status": "ready",
            "provider": "tamarind",
            "job_name": job_name,
            "result": result,
        }

    def poll_job(
        self,
        job_name: str,
        *,
        interval_seconds: int = 20,
        timeout_seconds: int = 900,
        include_result: bool = False,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {"status": "not_configured", "provider": "tamarind", "job": None}

        deadline = time.time() + max(timeout_seconds, interval_seconds)
        last_job = None
        while time.time() < deadline:
            current = self.get_job(job_name)
            last_job = current.get("job")
            current_status = self._extract_status(last_job)
            if current_status in self.TERMINAL_STATUSES:
                payload = {
                    "status": current_status,
                    "provider": "tamarind",
                    "job_name": job_name,
                    "job": last_job,
                }
                if include_result and current_status in {"completed", "complete", "succeeded", "success"}:
                    try:
                        payload["result"] = self.get_result(job_name).get("result")
                    except Exception as exc:  # pragma: no cover - defensive
                        payload["result_error"] = str(exc)
                return payload
            time.sleep(max(interval_seconds, 1))

        return {
            "status": "timeout",
            "provider": "tamarind",
            "job_name": job_name,
            "job": last_job,
        }

    def probe_status(self) -> dict[str, Any]:
        if not self.enabled:
            return {
                "status": "not_configured",
                "provider": "tamarind",
                "base_url": self.base_url,
            }
        try:
            payload = self._request("GET", "/jobs")
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            return {
                "status": "unauthorized" if status_code in {401, 403} else "degraded",
                "provider": "tamarind",
                "base_url": self.base_url,
                "http_status": status_code,
                "error": exc.response.text[:300],
            }
        except Exception as exc:
            return {
                "status": "unreachable",
                "provider": "tamarind",
                "base_url": self.base_url,
                "error": str(exc),
            }
        jobs = self._normalize_job_records(payload)
        return {
            "status": "ready",
            "provider": "tamarind",
            "base_url": self.base_url,
            "jobs_visible": len(jobs),
        }

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout, headers=self._headers()) as client:
            response = client.request(method, path, params=params, json=json)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return response.json()
            return response.text

    def _try_result_endpoints(self, payload: dict[str, Any]) -> Any:
        errors: list[str] = []
        for path in ("/result", "/results"):
            try:
                return self._request("POST", path, json=payload)
            except Exception as exc:  # pragma: no cover - best-effort fallback
                errors.append(f"{path}: {exc}")
        raise RuntimeError("; ".join(errors))

    def _normalize_job_records(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("jobs", "data", "results", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
            if any(key in payload for key in ("jobName", "job_name", "status", "jobStatus", "state")):
                return [payload]
        return []

    def _normalize_single_job(self, payload: Any, *, expected_job_name: str = "") -> dict[str, Any] | None:
        jobs = self._normalize_job_records(payload)
        if not jobs:
            return payload if isinstance(payload, dict) and payload else None
        if expected_job_name:
            for job in jobs:
                if self._extract_job_name(job) == expected_job_name:
                    return job
        return jobs[0]

    def _extract_job_name(self, job: dict[str, Any] | None) -> str:
        if not job:
            return ""
        for key in ("jobName", "job_name", "name", "id"):
            value = job.get(key)
            if value:
                return str(value)
        return ""

    def _extract_status(self, job: dict[str, Any] | None) -> str:
        if not job:
            return "unknown"
        for key in ("status", "jobStatus", "state", "phase"):
            value = job.get(key)
            if value:
                return str(value).strip().lower()
        return "unknown"
