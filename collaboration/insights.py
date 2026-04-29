"""
DrugMind 讨论洞察引擎 — Hermes改进
使用MIMO API分析讨论质量，生成行动建议

用户视角：药研人员开完会，需要知道"达成了什么共识、下一步做什么"
"""

import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DiscussionInsight:
    """讨论洞察"""
    session_id: str
    consensus_summary: str           # 共识总结
    key_decisions: List[str]         # 关键决策
    action_items: List[str]          # 行动项
    risk_flags: List[str]            # 风险标记
    confidence_score: float          # 共识信心度 0-1
    next_steps: List[str]            # 下一步建议


class DiscussionInsightEngine:
    """讨论洞察引擎 — 让每次讨论都有产出"""
    
    def __init__(self, llm_func=None):
        """
        Args:
            llm_func: LLM调用函数，签名 (messages: list) -> str
                      如果为None，使用规则引擎（无需LLM）
        """
        self.llm = llm_func
    
    def analyze_discussion(
        self,
        session_id: str,
        topic: str,
        messages: List[Dict],
        project_context: str = ""
    ) -> DiscussionInsight:
        """
        分析讨论会话，生成洞察
        
        Args:
            session_id: 会话ID
            topic: 讨论主题
            messages: 消息列表 [{"name": "张博士", "content": "...", "role": "..."}]
            project_context: 项目背景
        """
        if self.llm:
            return self._analyze_with_llm(session_id, topic, messages, project_context)
        else:
            return self._analyze_with_rules(session_id, topic, messages)
    
    def _analyze_with_llm(self, session_id, topic, messages, context) -> DiscussionInsight:
        """使用MIMO LLM分析"""
        messages_text = "\n".join([
            f"{m.get('name', '未知')}({m.get('role', '')}): {m.get('content', '')}"
            for m in messages[-20:]  # 最近20条
        ])
        
        prompt = f"""分析以下药物研发团队讨论，生成结构化洞察。

讨论主题：{topic}
项目背景：{context}

讨论记录：
{messages_text}

请以JSON格式输出：
{{
    "consensus_summary": "一句话总结共识",
    "key_decisions": ["决策1", "决策2"],
    "action_items": ["行动项1", "行动项2"],
    "risk_flags": ["风险1"],
    "confidence_score": 0.85,
    "next_steps": ["下一步1", "下一步2"]
}}"""
        
        try:
            response = self.llm([{"role": "user", "content": prompt}])
            data = json.loads(response)
            return DiscussionInsight(
                session_id=session_id,
                **data
            )
        except Exception as e:
            logger.error(f"LLM分析失败: {e}")
            return self._analyze_with_rules(session_id, topic, messages)
    
    def _analyze_with_rules(self, session_id, topic, messages) -> DiscussionInsight:
        """规则引擎分析（无需LLM）"""
        # 简单关键词分析
        all_text = " ".join([m.get("content", "") for m in messages])
        
        # 检测决策关键词
        decisions = []
        action_items = []
        risks = []
        
        decision_keywords = ["决定", "选择", "采用", "同意", "GO", "批准"]
        action_keywords = ["下一步", "需要", "安排", "负责", "跟进"]
        risk_keywords = ["风险", "担心", "问题", "困难", "不确定"]
        
        for msg in messages:
            content = msg.get("content", "")
            if any(kw in content for kw in decision_keywords):
                decisions.append(content[:100])
            if any(kw in content for kw in action_keywords):
                action_items.append(content[:100])
            if any(kw in content for kw in risk_keywords):
                risks.append(content[:100])
        
        # 共识度评估
        total = len(messages)
        agreement_signals = sum(1 for m in messages if any(w in m.get("content", "") for w in ["同意", "好的", "没问题", "对", "赞成"]))
        confidence = min(agreement_signals / max(total, 1) + 0.5, 1.0)
        
        return DiscussionInsight(
            session_id=session_id,
            consensus_summary=f"关于「{topic}」的讨论，共{total}条消息，{len(decisions)}个决策",
            key_decisions=decisions[:5],
            action_items=action_items[:5],
            risk_flags=risks[:3],
            confidence_score=round(confidence, 2),
            next_steps=["整理会议纪要", "分配行动项", "约定下次讨论时间"]
        )
    
    def format_insight(self, insight: DiscussionInsight) -> str:
        """格式化洞察为可读文本"""
        lines = [
            f"📊 讨论洞察 — {insight.session_id[:8]}",
            f"",
            f"📋 共识：{insight.consensus_summary}",
            f"🎯 信心度：{insight.confidence_score:.0%}",
        ]
        
        if insight.key_decisions:
            lines.append(f"\n✅ 关键决策：")
            for d in insight.key_decisions[:3]:
                lines.append(f"  • {d}")
        
        if insight.action_items:
            lines.append(f"\n📌 行动项：")
            for a in insight.action_items[:3]:
                lines.append(f"  ☐ {a}")
        
        if insight.risk_flags:
            lines.append(f"\n⚠️ 风险标记：")
            for r in insight.risk_flags[:3]:
                lines.append(f"  🔴 {r}")
        
        if insight.next_steps:
            lines.append(f"\n➡️ 下一步：")
            for s in insight.next_steps[:3]:
                lines.append(f"  → {s}")
        
        return "\n".join(lines)


# ============================================================
# 测试
# ============================================================
if __name__ == "__main__":
    engine = DiscussionInsightEngine()
    
    test_messages = [
        {"name": "张博士", "role": "药物化学", "content": "我认为应该优先优化化合物A的溶解度"},
        {"name": "李博士", "role": "药理学", "content": "同意，但需要关注肝毒性风险"},
        {"name": "王博士", "role": "ADMET", "content": "数据显示化合物A的CYP抑制风险较高"},
        {"name": "张博士", "role": "药物化学", "content": "好的，那我们决定先解决CYP抑制问题，再优化溶解度"},
        {"name": "李博士", "role": "药理学", "content": "没问题，我负责安排下周的体外代谢实验"},
    ]
    
    insight = engine.analyze_discussion(
        session_id="test-001",
        topic="先导化合物优化方向",
        messages=test_messages,
        project_context="GLP-1受体激动剂项目"
    )
    
    print(engine.format_insight(insight))
