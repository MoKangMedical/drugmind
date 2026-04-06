"""
Platform tool registry.
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
class ToolSpec:
    """Governed tool definition."""

    tool_id: str
    name: str
    description: str
    source: str
    entrypoint: str
    input_schema: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)
    auth_mode: str = "none"
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


class ToolRegistry:
    """Stores the platform's tool contract surface."""

    def __init__(self, data_dir: str = "./drugmind_data/platform/tools"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.data_dir / "tools.json"
        self.tools: dict[str, ToolSpec] = {}
        self._load()
        self._seed_defaults()

    def list_tools(self, tag: str = "", enabled_only: bool = True) -> list[dict]:
        tools = list(self.tools.values())
        if tag:
            tools = [tool for tool in tools if tag in tool.tags]
        if enabled_only:
            tools = [tool for tool in tools if tool.enabled]
        tools.sort(key=lambda tool: tool.name)
        return [asdict(tool) for tool in tools]

    def get_tool(self, tool_id: str) -> Optional[dict]:
        tool = self.tools.get(tool_id)
        return asdict(tool) if tool else None

    def register_tool(self, tool: ToolSpec) -> dict:
        tool.updated_at = datetime.now().isoformat()
        self.tools[tool.tool_id] = tool
        self._save()
        return asdict(tool)

    def count(self) -> int:
        return len(self.tools)

    def _seed_defaults(self):
        defaults = [
            ToolSpec(
                tool_id="tool.drugmind_ask",
                name="DrugMind Ask",
                description="Query the role-based drug discovery team for expert responses.",
                source="mcp",
                entrypoint="drugmind_ask",
                input_schema={"question": "string", "roles": "list[str]", "context": "string"},
                tags=["mcp", "agent", "qa"],
                scopes=["workspace:read"],
            ),
            ToolSpec(
                tool_id="tool.drugmind_discuss",
                name="DrugMind Discuss",
                description="Run a multi-agent discussion on a topic.",
                source="mcp",
                entrypoint="drugmind_discuss",
                input_schema={"topic": "string", "context": "string", "rounds": "int"},
                tags=["mcp", "discussion"],
                scopes=["workspace:write"],
            ),
            ToolSpec(
                tool_id="tool.drugmind_admet",
                name="DrugMind ADMET",
                description="Evaluate a compound's ADMET-related descriptors.",
                source="mcp",
                entrypoint="drugmind_admet",
                input_schema={"smiles": "string"},
                tags=["mcp", "chemistry", "admet"],
                scopes=["compound:read"],
            ),
            ToolSpec(
                tool_id="tool.drugmind_scenario",
                name="DrugMind Scenario",
                description="Retrieve a scenario checklist for a drug discovery stage.",
                source="mcp",
                entrypoint="drugmind_scenario",
                input_schema={"scenario": "string"},
                tags=["mcp", "workflow"],
                scopes=["workspace:read"],
            ),
            ToolSpec(
                tool_id="tool.drugmind_compound",
                name="DrugMind Compound",
                description="Manage the compound pipeline and add compounds.",
                source="mcp",
                entrypoint="drugmind_compound",
                input_schema={"action": "string", "compound_id": "string", "smiles": "string"},
                tags=["mcp", "compound", "pipeline"],
                scopes=["compound:write"],
            ),
            ToolSpec(
                tool_id="tool.project_kanban",
                name="Project Kanban",
                description="Access the internal project board and milestones.",
                source="internal",
                entrypoint="/api/v2/projects/board",
                tags=["project", "board"],
                scopes=["project:read"],
            ),
            ToolSpec(
                tool_id="tool.project_memory",
                name="Project Memory",
                description="Store and retrieve project memory entries and decision context.",
                source="internal",
                entrypoint="/api/v2/projects/{project_id}/memory",
                tags=["memory", "project"],
                scopes=["project:read", "project:write"],
            ),
            ToolSpec(
                tool_id="tool.second_me_sync",
                name="Second Me Sync",
                description="Create, chat with, and export linked Second Me instances.",
                source="internal",
                entrypoint="/api/v2/second-me/*",
                tags=["second_me", "integration"],
                scopes=["integration:write"],
            ),
        ]

        changed = False
        for tool in defaults:
            if tool.tool_id not in self.tools:
                self.tools[tool.tool_id] = tool
                changed = True
        if changed:
            self._save()
            logger.info("✅ Tool registry seeded with %s tools", len(self.tools))

    def _save(self):
        data = {tool_id: asdict(tool) for tool_id, tool in self.tools.items()}
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load(self):
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            self.tools = {
                tool_id: ToolSpec(**payload)
                for tool_id, payload in data.items()
            }
        except Exception as exc:
            logger.warning("加载 tool registry 失败: %s", exc)
            self.tools = {}
