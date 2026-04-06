"""
决策追踪模块
记录每个决策的理由、反对意见和最终结论
"""

import json
import logging
import uuid
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DecisionRecord:
    """决策记录"""
    decision_id: str
    project_id: str
    topic: str
    decision: str           # GO / NO-GO / CONDITIONAL
    rationale: str
    participants: list[str]  # twin_ids
    opinions: list[dict]     # 各角色意见
    dissenting: list[str]    # 反对意见
    conditions: list[str]    # 附带条件
    confidence: float = 0.0
    created_by: str = ""
    timestamp: str = ""
    session_id: str = ""
    workflow_run_id: str = ""
    related_memory_entries: list[str] = field(default_factory=list)
    related_discussions: list[str] = field(default_factory=list)


class DecisionLogger:
    """决策追踪器"""

    def __init__(self, log_dir: str = "./drugmind_data/decisions"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.records: dict[str, DecisionRecord] = {}
        self._load()

    def log_decision(
        self,
        project_id: str,
        topic: str,
        decision: str,
        rationale: str,
        participants: list[str],
        opinions: list[dict],
        dissenting: list[str] = None,
        conditions: list[str] = None,
        session_id: str = "",
        confidence: float = 0.0,
        created_by: str = "",
        workflow_run_id: str = "",
        related_memory_entries: list[str] = None,
        related_discussions: list[str] = None,
    ) -> DecisionRecord:
        """记录决策"""
        record = DecisionRecord(
            decision_id=f"dec_{uuid.uuid4().hex[:10]}",
            project_id=project_id,
            topic=topic,
            decision=decision,
            rationale=rationale,
            participants=participants,
            opinions=opinions,
            dissenting=dissenting or [],
            conditions=conditions or [],
            confidence=confidence,
            created_by=created_by,
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            workflow_run_id=workflow_run_id,
            related_memory_entries=related_memory_entries or [],
            related_discussions=related_discussions or [],
        )
        self.records[record.decision_id] = record
        self._save_record(record)
        return record

    def get_decision(self, decision_id: str) -> dict | None:
        record = self.records.get(decision_id)
        return asdict(record) if record else None

    def get_decision_history(self, project_id: str = "", topic_filter: str = "") -> list[dict]:
        """获取决策历史"""
        records = list(self.records.values())
        if project_id:
            records = [record for record in records if record.project_id == project_id]
        if topic_filter:
            records = [record for record in records if topic_filter.lower() in record.topic.lower()]
        records.sort(key=lambda record: record.timestamp, reverse=True)
        return [asdict(record) for record in records]

    def count(self, project_id: str = "") -> int:
        if not project_id:
            return len(self.records)
        return len([record for record in self.records.values() if record.project_id == project_id])

    def _save_record(self, record: DecisionRecord):
        """持久化决策记录"""
        path = self.log_dir / f"{record.decision_id}.json"
        path.write_text(json.dumps(asdict(record), ensure_ascii=False, indent=2))

    def _load(self):
        for path in sorted(self.log_dir.glob("dec_*.json")):
            try:
                payload = json.loads(path.read_text())
                payload.setdefault("project_id", "")
                payload.setdefault("confidence", 0.0)
                payload.setdefault("created_by", "")
                payload.setdefault("timestamp", "")
                payload.setdefault("session_id", "")
                payload.setdefault("workflow_run_id", "")
                payload.setdefault("related_memory_entries", [])
                payload.setdefault("related_discussions", [])
                record = DecisionRecord(**payload)
                self.records[record.decision_id] = record
            except Exception as exc:
                logger.warning(f"加载决策记录失败 {path.name}: {exc}")
