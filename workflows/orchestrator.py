"""
Lightweight workflow orchestrator with executable steps and approval gates.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

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
    capability_id: str = ""
    approval_required: bool = False


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
    capability_id: str = ""
    status: str = "pending"
    notes: list[str] = field(default_factory=list)
    output: str = ""
    state: dict = field(default_factory=dict)
    artifacts: list[dict] = field(default_factory=list)
    input_payload: dict = field(default_factory=dict)
    owner_type: str = "agent"
    owner_id: str = ""
    owner_label: str = ""
    approval_required: bool = False
    approval_status: str = "not_required"
    approvals: list[dict] = field(default_factory=list)
    executor_summary: str = ""
    last_error: str = ""
    execution_attempts: int = 0
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
    """Starts, executes, and advances durable workflow runs."""

    def __init__(
        self,
        data_dir: str = "./drugmind_data/platform/workflows",
        agent_registry=None,
        skill_registry=None,
        tool_registry=None,
        twin_engine=None,
        discussion_engine=None,
        decision_logger=None,
        workspace_store=None,
        project_memory=None,
        kanban=None,
        compound_tracker=None,
        second_me=None,
        second_me_bindings=None,
        drug_discovery_hub=None,
        blatant_why_adapter=None,
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
        self.attach_runtime(
            twin_engine=twin_engine,
            discussion_engine=discussion_engine,
            decision_logger=decision_logger,
            workspace_store=workspace_store,
            project_memory=project_memory,
            kanban=kanban,
            compound_tracker=compound_tracker,
            second_me=second_me,
            second_me_bindings=second_me_bindings,
            drug_discovery_hub=drug_discovery_hub,
            blatant_why_adapter=blatant_why_adapter,
        )
        self._load_templates()
        self._seed_templates()
        self._normalize_templates()
        self._load_runs()
        self._normalize_runs()

    def attach_runtime(
        self,
        *,
        twin_engine=None,
        discussion_engine=None,
        decision_logger=None,
        workspace_store=None,
        project_memory=None,
        kanban=None,
        compound_tracker=None,
        second_me=None,
        second_me_bindings=None,
        drug_discovery_hub=None,
        blatant_why_adapter=None,
    ):
        self.twin_engine = twin_engine
        self.discussion_engine = discussion_engine
        self.decision_logger = decision_logger
        self.workspace_store = workspace_store
        self.project_memory = project_memory
        self.kanban = kanban
        self.compound_tracker = compound_tracker
        self.second_me = second_me
        self.second_me_bindings = second_me_bindings
        self.drug_discovery_hub = drug_discovery_hub
        self.blatant_why_adapter = blatant_why_adapter
        return self

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
        steps = [self._build_step_run(step) for step in template.steps]
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

    def execute_current_step(
        self,
        run_id: str,
        *,
        requested_by: str = "",
        input_payloads: dict[str, dict] | None = None,
        max_steps: int = 1,
        note: str = "",
    ) -> dict:
        run = self.runs.get(run_id)
        if not run:
            raise ValueError(f"未知 workflow run: {run_id}")

        input_payloads = input_payloads or {}
        executed_steps: list[str] = []
        iterations = 0
        while iterations < max_steps:
            current = self._get_actionable_step(run)
            if not current:
                break
            current_index, step = current
            if step.status == "awaiting_approval":
                break
            if step.owner_type == "human":
                if step.status == "pending":
                    step.status = "awaiting_owner"
                    if not step.started_at:
                        step.started_at = datetime.now().isoformat()
                    run.status = "awaiting_owner"
                    run.updated_at = datetime.now().isoformat()
                    self._save_runs()
                break
            if step.status == "awaiting_owner":
                run.status = "awaiting_owner"
                run.updated_at = datetime.now().isoformat()
                self._save_runs()
                break
            if run.status in {"awaiting_approval", "completed", "failed", "blocked"}:
                break
            self.execute_step(
                run_id=run_id,
                step_id=step.step_id,
                input_payload=input_payloads.get(step.step_id, {}),
                note=note if iterations == 0 else "",
                requested_by=requested_by,
            )
            executed_steps.append(step.step_id)
            run = self.runs[run_id]
            iterations += 1
            if run.status in {"awaiting_approval", "completed", "failed", "blocked"}:
                break
            if current_index >= len(run.steps) - 1:
                break

        return {
            "run": asdict(run),
            "executed_steps": executed_steps,
        }

    def execute_step(
        self,
        run_id: str,
        step_id: str,
        *,
        input_payload: dict | None = None,
        note: str = "",
        requested_by: str = "",
        force_ai: bool = False,
    ) -> dict:
        run, step, step_index = self._locate_step(run_id, step_id)
        if run.status in {"completed", "failed"}:
            raise ValueError(f"Workflow run 已结束: {run.status}")
        if step.status == "completed":
            raise ValueError(f"Workflow step 已完成: {step_id}")
        if step.status == "awaiting_approval":
            raise ValueError(f"Workflow step 等待审批: {step_id}")
        if step.status == "rejected":
            raise ValueError(f"Workflow step 已被拒绝: {step_id}")
        if step.owner_type == "human" and not force_ai:
            raise ValueError(f"Workflow step 当前分配给人工 owner: {step.owner_label or step.owner_id}")

        now = datetime.now().isoformat()
        step.status = "in_progress"
        if not step.started_at:
            step.started_at = now
        if note:
            step.notes.append(note)
        payload = input_payload or {}
        if payload:
            step.input_payload = payload
        step.execution_attempts += 1
        run.status = "running"

        try:
            result = self._execute_step_logic(run, step, payload, requested_by=requested_by)
            step.output = result["output"]
            step.executor_summary = result["summary"]
            step.last_error = ""
            step.state.update(result.get("state", {}))
            run.execution_context.update(result.get("context_patch", {}))
            self._append_artifacts(run, step, result.get("artifacts", []))

            if step.approval_required:
                step.status = "awaiting_approval"
                step.approval_status = "pending"
                run.status = "awaiting_approval"
            else:
                step.status = "completed"
                step.completed_at = now
                self._advance_run(run, step_index)
        except Exception as exc:
            step.status = "failed"
            step.last_error = str(exc)
            step.notes.append(f"Execution failed: {exc}")
            run.status = "failed"

        run.updated_at = datetime.now().isoformat()
        self._save_runs()
        return asdict(run)

    def approve_step(
        self,
        run_id: str,
        step_id: str,
        *,
        approved: bool,
        approver_id: str = "",
        note: str = "",
    ) -> dict:
        run, step, step_index = self._locate_step(run_id, step_id)
        if not step.approval_required:
            raise ValueError(f"Workflow step 不需要审批: {step_id}")
        if step.status not in {"awaiting_approval", "rejected"}:
            raise ValueError(f"Workflow step 当前状态不能审批: {step.status}")

        approval = {
            "approved": approved,
            "approver_id": approver_id,
            "note": note,
            "timestamp": datetime.now().isoformat(),
        }
        step.approvals.append(approval)
        if note:
            step.notes.append(note)

        if approved:
            step.approval_status = "approved"
            step.status = "completed"
            step.completed_at = datetime.now().isoformat()
            run.status = "running"
            self._advance_run(run, step_index)
        else:
            step.approval_status = "rejected"
            step.status = "rejected"
            run.status = "blocked"

        run.updated_at = datetime.now().isoformat()
        self._save_runs()
        return asdict(run)

    def assign_step_owner(
        self,
        run_id: str,
        step_id: str,
        *,
        owner_type: str,
        owner_id: str,
        owner_label: str = "",
        assigned_by: str = "",
        note: str = "",
    ) -> dict:
        if owner_type not in {"agent", "human"}:
            raise ValueError("owner_type 必须是 agent 或 human")
        if not owner_id:
            raise ValueError("owner_id 为必填")

        run, step, step_index = self._locate_step(run_id, step_id)
        step.owner_type = owner_type
        step.owner_id = owner_id
        step.owner_label = owner_label or owner_id
        assignment_note = (
            f"Owner assigned to {step.owner_label} ({step.owner_type})"
            + (f" by {assigned_by}" if assigned_by else "")
        )
        step.notes.append(note or assignment_note)

        if step.status not in {"completed", "failed", "rejected", "awaiting_approval"}:
            if owner_type == "human":
                step.status = "awaiting_owner"
                if not step.started_at:
                    step.started_at = datetime.now().isoformat()
                if run.current_step_index == step_index:
                    run.status = "awaiting_owner"
            else:
                if step.status == "awaiting_owner":
                    step.status = "in_progress"
                elif step.status == "pending":
                    step.status = "in_progress" if run.current_step_index == step_index else "pending"
                if run.current_step_index == step_index and run.status == "awaiting_owner":
                    run.status = "running"

        run.updated_at = datetime.now().isoformat()
        self._save_runs()
        return asdict(run)

    def complete_step(self, run_id: str, step_id: str, output: str = "", note: str = "") -> dict:
        run, step, step_index = self._locate_step(run_id, step_id)

        step.status = "completed"
        step.completed_at = datetime.now().isoformat()
        if output:
            step.output = output
            step.executor_summary = self._summarize_text(output)
        if note:
            step.notes.append(note)
        if step.approval_required and step.approval_status in {"required", "pending"}:
            step.approval_status = "approved"
            step.approvals.append(
                {
                    "approved": True,
                    "approver_id": "manual_override",
                    "note": "Step manually completed",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        self._advance_run(run, step_index)
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
        step_index = min(run.current_step_index, len(run.steps) - 1) if run.steps else 0
        step = run.steps[step_index] if run.steps else None
        if step:
            self._append_artifacts(run, step, [artifact])
        run.updated_at = datetime.now().isoformat()
        self._save_runs()
        return asdict(run)

    def count_runs(self) -> int:
        return len(self.runs)

    def _build_step_run(self, step: WorkflowStepTemplate) -> WorkflowStepRun:
        approval_required = step.approval_required or step.agent_id == "agent.reviewer"
        owner_label = step.agent_id
        if self.agent_registry:
            agent = self.agent_registry.get_agent(step.agent_id)
            owner_label = (agent or {}).get("name", step.agent_id)
        return WorkflowStepRun(
            step_id=step.step_id,
            name=step.name,
            description=step.description,
            agent_id=step.agent_id,
            required_skills=list(step.required_skills),
            tool_ids=list(step.tool_ids),
            outputs=list(step.outputs),
            capability_id=step.capability_id,
            owner_type="agent",
            owner_id=step.agent_id,
            owner_label=owner_label,
            approval_required=approval_required,
            approval_status="required" if approval_required else "not_required",
        )

    def _locate_step(self, run_id: str, step_id: str) -> tuple[WorkflowRun, WorkflowStepRun, int]:
        run = self.runs.get(run_id)
        if not run:
            raise ValueError(f"未知 workflow run: {run_id}")

        for index, step in enumerate(run.steps):
            if step.step_id == step_id:
                return run, step, index
        raise ValueError(f"未知 workflow step: {step_id}")

    def _get_actionable_step(self, run: WorkflowRun) -> Optional[tuple[int, WorkflowStepRun]]:
        for index, step in enumerate(run.steps):
            if step.status in {"pending", "in_progress", "awaiting_owner", "awaiting_approval"}:
                return index, step
        return None

    def _advance_run(self, run: WorkflowRun, completed_index: int):
        next_index = completed_index + 1
        if next_index < len(run.steps):
            next_step = run.steps[next_index]
            if next_step.status == "pending":
                next_step.status = "awaiting_owner" if next_step.owner_type == "human" else "in_progress"
                next_step.started_at = datetime.now().isoformat()
            run.current_step_index = next_index
            if run.status != "awaiting_approval":
                run.status = "awaiting_owner" if next_step.owner_type == "human" else "running"
        else:
            run.current_step_index = len(run.steps) - 1 if run.steps else 0
            run.status = "completed"

    def _append_artifacts(self, run: WorkflowRun, step: WorkflowStepRun, artifacts: list[dict]):
        for artifact in artifacts:
            if not artifact.get("id"):
                continue
            if not any(item.get("type") == artifact["type"] and item.get("id") == artifact["id"] for item in step.artifacts):
                step.artifacts.append(artifact)

            if artifact["type"] == "decision" and artifact["id"] not in run.linked_decisions:
                run.linked_decisions.append(artifact["id"])
            elif artifact["type"] == "discussion" and artifact["id"] not in run.linked_discussions:
                run.linked_discussions.append(artifact["id"])
            elif artifact["type"] == "memory" and artifact["id"] not in run.linked_memory_entries:
                run.linked_memory_entries.append(artifact["id"])

    def _execute_step_logic(
        self,
        run: WorkflowRun,
        step: WorkflowStepRun,
        input_payload: dict,
        *,
        requested_by: str = "",
    ) -> dict:
        tool_execution = self._execute_tools(run, step, input_payload)
        brief = self._build_execution_brief(run, step, input_payload, tool_execution["results"])
        agent_output = self._generate_agent_output(run, step, brief, tool_execution["results"])
        summary = self._summarize_text(agent_output)

        memory_artifact = self._record_step_memory(run, step, agent_output)
        artifacts = list(tool_execution["artifacts"])
        if memory_artifact:
            artifacts.append(memory_artifact)

        decision_artifact = self._record_step_decision(
            run,
            step,
            output_text=agent_output,
            related_memory_id=memory_artifact["id"] if memory_artifact else "",
            related_discussions=[artifact["id"] for artifact in artifacts if artifact["type"] == "discussion"],
        )
        if decision_artifact:
            artifacts.append(decision_artifact)

        step_outputs = dict(run.execution_context.get("step_outputs", {}))
        step_outputs[step.step_id] = {
            "name": step.name,
            "agent_id": step.agent_id,
            "summary": summary,
            "output": agent_output,
            "updated_at": datetime.now().isoformat(),
        }
        context_patch = dict(tool_execution["context_patch"])
        context_patch["step_outputs"] = step_outputs
        context_patch["last_step_summary"] = {
            "step_id": step.step_id,
            "name": step.name,
            "summary": summary,
            "requested_by": requested_by,
        }

        state = {
            "tool_results": tool_execution["results"],
            "generated_at": datetime.now().isoformat(),
            "requested_by": requested_by,
            "agent_id": step.agent_id,
        }
        return {
            "output": agent_output,
            "summary": summary,
            "state": state,
            "artifacts": artifacts,
            "context_patch": context_patch,
        }

    def _execute_tools(self, run: WorkflowRun, step: WorkflowStepRun, input_payload: dict) -> dict:
        results: dict[str, Any] = {}
        artifacts: list[dict] = []
        context_patch: dict[str, Any] = {}

        if "tool.drug_discovery_execute" in step.tool_ids and self.drug_discovery_hub:
            capability_id = step.capability_id or input_payload.get("capability_id", "")
            if capability_id:
                capability_result = self.drug_discovery_hub.execute_capability(
                    run.project_id,
                    capability_id,
                    input_payload=input_payload,
                    triggered_by=input_payload.get("triggered_by", "") or run.created_by or "workflow",
                    sync_to_second_me=bool(input_payload.get("sync_to_second_me", False)),
                )
                results["capability_execution"] = capability_result
                artifacts.append(
                    {
                        "type": "capability_execution",
                        "id": capability_result["execution_id"],
                        "summary": self._summarize_text(capability_result.get("summary", "")),
                        "linked_at": datetime.now().isoformat(),
                    }
                )
                context_patch["latest_capability_execution"] = capability_result

        if "tool.drugmind_admet" in step.tool_ids:
            admet_result = self._run_admet_tool(run, input_payload)
            results["admet"] = admet_result
            if admet_result:
                artifacts.append(
                    {
                        "type": "admet_report",
                        "id": f"admet_{uuid.uuid4().hex[:8]}",
                        "summary": self._summarize_text(json.dumps(admet_result, ensure_ascii=False)),
                        "linked_at": datetime.now().isoformat(),
                    }
                )
                context_patch["latest_admet"] = admet_result

        if "tool.drugmind_discuss" in step.tool_ids:
            discussion_result = self._run_discussion_tool(run, step, input_payload)
            if discussion_result:
                results["discussion"] = discussion_result
                artifacts.append(
                    {
                        "type": "discussion",
                        "id": discussion_result["session_id"],
                        "summary": self._summarize_text(discussion_result["summary"]),
                        "linked_at": datetime.now().isoformat(),
                    }
                )
                context_patch["latest_discussion"] = {
                    "session_id": discussion_result["session_id"],
                    "summary": discussion_result["summary"],
                }

        if "tool.second_me_project_sync" in step.tool_ids:
            sync_result = self._run_second_me_sync(run, input_payload)
            if sync_result:
                results["second_me_sync"] = sync_result
                artifacts.append(
                    {
                        "type": "second_me_sync",
                        "id": sync_result.get("instance_id", f"sync_{uuid.uuid4().hex[:8]}"),
                        "summary": self._summarize_text(sync_result.get("summary", "Second Me sync executed")),
                        "linked_at": datetime.now().isoformat(),
                    }
                )
                context_patch["latest_second_me_sync"] = sync_result

        if "tool.project_kanban" in step.tool_ids and self.kanban:
            project_snapshot = self.kanban.get_project(run.project_id) or {}
            if project_snapshot:
                results["project"] = project_snapshot

        if "tool.project_memory" in step.tool_ids and self.project_memory:
            results["memory_context"] = self.project_memory.get_context(run.project_id, query=run.topic, limit=6)

        if "tool.by_biologics_pipeline" in step.tool_ids and self.blatant_why_adapter:
            results["by_biologics_pipeline"] = self.blatant_why_adapter.biologics_pipeline.build_campaign(
                project=self.kanban.get_project(run.project_id) if self.kanban else {"project_id": run.project_id},
                modality=input_payload.get("modality", "nanobody"),
                scaffolds=input_payload.get("scaffolds"),
                seeds=int(input_payload.get("seeds", 8)),
                designs_per_seed=int(input_payload.get("designs_per_seed", 8)),
                complexity=input_payload.get("complexity", "standard"),
            )

        if "tool.by_screening_bridge" in step.tool_ids and self.blatant_why_adapter and self.compound_tracker:
            compounds = self.compound_tracker.list_compounds(project_id=run.project_id)
            results["by_screening"] = self.blatant_why_adapter.run_small_molecule_screening(
                project=self.kanban.get_project(run.project_id) if self.kanban else {"project_id": run.project_id},
                compounds=compounds,
            )

        return {
            "results": results,
            "artifacts": artifacts,
            "context_patch": context_patch,
        }

    def _generate_agent_output(
        self,
        run: WorkflowRun,
        step: WorkflowStepRun,
        brief: str,
        tool_results: dict[str, Any],
    ) -> str:
        agent_profile = self.agent_registry.get_agent(step.agent_id) if self.agent_registry else None
        role_id = (agent_profile or {}).get("role_id", "")

        if role_id and self.twin_engine:
            twin_id = self._ensure_twin(role_id, (agent_profile or {}).get("name", role_id))
            response = self.twin_engine.ask_twin(
                twin_id=twin_id,
                question=(
                    f"请执行 workflow step『{step.name}』。"
                    f"你的目标是交付这些输出：{', '.join(step.outputs) or 'step deliverable'}。"
                    f"请给出可执行、可审阅的专业结论。"
                ),
                context=brief,
            )
            return response.message

        if step.agent_id == "agent.integration":
            return self._render_integration_output(run, step, tool_results)
        if step.agent_id == "agent.reviewer":
            return self._render_reviewer_output(run, step, tool_results)
        if step.agent_id == "agent.orchestrator":
            return self._render_orchestrator_output(run, step, tool_results)

        return (
            f"{step.name}\n\n"
            f"Workflow topic: {run.topic}\n"
            f"Step description: {step.description}\n"
            f"Context summary: {self._summarize_text(brief, limit=360)}"
        )

    def _render_integration_output(self, run: WorkflowRun, step: WorkflowStepRun, tool_results: dict[str, Any]) -> str:
        sync_result = tool_results.get("second_me_sync", {})
        workspace = tool_results.get("project", {}) or run.execution_context.get("workspace", {}) or {}
        lines = [
            f"Integration execution for {run.topic}",
            f"- Step: {step.name}",
            f"- Workspace linked workflows: {len((workspace or {}).get('linked_workflows', []))}",
            f"- Required outputs: {', '.join(step.outputs) or 'N/A'}",
        ]
        if sync_result:
            lines.append(f"- Second Me sync status: {sync_result.get('status', 'unknown')}")
            lines.append(f"- Synced instance: {sync_result.get('instance_id', 'N/A')}")
        else:
            lines.append("- No Second Me sync was executed in this step.")
        lines.append("- Recommendation: preserve the current integration contract and capture any missing auth or data-shape requirements before release.")
        return "\n".join(lines)

    def _render_reviewer_output(self, run: WorkflowRun, step: WorkflowStepRun, tool_results: dict[str, Any]) -> str:
        prior_outputs = run.execution_context.get("step_outputs", {})
        admet_result = tool_results.get("admet", {})
        discussion_result = tool_results.get("discussion", {})
        concerns: list[str] = []
        if admet_result.get("lipinski_violations", 0) > 1:
            concerns.append("compound exceeds the usual Lipinski comfort zone")
        if admet_result.get("qed", 1) and admet_result.get("qed", 1) < 0.35:
            concerns.append("compound desirability is low")
        if not prior_outputs:
            concerns.append("review is operating with limited upstream evidence")

        decision = "CONDITIONAL" if concerns else "GO"
        lines = [
            f"Reviewer outcome: {decision}",
            f"- Step: {step.name}",
            f"- Topic: {run.topic}",
            f"- Upstream outputs reviewed: {len(prior_outputs)}",
        ]
        if discussion_result:
            lines.append(f"- Discussion session: {discussion_result.get('session_id', 'N/A')}")
        if concerns:
            lines.append("- Key concerns:")
            lines.extend([f"  {index + 1}. {item}" for index, item in enumerate(concerns)])
            lines.append("- Approval recommendation: approve only if the team accepts the listed conditions and records mitigation actions.")
        else:
            lines.append("- No material scientific blockers were detected in the current workflow context.")
            lines.append("- Approval recommendation: approve and proceed to the next execution stage.")
        return "\n".join(lines)

    def _render_orchestrator_output(self, run: WorkflowRun, step: WorkflowStepRun, tool_results: dict[str, Any]) -> str:
        return (
            f"Workflow orchestration summary\n"
            f"- Topic: {run.topic}\n"
            f"- Active step: {step.name}\n"
            f"- Available tools: {', '.join(step.tool_ids) or 'none'}\n"
            f"- Prior outputs: {len(run.execution_context.get('step_outputs', {}))}\n"
            f"- Tool result keys: {', '.join(tool_results.keys()) or 'none'}"
        )

    def _build_execution_brief(
        self,
        run: WorkflowRun,
        step: WorkflowStepRun,
        input_payload: dict,
        tool_results: dict[str, Any],
    ) -> str:
        lines = [
            f"Workflow: {run.template_name}",
            f"Topic: {run.topic}",
            f"Step: {step.name}",
            f"Description: {step.description}",
        ]
        if step.capability_id:
            lines.append(f"Capability: {step.capability_id}")
        if step.required_skills:
            lines.append(f"Required skills: {', '.join(step.required_skills)}")
        if step.outputs:
            lines.append(f"Expected outputs: {', '.join(step.outputs)}")
        if input_payload:
            lines.append(f"Runtime input: {json.dumps(input_payload, ensure_ascii=False)}")

        workspace = run.execution_context.get("workspace", {})
        if workspace:
            lines.append(f"Workspace agents: {', '.join(workspace.get('default_agents', [])[:6])}")
            lines.append(f"Workspace tools: {', '.join(workspace.get('enabled_tools', [])[:6])}")

        memory_context = run.execution_context.get("memory_context", {})
        for block in memory_context.get("context_blocks", [])[:3]:
            lines.append(f"Memory [{block['memory_type']}]: {block['title']} -> {self._summarize_text(block['content'], 180)}")

        step_outputs = run.execution_context.get("step_outputs", {})
        for item in list(step_outputs.values())[-3:]:
            lines.append(f"Previous output [{item['name']}]: {self._summarize_text(item['summary'], 180)}")

        if tool_results:
            for tool_name, result in tool_results.items():
                lines.append(f"Tool result [{tool_name}]: {self._summarize_text(json.dumps(result, ensure_ascii=False), 220)}")

        return "\n".join(lines)

    def _run_admet_tool(self, run: WorkflowRun, input_payload: dict) -> dict:
        if not self.compound_tracker:
            return {"error": "compound tracker unavailable"}
        smiles = input_payload.get("smiles") or (input_payload.get("compound") or {}).get("smiles")
        if not smiles:
            compounds = self.compound_tracker.list_compounds(project_id=run.project_id)
            if compounds:
                smiles = compounds[0].get("smiles", "")
        if not smiles:
            return {"error": "no compound context provided"}

        from drug_modeling.admet_bridge import ADMETBridge

        return ADMETBridge().predict(smiles)

    def _run_discussion_tool(self, run: WorkflowRun, step: WorkflowStepRun, input_payload: dict) -> dict:
        if not self.discussion_engine:
            return {"error": "discussion engine unavailable"}

        participant_ids = self._select_discussion_participants(run, step)
        if not participant_ids:
            return {"error": "no participants available"}

        session = self.discussion_engine.create_discussion(run.topic, participant_ids)
        self.discussion_engine.run_round_robin(
            session.session_id,
            context=self._build_execution_brief(run, step, input_payload, {}),
            max_rounds=max(1, int(input_payload.get("rounds", 1))),
        )
        summary = self.discussion_engine.summarize_discussion(session.session_id)
        if self.workspace_store:
            self.workspace_store.link_discussion(run.project_id, session.session_id)
        return {
            "session_id": session.session_id,
            "participants": participant_ids,
            "summary": summary,
        }

    def _run_second_me_sync(self, run: WorkflowRun, input_payload: dict) -> dict:
        if not self.second_me or not self.second_me_bindings:
            return {"error": "second me integration unavailable"}

        instance_id = input_payload.get("instance_id", "")
        binding = None
        if instance_id:
            matches = self.second_me_bindings.list_bindings(project_id=run.project_id, instance_id=instance_id)
            binding = matches[0] if matches else None
        if not binding:
            bindings = self.second_me_bindings.list_bindings(project_id=run.project_id)
            binding = bindings[0] if bindings else None
        if not binding:
            return {"error": "no linked Second Me binding for project"}

        project = self.kanban.get_project(run.project_id) if self.kanban else {}
        workspace = self.workspace_store.get_workspace(run.project_id) if self.workspace_store else {}
        memory_entries = self.project_memory.list_entries(run.project_id, limit=8) if self.project_memory else []
        decisions = self.decision_logger.get_decision_history(project_id=run.project_id)[:6] if self.decision_logger else []
        return self.second_me.sync_project_context(
            binding["instance_id"],
            project=project,
            workspace=workspace,
            memory_entries=memory_entries,
            decisions=decisions,
            workflow_run=asdict(run),
            sync_note=input_payload.get("sync_note", f"Workflow step sync: {run.topic} / {run.run_id}"),
        )

    def _record_step_memory(self, run: WorkflowRun, step: WorkflowStepRun, output_text: str) -> Optional[dict]:
        if not self.project_memory:
            return None
        entry = self.project_memory.add_entry(
            project_id=run.project_id,
            memory_type="workflow_execution",
            title=f"{run.template_name}: {step.name}",
            content=output_text,
            tags=["workflow_execution", run.template_id, step.step_id],
            source="workflow.execute_step",
            related_agents=[step.agent_id],
        )
        if self.workspace_store:
            self.workspace_store.add_note(run.project_id, f"Workflow execution stored: {step.name}")
        return {
            "type": "memory",
            "id": entry["entry_id"],
            "summary": entry["title"],
            "linked_at": datetime.now().isoformat(),
        }

    def _record_step_decision(
        self,
        run: WorkflowRun,
        step: WorkflowStepRun,
        *,
        output_text: str,
        related_memory_id: str = "",
        related_discussions: list[str] | None = None,
    ) -> Optional[dict]:
        if not self.decision_logger:
            return None
        if not step.approval_required and "decision_record" not in step.outputs and "alignment_review" not in step.outputs:
            return None

        decision = self._infer_decision_label(output_text)
        record = self.decision_logger.log_decision(
            project_id=run.project_id,
            topic=f"{run.topic} / {step.name}",
            decision=decision,
            rationale=output_text,
            participants=[step.agent_id],
            opinions=[{"agent_id": step.agent_id, "summary": self._summarize_text(output_text, 320)}],
            workflow_run_id=run.run_id,
            related_memory_entries=[related_memory_id] if related_memory_id else [],
            related_discussions=related_discussions or [],
        )
        if self.kanban:
            self.kanban.add_decision(run.project_id, decision, output_text)
        if self.workspace_store:
            self.workspace_store.link_decision(run.project_id, record.decision_id)
        return {
            "type": "decision",
            "id": record.decision_id,
            "summary": decision,
            "linked_at": datetime.now().isoformat(),
        }

    def _select_discussion_participants(self, run: WorkflowRun, step: WorkflowStepRun) -> list[str]:
        participants: list[str] = []
        workspace = self.workspace_store.get_workspace(run.project_id) if self.workspace_store else {}
        agent_ids = (workspace or {}).get("default_agents", []) or []
        if not agent_ids and self.agent_registry:
            agent_ids = [agent["agent_id"] for agent in self.agent_registry.list_agents(category="domain")]
        for agent_id in agent_ids:
            agent = self.agent_registry.get_agent(agent_id) if self.agent_registry else None
            if not agent or not agent.get("role_id"):
                continue
            participants.append(self._ensure_twin(agent["role_id"], agent.get("name", agent_id)))
        if not participants and self.agent_registry:
            current_agent = self.agent_registry.get_agent(step.agent_id)
            if current_agent and current_agent.get("role_id"):
                participants.append(self._ensure_twin(current_agent["role_id"], current_agent.get("name", step.agent_id)))
        return participants

    def _ensure_twin(self, role_id: str, name: str) -> str:
        twin_id = f"{role_id}_{name}"
        if self.twin_engine and twin_id in getattr(self.twin_engine.personality, "_profiles", {}):
            return twin_id

        if self.twin_engine:
            for existing_twin_id in getattr(self.twin_engine.personality, "_profiles", {}).keys():
                if existing_twin_id.startswith(f"{role_id}_"):
                    return existing_twin_id
            self.twin_engine.create_twin(role_id, name)
            return twin_id
        return twin_id

    def _infer_decision_label(self, text: str) -> str:
        normalized = text.lower()
        if "no-go" in normalized or "不建议" in normalized or "终止" in normalized:
            return "NO-GO"
        if "conditional" in normalized or "条件" in normalized or "补充" in normalized or "mitigation" in normalized:
            return "CONDITIONAL"
        return "GO"

    def _summarize_text(self, text: str, limit: int = 220) -> str:
        compact = " ".join(str(text).split())
        if len(compact) <= limit:
            return compact
        return f"{compact[:limit - 3]}..."

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
                        tool_ids=["tool.project_memory", "tool.drugmind_scenario", "tool.drug_discovery_execute"],
                        outputs=["target_dossier"],
                        capability_id="capability.structural_research",
                    ),
                    WorkflowStepTemplate(
                        step_id="project_triage",
                        name="Project Triage",
                        description="Frame the target against program constraints and milestones.",
                        agent_id="agent.project_lead",
                        required_skills=["skill.project_triage"],
                        tool_ids=["tool.project_kanban", "tool.project_memory", "tool.drug_discovery_execute"],
                        outputs=["priority_plan"],
                        capability_id="capability.target_landscape",
                    ),
                    WorkflowStepTemplate(
                        step_id="decision_review",
                        name="Decision Review",
                        description="Review the evidence package and produce a go-forward recommendation.",
                        agent_id="agent.reviewer",
                        required_skills=["skill.go_nogo_review"],
                        tool_ids=["tool.drugmind_discuss", "tool.project_memory"],
                        outputs=["decision_record"],
                        approval_required=True,
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
                        tool_ids=["tool.drugmind_compound", "tool.project_memory", "tool.drug_discovery_execute"],
                        outputs=["chemistry_hypotheses"],
                        capability_id="capability.series_design",
                    ),
                    WorkflowStepTemplate(
                        step_id="admet_review",
                        name="ADMET Review",
                        description="Assess ADMET liabilities for the current candidates.",
                        agent_id="agent.pharmacologist",
                        required_skills=["skill.admet_assessment"],
                        tool_ids=["tool.drugmind_admet", "tool.project_memory", "tool.drug_discovery_execute"],
                        outputs=["admet_flags"],
                        capability_id="capability.admet_risk",
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
                template_id="workflow.discovery_bootstrap",
                name="Discovery Bootstrap Workflow",
                category="drug_discovery",
                description="Bootstrap a new project with structural research, target framing, and assay strategy.",
                tags=["bootstrap", "dmta", "target"],
                steps=[
                    WorkflowStepTemplate(
                        step_id="structural_research",
                        name="Structural Research",
                        description="Map sequence, structure, and prior-art evidence before program execution.",
                        agent_id="agent.biologist",
                        required_skills=["skill.structural_research"],
                        tool_ids=["tool.by_mcp_bridge", "tool.project_memory", "tool.drug_discovery_execute"],
                        outputs=["target_structure_plan"],
                        capability_id="capability.structural_research",
                    ),
                    WorkflowStepTemplate(
                        step_id="landscape_review",
                        name="Landscape Review",
                        description="Turn research into a target landscape and program rationale.",
                        agent_id="agent.discovery_strategist",
                        required_skills=["skill.target_evaluation", "skill.project_triage"],
                        tool_ids=["tool.project_memory", "tool.project_kanban", "tool.drug_discovery_execute"],
                        outputs=["target_dossier"],
                        capability_id="capability.target_landscape",
                    ),
                    WorkflowStepTemplate(
                        step_id="assay_cascade",
                        name="Assay Cascade",
                        description="Define the assay stack and quality gates for the next stage.",
                        agent_id="agent.discovery_strategist",
                        required_skills=["skill.assay_strategy"],
                        tool_ids=["tool.project_memory", "tool.drug_discovery_execute"],
                        outputs=["assay_stack"],
                        capability_id="capability.assay_strategy",
                    ),
                    WorkflowStepTemplate(
                        step_id="bootstrap_review",
                        name="Bootstrap Review",
                        description="Review whether the project is ready to enter active execution.",
                        agent_id="agent.reviewer",
                        required_skills=["skill.go_nogo_review", "skill.evidence_review"],
                        tool_ids=["tool.project_memory"],
                        outputs=["decision_record"],
                        approval_required=True,
                    ),
                ],
            ),
            WorkflowTemplate(
                template_id="workflow.hit_triage",
                name="Hit Triage Workflow",
                category="drug_discovery",
                description="Screen, rank, and triage hit matter before expensive chemistry cycles.",
                tags=["hits", "screening", "ranking"],
                steps=[
                    WorkflowStepTemplate(
                        step_id="screen_rank",
                        name="Screen & Rank",
                        description="Run DMTA screening and shortlist high-quality compounds.",
                        agent_id="agent.dmpk_strategist",
                        required_skills=["skill.dmta_screening", "skill.admet_assessment"],
                        tool_ids=["tool.by_screening_bridge", "tool.drugmind_admet", "tool.drug_discovery_execute"],
                        outputs=["shortlist"],
                        capability_id="capability.dmta_screening_ranking",
                    ),
                    WorkflowStepTemplate(
                        step_id="triage_hits",
                        name="Triage Hits",
                        description="Separate advance/rescue/stop compounds and prepare the next cycle.",
                        agent_id="agent.discovery_strategist",
                        required_skills=["skill.hit_triage", "skill.project_triage"],
                        tool_ids=["tool.drugmind_compound", "tool.project_memory", "tool.drug_discovery_execute"],
                        outputs=["ranked_hits"],
                        capability_id="capability.hit_triage",
                    ),
                    WorkflowStepTemplate(
                        step_id="hit_gate_review",
                        name="Hit Gate Review",
                        description="Review the shortlist and approve the next chemistry plan.",
                        agent_id="agent.reviewer",
                        required_skills=["skill.go_nogo_review"],
                        tool_ids=["tool.project_memory"],
                        outputs=["decision_record"],
                        approval_required=True,
                    ),
                ],
            ),
            WorkflowTemplate(
                template_id="workflow.candidate_nomination",
                name="Candidate Nomination Workflow",
                category="drug_discovery",
                description="Assemble a nomination-ready package and synchronize it into SecondMe.",
                tags=["candidate", "second_me", "gate"],
                steps=[
                    WorkflowStepTemplate(
                        step_id="nominate_candidate",
                        name="Nominate Candidate",
                        description="Identify the lead candidate and backup compounds.",
                        agent_id="agent.dmpk_strategist",
                        required_skills=["skill.candidate_nomination"],
                        tool_ids=["tool.project_memory", "tool.project_kanban", "tool.drug_discovery_execute"],
                        outputs=["lead_candidate", "gate_decision"],
                        capability_id="capability.candidate_nomination",
                    ),
                    WorkflowStepTemplate(
                        step_id="translational_package",
                        name="Translational Package",
                        description="Build the milestone path from candidate to preclinical evidence package.",
                        agent_id="agent.discovery_strategist",
                        required_skills=["skill.translational_strategy"],
                        tool_ids=["tool.project_memory", "tool.project_kanban", "tool.drug_discovery_execute"],
                        outputs=["translational_plan"],
                        capability_id="capability.translational_plan",
                    ),
                    WorkflowStepTemplate(
                        step_id="persona_sync",
                        name="Persona Sync",
                        description="Synchronize the nomination package into linked SecondMe personas.",
                        agent_id="agent.integration",
                        required_skills=["skill.campaign_memory", "skill.integration_delivery"],
                        tool_ids=["tool.project_memory", "tool.drug_discovery_execute"],
                        outputs=["persona_sync"],
                        capability_id="capability.second_me_program_sync",
                    ),
                    WorkflowStepTemplate(
                        step_id="nomination_review",
                        name="Nomination Review",
                        description="Final review before the candidate package is treated as decision-ready.",
                        agent_id="agent.reviewer",
                        required_skills=["skill.go_nogo_review"],
                        tool_ids=["tool.project_memory"],
                        outputs=["alignment_review"],
                        approval_required=True,
                    ),
                ],
            ),
            WorkflowTemplate(
                template_id="workflow.biologics_campaign",
                name="Biologics Campaign Workflow",
                category="drug_discovery",
                description="Run a BY-inspired biologics campaign inside DrugMind.",
                tags=["biologics", "by", "campaign"],
                steps=[
                    WorkflowStepTemplate(
                        step_id="research_target",
                        name="Research Target",
                        description="Gather structure, sequence, and prior-art evidence for the biologics campaign.",
                        agent_id="agent.biologist",
                        required_skills=["skill.structural_research"],
                        tool_ids=["tool.by_mcp_bridge", "tool.project_memory", "tool.drug_discovery_execute"],
                        outputs=["target_structure_plan"],
                        capability_id="capability.structural_research",
                    ),
                    WorkflowStepTemplate(
                        step_id="plan_campaign",
                        name="Plan Campaign",
                        description="Plan research-design-screen-rank with scaffolds and Tamarind estimates.",
                        agent_id="agent.discovery_strategist",
                        required_skills=["skill.biologics_campaign"],
                        tool_ids=["tool.by_biologics_pipeline", "tool.project_memory", "tool.drug_discovery_execute"],
                        outputs=["campaign_plan", "design_estimate"],
                        capability_id="capability.biologics_design_campaign",
                    ),
                    WorkflowStepTemplate(
                        step_id="record_campaign_memory",
                        name="Record Campaign Memory",
                        description="Summarize campaign state for knowledge carry-forward and SecondMe sync.",
                        agent_id="agent.integration",
                        required_skills=["skill.campaign_memory"],
                        tool_ids=["tool.project_memory", "tool.drug_discovery_execute"],
                        outputs=["campaign_memory_summary"],
                        capability_id="capability.campaign_memory",
                    ),
                    WorkflowStepTemplate(
                        step_id="campaign_review",
                        name="Campaign Review",
                        description="Review whether the biologics campaign is ready to progress.",
                        agent_id="agent.reviewer",
                        required_skills=["skill.go_nogo_review"],
                        tool_ids=["tool.project_memory"],
                        outputs=["decision_record"],
                        approval_required=True,
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
                        approval_required=True,
                    ),
                ],
            ),
            WorkflowTemplate(
                template_id="workflow.second_me_enablement",
                name="Second Me Enablement Workflow",
                category="platform",
                description="Bind a DrugMind project to a Second Me instance and sync execution context.",
                tags=["second_me", "integration", "workspace"],
                steps=[
                    WorkflowStepTemplate(
                        step_id="prepare_binding",
                        name="Prepare Binding",
                        description="Decide which project, user, and twin should be linked to the external persona.",
                        agent_id="agent.integration",
                        required_skills=["skill.integration_delivery", "skill.workflow_planning"],
                        tool_ids=["tool.second_me_sync", "tool.project_memory"],
                        outputs=["binding_contract"],
                    ),
                    WorkflowStepTemplate(
                        step_id="sync_project_context",
                        name="Sync Project Context",
                        description="Push the latest workspace, memory, and workflow state into the linked Second Me instance.",
                        agent_id="agent.integration",
                        required_skills=["skill.workflow_planning"],
                        tool_ids=["tool.second_me_project_sync", "tool.project_memory"],
                        outputs=["context_snapshot"],
                    ),
                    WorkflowStepTemplate(
                        step_id="review_alignment",
                        name="Review Alignment",
                        description="Review whether the exported identity and synced context are ready for user-facing usage.",
                        agent_id="agent.reviewer",
                        required_skills=["skill.evidence_review"],
                        tool_ids=["tool.project_memory"],
                        outputs=["alignment_review"],
                        approval_required=True,
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

    def _normalize_templates(self):
        changed = False
        capability_defaults = {
            "workflow.target_evaluation": {
                "collect_evidence": ("capability.structural_research", ["tool.drug_discovery_execute"]),
                "project_triage": ("capability.target_landscape", ["tool.drug_discovery_execute"]),
            },
            "workflow.lead_optimization": {
                "sar_review": ("capability.series_design", ["tool.drug_discovery_execute"]),
                "admet_review": ("capability.admet_risk", ["tool.drug_discovery_execute"]),
            },
        }
        for template in self.templates.values():
            for step in template.steps:
                if step.agent_id == "agent.reviewer" and not step.approval_required:
                    step.approval_required = True
                    changed = True
                capability_info = capability_defaults.get(template.template_id, {}).get(step.step_id)
                if capability_info:
                    capability_id, required_tools = capability_info
                    if not step.capability_id:
                        step.capability_id = capability_id
                        changed = True
                    for tool_id in required_tools:
                        if tool_id not in step.tool_ids:
                            step.tool_ids.append(tool_id)
                            changed = True
        if changed:
            self._save_templates()

    def _normalize_runs(self):
        changed = False
        template_lookup = {
            template_id: {step.step_id: step for step in template.steps}
            for template_id, template in self.templates.items()
        }
        for run in self.runs.values():
            for step in run.steps:
                if not step.owner_id:
                    step.owner_type = step.owner_type or "agent"
                    step.owner_id = step.agent_id
                    if self.agent_registry:
                        agent = self.agent_registry.get_agent(step.agent_id)
                        step.owner_label = step.owner_label or (agent or {}).get("name", step.agent_id)
                    else:
                        step.owner_label = step.owner_label or step.agent_id
                    changed = True
                template_step = template_lookup.get(run.template_id, {}).get(step.step_id)
                if template_step and not step.capability_id and template_step.capability_id:
                    step.capability_id = template_step.capability_id
                    changed = True
                if step.agent_id != "agent.reviewer":
                    continue
                if not step.approval_required:
                    step.approval_required = True
                    changed = True
                if step.status in {"completed", "failed", "rejected"}:
                    continue
                if step.approval_status == "not_required":
                    step.approval_status = "pending" if step.status == "awaiting_approval" else "required"
                    changed = True
        if changed:
            self._save_runs()

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
