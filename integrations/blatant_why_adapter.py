"""
BY architecture adapter for DrugMind.
"""

from __future__ import annotations

from typing import Any

from .biologics_pipeline import BiologicsPipeline
from .mcp_bridge import BlatantWhyMCPBridge
from .screening_bridge import ScreeningBridge
from .tamarind_client import TamarindClient


class BlatantWhyAdapter:
    """Adapt reusable BY concepts into DrugMind-native capabilities."""

    SOURCE_REPO = "https://github.com/001TMF/blatant-why"

    def __init__(
        self,
        *,
        mcp_bridge: BlatantWhyMCPBridge | None = None,
        screening_bridge: ScreeningBridge | None = None,
        tamarind_client: TamarindClient | None = None,
        biologics_pipeline: BiologicsPipeline | None = None,
    ):
        self.mcp_bridge = mcp_bridge or BlatantWhyMCPBridge()
        self.screening_bridge = screening_bridge or ScreeningBridge()
        self.tamarind_client = tamarind_client or TamarindClient()
        self.biologics_pipeline = biologics_pipeline or BiologicsPipeline(
            mcp_bridge=self.mcp_bridge,
            tamarind_client=self.tamarind_client,
        )
        self.core_agent_map = {
            "by-research": "agent.biologist",
            "by-campaign": "agent.discovery_strategist",
            "by-design": "agent.medicinal_chemist",
            "by-screening": "agent.pharmacologist",
            "by-evaluator": "agent.reviewer",
            "by-knowledge": "agent.integration",
            "by-diversity": "agent.data_scientist",
            "by-lab": "agent.project_lead",
        }

    def describe(self) -> dict[str, Any]:
        return {
            "source_repo": self.SOURCE_REPO,
            "reused_components": [
                "campaign_state_pattern",
                "research_to_design_to_screen_to_rank pipeline",
                "pdb/uniprot/sabdab research source mapping",
                "composite screening and Pareto ranking",
                "decision log and knowledge carry-forward",
            ],
            "runtime_adaptation": {
                "agent_runtime": "DrugMind + MIMO",
                "second_me": "project and persona sync target",
                "campaign_model": "implementation state + workflow runs + memory",
            },
            "core_agent_map": self.core_agent_map,
            "mcp_bridge": self.mcp_bridge.describe(),
            "compute": self.tamarind_client.describe(),
        }

    def run_target_research(
        self,
        *,
        project: dict[str, Any],
        modality: str | None = None,
        organism_id: int = 9606,
        pdb_rows: int = 6,
        sabdab_limit: int = 6,
    ) -> dict[str, Any]:
        return self.mcp_bridge.run_target_research(
            target=project.get("target") or project.get("name") or "unknown target",
            modality=modality or project.get("modality", "small_molecule"),
            disease=project.get("disease", ""),
            organism_id=organism_id,
            organism_label="human" if organism_id == 9606 else "",
            pdb_rows=pdb_rows,
            sabdab_limit=sabdab_limit,
        )

    def submit_tamarind_job(
        self,
        *,
        project: dict[str, Any],
        modality: str,
        settings: dict[str, Any],
        wait_for_completion: bool = False,
        poll_interval_seconds: int = 20,
        timeout_seconds: int = 900,
    ) -> dict[str, Any]:
        return self.biologics_pipeline.submit_design_job(
            project=project,
            modality=modality,
            settings=settings,
            wait_for_completion=wait_for_completion,
            poll_interval_seconds=poll_interval_seconds,
            timeout_seconds=timeout_seconds,
        )

    def build_dmta_blueprint(self, *, project: dict[str, Any]) -> dict[str, Any]:
        modality = project.get("modality", "small_molecule")
        if modality in {"biologics", "protein", "antibody", "nanobody"}:
            return self.biologics_pipeline.build_campaign(project=project, modality="nanobody" if modality == "biologics" else modality)

        return {
            "project_id": project.get("project_id", ""),
            "modality": modality,
            "pipeline": [
                {
                    "phase": "research",
                    "owner": self.core_agent_map["by-research"],
                    "focus": "target biology, structure, prior art, assay entry points",
                },
                {
                    "phase": "design",
                    "owner": self.core_agent_map["by-design"],
                    "focus": "compound ideation, series strategy, next-cycle design",
                },
                {
                    "phase": "screening",
                    "owner": self.core_agent_map["by-screening"],
                    "focus": "ADMET-aware triage and developability gating",
                },
                {
                    "phase": "ranking",
                    "owner": self.core_agent_map["by-diversity"],
                    "focus": "portfolio ranking, Pareto front, backup selection",
                },
            ],
            "state_contract": self.mcp_bridge.build_campaign_state_contract(modality=modality),
        }

    def run_small_molecule_screening(
        self,
        *,
        project: dict[str, Any],
        compounds: list[dict[str, Any]],
    ) -> dict[str, Any]:
        screening = self.screening_bridge.screen_series(compounds)
        pareto = self.screening_bridge.pareto_front(compounds)
        return {
            "project_id": project.get("project_id", ""),
            "project_name": project.get("name", ""),
            "screening": screening,
            "pareto_front": pareto,
            "campaign_recommendation": self._campaign_recommendation(screening),
        }

    def build_second_me_payload(
        self,
        *,
        project: dict[str, Any],
        implementation: dict[str, Any],
        executions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        current_phase = (implementation.get("current_phase") or {}).get("name", "")
        return {
            "project": {
                "project_id": project.get("project_id", ""),
                "name": project.get("name", ""),
                "target": project.get("target", ""),
                "disease": project.get("disease", ""),
                "modality": project.get("modality", "small_molecule"),
            },
            "by_dmta_summary": {
                "current_phase": current_phase,
                "recent_executions": [
                    {
                        "capability_id": item.get("capability_id", ""),
                        "summary": item.get("summary", ""),
                    }
                    for item in executions[:5]
                ],
            },
            "persona_instruction": (
                "Act as the synchronized project avatar. Speak from the latest DrugMind "
                "implementation state, preserve campaign memory, and explain next gates clearly."
            ),
        }

    def _campaign_recommendation(self, screening: dict[str, Any]) -> dict[str, Any]:
        attrition = screening.get("attrition", {})
        advance = int(attrition.get("advance", 0))
        if advance >= 3:
            gate = "GO"
        elif advance >= 1:
            gate = "CONDITIONAL"
        else:
            gate = "NO-GO"
        return {
            "gate": gate,
            "rationale": (
                f"{advance} compounds cleared the current screening bar; "
                "use rescue bucket only if chemistry space remains differentiated."
            ),
        }
