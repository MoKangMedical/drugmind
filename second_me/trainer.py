"""
Second Me 分身训练器
将药物研发专家的知识训练成数字分身
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TwinTrainer:
    """
    数字分身训练器
    将专家数据转化为可运行的Second Me
    """

    def __init__(self):
        self.training_data: dict[str, list] = {}

    def collect_expert_data(
        self,
        expert_name: str,
        papers: list[str] = None,
        experiment_logs: list[str] = None,
        decision_history: list[dict] = None,
        communication_style: list[str] = None
    ):
        """收集专家数据"""
        self.training_data[expert_name] = {
            "papers": papers or [],
            "experiment_logs": experiment_logs or [],
            "decision_history": decision_history or [],
            "communication_style": communication_style or [],
        }
        logger.info(f"收集 {expert_name} 的专家数据: "
                    f"{len(papers or [])}篇论文, "
                    f"{len(experiment_logs or [])}条实验记录, "
                    f"{len(decision_history or [])}条决策历史")

    def build_persona_prompt(self, expert_name: str) -> str:
        """构建人格提示词"""
        data = self.training_data.get(expert_name, {})
        parts = [f"你是{expert_name}的数字分身。"]

        if data.get("papers"):
            parts.append(f"你发表了{len(data['papers'])}篇论文。")

        if data.get("decision_history"):
            decisions = data["decision_history"][:3]
            for d in decisions:
                parts.append(f"你在'{d.get('topic', '')}'中做出了'{d.get('decision', '')}'的决定，因为{d.get('reason', '')}。")

        if data.get("communication_style"):
            parts.append(f"你的说话风格：{'; '.join(data['communication_style'][:3])}")

        return "\n".join(parts)
