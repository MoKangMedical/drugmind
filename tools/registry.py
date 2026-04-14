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
                tool_id="tool.drug_discovery_capability_catalog",
                name="Drug Discovery Capability Catalog",
                description="List the AI drug-discovery capabilities and implementation blueprints available in DrugMind.",
                source="internal",
                entrypoint="/api/v2/drug-discovery/capabilities",
                tags=["drug_discovery", "capability", "catalog"],
                scopes=["project:read"],
            ),
            ToolSpec(
                tool_id="tool.drug_discovery_execute",
                name="Drug Discovery Execute",
                description="Execute a concrete AI drug-discovery capability for a project and store the artifact.",
                source="internal",
                entrypoint="/api/v2/projects/{project_id}/capabilities/{capability_id}/execute",
                input_schema={"input_payload": "object", "triggered_by": "string", "sync_to_second_me": "boolean"},
                tags=["drug_discovery", "capability", "execution"],
                scopes=["project:read", "project:write", "integration:write"],
            ),
            ToolSpec(
                tool_id="tool.by_mcp_bridge",
                name="BY MCP Bridge",
                description="Inspect the reusable PDB, UniProt, SAbDab, campaign, and knowledge MCP contracts adapted from blatant-why.",
                source="internal",
                entrypoint="/api/v2/integrations/blatant-why",
                tags=["integration", "by", "mcp", "biology"],
                scopes=["project:read"],
            ),
            ToolSpec(
                tool_id="tool.by_structural_research",
                name="BY Structural Research",
                description="Run live UniProt, RCSB PDB, and SAbDab queries to assemble a target evidence bundle.",
                source="internal",
                entrypoint="/api/v2/integrations/blatant-why/research",
                input_schema={"project_id": "string", "target": "string", "modality": "string", "organism_id": "int"},
                tags=["integration", "by", "structure", "uniprot", "pdb", "sabdab"],
                scopes=["project:read", "integration:write"],
            ),
            ToolSpec(
                tool_id="tool.by_screening_bridge",
                name="BY Screening Bridge",
                description="Run BY-inspired ADMET-aware screening and Pareto ranking for DrugMind compound series.",
                source="internal",
                entrypoint="/api/v2/integrations/blatant-why/screening",
                input_schema={"project_id": "string", "compound_ids": "list[str]"},
                tags=["integration", "by", "screening", "ranking"],
                scopes=["project:read", "project:write"],
            ),
            ToolSpec(
                tool_id="tool.by_biologics_pipeline",
                name="BY Biologics Pipeline",
                description="Plan a BY-inspired biologics campaign with research, design, screening, ranking, and Tamarind compute estimates.",
                source="internal",
                entrypoint="/api/v2/integrations/blatant-why/biologics-pipeline",
                input_schema={"project_id": "string", "modality": "string", "scaffolds": "list[str]"},
                tags=["integration", "by", "biologics", "campaign"],
                scopes=["project:read", "integration:write"],
            ),
            ToolSpec(
                tool_id="tool.medi_pharma_bridge",
                name="MediPharma Bridge",
                description="Inspect MediPharma integration status, health, ecosystem, and supported runtime actions.",
                source="internal",
                entrypoint="/api/v2/integrations/medi-pharma",
                tags=["integration", "medi_pharma", "drug_discovery"],
                scopes=["integration:read"],
            ),
            ToolSpec(
                tool_id="tool.medi_pharma_target_discovery",
                name="MediPharma Target Discovery",
                description="Call MediPharma target discovery from disease context.",
                source="internal",
                entrypoint="/api/v2/integrations/medi-pharma/targets/discover",
                input_schema={"disease": "string", "max_papers": "int", "top_n": "int"},
                tags=["integration", "medi_pharma", "target"],
                scopes=["integration:write", "project:read"],
            ),
            ToolSpec(
                tool_id="tool.medi_pharma_virtual_screening",
                name="MediPharma Virtual Screening",
                description="Run MediPharma virtual screening against a configured ChEMBL target.",
                source="internal",
                entrypoint="/api/v2/integrations/medi-pharma/screening/run",
                input_schema={"target_chembl_id": "string", "max_compounds": "int", "top_n": "int", "use_docking": "boolean"},
                tags=["integration", "medi_pharma", "screening"],
                scopes=["integration:write", "project:read"],
            ),
            ToolSpec(
                tool_id="tool.medi_pharma_generation",
                name="MediPharma Molecule Generation",
                description="Generate candidate molecules through the MediPharma generation endpoint.",
                source="internal",
                entrypoint="/api/v2/integrations/medi-pharma/generate",
                input_schema={"target_name": "string", "scaffold": "string", "n_generate": "int", "top_n": "int"},
                tags=["integration", "medi_pharma", "generation"],
                scopes=["integration:write", "project:read"],
            ),
            ToolSpec(
                tool_id="tool.medi_pharma_admet",
                name="MediPharma ADMET",
                description="Call MediPharma single or batch ADMET prediction.",
                source="internal",
                entrypoint="/api/v2/integrations/medi-pharma/admet/*",
                input_schema={"smiles": "string", "smiles_list": "list[str]"},
                tags=["integration", "medi_pharma", "admet"],
                scopes=["integration:write", "compound:read"],
            ),
            ToolSpec(
                tool_id="tool.medi_pharma_lead_optimization",
                name="MediPharma Lead Optimization",
                description="Run MediPharma multi-objective lead optimization.",
                source="internal",
                entrypoint="/api/v2/integrations/medi-pharma/optimize",
                input_schema={"smiles": "string", "objective_weights": "object", "max_generations": "int"},
                tags=["integration", "medi_pharma", "lead_opt"],
                scopes=["integration:write", "project:read"],
            ),
            ToolSpec(
                tool_id="tool.medi_pharma_pipeline",
                name="MediPharma Pipeline",
                description="Launch the full MediPharma discovery pipeline from within DrugMind.",
                source="internal",
                entrypoint="/api/v2/integrations/medi-pharma/pipeline/run",
                input_schema={"disease": "string", "target": "string", "target_chembl_id": "string"},
                tags=["integration", "medi_pharma", "pipeline"],
                scopes=["integration:write", "project:read"],
            ),
            ToolSpec(
                tool_id="tool.medi_pharma_knowledge_report",
                name="MediPharma Knowledge Report",
                description="Generate a MediPharma knowledge report for a target-disease pair.",
                source="internal",
                entrypoint="/api/v2/integrations/medi-pharma/knowledge/report",
                input_schema={"target": "string", "disease": "string", "include_patents": "boolean"},
                tags=["integration", "medi_pharma", "knowledge"],
                scopes=["integration:write", "project:read"],
            ),
            ToolSpec(
                tool_id="tool.tamarind_job_control",
                name="Tamarind Job Control",
                description="Submit, inspect, poll, and retrieve results from real Tamarind compute jobs.",
                source="internal",
                entrypoint="/api/v2/integrations/tamarind/jobs",
                input_schema={"job_name": "string", "job_type": "string", "settings": "object"},
                tags=["integration", "tamarind", "compute", "biologics"],
                scopes=["integration:write"],
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
            ToolSpec(
                tool_id="tool.second_me_project_sync",
                name="Second Me Project Sync",
                description="Push project workspace, memory, and decision context into a linked Second Me instance.",
                source="internal",
                entrypoint="/api/v2/projects/{project_id}/second-me/sync",
                input_schema={"instance_id": "string", "workflow_run_id": "string", "sync_note": "string"},
                tags=["second_me", "integration", "workflow"],
                scopes=["integration:write", "project:read"],
            ),
            ToolSpec(
                tool_id="tool.mimo_media",
                name="MIMO Media",
                description="Generate audio/video assets using Xiaomi MIMO API.",
                source="internal",
                entrypoint="/api/v2/media/*",
                input_schema={"text": "string", "prompt": "string", "voice": "string", "format": "string"},
                tags=["media", "mimo", "audio", "video"],
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
