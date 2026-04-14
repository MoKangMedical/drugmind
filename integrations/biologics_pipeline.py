"""
BY-style biologics campaign planning adapted for DrugMind.
"""

from __future__ import annotations

from typing import Any

from .mcp_bridge import BlatantWhyMCPBridge
from .tamarind_client import TamarindClient


class BiologicsPipeline:
    """Plan biologics-oriented research/design/screen/rank campaigns."""

    def __init__(
        self,
        *,
        mcp_bridge: BlatantWhyMCPBridge | None = None,
        tamarind_client: TamarindClient | None = None,
    ):
        self.mcp_bridge = mcp_bridge or BlatantWhyMCPBridge()
        self.tamarind_client = tamarind_client or TamarindClient()

    def describe(self) -> dict[str, Any]:
        return {
            "name": "BY-inspired biologics pipeline",
            "steps": [
                "research",
                "campaign_planning",
                "design_submission",
                "screening",
                "ranking",
                "lab_gate",
            ],
            "compute_provider": self.tamarind_client.describe(),
            "mcp_servers": self.mcp_bridge.describe(),
        }

    def build_campaign(
        self,
        *,
        project: dict[str, Any],
        modality: str = "nanobody",
        scaffolds: list[str] | None = None,
        seeds: int = 8,
        designs_per_seed: int = 8,
        complexity: str = "standard",
    ) -> dict[str, Any]:
        scaffolds = scaffolds or self._default_scaffolds(modality)
        research_plan = self.mcp_bridge.build_target_research_plan(
            target=project.get("target") or project.get("name") or "unknown target",
            modality=modality,
            disease=project.get("disease", ""),
        )
        estimate = self.tamarind_client.estimate_job(
            job_type=f"{modality}_design",
            seeds=seeds,
            designs_per_seed=designs_per_seed,
            scaffolds=scaffolds,
            complexity=complexity,
        )
        return {
            "project_id": project.get("project_id", ""),
            "modality": modality,
            "scaffolds": scaffolds,
            "research_plan": research_plan,
            "campaign_state_contract": self.mcp_bridge.build_campaign_state_contract(modality=modality),
            "design_estimate": estimate,
            "screening_contract": {
                "required_metrics": [
                    "ipSAE_min",
                    "ipTM",
                    "shape_complementarity",
                    "developability_flags",
                    "diversity_cluster",
                ],
                "ranking_rule": "Composite structural quality + developability + diversity.",
            },
            "next_actions": [
                "Complete structural and prior-art research before design submission.",
                "Confirm scaffold list and design budget.",
                "Gate design submission through project plan approval.",
            ],
        }

    def submit_design_job(
        self,
        *,
        project: dict[str, Any],
        modality: str,
        settings: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        wait_for_completion: bool = False,
        poll_interval_seconds: int = 20,
        timeout_seconds: int = 900,
    ) -> dict[str, Any]:
        job_name = settings.get("jobName") or (
            f"{project.get('project_id', 'drugmind')}_{modality}_{datetime_stamp()}"
        )
        job_type = settings.get("jobType") or f"{modality}_design"
        provider_settings = settings.get("settings") if "settings" in settings else settings
        return self.tamarind_client.submit_job(
            job_name=job_name,
            job_type=job_type,
            settings=provider_settings,
            metadata=metadata or {
                "project_id": project.get("project_id", ""),
                "target": project.get("target", ""),
                "modality": modality,
            },
            wait_for_completion=wait_for_completion,
            poll_interval_seconds=poll_interval_seconds,
            timeout_seconds=timeout_seconds,
            include_result=True,
        )

    def build_second_me_sync_payload(
        self,
        *,
        project: dict[str, Any],
        campaign: dict[str, Any],
        screening_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "project": {
                "project_id": project.get("project_id", ""),
                "name": project.get("name", ""),
                "target": project.get("target", ""),
                "disease": project.get("disease", ""),
                "modality": project.get("modality", "small_molecule"),
            },
            "biologics_campaign": campaign,
            "screening_summary": screening_summary or {},
            "persona_prompt": (
                "Keep the external persona synchronized with the current biologics campaign, "
                "including research assumptions, compute budget, top-ranked candidates, and lab gate status."
            ),
        }

    def _default_scaffolds(self, modality: str) -> list[str]:
        if modality == "nanobody":
            return ["camelid_vhh", "synthetic_vhh", "humanized_vhh"]
        if modality == "antibody":
            return ["human_igg1", "human_igg4", "scfv_bridge"]
        return ["miniprotein_scaffold_a", "miniprotein_scaffold_b"]


def datetime_stamp() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d%H%M%S")
