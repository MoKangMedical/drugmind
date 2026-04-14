"""
MediPharma capability adapter for DrugMind.
"""

from __future__ import annotations

from typing import Any

from .medi_pharma_client import MediPharmaClient


class MediPharmaAdapter:
    """Translate DrugMind project context into MediPharma requests."""

    SOURCE_REPO = "https://github.com/MoKangMedical/medi-pharma"

    def __init__(self, *, client: MediPharmaClient | None = None):
        self.client = client or MediPharmaClient()

    def describe(self) -> dict[str, Any]:
        return {
            "source_repo": self.SOURCE_REPO,
            "runtime_adaptation": {
                "execution_mode": "DrugMind -> MediPharma REST bridge",
                "project_context": "project + compounds + optional input payload",
                "transport": "httpx",
            },
            "client": self.client.describe(),
            "status": self.probe_status(),
        }

    def probe_status(self) -> dict[str, Any]:
        return self.client.probe_status()

    def health(self) -> dict[str, Any]:
        return self._safe_call("health", request_preview=None)

    def ecosystem(self) -> dict[str, Any]:
        return self._safe_call("ecosystem", request_preview=None)

    def discover_targets(self, *, project: dict[str, Any] | None = None, input_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        project = project or {}
        input_payload = input_payload or {}
        disease = (input_payload.get("disease") or project.get("disease") or "").strip()
        payload = {
            "disease": disease,
            "max_papers": int(input_payload.get("max_papers", 30)),
            "top_n": int(input_payload.get("top_n", 8)),
            "disease_burden": float(input_payload.get("disease_burden", 0.8)),
            "unmet_need": float(input_payload.get("unmet_need", 0.8)),
        }
        if not disease:
            return self._insufficient_context(
                "靶点发现需要 disease。",
                request_preview=payload,
                missing=["disease"],
            )
        return self._safe_call("discover_targets", request_preview=payload, payload=payload)

    def run_screening(
        self,
        *,
        project: dict[str, Any] | None = None,
        compounds: list[dict[str, Any]] | None = None,
        input_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        project = project or {}
        compounds = compounds or []
        input_payload = input_payload or {}
        payload = {
            "target_chembl_id": (input_payload.get("target_chembl_id") or project.get("target_chembl_id") or "").strip(),
            "protein_pdb": (input_payload.get("protein_pdb") or "").strip() or None,
            "max_compounds": int(input_payload.get("max_compounds", max(len(compounds), 100) or 100)),
            "top_n": int(input_payload.get("top_n", 20)),
            "use_docking": bool(input_payload.get("use_docking", False)),
        }
        if not payload["target_chembl_id"]:
            return self._insufficient_context(
                "虚拟筛选需要 target_chembl_id。",
                request_preview=payload,
                missing=["target_chembl_id"],
            )
        return self._safe_call("run_screening", request_preview=payload, payload=payload)

    def generate(
        self,
        *,
        project: dict[str, Any] | None = None,
        input_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        project = project or {}
        input_payload = input_payload or {}
        payload = {
            "target_name": (input_payload.get("target_name") or project.get("target") or project.get("name") or "").strip(),
            "scaffold": (input_payload.get("scaffold") or "").strip() or None,
            "n_generate": int(input_payload.get("n_generate", 120)),
            "top_n": int(input_payload.get("top_n", 12)),
            "target_mw": float(input_payload.get("target_mw", 400)),
            "target_logp": float(input_payload.get("target_logp", 2.5)),
        }
        return self._safe_call("generate", request_preview=payload, payload=payload)

    def predict_admet(self, *, smiles: str) -> dict[str, Any]:
        smiles = (smiles or "").strip()
        payload = {"smiles": smiles}
        if not smiles:
            return self._insufficient_context(
                "ADMET 单分子预测需要 smiles。",
                request_preview=payload,
                missing=["smiles"],
            )
        return self._safe_call("predict_admet", request_preview=payload, payload=payload)

    def batch_predict_admet(
        self,
        *,
        compounds: list[dict[str, Any]] | None = None,
        input_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        compounds = compounds or []
        input_payload = input_payload or {}
        smiles_list = input_payload.get("smiles_list") or [
            item.get("smiles")
            for item in compounds
            if item.get("smiles")
        ]
        payload = {"smiles_list": smiles_list}
        if not smiles_list:
            return self._insufficient_context(
                "ADMET 批量预测需要 smiles_list 或项目 compounds。",
                request_preview=payload,
                missing=["smiles_list"],
            )
        return self._safe_call("batch_predict_admet", request_preview=payload, payload=payload)

    def optimize(
        self,
        *,
        compounds: list[dict[str, Any]] | None = None,
        input_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        compounds = compounds or []
        input_payload = input_payload or {}
        lead_smiles = (input_payload.get("smiles") or "").strip()
        if not lead_smiles:
            for item in compounds:
                if item.get("smiles"):
                    lead_smiles = item["smiles"]
                    break
        payload = {
            "smiles": lead_smiles,
            "objective_weights": input_payload.get("objective_weights"),
            "max_generations": int(input_payload.get("max_generations", 12)),
            "population_size": int(input_payload.get("population_size", 24)),
        }
        if not lead_smiles:
            return self._insufficient_context(
                "先导优化需要起始 smiles。",
                request_preview=payload,
                missing=["smiles"],
            )
        return self._safe_call("optimize", request_preview=payload, payload=payload)

    def run_pipeline(
        self,
        *,
        project: dict[str, Any] | None = None,
        input_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        project = project or {}
        input_payload = input_payload or {}
        disease = (input_payload.get("disease") or project.get("disease") or "").strip()
        target = (input_payload.get("target") or project.get("target") or "").strip()
        payload = {
            "disease": disease,
            "target": target,
            "target_chembl_id": (input_payload.get("target_chembl_id") or project.get("target_chembl_id") or "").strip(),
            "max_papers": int(input_payload.get("max_papers", 20)),
            "max_compounds": int(input_payload.get("max_compounds", 200)),
            "n_generate": int(input_payload.get("n_generate", 80)),
            "top_n": int(input_payload.get("top_n", 10)),
            "auto_mode": bool(input_payload.get("auto_mode", True)),
        }
        if not disease:
            return self._insufficient_context(
                "全流水线需要 disease。",
                request_preview=payload,
                missing=["disease"],
            )
        return self._safe_call("run_pipeline", request_preview=payload, payload=payload)

    def knowledge_report(self, *, project: dict[str, Any] | None = None, input_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        project = project or {}
        input_payload = input_payload or {}
        target = (input_payload.get("target") or project.get("target") or "").strip()
        disease = (input_payload.get("disease") or project.get("disease") or "").strip()
        payload = {
            "target": target,
            "disease": disease,
            "include_patents": bool(input_payload.get("include_patents", True)),
            "include_clinical": bool(input_payload.get("include_clinical", True)),
        }
        missing = []
        if not target:
            missing.append("target")
        if not disease:
            missing.append("disease")
        if missing:
            return self._insufficient_context(
                "知识引擎报告需要 target 和 disease。",
                request_preview=payload,
                missing=missing,
            )
        return self._safe_call("knowledge_report", request_preview=payload, payload=payload)

    def _safe_call(
        self,
        method_name: str,
        *,
        request_preview: dict[str, Any] | None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.client.enabled:
            return {
                "status": "not_configured",
                "provider": "medi_pharma",
                "request_preview": request_preview,
                "note": "MEDI_PHARMA_BASE_URL 未配置，尚未调用真实 MediPharma 服务。",
            }
        try:
            method = getattr(self.client, method_name)
            response = method(payload) if payload is not None else method()
            return {
                "status": "ready",
                "provider": "medi_pharma",
                "request_preview": request_preview,
                "response": response,
            }
        except Exception as exc:
            return {
                "status": "error",
                "provider": "medi_pharma",
                "request_preview": request_preview,
                "error": str(exc),
            }

    def _insufficient_context(
        self,
        note: str,
        *,
        request_preview: dict[str, Any] | None,
        missing: list[str],
    ) -> dict[str, Any]:
        return {
            "status": "insufficient_context",
            "provider": "medi_pharma",
            "request_preview": request_preview,
            "missing": missing,
            "note": note,
        }
