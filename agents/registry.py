"""
Platform agent registry.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from digital_twin.roles import ROLE_REGISTRY

logger = logging.getLogger(__name__)


@dataclass
class AgentProfile:
    """Registered agent definition."""

    agent_id: str
    name: str
    category: str
    description: str
    role_id: str = ""
    specialties: list[str] = field(default_factory=list)
    default_skills: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    memory_scope: str = "project"
    execution_mode: str = "copilot"
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


class AgentRegistry:
    """Stores the platform's available agents."""

    def __init__(self, data_dir: str = "./drugmind_data/platform/agents"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.data_dir / "agents.json"
        self.agents: dict[str, AgentProfile] = {}
        self._load()
        self._seed_defaults()

    def list_agents(self, category: str = "", active_only: bool = True) -> list[dict]:
        agents = list(self.agents.values())
        if category:
            agents = [agent for agent in agents if agent.category == category]
        if active_only:
            agents = [agent for agent in agents if agent.is_active]
        agents.sort(key=lambda agent: (agent.category, agent.name))
        return [asdict(agent) for agent in agents]

    def get_agent(self, agent_id: str) -> Optional[dict]:
        agent = self.agents.get(agent_id)
        return asdict(agent) if agent else None

    def register_agent(self, profile: AgentProfile) -> dict:
        profile.updated_at = datetime.now().isoformat()
        self.agents[profile.agent_id] = profile
        self._save()
        return asdict(profile)

    def count(self) -> int:
        return len(self.agents)

    def _seed_defaults(self):
        changed = False

        role_skill_map = {
            "medicinal_chemist": ["skill.sar_review", "skill.lead_optimization"],
            "biologist": ["skill.target_evaluation", "skill.evidence_review"],
            "pharmacologist": ["skill.admet_assessment", "skill.go_nogo_review"],
            "data_scientist": ["skill.modeling_strategy", "skill.evidence_review"],
            "project_lead": ["skill.project_triage", "skill.go_nogo_review"],
        }
        role_tool_map = {
            "medicinal_chemist": ["tool.drugmind_ask", "tool.drugmind_compound", "tool.project_kanban"],
            "biologist": ["tool.drugmind_ask", "tool.drugmind_scenario"],
            "pharmacologist": ["tool.drugmind_admet", "tool.drugmind_scenario"],
            "data_scientist": ["tool.drugmind_ask", "tool.drugmind_admet"],
            "project_lead": ["tool.drugmind_discuss", "tool.project_kanban", "tool.project_memory"],
        }

        for role_id, role in ROLE_REGISTRY.items():
            agent_id = f"agent.{role_id}"
            if agent_id in self.agents:
                continue
            self.agents[agent_id] = AgentProfile(
                agent_id=agent_id,
                name=role.display_name,
                category="domain",
                description=f"{role.display_name} agent for drug discovery collaboration",
                role_id=role_id,
                specialties=role.expertise,
                default_skills=role_skill_map.get(role_id, []),
                allowed_tools=role_tool_map.get(role_id, []),
                execution_mode="expert",
            )
            changed = True

        platform_agents = [
            AgentProfile(
                agent_id="agent.orchestrator",
                name="Workflow Orchestrator",
                category="platform",
                description="Coordinates multi-agent workflows and assigns tasks.",
                default_skills=["skill.workflow_planning", "skill.discussion_synthesis"],
                allowed_tools=["tool.project_memory", "tool.drugmind_discuss", "tool.project_kanban"],
                memory_scope="workspace",
                execution_mode="orchestrator",
            ),
            AgentProfile(
                agent_id="agent.reviewer",
                name="Scientific Reviewer",
                category="platform",
                description="Reviews outputs for scientific consistency and evidence gaps.",
                default_skills=["skill.evidence_review", "skill.go_nogo_review"],
                allowed_tools=["tool.project_memory", "tool.drugmind_ask"],
                execution_mode="reviewer",
            ),
            AgentProfile(
                agent_id="agent.integration",
                name="Integration Agent",
                category="platform",
                description="Owns MCP, Second Me, and external system integration tasks.",
                default_skills=["skill.integration_delivery", "skill.workflow_planning"],
                allowed_tools=["tool.second_me_sync", "tool.second_me_project_sync", "tool.drugmind_ask"],
                memory_scope="workspace",
            ),
            AgentProfile(
                agent_id="agent.discovery_strategist",
                name="Discovery Strategist",
                category="domain",
                description="Turns a project brief into an executable drug discovery implementation plan.",
                default_skills=["skill.target_evaluation", "skill.assay_strategy", "skill.translational_strategy"],
                allowed_tools=["tool.drug_discovery_execute", "tool.project_memory", "tool.project_kanban"],
                memory_scope="workspace",
                execution_mode="strategist",
            ),
            AgentProfile(
                agent_id="agent.dmpk_strategist",
                name="DMPK Strategist",
                category="domain",
                description="Owns developability, DMPK, and candidate nomination tradeoffs across a compound series.",
                default_skills=["skill.admet_assessment", "skill.candidate_nomination"],
                allowed_tools=["tool.drugmind_admet", "tool.drug_discovery_execute", "tool.project_memory"],
                memory_scope="workspace",
                execution_mode="strategist",
            ),
        ]

        for agent in platform_agents:
            if agent.agent_id not in self.agents:
                self.agents[agent.agent_id] = agent
                changed = True

        if changed:
            self._save()
            logger.info("✅ Agent registry seeded with %s agents", len(self.agents))

    def _save(self):
        data = {agent_id: asdict(agent) for agent_id, agent in self.agents.items()}
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load(self):
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            self.agents = {
                agent_id: AgentProfile(**payload)
                for agent_id, payload in data.items()
            }
        except Exception as exc:
            logger.warning("加载 agent registry 失败: %s", exc)
            self.agents = {}
