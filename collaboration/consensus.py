"""
共识形成模块
通过投票和权衡达成团队共识
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConsensusResult:
    """共识结果"""
    topic: str
    final_decision: str
    vote_distribution: dict  # {option: count}
    confidence: float
    dissenting_opinions: list[str]


class ConsensusEngine:
    """共识形成引擎"""

    def vote(
        self,
        topic: str,
        options: list[str],
        votes: dict[str, str],  # {twin_id: option}
        weights: dict[str, float] = None  # {twin_id: weight}
    ) -> ConsensusResult:
        """
        投票共识

        Args:
            topic: 议题
            options: 可选方案 ["GO", "NO-GO", "CONDITIONAL"]
            votes: 各分身投票 {twin_id: 选择}
            weights: 权重（项目负责人权重更高）
        """
        # 统计投票
        distribution = {opt: 0 for opt in options}
        for twin_id, vote in votes.items():
            w = weights.get(twin_id, 1.0) if weights else 1.0
            distribution[vote] = distribution.get(vote, 0) + w

        # 最高票方案
        winner = max(distribution, key=distribution.get)
        total = sum(distribution.values())
        confidence = distribution[winner] / total if total > 0 else 0

        # 反对意见
        dissenting = [
            f"{tid}: 选择了 {vote}"
            for tid, vote in votes.items()
            if vote != winner
        ]

        return ConsensusResult(
            topic=topic,
            final_decision=winner,
            vote_distribution=distribution,
            confidence=round(confidence, 3),
            dissenting_opinions=dissenting
        )
