"""
项目工作区
把项目、Agent、讨论、Workflow、Decision 组织成同一个协作对象
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
class ProjectWorkspace:
    """Project-centric collaboration workspace."""

    project_id: str
    name: str
    owner_id: str = ""
    status: str = "active"
    tags: list[str] = field(default_factory=list)
    members: list[dict] = field(default_factory=list)
    default_agents: list[str] = field(default_factory=list)
    enabled_skills: list[str] = field(default_factory=list)
    enabled_tools: list[str] = field(default_factory=list)
    linked_workflows: list[str] = field(default_factory=list)
    linked_discussions: list[str] = field(default_factory=list)
    linked_decisions: list[str] = field(default_factory=list)
    linked_compounds: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


class ProjectWorkspaceStore:
    """Stores collaboration configuration for each project."""

    def __init__(self, data_dir: str = "./drugmind_data/platform/workspaces"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.data_dir / "workspaces.json"
        self.workspaces: dict[str, ProjectWorkspace] = {}
        self._load()

    def ensure_workspace(
        self,
        project_id: str,
        name: str,
        owner_id: str = "",
        default_agents: list[str] | None = None,
        enabled_skills: list[str] | None = None,
        enabled_tools: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        existing = self.workspaces.get(project_id)
        if existing:
            changed = False
            if name and existing.name != name:
                existing.name = name
                changed = True
            if owner_id and not existing.owner_id:
                existing.owner_id = owner_id
                changed = True
            if tags:
                for tag in tags:
                    if tag not in existing.tags:
                        existing.tags.append(tag)
                        changed = True
            if default_agents:
                for agent_id in default_agents:
                    if agent_id not in existing.default_agents:
                        existing.default_agents.append(agent_id)
                        changed = True
            if enabled_skills:
                for skill_id in enabled_skills:
                    if skill_id not in existing.enabled_skills:
                        existing.enabled_skills.append(skill_id)
                        changed = True
            if enabled_tools:
                for tool_id in enabled_tools:
                    if tool_id not in existing.enabled_tools:
                        existing.enabled_tools.append(tool_id)
                        changed = True
            if changed:
                existing.updated_at = datetime.now().isoformat()
                self._save()
            return asdict(existing)

        workspace = ProjectWorkspace(
            project_id=project_id,
            name=name,
            owner_id=owner_id,
            tags=tags or [],
            default_agents=default_agents or [],
            enabled_skills=enabled_skills or [],
            enabled_tools=enabled_tools or [],
        )
        self.workspaces[project_id] = workspace
        self._save()
        return asdict(workspace)

    def get_workspace(self, project_id: str) -> Optional[dict]:
        workspace = self.workspaces.get(project_id)
        return asdict(workspace) if workspace else None

    def list_workspaces(self, status: str = "") -> list[dict]:
        workspaces = list(self.workspaces.values())
        if status:
            workspaces = [workspace for workspace in workspaces if workspace.status == status]
        workspaces.sort(key=lambda workspace: workspace.updated_at, reverse=True)
        return [asdict(workspace) for workspace in workspaces]

    def update_workspace(self, project_id: str, **updates) -> dict:
        workspace = self.workspaces.get(project_id)
        if not workspace:
            raise ValueError(f"项目工作区不存在: {project_id}")

        list_fields = {
            "tags",
            "members",
            "default_agents",
            "enabled_skills",
            "enabled_tools",
            "linked_workflows",
            "linked_discussions",
            "linked_decisions",
            "linked_compounds",
            "notes",
        }
        for key, value in updates.items():
            if value is None or not hasattr(workspace, key):
                continue
            if key in list_fields and isinstance(value, list):
                setattr(workspace, key, value)
            elif key not in list_fields:
                setattr(workspace, key, value)
        workspace.updated_at = datetime.now().isoformat()
        self._save()
        return asdict(workspace)

    def add_member(self, project_id: str, member: dict) -> dict:
        workspace = self._get(project_id)
        member_id = member.get("user_id") or member.get("id") or member.get("name", "")
        if member_id and not any((item.get("user_id") or item.get("id") or item.get("name")) == member_id for item in workspace.members):
            workspace.members.append(member)
            workspace.updated_at = datetime.now().isoformat()
            self._save()
        return asdict(workspace)

    def add_note(self, project_id: str, note: str) -> dict:
        workspace = self._get(project_id)
        workspace.notes.append(f"[{datetime.now().strftime('%m-%d %H:%M')}] {note}")
        workspace.updated_at = datetime.now().isoformat()
        self._save()
        return asdict(workspace)

    def link_workflow(self, project_id: str, run_id: str) -> dict:
        return self._link(project_id, "linked_workflows", run_id)

    def link_discussion(self, project_id: str, session_id: str) -> dict:
        return self._link(project_id, "linked_discussions", session_id)

    def link_decision(self, project_id: str, decision_id: str) -> dict:
        return self._link(project_id, "linked_decisions", decision_id)

    def link_compound(self, project_id: str, compound_id: str) -> dict:
        return self._link(project_id, "linked_compounds", compound_id)

    def count(self) -> int:
        return len(self.workspaces)

    def _link(self, project_id: str, field_name: str, value: str) -> dict:
        workspace = self._get(project_id)
        values = getattr(workspace, field_name)
        if value and value not in values:
            values.append(value)
            workspace.updated_at = datetime.now().isoformat()
            self._save()
        return asdict(workspace)

    def _get(self, project_id: str) -> ProjectWorkspace:
        workspace = self.workspaces.get(project_id)
        if not workspace:
            raise ValueError(f"项目工作区不存在: {project_id}")
        return workspace

    def _save(self):
        data = {project_id: asdict(workspace) for project_id, workspace in self.workspaces.items()}
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load(self):
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            self.workspaces = {
                project_id: ProjectWorkspace(**payload)
                for project_id, payload in data.items()
            }
        except Exception as exc:
            logger.warning("加载 project workspaces 失败: %s", exc)
            self.workspaces = {}
