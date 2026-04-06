"""
Platform skill registry.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SkillSpec:
    """Skill package definition for agents."""

    skill_id: str
    name: str
    category: str
    description: str
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    tool_dependencies: list[str] = field(default_factory=list)
    recommended_agents: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    version: str = "0.1.0"
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


class SkillRegistry:
    """Stores reusable skill specs."""

    def __init__(self, data_dir: str = "./drugmind_data/platform/skills"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.data_dir / "skills.json"
        self.skills: dict[str, SkillSpec] = {}
        self._load()
        self._seed_defaults()

    def list_skills(self, category: str = "") -> list[dict]:
        skills = list(self.skills.values())
        if category:
            skills = [skill for skill in skills if skill.category == category]
        skills.sort(key=lambda skill: (skill.category, skill.name))
        return [asdict(skill) for skill in skills]

    def get_skill(self, skill_id: str) -> Optional[dict]:
        skill = self.skills.get(skill_id)
        return asdict(skill) if skill else None

    def register_skill(self, skill: SkillSpec) -> dict:
        skill.updated_at = datetime.now().isoformat()
        self.skills[skill.skill_id] = skill
        self._save()
        return asdict(skill)

    def count(self) -> int:
        return len(self.skills)

    def _seed_defaults(self):
        defaults = [
            SkillSpec(
                skill_id="skill.target_evaluation",
                name="Target Evaluation",
                category="drug_discovery",
                description="Evaluate a target from mechanism, evidence, competition, and tractability.",
                inputs=["target", "disease_context", "evidence"],
                outputs=["target_dossier", "open_questions"],
                tool_dependencies=["tool.drugmind_scenario", "tool.project_memory"],
                recommended_agents=["agent.biologist", "agent.project_lead"],
                tags=["target", "biology", "strategy"],
            ),
            SkillSpec(
                skill_id="skill.lead_optimization",
                name="Lead Optimization",
                category="drug_discovery",
                description="Drive lead optimization through SAR, ADMET, and project tradeoffs.",
                inputs=["compound_series", "assay_data", "constraints"],
                outputs=["optimization_plan", "priority_compounds"],
                tool_dependencies=["tool.drugmind_admet", "tool.drugmind_compound"],
                recommended_agents=["agent.medicinal_chemist", "agent.pharmacologist"],
                tags=["sar", "lead_opt"],
            ),
            SkillSpec(
                skill_id="skill.sar_review",
                name="SAR Review",
                category="drug_discovery",
                description="Review structure-activity relationships and propose next chemistry moves.",
                inputs=["compound_series", "activity_table"],
                outputs=["sar_hypotheses", "next_round_ideas"],
                tool_dependencies=["tool.drugmind_compound", "tool.project_memory"],
                recommended_agents=["agent.medicinal_chemist"],
                tags=["sar", "chemistry"],
            ),
            SkillSpec(
                skill_id="skill.admet_assessment",
                name="ADMET Assessment",
                category="drug_discovery",
                description="Assess ADMET liabilities and propose mitigations.",
                inputs=["smiles", "admet_data"],
                outputs=["admet_report", "risk_flags"],
                tool_dependencies=["tool.drugmind_admet", "tool.project_memory"],
                recommended_agents=["agent.pharmacologist"],
                tags=["admet", "tox"],
            ),
            SkillSpec(
                skill_id="skill.modeling_strategy",
                name="Modeling Strategy",
                category="analytics",
                description="Define predictive modeling strategy for QSAR and prioritization.",
                inputs=["dataset_summary", "endpoints", "quality_constraints"],
                outputs=["model_plan", "feature_strategy"],
                tool_dependencies=["tool.drugmind_ask", "tool.project_memory"],
                recommended_agents=["agent.data_scientist"],
                tags=["ml", "qsar"],
            ),
            SkillSpec(
                skill_id="skill.project_triage",
                name="Project Triage",
                category="coordination",
                description="Prioritize the next actions for a project based on evidence and risk.",
                inputs=["project_state", "current_risks", "timeline"],
                outputs=["priority_queue", "owner_assignments"],
                tool_dependencies=["tool.project_kanban", "tool.project_memory"],
                recommended_agents=["agent.project_lead", "agent.orchestrator"],
                tags=["triage", "project"],
            ),
            SkillSpec(
                skill_id="skill.go_nogo_review",
                name="Go/No-Go Review",
                category="coordination",
                description="Structure a stage-gate review and record the decision basis.",
                inputs=["project_state", "evidence", "risk_flags"],
                outputs=["decision_record", "required_followups"],
                tool_dependencies=["tool.drugmind_discuss", "tool.project_memory"],
                recommended_agents=["agent.project_lead", "agent.reviewer"],
                tags=["decision", "go_nogo"],
            ),
            SkillSpec(
                skill_id="skill.evidence_review",
                name="Evidence Review",
                category="coordination",
                description="Review current evidence and identify missing support for a claim.",
                inputs=["discussion_summary", "citations", "experiment_results"],
                outputs=["evidence_map", "gaps"],
                tool_dependencies=["tool.project_memory", "tool.drugmind_ask"],
                recommended_agents=["agent.biologist", "agent.reviewer"],
                tags=["evidence", "quality"],
            ),
            SkillSpec(
                skill_id="skill.discussion_synthesis",
                name="Discussion Synthesis",
                category="coordination",
                description="Turn multi-agent discussion into concise conclusions and action items.",
                inputs=["discussion_messages"],
                outputs=["summary", "action_items"],
                tool_dependencies=["tool.drugmind_discuss", "tool.project_memory"],
                recommended_agents=["agent.orchestrator", "agent.project_lead"],
                tags=["discussion", "summary"],
            ),
            SkillSpec(
                skill_id="skill.workflow_planning",
                name="Workflow Planning",
                category="platform",
                description="Plan a multi-agent workflow with ordered steps and owners.",
                inputs=["goal", "constraints", "available_agents"],
                outputs=["workflow_plan"],
                tool_dependencies=["tool.project_memory", "tool.project_kanban"],
                recommended_agents=["agent.orchestrator", "agent.integration"],
                tags=["workflow", "platform"],
            ),
            SkillSpec(
                skill_id="skill.integration_delivery",
                name="Integration Delivery",
                category="platform",
                description="Prepare and validate MCP, Second Me, and external integration deliverables.",
                inputs=["integration_spec", "endpoint_config"],
                outputs=["integration_status", "delivery_notes"],
                tool_dependencies=["tool.second_me_sync", "tool.project_memory"],
                recommended_agents=["agent.integration"],
                tags=["integration", "mcp"],
            ),
        ]

        changed = False
        for skill in defaults:
            if skill.skill_id not in self.skills:
                self.skills[skill.skill_id] = skill
                changed = True
        if changed:
            self._save()
            logger.info("✅ Skill registry seeded with %s skills", len(self.skills))

    def _save(self):
        data = {skill_id: asdict(skill) for skill_id, skill in self.skills.items()}
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load(self):
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            self.skills = {
                skill_id: SkillSpec(**payload)
                for skill_id, payload in data.items()
            }
        except Exception as exc:
            logger.warning("加载 skill registry 失败: %s", exc)
            self.skills = {}
