"""
Lightweight workflow orchestrator skeleton.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStepTemplate:
    """Template definition for a workflow step."""

    step_id: str
    name: str
    description: str
    agent_id: str
    required_skills: list[str] = field(default_factory=list)
    tool_ids: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)


@dataclass
class WorkflowTemplate:
    """Template definition for an orchestrated workflow."""

    template_id: str
    name: str
    category: str
    description: str
    tags: list[str] = field(default_factory=list)
    steps: list[WorkflowStepTemplate] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        self.steps = [
            step if isinstance(step, WorkflowStepTemplate) else WorkflowStepTemplate(**step)
            for step in self.steps
        ]


@dataclass
class WorkflowStepRun:
    """Runtime step state."""

    step_id: str
    name: str
    description: str
    agent_id: str
    required_skills: list[str] = field(default_factory=list)
    tool_ids: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    status: str = "pending"
    notes: list[str] = field(default_factory=list)
    output: str = ""
    state: dict = field(default_factory=dict)
    artifacts: list[dict] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""


@dataclass
class WorkflowRun:
    """Runtime workflow object."""

    run_id: str
    template_id: str
    template_name: str
    project_id: str
    topic: str
    status: str = "running"
    current_step_index: int = 0
    created_by: str = ""
    context: dict = field(default_factory=dict)
    execution_context: dict = field(default_factory=dict)
    linked_decisions: list[str] = field(default_factory=list)
    linked_discussions: list[str] = field(default_factory=list)
    linked_memory_entries: list[str] = field(default_factory=list)
    steps: list[WorkflowStepRun] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        self.steps = [
            step if isinstance(step, WorkflowStepRun) else WorkflowStepRun(**step)
            for step in self.steps
        ]


class WorkflowOrchestrator:
    """Starts and advances durable workflow runs."""

    def __init__(
        self,
        data_dir: str = "./drugmind_data/platform/workflows",
        agent_registry=None,
        skill_registry=None,
        tool_registry=None,
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._templates_path = self.data_dir / "workflow_templates.json"
        self._runs_path = self.data_dir / "workflow_runs.json"
        self.agent_registry = agent_registry
        self.skill_registry = skill_registry
        self.tool_registry = tool_registry
        self.templates: dict[str, WorkflowTemplate] = {}
        self.runs: dict[str, WorkflowRun] = {}
        self._load_templates()
        self._seed_templates()
        self._load_runs()

    def list_templates(self, category: str = "") -> list[dict]:
        templates = list(self.templates.values())
        if category:
            templates = [template for template in templates if template.category == category]
        templates.sort(key=lambda template: template.name)
        return [asdict(template) for template in templates]

    def get_template(self, template_id: str) -> Optional[dict]:
        template = self.templates.get(template_id)
        return asdict(template) if template else None

    def list_runs(self, project_id: str = "", status: str = "") -> list[dict]:
        runs = list(self.runs.values())
        if project_id:
            runs = [run for run in runs if run.project_id == project_id]
        if status:
            runs = [run for run in runs if run.status == status]
        runs.sort(key=lambda run: run.updated_at, reverse=True)
        return [asdict(run) for run in runs]

    def get_run(self, run_id: str) -> Optional[dict]:
        run = self.runs.get(run_id)
        return asdict(run) if run else None

    def start_run(
        self,
        template_id: str,
        project_id: str,
        topic: str,
        created_by: str = "",
        context: dict | None = None,
        execution_context: dict | None = None,
    ) -> dict:
        template = self.templates.get(template_id)
        if not template:
            raise ValueError(f"未知 workflow template: {template_id}")

        run_id = f"wf_{uuid.uuid4().hex[:10]}"
        steps = [
            WorkflowStepRun(
                step_id=step.step_id,
                name=step.name,
                description=step.description,
                agent_id=step.agent_id,
                required_skills=list(step.required_skills),
                tool_ids=list(step.tool_ids),
                outputs=list(step.outputs),
            )
            for step in template.steps
        ]
        if steps:
            steps[0].status = "in_progress"
            steps[0].started_at = datetime.now().isoformat()

        run = WorkflowRun(
            run_id=run_id,
            template_id=template.template_id,
            template_name=template.name,
            project_id=project_id,
            topic=topic,
            created_by=created_by,
            context=context or {},
            execution_context=execution_context or {},
            steps=steps,
        )
        self.runs[run_id] = run
        self._save_runs()
        return asdict(run)

    def complete_step(self, run_id: str, step_id: str, output: str = "", note: str = "") -> dict:
        run = self.runs.get(run_id)
        if not run:
            raise ValueError(f"未知 workflow run: {run_id}")

        matched_index = None
        for index, step in enumerate(run.steps):
            if step.step_id == step_id:
                matched_index = index
                break
        if matched_index is None:
            raise ValueError(f"未知 workflow step: {step_id}")

        step = run.steps[matched_index]
        step.status = "completed"
        step.completed_at = datetime.now().isoformat()
        if output:
            step.output = output
        if note:
            step.notes.append(note)

        next_index = matched_index + 1
        if next_index < len(run.steps):
            next_step = run.steps[next_index]
            if next_step.status == "pending":
                next_step.status = "in_progress"
                next_step.started_at = datetime.now().isoformat()
            run.current_step_index = next_index
        else:
            run.current_step_index = len(run.steps) - 1 if run.steps else 0
            run.status = "completed"

        run.updated_at = datetime.now().isoformat()
        self._save_runs()
        return asdict(run)

    def update_context(self, run_id: str, context_patch: dict | None = None, note: str = "") -> dict:
        run = self.runs.get(run_id)
        if not run:
            raise ValueError(f"未知 workflow run: {run_id}")
        if context_patch:
            run.execution_context.update(context_patch)
        if note and run.steps:
            current_index = min(run.current_step_index, len(run.steps) - 1)
            run.steps[current_index].notes.append(note)
        run.updated_at = datetime.now().isoformat()
        self._save_runs()
        return asdict(run)

    def link_artifact(self, run_id: str, artifact_type: str, artifact_id: str, summary: str = "") -> dict:
        run = self.runs.get(run_id)
        if not run:
            raise ValueError(f"未知 workflow run: {run_id}")

        artifact = {
            "type": artifact_type,
            "id": artifact_id,
            "summary": summary,
            "linked_at": datetime.now().isoformat(),
        }
        if run.steps:
            current_index = min(run.current_step_index, len(run.steps) - 1)
            run.steps[current_index].artifacts.append(artifact)

        if artifact_type == "decision" and artifact_id not in run.linked_decisions:
            run.linked_decisions.append(artifact_id)
        elif artifact_type == "discussion" and artifact_id not in run.linked_discussions:
            run.linked_discussions.append(artifact_id)
        elif artifact_type == "memory" and artifact_id not in run.linked_memory_entries:
            run.linked_memory_entries.append(artifact_id)

        run.updated_at = datetime.now().isoformat()
        self._save_runs()
        return asdict(run)

    def count_runs(self) -> int:
        return len(self.runs)

    def _seed_templates(self):
        defaults = [
            WorkflowTemplate(
                template_id="workflow.target_evaluation",
                name="Target Evaluation Workflow",
                category="drug_discovery",
                description="Evaluate a new target with biology, evidence, and project strategy reviews.",
                tags=["target", "discovery"],
                steps=[
                    WorkflowStepTemplate(
                        step_id="collect_evidence",
                        name="Collect Evidence",
                        description="Gather the current biology and disease rationale.",
                        agent_id="agent.biologist",
                        required_skills=["skill.target_evaluation", "skill.evidence_review"],
                        tool_ids=["tool.project_memory", "tool.drugmind_scenario"],
                        outputs=["target_dossier"],
                    ),
                    WorkflowStepTemplate(
                        step_id="project_triage",
                        name="Project Triage",
                        description="Frame the target against program constraints and milestones.",
                        agent_id="agent.project_lead",
                        required_skills=["skill.project_triage"],
                        tool_ids=["tool.project_kanban", "tool.project_memory"],
                        outputs=["priority_plan"],
                    ),
                    WorkflowStepTemplate(
                        step_id="decision_review",
                        name="Decision Review",
                        description="Review the evidence package and produce a go-forward recommendation.",
                        agent_id="agent.reviewer",
                        required_skills=["skill.go_nogo_review"],
                        tool_ids=["tool.drugmind_discuss", "tool.project_memory"],
                        outputs=["decision_record"],
                    ),
                ],
            ),
            WorkflowTemplate(
                template_id="workflow.lead_optimization",
                name="Lead Optimization Workflow",
                category="drug_discovery",
                description="Coordinate SAR review, ADMET review, and prioritization for a lead series.",
                tags=["lead_opt", "chemistry"],
                steps=[
                    WorkflowStepTemplate(
                        step_id="sar_review",
                        name="SAR Review",
                        description="Analyze compound series and propose the next chemistry moves.",
                        agent_id="agent.medicinal_chemist",
                        required_skills=["skill.sar_review", "skill.lead_optimization"],
                        tool_ids=["tool.drugmind_compound", "tool.project_memory"],
                        outputs=["chemistry_hypotheses"],
                    ),
                    WorkflowStepTemplate(
                        step_id="admet_review",
                        name="ADMET Review",
                        description="Assess ADMET liabilities for the current candidates.",
                        agent_id="agent.pharmacologist",
                        required_skills=["skill.admet_assessment"],
                        tool_ids=["tool.drugmind_admet", "tool.project_memory"],
                        outputs=["admet_flags"],
                    ),
                    WorkflowStepTemplate(
                        step_id="priority_decision",
                        name="Priority Decision",
                        description="Set the next sprint priorities for the project team.",
                        agent_id="agent.project_lead",
                        required_skills=["skill.project_triage", "skill.go_nogo_review"],
                        tool_ids=["tool.project_kanban", "tool.project_memory"],
                        outputs=["priority_queue"],
                    ),
                ],
            ),
            WorkflowTemplate(
                template_id="workflow.integration_delivery",
                name="Integration Delivery Workflow",
                category="platform",
                description="Prepare, validate, and review an external integration before release.",
                tags=["mcp", "integration"],
                steps=[
                    WorkflowStepTemplate(
                        step_id="plan_integration",
                        name="Plan Integration",
                        description="Outline deliverables, endpoints, and constraints.",
                        agent_id="agent.integration",
                        required_skills=["skill.integration_delivery", "skill.workflow_planning"],
                        tool_ids=["tool.second_me_sync", "tool.project_memory"],
                        outputs=["integration_plan"],
                    ),
                    WorkflowStepTemplate(
                        step_id="review_delivery",
                        name="Review Delivery",
                        description="Review setup quality and release readiness.",
                        agent_id="agent.reviewer",
                        required_skills=["skill.evidence_review"],
                        tool_ids=["tool.project_memory"],
                        outputs=["review_notes"],
                    ),
                ],
            ),
        ]

        changed = False
        for template in defaults:
            if template.template_id not in self.templates:
                self.templates[template.template_id] = template
                changed = True
        if changed:
            self._save_templates()
            logger.info("✅ Workflow orchestrator seeded with %s templates", len(self.templates))

    def _save_templates(self):
        data = {template_id: asdict(template) for template_id, template in self.templates.items()}
        self._templates_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _save_runs(self):
        data = {run_id: asdict(run) for run_id, run in self.runs.items()}
        self._runs_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load_templates(self):
        if not self._templates_path.exists():
            return
        try:
            data = json.loads(self._templates_path.read_text())
            self.templates = {
                template_id: WorkflowTemplate(**payload)
                for template_id, payload in data.items()
            }
        except Exception as exc:
            logger.warning("加载 workflow templates 失败: %s", exc)
            self.templates = {}

    def _load_runs(self):
        if not self._runs_path.exists():
            return
        try:
            data = json.loads(self._runs_path.read_text())
            self.runs = {
                run_id: WorkflowRun(**payload)
                for run_id, payload in data.items()
            }
        except Exception as exc:
            logger.warning("加载 workflow runs 失败: %s", exc)
            self.runs = {}
