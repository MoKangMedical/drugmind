"""
化合物追踪模块
管理药物研发项目中的化合物进展
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Compound:
    """化合物"""
    compound_id: str
    smiles: str
    name: str = ""
    project_id: str = ""
    stage: str = "hit"  # hit / lead / candidate / clinical
    activity_pIC50: float = 0.0
    admet_score: float = 0.0
    sa_score: float = 0.0
    notes: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class CompoundTracker:
    """化合物追踪器"""

    def __init__(self, data_dir: str = "./drugmind_data/compounds"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.compounds: dict[str, Compound] = {}

    def add_compound(self, compound_id: str, smiles: str, **kwargs) -> Compound:
        """添加化合物"""
        comp = Compound(compound_id=compound_id, smiles=smiles, **kwargs)
        self.compounds[compound_id] = comp
        self._save()
        return comp

    def update_stage(self, compound_id: str, new_stage: str):
        """更新开发阶段"""
        if compound_id in self.compounds:
            self.compounds[compound_id].stage = new_stage
            self.compounds[compound_id].updated_at = datetime.now().isoformat()
            self._save()

    def add_note(self, compound_id: str, note: str):
        """添加备注"""
        if compound_id in self.compounds:
            self.compounds[compound_id].notes.append(
                f"[{datetime.now().strftime('%m-%d %H:%M')}] {note}"
            )
            self._save()

    def list_by_stage(self, stage: str) -> list[dict]:
        """按阶段列出化合物"""
        return [
            asdict(c) for c in self.compounds.values()
            if c.stage == stage
        ]

    def get_pipeline(self) -> dict:
        """获取化合物管线概览"""
        pipeline = {"hit": [], "lead": [], "candidate": [], "clinical": []}
        for comp in self.compounds.values():
            if comp.stage in pipeline:
                pipeline[comp.stage].append({
                    "id": comp.compound_id,
                    "name": comp.name or comp.compound_id,
                    "smiles": comp.smiles[:30],
                    "activity": comp.activity_pIC50,
                })
        return pipeline

    def _save(self):
        """持久化"""
        data = {k: asdict(v) for k, v in self.compounds.items()}
        path = self.data_dir / "compounds.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
