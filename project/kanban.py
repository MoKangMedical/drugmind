"""
项目看板
药物研发项目管理
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Project:
    """药物研发项目"""
    project_id: str
    name: str
    target: str = ""
    disease: str = ""
    status: str = "active"  # active / paused / completed
    stage: str = "target_id"  # target_id / screening / hit_to_lead / lead_opt / candidate
    compounds: list[dict] = field(default_factory=list)
    milestones: list[dict] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)
    budget_total: float = 0
    budget_spent: float = 0
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class KanbanBoard:
    """项目看板"""

    STAGES = [
        ("target_id", "🎯 靶点确认"),
        ("screening", "🔬 虚拟筛选"),
        ("hit_to_lead", "🧪 Hit-to-Lead"),
        ("lead_opt", "💡 先导优化"),
        ("candidate", "🏆 候选化合物"),
        ("preclinical", "🐭 临床前"),
        ("clinical", "🏥 临床"),
    ]

    def __init__(self, data_dir: str = "./drugmind_data/projects"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.projects: dict[str, Project] = {}
        self._load()

    def create_project(
        self,
        project_id: str,
        name: str,
        target: str = "",
        disease: str = "",
        budget: float = 0
    ) -> Project:
        """创建项目"""
        project = Project(
            project_id=project_id,
            name=name,
            target=target,
            disease=disease,
            budget_total=budget,
        )
        self.projects[project_id] = project
        self._save()
        logger.info(f"创建项目: {name} (靶点: {target})")
        return project

    def get_project(self, project_id: str) -> dict | None:
        project = self.projects.get(project_id)
        return asdict(project) if project else None

    def list_projects(self, status: str = "") -> list[dict]:
        projects = list(self.projects.values())
        if status:
            projects = [project for project in projects if project.status == status]
        projects.sort(key=lambda project: project.updated_at or project.created_at, reverse=True)
        return [asdict(project) for project in projects]

    def advance_stage(self, project_id: str, compound_id: str = ""):
        """推进项目阶段"""
        project = self.projects.get(project_id)
        if not project:
            return

        stage_order = [s[0] for s in self.STAGES]
        current_idx = stage_order.index(project.stage) if project.stage in stage_order else 0

        if current_idx < len(stage_order) - 1:
            project.stage = stage_order[current_idx + 1]
            project.updated_at = datetime.now().isoformat()
            project.milestones.append({
                "type": "stage_advance",
                "from": stage_order[current_idx],
                "to": project.stage,
                "compound_id": compound_id,
                "timestamp": datetime.now().isoformat()
            })
            self._save()

    def add_decision(
        self,
        project_id: str,
        decision: str,
        rationale: str
    ):
        """添加决策记录"""
        project = self.projects.get(project_id)
        if project:
            project.decisions.append({
                "decision": decision,
                "rationale": rationale,
                "timestamp": datetime.now().isoformat()
            })
            self._save()

    def link_compound(self, project_id: str, compound_id: str, compound_name: str = ""):
        project = self.projects.get(project_id)
        if not project:
            return
        if any(item.get("compound_id") == compound_id for item in project.compounds):
            return
        project.compounds.append({
            "compound_id": compound_id,
            "name": compound_name or compound_id,
            "linked_at": datetime.now().isoformat(),
        })
        project.updated_at = datetime.now().isoformat()
        self._save()

    def count(self) -> int:
        return len(self.projects)

    def get_board(self) -> dict:
        """获取看板数据"""
        board = {stage[0]: {"name": stage[1], "projects": []} for stage in self.STAGES}

        for project in self.projects.values():
            stage = project.stage
            if stage in board:
                board[stage]["projects"].append({
                    "project_id": project.project_id,
                    "name": project.name,
                    "target": project.target,
                    "disease": project.disease,
                    "compounds": len(project.compounds),
                    "status": project.status,
                })

        return board

    def _save(self):
        """持久化"""
        data = {k: asdict(v) for k, v in self.projects.items()}
        path = self.data_dir / "projects.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load(self):
        path = self.data_dir / "projects.json"
        if path.exists():
            data = json.loads(path.read_text())
            self.projects = {k: Project(**v) for k, v in data.items()}
