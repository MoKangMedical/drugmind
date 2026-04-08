"""
数字分身主引擎
构建、管理和调用药物研发数字分身
"""

import logging
from typing import Optional
from dataclasses import dataclass, asdict

from .personality import PersonalityManager, PersonalityProfile
from .memory import HierarchicalMemory
from .roles import get_role, list_roles

logger = logging.getLogger(__name__)


@dataclass
class TwinResponse:
    """数字分身的回复"""
    twin_id: str
    name: str
    role: str
    emoji: str
    message: str
    confidence: float
    reasoning: str


class DigitalTwinEngine:
    """
    数字分身引擎
    基于Second Me理念：将人的判断力固化成AI分身
    """

    def __init__(
        self,
        storage_dir: str = "./drugmind_data",
        use_llm: bool = True,
    ):
        self.personality = PersonalityManager(f"{storage_dir}/profiles")
        self.memories: dict[str, HierarchicalMemory] = {}
        self.storage_dir = storage_dir
        self.use_llm = use_llm
        self._llm_fn = None

        if use_llm:
            try:
                from llm import chat
                self._llm_fn = chat
                logger.info("✅ MIMO LLM已连接")
            except Exception as e:
                logger.warning(f"⚠️ LLM未配置，使用模板: {e}")
                self.use_llm = False

    def create_twin(
        self,
        role_id: str,
        name: str,
        custom_expertise: Optional[list[str]] = None,
    ) -> dict:
        """创建数字分身"""
        profile = self.personality.create_twin(
            role_id=role_id,
            name=name,
            custom_expertise=custom_expertise,
        )

        twin_id = f"{role_id}_{name}"
        self.memories[twin_id] = HierarchicalMemory(f"{self.storage_dir}/memory")
        self.memories[twin_id].load(twin_id)

        role = get_role(role_id)
        return {
            "twin_id": twin_id,
            "name": name,
            "role": role.display_name,
            "emoji": role.emoji,
            "status": "created",
        }

    def ensure_twin(
        self,
        role_id: str,
        name: str,
        custom_expertise: Optional[list[str]] = None,
    ) -> str:
        """Ensure a twin exists for the given role/name pair."""
        twin_id = f"{role_id}_{name}"
        if twin_id not in self.personality._profiles:
            self.create_twin(role_id, name, custom_expertise=custom_expertise)
        elif twin_id not in self.memories:
            self.memories[twin_id] = HierarchicalMemory(f"{self.storage_dir}/memory")
            self.memories[twin_id].load(twin_id)
        return twin_id

    def ask_twin(
        self,
        twin_id: str,
        question: str,
        context: str = "",
        temperature: float = 0.4,
    ) -> TwinResponse:
        """向数字分身提问"""
        profile_data = self.personality._profiles.get(twin_id)
        if not profile_data:
            return TwinResponse(
                twin_id=twin_id, name="Unknown", role="Unknown", emoji="❓",
                message=f"找不到分身 {twin_id}", confidence=0, reasoning="",
            )

        role = get_role(profile_data.role_id)
        system_prompt = self.personality.get_system_prompt(twin_id)

        # 获取相关记忆
        memory_context = ""
        if twin_id in self.memories:
            memory_context = self.memories[twin_id].get_context_for_discussion(question)

        # 构建完整提示
        full_prompt = question
        if context:
            full_prompt += f"\n\n【讨论背景】\n{context}"
        if memory_context:
            full_prompt += f"\n\n【相关经验】\n{memory_context}"

        if self.use_llm and self._llm_fn:
            try:
                message = self._llm_fn(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": full_prompt},
                    ],
                    temperature=temperature,
                )

                # 记录到记忆
                if twin_id in self.memories:
                    self.memories[twin_id].add_decision(
                        decision=message[:100],
                        rationale=message,
                        context=question,
                    )

                return TwinResponse(
                    twin_id=twin_id,
                    name=profile_data.name,
                    role=role.display_name,
                    emoji=role.emoji,
                    message=message,
                    confidence=0.85,
                    reasoning=f"基于{role.display_name}专业知识和AI推理",
                )
            except Exception as e:
                logger.error(f"LLM调用失败: {e}")

        # Fallback: 模板回复
        return TwinResponse(
            twin_id=twin_id,
            name=profile_data.name,
            role=role.display_name,
            emoji=role.emoji,
            message=self._template_response(profile_data.role_id, question),
            confidence=0.3,
            reasoning="模板回复（LLM未连接）",
        )

    def ask_agent(
        self,
        agent_id: str,
        question: str,
        context: str = "",
        *,
        agent_profile: Optional[dict] = None,
        temperature: float = 0.35,
    ) -> TwinResponse:
        """Ask a registered agent, routing domain agents through twins."""
        agent = agent_profile or {}
        if not agent:
            return TwinResponse(
                twin_id=agent_id,
                name=agent_id,
                role="Unknown agent",
                emoji="🤖",
                message=f"找不到 agent {agent_id}",
                confidence=0,
                reasoning="agent registry lookup failed",
            )

        role_id = agent.get("role_id", "")
        if role_id:
            twin_id = self.ensure_twin(role_id, agent.get("name", role_id))
            return self.ask_twin(
                twin_id=twin_id,
                question=question,
                context=context,
                temperature=temperature,
            )

        system_prompt = self._build_agent_system_prompt(agent)
        full_prompt = question
        if context:
            full_prompt += f"\n\n【项目与会话上下文】\n{context}"

        if self.use_llm and self._llm_fn:
            try:
                message = self._llm_fn(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": full_prompt},
                    ],
                    temperature=temperature,
                )
                return TwinResponse(
                    twin_id=agent_id,
                    name=agent.get("name", agent_id),
                    role=agent.get("category", "platform"),
                    emoji=self._agent_emoji(agent_id),
                    message=message,
                    confidence=0.82,
                    reasoning=f"基于 {agent.get('name', agent_id)} 的平台职责生成回复",
                )
            except Exception as exc:
                logger.error("平台 agent 调用失败: %s", exc)

        return TwinResponse(
            twin_id=agent_id,
            name=agent.get("name", agent_id),
            role=agent.get("category", "platform"),
            emoji=self._agent_emoji(agent_id),
            message=self._platform_template_response(agent, question),
            confidence=0.28,
            reasoning="模板回复（LLM未连接）",
        )

    def teach_twin(self, twin_id: str, content: str, source: str = ""):
        """教数字分身新知识"""
        if twin_id in self.memories:
            self.memories[twin_id].add_knowledge(content, source)
            self.memories[twin_id].save(twin_id)
        self.personality.add_knowledge(twin_id, source, content)

    def get_twin_memory(self, twin_id: str, query: str = "") -> list[dict]:
        """获取分身记忆"""
        if twin_id in self.memories:
            entries = self.memories[twin_id].retrieve(query)
            return [{"content": e.content, "type": e.memory_type, "importance": e.importance} for e in entries]
        return []

    def list_twins(self) -> list[dict]:
        """列出所有数字分身"""
        return self.personality.list_twins()

    def _template_response(self, role_id: str, question: str) -> str:
        """模板回复（LLM未配置时）"""
        templates = {
            "medicinal_chemist": "从合成角度，我需要先评估这个分子的合成路线和SA Score。建议先跑retrosynthesis分析。",
            "biologist": "需要更多实验数据支持。建议设计体外活性和选择性实验。",
            "pharmacologist": "需要关注hERG风险和ADMET特性。安全性评估必须先行。",
            "data_scientist": "从数据角度来看，建议先建立QSAR模型预测活性和ADMET。",
            "project_lead": "综合考虑，我建议先明确Go/No-Go标准，再评估各项指标。",
        }
        return templates.get(role_id, "需要更多信息才能给出建议。")

    def _build_agent_system_prompt(self, agent: dict) -> str:
        allowed_tools = ", ".join(agent.get("allowed_tools", [])[:8]) or "暂无明确工具"
        default_skills = ", ".join(agent.get("default_skills", [])[:8]) or "暂无明确技能"
        return (
            f"你是 DrugMind 平台中的 {agent.get('name', agent.get('agent_id', 'Agent'))}。\n"
            f"角色类型: {agent.get('category', 'platform')}\n"
            f"职责说明: {agent.get('description', '')}\n"
            f"默认技能: {default_skills}\n"
            f"可用工具: {allowed_tools}\n\n"
            "你正在与一位真实的药物研发工作人员对话。"
            "请直接给出判断，不要空泛地讲平台介绍。"
            "输出格式默认遵守：\n"
            "1. 先给结论\n"
            "2. 再给关键依据\n"
            "3. 最后给下一步动作\n"
            "4. 如果存在风险或审批门，明确指出。"
        )

    def _platform_template_response(self, agent: dict, question: str) -> str:
        name = agent.get("name", "Agent")
        return (
            f"{name} 已收到你的问题：{question}\n"
            "当前我建议先把问题拆成可执行步骤，明确 owner、artifact 和下一步动作，"
            "再进入流程推进。"
        )

    def _agent_emoji(self, agent_id: str) -> str:
        if agent_id == "agent.orchestrator":
            return "🛰️"
        if agent_id == "agent.reviewer":
            return "✅"
        if agent_id == "agent.integration":
            return "🔗"
        return "🤖"
