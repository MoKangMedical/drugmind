"""
决策追踪模块
记录每个决策的理由、反对意见和最终结论
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DecisionRecord:
    """决策记录"""
    decision_id: str
    topic: str
    decision: str           # GO / NO-GO / CONDITIONAL
    rationale: str
    participants: list[str]  # twin_ids
    opinions: list[dict]     # 各角色意见
    dissenting: list[str]    # 反对意见
    conditions: list[str]    # 附带条件
    timestamp: str = ""
    session_id: str = ""


class DecisionLogger:
    """决策追踪器"""

    def __init__(self, log_dir: str = "./drugmind_data/decisions"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.records: list[DecisionRecord] = []

    def log_decision(
        self,
        topic: str,
        decision: str,
        rationale: str,
        participants: list[str],
        opinions: list[dict],
        dissenting: list[str] = None,
        conditions: list[str] = None,
        session_id: str = ""
    ) -> DecisionRecord:
        """记录决策"""
        record = DecisionRecord(
            decision_id=f"dec_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            topic=topic,
            decision=decision,
            rationale=rationale,
            participants=participants,
            opinions=opinions,
            dissenting=dissenting or [],
            conditions=conditions or [],
            timestamp=datetime.now().isoformat(),
            session_id=session_id
        )
        self.records.append(record)
        self._save_record(record)
        return record

    def get_decision_history(self, topic_filter: str = "") -> list[dict]:
        """获取决策历史"""
        records = self.records
        if topic_filter:
            records = [r for r in records if topic_filter.lower() in r.topic.lower()]
        return [asdict(r) for r in records]

    def _save_record(self, record: DecisionRecord):
        """持久化决策记录"""
        path = self.log_dir / f"{record.decision_id}.json"
        path.write_text(json.dumps(asdict(record), ensure_ascii=False, indent=2))
