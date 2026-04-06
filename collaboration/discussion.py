"""
结构化讨论引擎
多个数字分身围绕议题展开讨论
"""

import logging
import uuid
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

from digital_twin.engine import DigitalTwinEngine, TwinResponse

logger = logging.getLogger(__name__)


@dataclass
class DiscussionMessage:
    """讨论消息"""
    message_id: str
    session_id: str
    twin_id: str
    name: str
    role: str
    emoji: str
    content: str
    message_type: str = "discussion"  # discussion / question / answer / vote / summary
    reply_to: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.message_id:
            self.message_id = str(uuid.uuid4())[:8]


@dataclass
class DiscussionSession:
    """讨论会话"""
    session_id: str
    topic: str
    participants: list[str]  # twin_ids
    messages: list[DiscussionMessage] = field(default_factory=list)
    status: str = "active"  # active / completed / paused
    created_at: str = ""
    summary: str = ""
    decision: str = ""


class DiscussionEngine:
    """
    结构化讨论引擎
    管理多个数字分身的协作讨论
    """

    def __init__(self, twin_engine: DigitalTwinEngine):
        self.twin = twin_engine
        self.sessions: dict[str, DiscussionSession] = {}

    def create_discussion(
        self,
        topic: str,
        participant_ids: list[str],
        context: str = ""
    ) -> DiscussionSession:
        """
        创建讨论会话

        Args:
            topic: 讨论议题（如"Compound #47是否进入先导优化"）
            participant_ids: 参与讨论的分身ID列表
            context: 额外背景信息
        """
        session_id = f"disc_{uuid.uuid4().hex[:8]}"
        session = DiscussionSession(
            session_id=session_id,
            topic=topic,
            participants=participant_ids,
            created_at=datetime.now().isoformat()
        )
        self.sessions[session_id] = session
        logger.info(f"创建讨论: {topic} | 参与者: {len(participant_ids)}")
        return session

    def run_round_robin(
        self,
        session_id: str,
        context: str = "",
        max_rounds: int = 2
    ) -> list[DiscussionMessage]:
        """
        轮询讨论：每个分身轮流发言

        Args:
            session_id: 讨论会话ID
            context: 额外背景
            max_rounds: 最大轮数
        """
        session = self.sessions.get(session_id)
        if not session:
            return []

        all_messages = []
        conversation_history = ""

        for round_num in range(max_rounds):
            logger.info(f"讨论轮次 {round_num + 1}/{max_rounds}")

            for twin_id in session.participants:
                # 构建讨论上下文
                discussion_context = f"## 讨论议题\n{session.topic}\n\n"
                if context:
                    discussion_context += f"## 背景信息\n{context}\n\n"
                if conversation_history:
                    discussion_context += f"## 之前的发言\n{conversation_history}\n\n"

                # 询问分身
                response = self.twin.ask_twin(
                    twin_id=twin_id,
                    question=f"请就以下议题发表你的专业意见：\n{session.topic}",
                    context=discussion_context
                )

                # 记录消息
                msg = DiscussionMessage(
                    message_id="",
                    session_id=session_id,
                    twin_id=twin_id,
                    name=response.name,
                    role=response.role,
                    emoji=response.emoji,
                    content=response.message,
                )
                session.messages.append(msg)
                all_messages.append(msg)

                # 更新对话历史
                conversation_history += f"\n{response.emoji} **{response.name}** ({response.role}):\n{response.message}\n"

        session.status = "completed"
        return all_messages

    def run_debate(
        self,
        session_id: str,
        question: str,
        context: str = ""
    ) -> dict:
        """
        角色辩论模式：正反两方辩论

        Args:
            session_id: 讨论会话ID
            question: 辩论问题
            context: 背景信息
        """
        session = self.sessions.get(session_id)
        if not session:
            return {}

        # 将参与者分为正反两方
        participants = session.participants
        if len(participants) < 2:
            return {"error": "辩论至少需要2个参与者"}

        mid = len(participants) // 2
        pro_side = participants[:mid]
        con_side = participants[mid:]

        debate = {
            "question": question,
            "pro_side": [],
            "con_side": [],
            "summary": "",
        }

        # 正方发言
        for twin_id in pro_side:
            response = self.twin.ask_twin(
                twin_id=twin_id,
                question=f"请支持以下观点并给出论据：{question}",
                context=context
            )
            debate["pro_side"].append(asdict(response))

        # 反方发言
        for twin_id in con_side:
            response = self.twin.ask_twin(
                twin_id=twin_id,
                question=f"请反对以下观点并给出论据：{question}",
                context=context
            )
            debate["con_side"].append(asdict(response))

        return debate

    def summarize_discussion(self, session_id: str) -> str:
        """生成讨论摘要"""
        session = self.sessions.get(session_id)
        if not session or not session.messages:
            return "无讨论记录"

        summary = f"# 讨论摘要: {session.topic}\n\n"
        summary += f"参与者: {len(session.participants)}位\n"
        summary += f"消息数: {len(session.messages)}\n\n"

        # 按角色汇总
        role_opinions = {}
        for msg in session.messages:
            if msg.role not in role_opinions:
                role_opinions[msg.role] = []
            role_opinions[msg.role].append(msg.content[:200])

        for role, opinions in role_opinions.items():
            summary += f"### {role}\n"
            for op in opinions:
                summary += f"- {op}\n"
            summary += "\n"

        session.summary = summary
        return summary

    def get_session_messages(
        self,
        session_id: str,
        limit: int = 50
    ) -> list[dict]:
        """获取讨论消息"""
        session = self.sessions.get(session_id)
        if not session:
            return []

        return [
            {
                "message_id": m.message_id,
                "emoji": m.emoji,
                "name": m.name,
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp,
                "type": m.message_type,
            }
            for m in session.messages[-limit:]
        ]

    def list_sessions(self) -> list[dict]:
        """列出所有讨论"""
        return [
            {
                "session_id": s.session_id,
                "topic": s.topic,
                "participants": len(s.participants),
                "messages": len(s.messages),
                "status": s.status,
                "created_at": s.created_at,
            }
            for s in self.sessions.values()
        ]
