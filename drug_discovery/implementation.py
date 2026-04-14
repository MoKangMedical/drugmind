"""
Drug discovery implementation layer.

This module turns DrugMind from a collection of isolated drug-discovery tools
into a project-centric capability platform:

- capability registry: what AI drug-discovery abilities exist
- implementation blueprints: how a project should progress by phase
- durable executions: what has already been analyzed and delivered
- Second Me sync hooks: how capability outputs propagate to external personas
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from drug_modeling.admet_bridge import ADMETBridge
from integrations import BlatantWhyAdapter, MediPharmaAdapter

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryCapability:
    """A reusable drug-discovery capability."""

    capability_id: str
    name: str
    category: str
    description: str
    stage_ids: list[str] = field(default_factory=list)
    required_inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    recommended_agents: list[str] = field(default_factory=list)
    related_skills: list[str] = field(default_factory=list)
    tool_ids: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


@dataclass
class ImplementationPhase:
    """A phase in the project implementation blueprint."""

    phase_id: str
    name: str
    description: str
    objective: str
    default_capabilities: list[str] = field(default_factory=list)
    exit_criteria: list[str] = field(default_factory=list)
    recommended_workflows: list[str] = field(default_factory=list)
    success_metrics: list[str] = field(default_factory=list)


@dataclass
class ImplementationBlueprint:
    """Defines how a drug discovery project should be implemented."""

    blueprint_id: str
    name: str
    description: str
    phases: list[ImplementationPhase] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        self.phases = [
            phase if isinstance(phase, ImplementationPhase) else ImplementationPhase(**phase)
            for phase in self.phases
        ]


@dataclass
class ProjectImplementationState:
    """Durable implementation state for one project."""

    project_id: str
    blueprint_id: str
    current_phase_id: str
    active_capabilities: list[str] = field(default_factory=list)
    phase_history: list[dict] = field(default_factory=list)
    last_capability_execution_ids: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


@dataclass
class CapabilityExecution:
    """One executed capability artifact."""

    execution_id: str
    project_id: str
    capability_id: str
    capability_name: str
    status: str = "completed"
    summary: str = ""
    structured_output: dict[str, Any] = field(default_factory=dict)
    related_agents: list[str] = field(default_factory=list)
    related_compounds: list[str] = field(default_factory=list)
    triggered_by: str = ""
    second_me_sync: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.execution_id:
            self.execution_id = f"cap_{uuid.uuid4().hex[:10]}"
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


class DrugDiscoveryImplementationHub:
    """Owns project implementation blueprints and AI drug-discovery capabilities."""

    STAGE_TO_PHASE = {
        "target_id": "phase.target_assessment",
        "screening": "phase.hit_generation",
        "hit_to_lead": "phase.hit_to_lead",
        "lead_opt": "phase.lead_optimization",
        "candidate": "phase.candidate_selection",
        "preclinical": "phase.candidate_selection",
        "clinical": "phase.translational_execution",
    }

    DEFAULT_BLUEPRINT_ID = "blueprint.small_molecule_ai_discovery"
    BIOLOGICS_BLUEPRINT_ID = "blueprint.biologics_ai_discovery"

    def __init__(
        self,
        data_dir: str = "./drugmind_data/platform/drug_discovery",
        *,
        twin_engine=None,
        agent_registry=None,
        skill_registry=None,
        tool_registry=None,
        kanban=None,
        workspace_store=None,
        project_memory=None,
        compound_tracker=None,
        decision_logger=None,
        second_me=None,
        second_me_bindings=None,
        blatant_why_adapter=None,
        medi_pharma_adapter=None,
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._capabilities_path = self.data_dir / "capabilities.json"
        self._blueprints_path = self.data_dir / "blueprints.json"
        self._states_path = self.data_dir / "implementation_states.json"
        self._executions_path = self.data_dir / "capability_executions.json"
        self.capabilities: dict[str, DiscoveryCapability] = {}
        self.blueprints: dict[str, ImplementationBlueprint] = {}
        self.states: dict[str, ProjectImplementationState] = {}
        self.executions: dict[str, CapabilityExecution] = {}
        self.attach_runtime(
            twin_engine=twin_engine,
            agent_registry=agent_registry,
            skill_registry=skill_registry,
            tool_registry=tool_registry,
            kanban=kanban,
            workspace_store=workspace_store,
            project_memory=project_memory,
            compound_tracker=compound_tracker,
            decision_logger=decision_logger,
            second_me=second_me,
            second_me_bindings=second_me_bindings,
            blatant_why_adapter=blatant_why_adapter,
            medi_pharma_adapter=medi_pharma_adapter,
        )
        self._load()
        self._seed_capabilities()
        self._seed_blueprints()
        self._normalize_states()

    def attach_runtime(
        self,
        *,
        twin_engine=None,
        agent_registry=None,
        skill_registry=None,
        tool_registry=None,
        kanban=None,
        workspace_store=None,
        project_memory=None,
        compound_tracker=None,
        decision_logger=None,
        second_me=None,
        second_me_bindings=None,
        blatant_why_adapter=None,
        medi_pharma_adapter=None,
    ):
        self.twin_engine = twin_engine
        self.agent_registry = agent_registry
        self.skill_registry = skill_registry
        self.tool_registry = tool_registry
        self.kanban = kanban
        self.workspace_store = workspace_store
        self.project_memory = project_memory
        self.compound_tracker = compound_tracker
        self.decision_logger = decision_logger
        self.second_me = second_me
        self.second_me_bindings = second_me_bindings
        self.blatant_why_adapter = blatant_why_adapter or BlatantWhyAdapter()
        self.medi_pharma_adapter = medi_pharma_adapter or MediPharmaAdapter()
        return self

    def list_capabilities(self, stage_id: str = "", category: str = "") -> list[dict]:
        capabilities = list(self.capabilities.values())
        if stage_id:
            capabilities = [cap for cap in capabilities if stage_id in cap.stage_ids]
        if category:
            capabilities = [cap for cap in capabilities if cap.category == category]
        capabilities.sort(key=lambda item: (item.category, item.name))
        return [asdict(item) for item in capabilities]

    def get_capability(self, capability_id: str) -> Optional[dict]:
        capability = self.capabilities.get(capability_id)
        return asdict(capability) if capability else None

    def count_capabilities(self) -> int:
        return len(self.capabilities)

    def list_blueprints(self) -> list[dict]:
        blueprints = list(self.blueprints.values())
        blueprints.sort(key=lambda item: item.name)
        return [asdict(item) for item in blueprints]

    def get_blueprint(self, blueprint_id: str) -> Optional[dict]:
        blueprint = self.blueprints.get(blueprint_id)
        return asdict(blueprint) if blueprint else None

    def list_executions(self, project_id: str = "", capability_id: str = "", limit: int = 50) -> list[dict]:
        executions = list(self.executions.values())
        if project_id:
            executions = [item for item in executions if item.project_id == project_id]
        if capability_id:
            executions = [item for item in executions if item.capability_id == capability_id]
        executions.sort(key=lambda item: item.updated_at or item.created_at, reverse=True)
        return [asdict(item) for item in executions[:limit]]

    def count_executions(self, project_id: str = "") -> int:
        if not project_id:
            return len(self.executions)
        return len([item for item in self.executions.values() if item.project_id == project_id])

    def describe(self) -> dict:
        return {
            "capabilities_count": self.count_capabilities(),
            "blueprints_count": len(self.blueprints),
            "executions_count": len(self.executions),
            "categories": sorted({cap.category for cap in self.capabilities.values()}),
            "blueprints": [blueprint["blueprint_id"] for blueprint in self.list_blueprints()],
            "blatant_why": self.blatant_why_adapter.describe() if self.blatant_why_adapter else {},
            "medi_pharma": self.medi_pharma_adapter.describe() if self.medi_pharma_adapter else {},
        }

    def bootstrap_project(
        self,
        project_id: str,
        *,
        blueprint_id: str = "",
        activated_by: str = "",
        note: str = "",
    ) -> dict:
        project = self._require_project(project_id)
        blueprint_id = blueprint_id or self._default_blueprint_for_project(project)
        blueprint = self.blueprints.get(blueprint_id)
        if not blueprint:
            raise ValueError(f"未知 implementation blueprint: {blueprint_id}")

        phase_id = self._phase_for_project(project)
        phase = self._get_phase(blueprint, phase_id)
        now = datetime.now().isoformat()
        state = self.states.get(project_id)
        if not state:
            state = ProjectImplementationState(
                project_id=project_id,
                blueprint_id=blueprint_id,
                current_phase_id=phase_id,
                active_capabilities=list(phase.default_capabilities),
                phase_history=[
                    {
                        "phase_id": phase_id,
                        "entered_at": now,
                        "reason": "project_bootstrap",
                        "activated_by": activated_by,
                    }
                ],
                notes=[note] if note else [],
            )
            self.states[project_id] = state
        else:
            changed = False
            if state.blueprint_id != blueprint_id:
                state.blueprint_id = blueprint_id
                changed = True
            if state.current_phase_id != phase_id:
                state.current_phase_id = phase_id
                state.phase_history.append(
                    {
                        "phase_id": phase_id,
                        "entered_at": now,
                        "reason": "project_stage_change",
                        "activated_by": activated_by,
                    }
                )
                changed = True
            if phase.default_capabilities != state.active_capabilities:
                state.active_capabilities = list(phase.default_capabilities)
                changed = True
            if note:
                state.notes.append(note)
                changed = True
            if changed:
                state.updated_at = now
        self._save_states()
        self._sync_workspace_implementation(project_id, state, phase)
        self._record_bootstrap_memory(project, blueprint, phase, activated_by=activated_by)
        return self.get_project_implementation(project_id)

    def get_project_state(self, project_id: str) -> Optional[dict]:
        state = self.states.get(project_id)
        return asdict(state) if state else None

    def get_project_implementation(self, project_id: str) -> dict:
        project = self._require_project(project_id)
        state = self.states.get(project_id)
        if not state:
            return self.bootstrap_project(project_id)
        phase_id = self._phase_for_project(project)
        if phase_id != state.current_phase_id:
            return self.bootstrap_project(project_id, blueprint_id=state.blueprint_id)

        blueprint = self.blueprints[state.blueprint_id]
        phase = self._get_phase(blueprint, state.current_phase_id)
        compounds = self._build_compound_panel(project_id, limit=12)
        executions = self.list_executions(project_id=project_id, limit=12)
        available_capability_ids = self._visible_capability_ids(state, phase)
        return {
            "project": project,
            "state": asdict(state),
            "blueprint": asdict(blueprint),
            "current_phase": asdict(phase),
            "phase_index": next((index for index, item in enumerate(blueprint.phases) if item.phase_id == phase.phase_id), 0),
            "compound_panel": compounds,
            "recent_executions": executions,
            "available_capabilities": [
                asdict(self.capabilities[capability_id])
                for capability_id in available_capability_ids
                if capability_id in self.capabilities
            ],
            "blatant_why": self.blatant_why_adapter.build_dmta_blueprint(project=project) if self.blatant_why_adapter else {},
            "medi_pharma": self.medi_pharma_adapter.describe() if self.medi_pharma_adapter else {},
        }

    def execute_capability(
        self,
        project_id: str,
        capability_id: str,
        *,
        input_payload: Optional[dict] = None,
        triggered_by: str = "",
        sync_to_second_me: bool = False,
    ) -> dict:
        project = self._require_project(project_id)
        capability = self.capabilities.get(capability_id)
        if not capability:
            raise ValueError(f"未知 capability: {capability_id}")
        if project_id not in self.states:
            self.bootstrap_project(project_id)

        input_payload = input_payload or {}
        compounds = self._build_compound_panel(
            project_id,
            compound_ids=input_payload.get("compound_ids", []),
            limit=int(input_payload.get("compound_limit", 24)),
        )
        handler = getattr(self, f"_execute_{capability_id.split('.')[-1]}", None)
        if not handler:
            raise ValueError(f"capability 暂无执行器: {capability_id}")

        result = handler(project, capability, compounds, input_payload)
        execution = CapabilityExecution(
            execution_id="",
            project_id=project_id,
            capability_id=capability_id,
            capability_name=capability.name,
            status=result.get("status", "completed"),
            summary=result.get("summary", ""),
            structured_output=result.get("structured_output", {}),
            related_agents=result.get("related_agents", []),
            related_compounds=result.get("related_compounds", []),
            triggered_by=triggered_by,
        )

        self._record_execution_memory(project_id, capability, execution)
        self.executions[execution.execution_id] = execution
        state = self.states[project_id]
        if execution.execution_id not in state.last_capability_execution_ids:
            state.last_capability_execution_ids.append(execution.execution_id)
            state.last_capability_execution_ids = state.last_capability_execution_ids[-20:]
        state.updated_at = datetime.now().isoformat()
        self._save_states()
        self._save_executions()
        self._sync_workspace_execution(project_id, execution.execution_id)

        if sync_to_second_me or capability_id == "capability.second_me_program_sync":
            execution.second_me_sync = self._sync_capability_to_second_me(
                project_id=project_id,
                execution=execution,
                input_payload=input_payload,
            )
            execution.updated_at = datetime.now().isoformat()
            self._save_executions()

        return asdict(execution)

    def _execute_target_landscape(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        target = project.get("target") or "未定义靶点"
        disease = project.get("disease") or "未定义适应症"
        hypotheses = [
            f"验证 {target} 在 {disease} 中是否具有明确的人体遗传学或患者分层证据。",
            f"确认 {target} 的调控方向、成药方式和安全窗口是否可解释。",
            f"把靶点生物学、竞争态势和项目资源约束放到同一张 go/no-go 表里。",
        ]
        experiments = [
            "建立 target engagement / pathway modulation readout",
            "补齐 disease-relevant cellular model 和阳性对照",
            "定义最小成药性门槛：选择性、暴露、安全窗口、转化标志物",
        ]
        agent_views = self._collect_agent_views(
            capability,
            project,
            prompt=(
                f"请围绕靶点 {target} 在 {disease} 场景下的项目启动价值，"
                "给出机制、证据、风险和下一步实验建议。"
            ),
            limit=2,
        )
        summary = (
            f"{target} / {disease} 的项目实施应先锁定机制证据、可测 readout 和最小成药门槛，"
            "再进入 hit generation。"
        )
        return {
            "summary": summary,
            "structured_output": {
                "target": target,
                "disease": disease,
                "priority_hypotheses": hypotheses,
                "recommended_experiments": experiments,
                "open_questions": [
                    "人体或患者层面的因果证据是否足够强？",
                    "调控该靶点后最容易观测到的药效 readout 是什么？",
                    "是否存在明确的安全性/组织选择性风险？",
                ],
                "agent_views": agent_views,
            },
            "related_agents": [view["agent_id"] for view in agent_views],
            "related_compounds": [],
        }

    def _execute_structural_research(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        modality = project.get("modality", "small_molecule")
        if self.blatant_why_adapter:
            research_bundle = self.blatant_why_adapter.run_target_research(
                project=project,
                modality=input_payload.get("modality") or modality,
                organism_id=int(input_payload.get("organism_id", 9606)),
                pdb_rows=int(input_payload.get("pdb_rows", 6)),
                sabdab_limit=int(input_payload.get("sabdab_limit", 6)),
            )
        else:
            research_bundle = {}
        pdb_count = len(((research_bundle.get("pdb") or {}).get("structures")) or [])
        sabdab_count = int(((research_bundle.get("sabdab") or {}).get("count")) or 0)
        accession = (((research_bundle.get("uniprot") or {}).get("primary_entry")) or {}).get("primary_accession", "")
        summary = (
            f"已完成 {project.get('target') or project.get('name')} 的结构研究检索，"
            f"UniProt={accession or 'N/A'}，PDB={pdb_count}，SAbDab={sabdab_count}。"
        )
        return {
            "summary": summary,
            "structured_output": research_bundle,
            "related_agents": capability.recommended_agents[:2],
            "related_compounds": [],
        }

    def _execute_assay_strategy(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        target = project.get("target") or "当前靶点"
        assay_stack = [
            {"tier": "primary", "assay": f"{target} biochemical potency assay", "goal": "确认 on-target potency"},
            {"tier": "secondary", "assay": "cell-based functional assay", "goal": "验证 pathway modulation"},
            {"tier": "secondary", "assay": "selectivity / counter-screen panel", "goal": "暴露早期 off-target 风险"},
            {"tier": "translational", "assay": "PK/PD bridge biomarker", "goal": "连接体外结果与体内读数"},
        ]
        agent_views = self._collect_agent_views(
            capability,
            project,
            prompt="请给出 target-to-assay 的分层实验策略、readout 和数据质量要求。",
            limit=2,
        )
        return {
            "summary": "建议把 assay 体系拆成 primary / secondary / translational 三层，并提前定义数据质量门槛。",
            "structured_output": {
                "assay_stack": assay_stack,
                "data_schema": [
                    "batch_id",
                    "compound_id",
                    "concentration",
                    "readout_value",
                    "control_window",
                    "replicate_cv",
                ],
                "quality_gates": [
                    "primary assay 必须有稳定阳性/阴性对照",
                    "cell assay 必须记录 target expression / cell health",
                    "每轮筛选都需要可追溯 batch 元数据",
                ],
                "agent_views": agent_views,
            },
            "related_agents": [view["agent_id"] for view in agent_views],
            "related_compounds": [],
        }

    def _execute_biologics_design_campaign(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        if not self.blatant_why_adapter:
            return {
                "status": "unavailable",
                "summary": "BY biologics adapter unavailable.",
                "structured_output": {},
                "related_agents": [],
                "related_compounds": [],
            }
        modality = input_payload.get("modality") or project.get("modality", "nanobody")
        campaign = self.blatant_why_adapter.biologics_pipeline.build_campaign(
            project=project,
            modality=modality,
            scaffolds=input_payload.get("scaffolds"),
            seeds=int(input_payload.get("seeds", 8)),
            designs_per_seed=int(input_payload.get("designs_per_seed", 8)),
            complexity=input_payload.get("complexity", "standard"),
        )
        job_submission = None
        if input_payload.get("submit_job") or input_payload.get("tamarind_settings"):
            settings = input_payload.get("tamarind_settings") or {
                "jobType": input_payload.get("job_type", f"{modality}_design"),
                "settings": {
                    "target": project.get("target", ""),
                    "modality": modality,
                    "scaffolds": campaign.get("scaffolds", []),
                    "seeds": int(input_payload.get("seeds", 8)),
                    "designsPerSeed": int(input_payload.get("designs_per_seed", 8)),
                    "complexity": input_payload.get("complexity", "standard"),
                    **(input_payload.get("job_settings", {}) or {}),
                },
            }
            job_submission = self.blatant_why_adapter.submit_tamarind_job(
                project=project,
                modality=modality,
                settings=settings,
                wait_for_completion=bool(input_payload.get("wait_for_completion", False)),
                poll_interval_seconds=int(input_payload.get("poll_interval_seconds", 20)),
                timeout_seconds=int(input_payload.get("timeout_seconds", 900)),
            )
        return {
            "summary": (
                "已生成 BY 风格 biologics campaign，包含 research→design→screen→rank 和 Tamarind 估算。"
                if not job_submission
                else "已生成 BY 风格 biologics campaign，并向 Tamarind 提交了真实 job。"
            ),
            "structured_output": {
                "campaign": campaign,
                "tamarind_job": job_submission,
            },
            "related_agents": capability.recommended_agents[:2],
            "related_compounds": [],
        }

    def _execute_hit_triage(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        if not compounds:
            return {
                "status": "insufficient_context",
                "summary": "当前项目还没有化合物数据，无法执行 hit triage。",
                "structured_output": {
                    "gaps": [
                        "至少录入一批 hit/lead compounds",
                        "补充 activity_pIC50 或项目优先级字段",
                    ]
                },
                "related_agents": [],
                "related_compounds": [],
            }

        ranked = sorted(compounds, key=lambda item: item.get("composite_score", 0), reverse=True)
        top_hits = ranked[: min(5, len(ranked))]
        summary = (
            f"已完成 {len(compounds)} 个化合物的 triage，"
            f"优先建议跟进 {', '.join(item['compound_id'] for item in top_hits[:3])}。"
        )
        return {
            "summary": summary,
            "structured_output": {
                "top_hits": top_hits,
                "decision_rules": [
                    "先看活性和成药性，不把明显 developability liabilities 带入后续周期",
                    "优先保留 potency / QED / Lipinski balance 更好的系列",
                    "对高活性但高风险分子，单独列成 rescue bucket",
                ],
                "rescue_bucket": [
                    item for item in ranked
                    if item.get("composite_score", 0) < top_hits[-1].get("composite_score", 0)
                    and item.get("activity_pIC50", 0) >= 6.0
                ][:3],
            },
            "related_agents": capability.recommended_agents[:2],
            "related_compounds": [item["compound_id"] for item in top_hits],
        }

    def _execute_series_design(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        if not compounds:
            return {
                "status": "insufficient_context",
                "summary": "没有 compound series 可用于 series design。",
                "structured_output": {"gaps": ["请先导入一组 hit-to-lead 或 lead-opt compounds"]},
                "related_agents": [],
                "related_compounds": [],
            }

        avg_logp = round(sum(item.get("logp", 0) for item in compounds) / len(compounds), 2)
        avg_mw = round(sum(item.get("mw", 0) for item in compounds) / len(compounds), 1)
        chemistry_moves: list[str] = []
        if avg_logp > 3.5:
            chemistry_moves.append("降低整体脂溶性，优先考虑减小疏水取代基或加入弱极性片段。")
        if avg_mw > 480:
            chemistry_moves.append("控制分子量增长，避免在 lead optimization 阶段过早进入高 MW 区间。")
        if not chemistry_moves:
            chemistry_moves.append("当前 series 的理化空间尚可，优先围绕 SAR 热点做定点探索。")
        chemistry_moves.append("保留活性核心，同时针对 ADMET liabilities 做定向 rescue。")

        agent_views = self._collect_agent_views(
            capability,
            project,
            prompt="请基于当前 compound series 给出下一轮化学设计方向、SAR 假设和保留/放弃逻辑。",
            limit=2,
        )
        top_compounds = sorted(compounds, key=lambda item: item.get("composite_score", 0), reverse=True)[:4]
        return {
            "summary": "已形成下一轮 series design 方向，建议围绕理化平衡和 SAR 热点做小步快跑式优化。",
            "structured_output": {
                "series_snapshot": {
                    "compounds": len(compounds),
                    "avg_logp": avg_logp,
                    "avg_mw": avg_mw,
                },
                "chemistry_moves": chemistry_moves,
                "priority_compounds": top_compounds,
                "agent_views": agent_views,
            },
            "related_agents": [view["agent_id"] for view in agent_views],
            "related_compounds": [item["compound_id"] for item in top_compounds],
        }

    def _execute_admet_risk(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        if not compounds:
            return {
                "status": "insufficient_context",
                "summary": "没有化合物可供 ADMET 风险评估。",
                "structured_output": {"gaps": ["请先录入 compounds"]},
                "related_agents": [],
                "related_compounds": [],
            }

        high_risk = []
        medium_risk = []
        for item in compounds:
            if item.get("lipinski_violations", 0) >= 2 or item.get("logp", 0) > 4.5 or item.get("qed", 1) < 0.3:
                high_risk.append(item)
            elif item.get("lipinski_violations", 0) == 1 or item.get("qed", 1) < 0.45:
                medium_risk.append(item)

        mitigations = [
            "高 logP 系列优先做极性修饰或清理疏水尾部",
            "高 MW / 多违规系列尽量减少不必要的刚性取代",
            "对 rescue compounds 单独建立暴露-活性权衡表",
        ]
        return {
            "summary": f"ADMET 风险评估完成，高风险 {len(high_risk)} 个，中风险 {len(medium_risk)} 个。",
            "structured_output": {
                "high_risk_compounds": high_risk[:6],
                "medium_risk_compounds": medium_risk[:6],
                "mitigation_actions": mitigations,
                "portfolio_signal": "需要把 developability 风险前置到化学设计循环中。",
            },
            "related_agents": capability.recommended_agents[:1],
            "related_compounds": [item["compound_id"] for item in high_risk[:6] + medium_risk[:4]],
        }

    def _execute_dmta_screening_ranking(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        if not compounds:
            return {
                "status": "insufficient_context",
                "summary": "没有 compound series，无法运行 DMTA screening。",
                "structured_output": {"gaps": ["请先添加 compounds 和基础活性数据"]},
                "related_agents": [],
                "related_compounds": [],
            }
        bridge_result = self.blatant_why_adapter.run_small_molecule_screening(
            project=project,
            compounds=compounds,
        ) if self.blatant_why_adapter else {}
        shortlist = bridge_result.get("screening", {}).get("shortlist", [])
        return {
            "summary": (
                f"已完成 DMTA screening，shortlist {len(shortlist)} 个，"
                f"当前 gate = {bridge_result.get('campaign_recommendation', {}).get('gate', 'N/A')}。"
            ),
            "structured_output": bridge_result,
            "related_agents": capability.recommended_agents[:2],
            "related_compounds": [item["compound_id"] for item in shortlist[:6]],
        }

    def _execute_biomarker_strategy(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        target = project.get("target") or "当前靶点"
        disease = project.get("disease") or "目标适应症"
        agent_views = self._collect_agent_views(
            capability,
            project,
            prompt=f"请围绕 {target} / {disease} 给出分层、生物标志物和转化 readout 方案。",
            limit=2,
        )
        return {
            "summary": "建议把 biomarker strategy 拆成 target engagement、pathway modulation 和 patient stratification 三层。",
            "structured_output": {
                "biomarker_layers": [
                    "target engagement marker",
                    "pathway modulation marker",
                    "patient stratification marker",
                ],
                "decision_points": [
                    "哪些 biomarker 能在体外、体内、患者样本中连续追踪？",
                    "哪些 readout 可直接作为 go/no-go gate？",
                ],
                "agent_views": agent_views,
            },
            "related_agents": [view["agent_id"] for view in agent_views],
            "related_compounds": [],
        }

    def _execute_translational_plan(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        top_compounds = sorted(compounds, key=lambda item: item.get("composite_score", 0), reverse=True)[:3]
        agent_views = self._collect_agent_views(
            capability,
            project,
            prompt="请给出从 lead/candidate 到 preclinical evidence package 的转化实施路径。",
            limit=2,
        )
        return {
            "summary": "已生成 translational plan，建议围绕 PK/PD、疾病模型和 biomarker 读数建立一条连续证据链。",
            "structured_output": {
                "milestones": [
                    "锁定候选化合物及 backup compounds",
                    "建立 PK/PD bridge 和剂量-暴露-药效关系",
                    "在疾病相关模型里验证 efficacy / safety window",
                    "形成 candidate nomination package",
                ],
                "priority_compounds": top_compounds,
                "agent_views": agent_views,
            },
            "related_agents": [view["agent_id"] for view in agent_views],
            "related_compounds": [item["compound_id"] for item in top_compounds],
        }

    def _execute_candidate_nomination(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        if not compounds:
            return {
                "status": "insufficient_context",
                "summary": "候选提名需要 compound panel，目前项目为空。",
                "structured_output": {"gate": "NO-GO", "reason": "no compounds"},
                "related_agents": [],
                "related_compounds": [],
            }

        ranked = sorted(compounds, key=lambda item: item.get("composite_score", 0), reverse=True)
        lead = ranked[0]
        gate = "GO" if lead.get("composite_score", 0) >= 90 else "CONDITIONAL" if lead.get("composite_score", 0) >= 70 else "NO-GO"
        gate_rationale = [
            f"top compound = {lead['compound_id']}",
            f"activity_pIC50 = {lead.get('activity_pIC50', 0)}",
            f"qed = {lead.get('qed', 0)}",
            f"lipinski_violations = {lead.get('lipinski_violations', 0)}",
        ]
        return {
            "summary": f"候选提名评估完成，当前建议 {gate}。",
            "structured_output": {
                "gate": gate,
                "lead_candidate": lead,
                "backup_candidates": ranked[1:4],
                "gate_rationale": gate_rationale,
                "required_followups": [
                    "确认暴露-药效关系",
                    "补齐关键安全性/选择性证据",
                    "形成完整 nomination deck",
                ],
            },
            "related_agents": capability.recommended_agents[:2],
            "related_compounds": [item["compound_id"] for item in ranked[:4]],
        }

    def _execute_second_me_program_sync(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        implementation = self.get_project_implementation(project["project_id"])
        by_payload = self.blatant_why_adapter.build_second_me_payload(
            project=project,
            implementation=implementation,
            executions=self.list_executions(project_id=project["project_id"], limit=8),
        ) if self.blatant_why_adapter else {}
        return {
            "summary": "已准备项目实施蓝图与能力执行摘要，可同步到 Second Me persona。",
            "structured_output": {
                "current_phase": implementation["current_phase"]["name"],
                "active_capabilities": implementation["state"]["active_capabilities"],
                "recent_executions": [
                    {
                        "capability_id": item["capability_id"],
                        "summary": item["summary"],
                    }
                    for item in implementation["recent_executions"][:5]
                ],
                "by_dmta_payload": by_payload,
            },
            "related_agents": capability.recommended_agents[:1],
            "related_compounds": [item["compound_id"] for item in compounds[:3]],
        }

    def _execute_campaign_memory(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        implementation = self.get_project_implementation(project["project_id"])
        recent_executions = self.list_executions(project_id=project["project_id"], limit=12)
        memory_summary = {
            "project_id": project["project_id"],
            "current_phase": implementation["current_phase"]["name"],
            "active_capabilities": implementation["state"]["active_capabilities"],
            "lessons": [
                execution["summary"]
                for execution in recent_executions[:5]
                if execution.get("summary")
            ],
            "second_me_payload": self.blatant_why_adapter.build_second_me_payload(
                project=project,
                implementation=implementation,
                executions=recent_executions,
            ) if self.blatant_why_adapter else {},
        }
        return {
            "summary": "已生成跨 workflow / capability / Second Me 的 campaign memory 摘要。",
            "structured_output": memory_summary,
            "related_agents": capability.recommended_agents[:2],
            "related_compounds": [item["compound_id"] for item in compounds[:4]],
        }

    def _execute_medi_pharma_target_discovery(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        result = self.medi_pharma_adapter.discover_targets(project=project, input_payload=input_payload)
        response = result.get("response", {})
        top_targets = response.get("top_targets", []) if isinstance(response, dict) else []
        target_labels = [item.get("gene_symbol", "") for item in top_targets[:3] if item.get("gene_symbol")]
        summary = (
            f"MediPharma 靶点发现完成，Top targets: {', '.join(target_labels)}。"
            if result.get("status") == "ready"
            else result.get("note") or result.get("error") or "MediPharma 靶点发现未完成。"
        )
        return {
            "status": "completed" if result.get("status") == "ready" else result.get("status", "error"),
            "summary": summary,
            "structured_output": result,
            "related_agents": capability.recommended_agents[:2],
            "related_compounds": [],
        }

    def _execute_medi_pharma_virtual_screening(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        result = self.medi_pharma_adapter.run_screening(project=project, compounds=compounds, input_payload=input_payload)
        response = result.get("response", {})
        top_candidates = response.get("top_candidates", []) if isinstance(response, dict) else []
        summary = (
            f"MediPharma 虚拟筛选完成，hits={response.get('hits_found', 0)}，top_candidates={len(top_candidates)}。"
            if result.get("status") == "ready"
            else result.get("note") or result.get("error") or "MediPharma 虚拟筛选未完成。"
        )
        return {
            "status": "completed" if result.get("status") == "ready" else result.get("status", "error"),
            "summary": summary,
            "structured_output": result,
            "related_agents": capability.recommended_agents[:2],
            "related_compounds": [item.get("compound_id", "") for item in compounds[:5] if item.get("compound_id")],
        }

    def _execute_medi_pharma_molecule_generation(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        result = self.medi_pharma_adapter.generate(project=project, input_payload=input_payload)
        response = result.get("response", {})
        summary = (
            f"MediPharma 分子生成完成，valid={response.get('valid_molecules', 0)} / total={response.get('total_generated', 0)}。"
            if result.get("status") == "ready"
            else result.get("note") or result.get("error") or "MediPharma 分子生成未完成。"
        )
        return {
            "status": "completed" if result.get("status") == "ready" else result.get("status", "error"),
            "summary": summary,
            "structured_output": result,
            "related_agents": capability.recommended_agents[:2],
            "related_compounds": [],
        }

    def _execute_medi_pharma_admet_batch(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        result = self.medi_pharma_adapter.batch_predict_admet(compounds=compounds, input_payload=input_payload)
        response = result.get("response", {})
        rows = response.get("results", []) if isinstance(response, dict) else []
        pass_count = len([row for row in rows if row.get("pass_filter")])
        summary = (
            f"MediPharma ADMET 批量预测完成，pass_filter={pass_count}/{len(rows)}。"
            if result.get("status") == "ready"
            else result.get("note") or result.get("error") or "MediPharma ADMET 批量预测未完成。"
        )
        return {
            "status": "completed" if result.get("status") == "ready" else result.get("status", "error"),
            "summary": summary,
            "structured_output": result,
            "related_agents": capability.recommended_agents[:1],
            "related_compounds": [item.get("compound_id", "") for item in compounds[:8] if item.get("compound_id")],
        }

    def _execute_medi_pharma_lead_optimization(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        result = self.medi_pharma_adapter.optimize(compounds=compounds, input_payload=input_payload)
        response = result.get("response", {})
        summary = (
            f"MediPharma 先导优化完成，candidates_found={response.get('candidates_found', 0)}。"
            if result.get("status") == "ready"
            else result.get("note") or result.get("error") or "MediPharma 先导优化未完成。"
        )
        return {
            "status": "completed" if result.get("status") == "ready" else result.get("status", "error"),
            "summary": summary,
            "structured_output": result,
            "related_agents": capability.recommended_agents[:2],
            "related_compounds": [item.get("compound_id", "") for item in compounds[:5] if item.get("compound_id")],
        }

    def _execute_medi_pharma_pipeline_run(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        result = self.medi_pharma_adapter.run_pipeline(project=project, input_payload=input_payload)
        response = result.get("response", {})
        stages = response.get("stages_completed", []) if isinstance(response, dict) else []
        final_candidates = response.get("final_candidates", []) if isinstance(response, dict) else []
        summary = (
            f"MediPharma 全流水线完成，stages={len(stages)}，final_candidates={len(final_candidates)}。"
            if result.get("status") == "ready"
            else result.get("note") or result.get("error") or "MediPharma 全流水线未完成。"
        )
        return {
            "status": "completed" if result.get("status") == "ready" else result.get("status", "error"),
            "summary": summary,
            "structured_output": result,
            "related_agents": capability.recommended_agents[:2],
            "related_compounds": [item.get("compound_id", "") for item in compounds[:5] if item.get("compound_id")],
        }

    def _execute_medi_pharma_knowledge_report(
        self,
        project: dict,
        capability: DiscoveryCapability,
        compounds: list[dict],
        input_payload: dict,
    ) -> dict:
        result = self.medi_pharma_adapter.knowledge_report(project=project, input_payload=input_payload)
        response = result.get("response", {})
        insights = response.get("key_insights", []) if isinstance(response, dict) else []
        summary = (
            f"MediPharma 知识引擎报告完成，key_insights={len(insights)}。"
            if result.get("status") == "ready"
            else result.get("note") or result.get("error") or "MediPharma 知识引擎报告未完成。"
        )
        return {
            "status": "completed" if result.get("status") == "ready" else result.get("status", "error"),
            "summary": summary,
            "structured_output": result,
            "related_agents": capability.recommended_agents[:2],
            "related_compounds": [],
        }

    def _collect_agent_views(self, capability: DiscoveryCapability, project: dict, *, prompt: str, limit: int = 2) -> list[dict]:
        if not self.twin_engine or not self.agent_registry:
            return []
        views = []
        context = self._build_agent_context(project)
        for agent_id in capability.recommended_agents[:limit]:
            agent = self.agent_registry.get_agent(agent_id)
            if not agent:
                continue
            response = self.twin_engine.ask_agent(
                agent_id=agent_id,
                question=prompt,
                context=context,
                agent_profile=agent,
            )
            views.append(
                {
                    "agent_id": agent_id,
                    "name": response.name,
                    "message": response.message,
                    "confidence": response.confidence,
                }
            )
        return views

    def _build_agent_context(self, project: dict) -> str:
        state = self.states.get(project["project_id"])
        workspace = self.workspace_store.get_workspace(project["project_id"]) if self.workspace_store else {}
        return (
            f"Project={project.get('name', project['project_id'])}\n"
            f"Target={project.get('target', 'N/A')} | Disease={project.get('disease', 'N/A')} | Stage={project.get('stage', 'N/A')}\n"
            f"Phase={state.current_phase_id if state else 'N/A'}\n"
            f"Active capabilities={', '.join((state.active_capabilities if state else [])[:6])}\n"
            f"Workspace agents={', '.join((workspace or {}).get('default_agents', [])[:6])}"
        )

    def _build_compound_panel(
        self,
        project_id: str,
        *,
        compound_ids: Optional[list[str]] = None,
        limit: int = 24,
    ) -> list[dict]:
        if not self.compound_tracker:
            return []
        compounds = self.compound_tracker.list_compounds(project_id=project_id)
        if compound_ids:
            compounds = [item for item in compounds if item["compound_id"] in set(compound_ids)]
        bridge = ADMETBridge()
        panel = []
        for item in compounds[:limit]:
            admet = bridge.predict(item.get("smiles", ""))
            activity = float(item.get("activity_pIC50") or 0)
            qed = float(admet.get("qed") or 0)
            lipinski = int(admet.get("lipinski_violations") or 0)
            logp = float(admet.get("logp") or 0)
            mw = float(admet.get("mw") or 0)
            composite_score = round(
                (activity * 12)
                + (qed * 40)
                - (lipinski * 15)
                - max(logp - 3.5, 0) * 7
                - max(mw - 480, 0) / 18,
                1,
            )
            panel.append(
                {
                    **item,
                    "mw": mw,
                    "logp": logp,
                    "qed": qed,
                    "tpsa": float(admet.get("tpsa") or 0),
                    "sa_score_local": float(admet.get("sa_score") or 0),
                    "lipinski_violations": lipinski,
                    "composite_score": composite_score,
                }
            )
        return panel

    def _sync_capability_to_second_me(
        self,
        *,
        project_id: str,
        execution: CapabilityExecution,
        input_payload: dict,
    ) -> dict:
        if not self.second_me or not self.second_me_bindings:
            return {"status": "skipped", "reason": "second_me_unavailable"}

        instance_id = input_payload.get("instance_id", "")
        binding = None
        if instance_id:
            matches = self.second_me_bindings.list_bindings(project_id=project_id, instance_id=instance_id)
            binding = matches[0] if matches else None
        if not binding:
            bindings = self.second_me_bindings.list_bindings(project_id=project_id)
            binding = bindings[0] if bindings else None
        if not binding:
            return {"status": "skipped", "reason": "no_second_me_binding"}

        project = self.kanban.get_project(project_id) if self.kanban else {}
        workspace = self.workspace_store.get_workspace(project_id) if self.workspace_store else {}
        memory_entries = self.project_memory.list_entries(project_id, limit=10) if self.project_memory else []
        decisions = self.decision_logger.get_decision_history(project_id=project_id)[:6] if self.decision_logger else []
        sync_result = self.second_me.sync_project_context(
            binding["instance_id"],
            project=project,
            workspace=workspace,
            memory_entries=memory_entries,
            decisions=decisions,
            workflow_run={},
            sync_note=input_payload.get(
                "sync_note",
                f"Capability sync: {execution.capability_name} / {execution.execution_id} / {execution.summary}",
            ),
        )
        share_url = self.second_me.get_share_url(binding["instance_id"])
        export_snapshot = self.second_me.export_for_second_me(binding["instance_id"])
        synced_binding = self.second_me_bindings.mark_synced(
            binding["binding_id"],
            summary=execution.summary,
            share_url=share_url,
            export_snapshot=export_snapshot,
        )
        return {
            "status": sync_result.get("status", "synced"),
            "instance_id": binding["instance_id"],
            "binding_id": binding["binding_id"],
            "share_url": share_url,
            "binding": synced_binding,
            "sync_result": sync_result,
        }

    def _sync_workspace_implementation(
        self,
        project_id: str,
        state: ProjectImplementationState,
        phase: ImplementationPhase,
    ):
        if not self.workspace_store:
            return
        enabled_capabilities = self._visible_capability_ids(state, phase)
        try:
            self.workspace_store.update_workspace(
                project_id,
                implementation_blueprint_id=state.blueprint_id,
                implementation_phase_id=state.current_phase_id,
                enabled_capabilities=enabled_capabilities,
            )
        except ValueError:
            self.workspace_store.ensure_workspace(
                project_id=project_id,
                name=project_id,
                enabled_capabilities=enabled_capabilities,
            )
            self.workspace_store.update_workspace(
                project_id,
                implementation_blueprint_id=state.blueprint_id,
                implementation_phase_id=state.current_phase_id,
                enabled_capabilities=enabled_capabilities,
            )

    def _sync_workspace_execution(self, project_id: str, execution_id: str):
        if not self.workspace_store:
            return
        self.workspace_store.link_capability_execution(project_id, execution_id)

    def _record_bootstrap_memory(
        self,
        project: dict,
        blueprint: ImplementationBlueprint,
        phase: ImplementationPhase,
        *,
        activated_by: str = "",
    ):
        if not self.project_memory:
            return
        self.project_memory.add_entry(
            project_id=project["project_id"],
            memory_type="implementation_bootstrap",
            title=f"Implementation bootstrap · {phase.name}",
            content=(
                f"Blueprint={blueprint.name}; phase={phase.name}; objective={phase.objective}; "
                f"capabilities={', '.join(phase.default_capabilities)}; activated_by={activated_by}"
            ),
            tags=["implementation", "bootstrap", phase.phase_id],
            source="drug_discovery.bootstrap_project",
            author_id=activated_by,
        )

    def _record_execution_memory(
        self,
        project_id: str,
        capability: DiscoveryCapability,
        execution: CapabilityExecution,
    ):
        if not self.project_memory:
            return
        content = json.dumps(execution.structured_output, ensure_ascii=False, indent=2)
        self.project_memory.add_entry(
            project_id=project_id,
            memory_type="capability_execution",
            title=f"{capability.name} · {execution.execution_id}",
            content=content if content and content != "{}" else execution.summary,
            tags=["capability", capability.capability_id, capability.category],
            source="drug_discovery.execute_capability",
            author_id=execution.triggered_by,
            related_agents=execution.related_agents,
            related_compounds=execution.related_compounds,
        )

    def _require_project(self, project_id: str) -> dict:
        if not self.kanban:
            raise ValueError("project board unavailable")
        project = self.kanban.get_project(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")
        return project

    def _default_blueprint_for_project(self, project: dict) -> str:
        modality = (project.get("modality") or "small_molecule").lower()
        if modality in {"biologics", "protein", "antibody", "nanobody"}:
            return self.BIOLOGICS_BLUEPRINT_ID
        return self.DEFAULT_BLUEPRINT_ID

    def _phase_for_project(self, project: dict) -> str:
        return self.STAGE_TO_PHASE.get(project.get("stage", ""), "phase.target_assessment")

    def _get_phase(self, blueprint: ImplementationBlueprint, phase_id: str) -> ImplementationPhase:
        for phase in blueprint.phases:
            if phase.phase_id == phase_id:
                return phase
        return blueprint.phases[0]

    def _visible_capability_ids(self, state: ProjectImplementationState, phase: ImplementationPhase) -> list[str]:
        return list(dict.fromkeys(list(phase.default_capabilities) + list(state.active_capabilities)))

    def _normalize_states(self):
        changed = False
        for project_id, state in self.states.items():
            blueprint = self.blueprints.get(state.blueprint_id)
            if not blueprint:
                state.blueprint_id = self.DEFAULT_BLUEPRINT_ID
                blueprint = self.blueprints[self.DEFAULT_BLUEPRINT_ID]
                changed = True
            phase = self._get_phase(blueprint, state.current_phase_id)
            if phase.phase_id != state.current_phase_id:
                state.current_phase_id = phase.phase_id
                changed = True
            merged_capabilities = self._visible_capability_ids(state, phase)
            if merged_capabilities != state.active_capabilities:
                state.active_capabilities = merged_capabilities
                changed = True
            if self.workspace_store:
                try:
                    self._sync_workspace_implementation(project_id, state, phase)
                except Exception:
                    pass
        if changed:
            self._save_states()

    def _seed_capabilities(self):
        defaults = [
            DiscoveryCapability(
                capability_id="capability.structural_research",
                name="Structural Research",
                category="biology",
                description="Use PDB, UniProt, SAbDab, and knowledge traces to frame target feasibility.",
                stage_ids=["target_id", "screening"],
                required_inputs=["target", "modality"],
                outputs=["target_structure_plan", "prior_art_summary"],
                recommended_agents=["agent.biologist", "agent.discovery_strategist"],
                related_skills=["skill.structural_research", "skill.target_evaluation"],
                tool_ids=["tool.by_mcp_bridge", "tool.project_memory"],
            ),
            DiscoveryCapability(
                capability_id="capability.target_landscape",
                name="Target Landscape",
                category="biology",
                description="Frame target rationale, evidence strength, and project-start questions.",
                stage_ids=["target_id"],
                required_inputs=["target", "disease"],
                outputs=["target_dossier", "open_questions"],
                recommended_agents=["agent.biologist", "agent.project_lead"],
                related_skills=["skill.target_evaluation", "skill.evidence_review"],
                tool_ids=["tool.project_memory"],
            ),
            DiscoveryCapability(
                capability_id="capability.assay_strategy",
                name="Assay Strategy",
                category="biology",
                description="Design a layered assay cascade and data contract for discovery decisions.",
                stage_ids=["target_id", "screening"],
                required_inputs=["target", "assay_context"],
                outputs=["assay_stack", "quality_gates"],
                recommended_agents=["agent.biologist", "agent.data_scientist"],
                related_skills=["skill.assay_strategy", "skill.evidence_review"],
                tool_ids=["tool.project_memory"],
            ),
            DiscoveryCapability(
                capability_id="capability.hit_triage",
                name="Hit Triage",
                category="chemistry",
                description="Rank current hits using activity and developability heuristics.",
                stage_ids=["screening", "hit_to_lead"],
                required_inputs=["compound_series"],
                outputs=["top_hits", "rescue_bucket"],
                recommended_agents=["agent.medicinal_chemist", "agent.project_lead"],
                related_skills=["skill.hit_triage", "skill.project_triage"],
                tool_ids=["tool.drugmind_admet", "tool.drugmind_compound"],
            ),
            DiscoveryCapability(
                capability_id="capability.series_design",
                name="Series Design",
                category="chemistry",
                description="Turn compound evidence into the next chemistry cycle.",
                stage_ids=["hit_to_lead", "lead_opt"],
                required_inputs=["compound_series", "constraints"],
                outputs=["chemistry_moves", "priority_compounds"],
                recommended_agents=["agent.medicinal_chemist", "agent.pharmacologist"],
                related_skills=["skill.series_design", "skill.lead_optimization"],
                tool_ids=["tool.drugmind_compound", "tool.project_memory"],
            ),
            DiscoveryCapability(
                capability_id="capability.admet_risk",
                name="ADMET Risk",
                category="dmpk",
                description="Surface developability liabilities early and turn them into action items.",
                stage_ids=["hit_to_lead", "lead_opt", "candidate"],
                required_inputs=["compound_series"],
                outputs=["high_risk_compounds", "mitigation_actions"],
                recommended_agents=["agent.pharmacologist"],
                related_skills=["skill.admet_assessment"],
                tool_ids=["tool.drugmind_admet", "tool.project_memory"],
            ),
            DiscoveryCapability(
                capability_id="capability.dmta_screening_ranking",
                name="DMTA Screening & Ranking",
                category="screening",
                description="Run BY-inspired attrition, shortlist, and Pareto ranking for small-molecule programs.",
                stage_ids=["screening", "hit_to_lead", "lead_opt"],
                required_inputs=["compound_series", "activity_table"],
                outputs=["shortlist", "pareto_front", "campaign_gate"],
                recommended_agents=["agent.dmpk_strategist", "agent.data_scientist"],
                related_skills=["skill.dmta_screening", "skill.admet_assessment"],
                tool_ids=["tool.by_screening_bridge", "tool.drugmind_admet"],
            ),
            DiscoveryCapability(
                capability_id="capability.biomarker_strategy",
                name="Biomarker Strategy",
                category="translational",
                description="Plan engagement, pathway, and stratification biomarkers.",
                stage_ids=["target_id", "preclinical", "candidate"],
                required_inputs=["target", "disease"],
                outputs=["biomarker_layers", "decision_points"],
                recommended_agents=["agent.biologist", "agent.data_scientist"],
                related_skills=["skill.biomarker_strategy", "skill.evidence_review"],
                tool_ids=["tool.project_memory"],
            ),
            DiscoveryCapability(
                capability_id="capability.translational_plan",
                name="Translational Plan",
                category="translational",
                description="Build the evidence chain from lead series to preclinical package.",
                stage_ids=["candidate", "preclinical", "clinical"],
                required_inputs=["compound_series", "biomarker_strategy"],
                outputs=["milestones", "priority_compounds"],
                recommended_agents=["agent.project_lead", "agent.biologist"],
                related_skills=["skill.translational_strategy", "skill.go_nogo_review"],
                tool_ids=["tool.project_memory", "tool.project_kanban"],
            ),
            DiscoveryCapability(
                capability_id="capability.candidate_nomination",
                name="Candidate Nomination",
                category="portfolio",
                description="Prepare a gate-ready nomination package and backup plan.",
                stage_ids=["lead_opt", "candidate", "preclinical"],
                required_inputs=["compound_series", "decision_rules"],
                outputs=["lead_candidate", "backup_candidates", "gate"],
                recommended_agents=["agent.project_lead", "agent.pharmacologist"],
                related_skills=["skill.candidate_nomination", "skill.go_nogo_review"],
                tool_ids=["tool.project_memory", "tool.project_kanban"],
            ),
            DiscoveryCapability(
                capability_id="capability.biologics_design_campaign",
                name="Biologics Design Campaign",
                category="biologics",
                description="Generate a BY-style biologics campaign with compute planning and screening gates.",
                stage_ids=["target_id", "screening", "candidate"],
                required_inputs=["target", "modality", "scaffolds"],
                outputs=["campaign_plan", "design_estimate"],
                recommended_agents=["agent.discovery_strategist", "agent.project_lead"],
                related_skills=["skill.biologics_campaign", "skill.structural_research"],
                tool_ids=["tool.by_biologics_pipeline", "tool.by_mcp_bridge"],
            ),
            DiscoveryCapability(
                capability_id="capability.second_me_program_sync",
                name="Second Me Program Sync",
                category="integration",
                description="Project implementation snapshot prepared for linked Second Me personas.",
                stage_ids=["target_id", "screening", "hit_to_lead", "lead_opt", "candidate", "preclinical", "clinical"],
                required_inputs=["implementation_state"],
                outputs=["persona_sync"],
                recommended_agents=["agent.integration"],
                related_skills=["skill.integration_delivery", "skill.workflow_planning"],
                tool_ids=["tool.second_me_project_sync", "tool.project_memory"],
            ),
            DiscoveryCapability(
                capability_id="capability.campaign_memory",
                name="Campaign Memory",
                category="integration",
                description="Condense current project execution into reusable campaign memory and persona-ready context.",
                stage_ids=["screening", "hit_to_lead", "lead_opt", "candidate", "preclinical", "clinical"],
                required_inputs=["execution_history"],
                outputs=["campaign_memory_summary"],
                recommended_agents=["agent.integration", "agent.project_lead"],
                related_skills=["skill.campaign_memory", "skill.workflow_planning"],
                tool_ids=["tool.project_memory", "tool.second_me_project_sync"],
            ),
            DiscoveryCapability(
                capability_id="capability.medi_pharma_target_discovery",
                name="MediPharma Target Discovery",
                category="biology",
                description="Use MediPharma to discover and rank candidate targets from disease context.",
                stage_ids=["target_id"],
                required_inputs=["disease"],
                outputs=["top_targets", "target_summary"],
                recommended_agents=["agent.biologist", "agent.discovery_strategist"],
                related_skills=["skill.medi_pharma_target_discovery", "skill.target_evaluation"],
                tool_ids=["tool.medi_pharma_target_discovery", "tool.medi_pharma_bridge"],
            ),
            DiscoveryCapability(
                capability_id="capability.medi_pharma_virtual_screening",
                name="MediPharma Virtual Screening",
                category="screening",
                description="Run MediPharma virtual screening against a configured ChEMBL target.",
                stage_ids=["screening", "hit_to_lead"],
                required_inputs=["target_chembl_id"],
                outputs=["top_candidates", "screening_summary"],
                recommended_agents=["agent.data_scientist", "agent.discovery_strategist"],
                related_skills=["skill.medi_pharma_virtual_screening", "skill.dmta_screening"],
                tool_ids=["tool.medi_pharma_virtual_screening", "tool.medi_pharma_bridge"],
            ),
            DiscoveryCapability(
                capability_id="capability.medi_pharma_molecule_generation",
                name="MediPharma Molecule Generation",
                category="chemistry",
                description="Generate candidate molecules around a target or scaffold using MediPharma.",
                stage_ids=["screening", "hit_to_lead", "lead_opt"],
                required_inputs=["target_name"],
                outputs=["top_candidates", "generation_summary"],
                recommended_agents=["agent.medicinal_chemist", "agent.discovery_strategist"],
                related_skills=["skill.medi_pharma_molecule_generation", "skill.series_design"],
                tool_ids=["tool.medi_pharma_generation", "tool.medi_pharma_bridge"],
            ),
            DiscoveryCapability(
                capability_id="capability.medi_pharma_admet_batch",
                name="MediPharma Batch ADMET",
                category="dmpk",
                description="Run MediPharma ADMET batch prediction across the current compound panel.",
                stage_ids=["screening", "hit_to_lead", "lead_opt", "candidate"],
                required_inputs=["smiles_list"],
                outputs=["admet_batch", "pass_filter_summary"],
                recommended_agents=["agent.dmpk_strategist", "agent.pharmacologist"],
                related_skills=["skill.medi_pharma_admet_batch", "skill.admet_assessment"],
                tool_ids=["tool.medi_pharma_admet", "tool.medi_pharma_bridge"],
            ),
            DiscoveryCapability(
                capability_id="capability.medi_pharma_lead_optimization",
                name="MediPharma Lead Optimization",
                category="chemistry",
                description="Use MediPharma multi-objective optimization on a seed molecule from the project.",
                stage_ids=["hit_to_lead", "lead_opt"],
                required_inputs=["smiles"],
                outputs=["top_candidates", "optimization_trajectory"],
                recommended_agents=["agent.medicinal_chemist", "agent.dmpk_strategist"],
                related_skills=["skill.medi_pharma_lead_optimization", "skill.lead_optimization"],
                tool_ids=["tool.medi_pharma_lead_optimization", "tool.medi_pharma_bridge"],
            ),
            DiscoveryCapability(
                capability_id="capability.medi_pharma_pipeline_run",
                name="MediPharma Pipeline Run",
                category="portfolio",
                description="Run the MediPharma end-to-end target-to-candidate pipeline from inside DrugMind.",
                stage_ids=["target_id", "screening", "hit_to_lead", "lead_opt"],
                required_inputs=["disease"],
                outputs=["stages_completed", "final_candidates"],
                recommended_agents=["agent.discovery_strategist", "agent.project_lead"],
                related_skills=["skill.medi_pharma_pipeline", "skill.project_triage"],
                tool_ids=["tool.medi_pharma_pipeline", "tool.medi_pharma_bridge"],
            ),
            DiscoveryCapability(
                capability_id="capability.medi_pharma_knowledge_report",
                name="MediPharma Knowledge Report",
                category="biology",
                description="Generate a target-disease knowledge report with literature, patents, and clinical context.",
                stage_ids=["target_id", "candidate", "preclinical"],
                required_inputs=["target", "disease"],
                outputs=["knowledge_report", "key_insights"],
                recommended_agents=["agent.biologist", "agent.project_lead"],
                related_skills=["skill.medi_pharma_knowledge_engine", "skill.target_evaluation"],
                tool_ids=["tool.medi_pharma_knowledge_report", "tool.medi_pharma_bridge"],
            ),
        ]
        changed = False
        for capability in defaults:
            if capability.capability_id not in self.capabilities:
                self.capabilities[capability.capability_id] = capability
                changed = True
        if changed:
            self._save_capabilities()
            logger.info("✅ Drug discovery capabilities seeded with %s items", len(self.capabilities))

    def _seed_blueprints(self):
        defaults = [
            ImplementationBlueprint(
                blueprint_id=self.DEFAULT_BLUEPRINT_ID,
                name="AI-First Small Molecule Discovery",
                description="Executable blueprint for AI-assisted small-molecule drug discovery in DrugMind.",
                phases=[
                    ImplementationPhase(
                        phase_id="phase.target_assessment",
                        name="Target Assessment",
                        description="Validate whether the program should be started at all.",
                        objective="Lock target rationale, assay entry point, and translational anchor.",
                        default_capabilities=[
                            "capability.structural_research",
                            "capability.medi_pharma_target_discovery",
                            "capability.target_landscape",
                            "capability.assay_strategy",
                            "capability.biomarker_strategy",
                            "capability.medi_pharma_knowledge_report",
                        ],
                        exit_criteria=[
                            "target rationale and disease linkage documented",
                            "assay cascade and data quality gate defined",
                            "initial biomarker plan agreed",
                        ],
                        recommended_workflows=["workflow.target_evaluation", "workflow.discovery_bootstrap"],
                        success_metrics=["time_to_target_decision", "assay_readiness", "evidence_density"],
                    ),
                    ImplementationPhase(
                        phase_id="phase.hit_generation",
                        name="Hit Generation",
                        description="Prioritize early hits and stop weak chemical matter from entering the funnel.",
                        objective="Convert screening output into a disciplined hit list.",
                        default_capabilities=[
                            "capability.medi_pharma_virtual_screening",
                            "capability.medi_pharma_molecule_generation",
                            "capability.medi_pharma_admet_batch",
                            "capability.hit_triage",
                            "capability.admet_risk",
                            "capability.dmta_screening_ranking",
                        ],
                        exit_criteria=[
                            "top hits ranked and rescue bucket separated",
                            "early ADMET liabilities surfaced",
                        ],
                        recommended_workflows=["workflow.hit_triage"],
                        success_metrics=["hit_quality", "developability_signal"],
                    ),
                    ImplementationPhase(
                        phase_id="phase.hit_to_lead",
                        name="Hit to Lead",
                        description="Turn hits into tractable, hypothesis-driven series.",
                        objective="Build the first serious chemistry-learning loop.",
                        default_capabilities=[
                            "capability.medi_pharma_molecule_generation",
                            "capability.medi_pharma_admet_batch",
                            "capability.medi_pharma_lead_optimization",
                            "capability.hit_triage",
                            "capability.series_design",
                            "capability.admet_risk",
                            "capability.dmta_screening_ranking",
                        ],
                        exit_criteria=[
                            "series design hypothesis logged",
                            "priority compounds chosen for next cycle",
                            "risk mitigation strategy documented",
                        ],
                        recommended_workflows=["workflow.lead_optimization", "workflow.hit_triage"],
                        success_metrics=["cycle_time", "series_quality", "risk_burndown"],
                    ),
                    ImplementationPhase(
                        phase_id="phase.lead_optimization",
                        name="Lead Optimization",
                        description="Balance potency, selectivity, exposure, and safety under project constraints.",
                        objective="Create a nomination-ready lead series.",
                        default_capabilities=[
                            "capability.medi_pharma_admet_batch",
                            "capability.medi_pharma_lead_optimization",
                            "capability.medi_pharma_pipeline_run",
                            "capability.series_design",
                            "capability.admet_risk",
                            "capability.dmta_screening_ranking",
                            "capability.candidate_nomination",
                        ],
                        exit_criteria=[
                            "lead series meets project gates",
                            "backup compounds are defined",
                            "candidate nomination package drafted",
                        ],
                        recommended_workflows=["workflow.lead_optimization", "workflow.candidate_nomination"],
                        success_metrics=["lead_quality", "nomination_readiness", "backup_depth"],
                    ),
                    ImplementationPhase(
                        phase_id="phase.candidate_selection",
                        name="Candidate Selection",
                        description="Build a coherent package for candidate selection and external communication.",
                        objective="Make the project explainable to humans and personas.",
                        default_capabilities=[
                            "capability.candidate_nomination",
                            "capability.translational_plan",
                            "capability.second_me_program_sync",
                            "capability.campaign_memory",
                        ],
                        exit_criteria=[
                            "lead candidate and backups agreed",
                            "translational milestones documented",
                            "Second Me persona carries the latest project state",
                        ],
                        recommended_workflows=["workflow.candidate_nomination", "workflow.second_me_enablement"],
                        success_metrics=["candidate_quality", "translational_readiness", "external_alignment"],
                    ),
                    ImplementationPhase(
                        phase_id="phase.translational_execution",
                        name="Translational Execution",
                        description="Run the program as a durable evidence-production system.",
                        objective="Maintain synchronized project memory across humans, agents, and external personas.",
                        default_capabilities=[
                            "capability.translational_plan",
                            "capability.second_me_program_sync",
                            "capability.campaign_memory",
                        ],
                        exit_criteria=[
                            "PK/PD and biomarker milestones tracked",
                            "external personas remain in sync",
                        ],
                        recommended_workflows=["workflow.second_me_enablement"],
                        success_metrics=["evidence_velocity", "persona_alignment"],
                    ),
                ],
            ),
            ImplementationBlueprint(
                blueprint_id=self.BIOLOGICS_BLUEPRINT_ID,
                name="AI-First Biologics Discovery",
                description="BY-inspired biologics discovery blueprint adapted for DrugMind and SecondMe.",
                phases=[
                    ImplementationPhase(
                        phase_id="phase.target_assessment",
                        name="Target & Epitope Research",
                        description="Lock sequence, structure, epitope options, and assay constraints before design.",
                        objective="Finish structural research and campaign framing before any compute is spent.",
                        default_capabilities=[
                            "capability.structural_research",
                            "capability.target_landscape",
                            "capability.biologics_design_campaign",
                        ],
                        exit_criteria=[
                            "best structure or model identified",
                            "epitope/prior-art summary written",
                            "campaign compute estimate agreed",
                        ],
                        recommended_workflows=["workflow.discovery_bootstrap", "workflow.biologics_campaign"],
                        success_metrics=["structure_coverage", "epitope_clarity", "campaign_readiness"],
                    ),
                    ImplementationPhase(
                        phase_id="phase.hit_generation",
                        name="Design & Screen",
                        description="Generate, screen, and rank biologics candidates.",
                        objective="Create a ranked panel of binders with explicit developability and diversity views.",
                        default_capabilities=[
                            "capability.biologics_design_campaign",
                            "capability.campaign_memory",
                        ],
                        exit_criteria=[
                            "ranked shortlist ready",
                            "screening gates documented",
                        ],
                        recommended_workflows=["workflow.biologics_campaign"],
                        success_metrics=["design_success_rate", "screening_attrition", "shortlist_quality"],
                    ),
                    ImplementationPhase(
                        phase_id="phase.hit_to_lead",
                        name="Biologics Optimization",
                        description="Refine candidates with developability and ranking feedback.",
                        objective="Balance affinity, interface quality, and developability.",
                        default_capabilities=[
                            "capability.biologics_design_campaign",
                            "capability.campaign_memory",
                            "capability.second_me_program_sync",
                        ],
                        exit_criteria=[
                            "top candidates carry clear optimization hypotheses",
                            "external persona is synchronized for partner communication",
                        ],
                        recommended_workflows=["workflow.biologics_campaign", "workflow.second_me_enablement"],
                        success_metrics=["candidate_consistency", "developability_signal", "persona_alignment"],
                    ),
                    ImplementationPhase(
                        phase_id="phase.candidate_selection",
                        name="Candidate Decision",
                        description="Prepare nomination-ready biologics package and external narrative.",
                        objective="Make the biologics program reviewable by humans, agents, and external partners.",
                        default_capabilities=[
                            "capability.campaign_memory",
                            "capability.second_me_program_sync",
                        ],
                        exit_criteria=[
                            "candidate package assembled",
                            "SecondMe persona aligned to latest shortlist",
                        ],
                        recommended_workflows=["workflow.candidate_nomination", "workflow.second_me_enablement"],
                        success_metrics=["nomination_readiness", "external_alignment"],
                    ),
                ],
            ),
        ]
        changed = False
        for blueprint in defaults:
            existing = self.blueprints.get(blueprint.blueprint_id)
            if not existing:
                self.blueprints[blueprint.blueprint_id] = blueprint
                changed = True
                continue
            if existing.name != blueprint.name:
                existing.name = blueprint.name
                changed = True
            if existing.description != blueprint.description:
                existing.description = blueprint.description
                changed = True
            existing_phases = {phase.phase_id: phase for phase in existing.phases}
            merged_phases: list[ImplementationPhase] = []
            for default_phase in blueprint.phases:
                current_phase = existing_phases.get(default_phase.phase_id)
                if not current_phase:
                    merged_phases.append(default_phase)
                    changed = True
                    continue
                merged_capabilities = list(dict.fromkeys(list(default_phase.default_capabilities) + list(current_phase.default_capabilities)))
                merged_exit = list(dict.fromkeys(list(current_phase.exit_criteria) + list(default_phase.exit_criteria)))
                merged_workflows = list(dict.fromkeys(list(current_phase.recommended_workflows) + list(default_phase.recommended_workflows)))
                merged_metrics = list(dict.fromkeys(list(current_phase.success_metrics) + list(default_phase.success_metrics)))
                updated_phase = ImplementationPhase(
                    phase_id=current_phase.phase_id,
                    name=default_phase.name,
                    description=default_phase.description,
                    objective=default_phase.objective,
                    default_capabilities=merged_capabilities,
                    exit_criteria=merged_exit,
                    recommended_workflows=merged_workflows,
                    success_metrics=merged_metrics,
                )
                if asdict(updated_phase) != asdict(current_phase):
                    changed = True
                merged_phases.append(updated_phase)
            extra_phase_ids = {phase.phase_id for phase in merged_phases}
            for current_phase in existing.phases:
                if current_phase.phase_id not in extra_phase_ids:
                    merged_phases.append(current_phase)
            existing.phases = merged_phases
        if changed:
            self._save_blueprints()
            logger.info("✅ Drug discovery blueprints seeded with %s items", len(self.blueprints))

    def _save_capabilities(self):
        payload = {capability_id: asdict(capability) for capability_id, capability in self.capabilities.items()}
        self._capabilities_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    def _save_blueprints(self):
        payload = {blueprint_id: asdict(blueprint) for blueprint_id, blueprint in self.blueprints.items()}
        self._blueprints_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    def _save_states(self):
        payload = {project_id: asdict(state) for project_id, state in self.states.items()}
        self._states_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    def _save_executions(self):
        payload = {execution_id: asdict(execution) for execution_id, execution in self.executions.items()}
        self._executions_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    def _load(self):
        if self._capabilities_path.exists():
            try:
                data = json.loads(self._capabilities_path.read_text())
                self.capabilities = {
                    capability_id: DiscoveryCapability(**payload)
                    for capability_id, payload in data.items()
                }
            except Exception as exc:
                logger.warning("加载 discovery capabilities 失败: %s", exc)
                self.capabilities = {}
        if self._blueprints_path.exists():
            try:
                data = json.loads(self._blueprints_path.read_text())
                self.blueprints = {
                    blueprint_id: ImplementationBlueprint(**payload)
                    for blueprint_id, payload in data.items()
                }
            except Exception as exc:
                logger.warning("加载 implementation blueprints 失败: %s", exc)
                self.blueprints = {}
        if self._states_path.exists():
            try:
                data = json.loads(self._states_path.read_text())
                self.states = {
                    project_id: ProjectImplementationState(**payload)
                    for project_id, payload in data.items()
                }
            except Exception as exc:
                logger.warning("加载 implementation states 失败: %s", exc)
                self.states = {}
        if self._executions_path.exists():
            try:
                data = json.loads(self._executions_path.read_text())
                self.executions = {
                    execution_id: CapabilityExecution(**payload)
                    for execution_id, payload in data.items()
                }
            except Exception as exc:
                logger.warning("加载 capability executions 失败: %s", exc)
                self.executions = {}
