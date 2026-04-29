"""
数字分身人格配置系统
管理Second Me的人格、知识和判断模式
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

from .roles import RoleConfig, get_role, list_roles, ROLE_REGISTRY

logger = logging.getLogger(__name__)


@dataclass
class PersonalityProfile:
    """人格画像"""
    role_id: str
    name: str  # 专家姓名（如"张博士"）
    avatar_emoji: str
    custom_expertise: list[str] = field(default_factory=list)
    custom_system_prompt: str = ""
    risk_tolerance_override: Optional[float] = None
    innovation_style_override: Optional[float] = None
    knowledge_files: list[str] = field(default_factory=list)  # 上传的知识文件
    memory_entries: list[dict] = field(default_factory=list)  # 经验记忆


class PersonalityManager:
    """人格管理器"""

    def __init__(self, profiles_dir: str = "./profiles"):
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._profiles: dict[str, PersonalityProfile] = {}
        self._load_profiles()

    def create_twin(
        self,
        role_id: str,
        name: str,
        custom_expertise: Optional[list[str]] = None,
        custom_prompt: str = ""
    ) -> PersonalityProfile:
        """创建新的数字分身"""
        role = get_role(role_id)

        profile = PersonalityProfile(
            role_id=role_id,
            name=name,
            avatar_emoji=role.emoji,
            custom_expertise=custom_expertise or [],
            custom_system_prompt=custom_prompt,
        )

        twin_id = f"{role_id}_{name}"
        self._profiles[twin_id] = profile
        self._save_profile(twin_id, profile)

        logger.info(f"创建数字分身: {name} ({role.display_name})")
        return profile

    def get_system_prompt(self, twin_id: str) -> str:
        """获取数字分身的完整系统提示"""
        profile = self._profiles.get(twin_id)
        if not profile:
            return "你是一个通用药物研发AI助手。"

        role = get_role(profile.role_id)

        # 基础人格
        prompt = profile.custom_system_prompt or role.system_prompt

        # 专业知识注入
        if profile.custom_expertise:
            prompt += f"\n\n你的额外专业领域：{', '.join(profile.custom_expertise)}"

        # 知识文件注入
        if profile.knowledge_files:
            prompt += f"\n\n你已学习的知识文件：{len(profile.knowledge_files)}个"

        # 记忆注入
        if profile.memory_entries:
            recent = profile.memory_entries[-5:]
            memories = "\n".join([f"- {m.get('content', '')}" for m in recent])
            prompt += f"\n\n你的经验记忆：\n{memories}"

        # 人格微调
        risk = profile.risk_tolerance_override or role.risk_tolerance
        innovation = profile.innovation_style_override or role.innovation_style
        prompt += f"\n\n人格参数：风险容忍度={risk:.1f}/1.0，创新倾向={innovation:.1f}/1.0"

        return prompt

    def add_knowledge(self, twin_id: str, file_path: str, content: str):
        """为数字分身添加知识"""
        profile = self._profiles.get(twin_id)
        if profile:
            profile.knowledge_files.append(file_path)
            # 存储知识摘要
            profile.memory_entries.append({
                "type": "knowledge",
                "source": file_path,
                "content": content[:2000],
                "timestamp": __import__('datetime').datetime.now().isoformat()
            })
            self._save_profile(twin_id, profile)

    def add_memory(self, twin_id: str, content: str, memory_type: str = "experience"):
        """为数字分身添加记忆"""
        profile = self._profiles.get(twin_id)
        if profile:
            profile.memory_entries.append({
                "type": memory_type,
                "content": content,
                "timestamp": __import__('datetime').datetime.now().isoformat()
            })
            # 只保留最近100条
            if len(profile.memory_entries) > 100:
                profile.memory_entries = profile.memory_entries[-100:]
            self._save_profile(twin_id, profile)

    def list_twins(self) -> list[dict]:
        """列出所有数字分身"""
        result = []
        for twin_id, profile in self._profiles.items():
            role = get_role(profile.role_id)
            result.append({
                "twin_id": twin_id,
                "name": profile.name,
                "role": role.display_name,
                "emoji": profile.avatar_emoji,
                "knowledge_count": len(profile.knowledge_files),
                "memory_count": len(profile.memory_entries),
            })
        return result

    def _save_profile(self, twin_id: str, profile: PersonalityProfile):
        """保存人格画像到文件"""
        path = self.profiles_dir / f"{twin_id}.json"
        path.write_text(json.dumps(asdict(profile), ensure_ascii=False, indent=2))

    def _load_profiles(self):
        """加载已有画像"""
        if not self.profiles_dir.exists():
            return
        for path in self.profiles_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                twin_id = path.stem
                self._profiles[twin_id] = PersonalityProfile(**data)
            except Exception as e:
                logger.warning(f"加载画像失败 {path}: {e}")
