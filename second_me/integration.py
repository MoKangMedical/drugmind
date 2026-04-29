"""
DrugMind × Second Me 完整集成层

架构：
Second Me (HMM记忆建模 + 人格一致性) × DrugMind (药物研发垂直角色)
= 药物研发人员的数字分身协作平台

Second Me提供：
- 个人知识训练（HMM三层记忆）
- Me-Alignment（人格一致性）
- 去中心化网络（分身间通信）
- 云端API (app.secondme.io)

DrugMind提供：
- 药物研发垂直领域角色
- 结构化讨论/辩论/共识
- 药物建模工具集成
- 项目管理和化合物追踪
"""

import json
import logging
import http.client
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)

# Second Me配置
SECOND_ME_API = "app.secondme.io"
SECOND_ME_REGISTRY = "https://app.secondme.io"


@dataclass
class SecondMeInstance:
    """Second Me实例"""
    instance_id: str
    name: str
    role: str  # 药物研发角色
    description: str = ""
    public_url: str = ""
    status: str = "created"


class SecondMeIntegration:
    """
    Second Me集成层
    
    双模式：
    1. 云端模式 - 使用app.secondme.io的API
    2. 本地模式 - 连接本地部署的Second Me
    """

    def __init__(self, mode: str = "cloud", local_url: str = "http://localhost:8002"):
        self.mode = mode
        self.local_url = local_url
        self.instances: dict[str, SecondMeInstance] = {}
        self._conversation_history: dict[str, list] = {}

    def create_pharma_twin(
        self,
        name: str,
        role: str,
        expertise: list[str],
        knowledge: list[str] = None,
        personality: str = "balanced",
    ) -> dict:
        """
        创建药物研发数字分身
        
        在Second Me上创建一个药物研发专家的数字分身
        """
        # 构建药物研发专属训练数据
        training_data = self._build_training_prompt(name, role, expertise, knowledge, personality)

        instance_id = f"{role}_{name}".lower().replace(" ", "_")

        instance = SecondMeInstance(
            instance_id=instance_id,
            name=name,
            role=role,
            description=f"{name}的药物研发数字分身 — {role}",
        )
        self.instances[instance_id] = instance

        # 构建对话历史
        self._conversation_history[instance_id] = [
            {"role": "system", "content": training_data}
        ]

        return {
            "instance_id": instance_id,
            "name": name,
            "role": role,
            "status": "ready",
            "mode": self.mode,
            "note": f"使用{self.mode}模式，训练数据已就绪",
        }

    def chat(self, instance_id: str, message: str) -> dict:
        """与数字分身对话"""
        if instance_id not in self.instances:
            return {"error": f"实例 {instance_id} 不存在"}

        instance = self.instances[instance_id]

        # 添加用户消息
        if instance_id not in self._conversation_history:
            self._conversation_history[instance_id] = []

        self._conversation_history[instance_id].append(
            {"role": "user", "content": message}
        )

        if self.mode == "cloud":
            response = self._chat_cloud(instance_id, message)
        else:
            response = self._chat_local(instance_id, message)

        # 记录回复
        self._conversation_history[instance_id].append(
            {"role": "assistant", "content": response}
        )

        return {
            "instance_id": instance_id,
            "name": instance.name,
            "role": instance.role,
            "message": response,
        }

    def _chat_cloud(self, instance_id: str, message: str) -> str:
        """通过Second Me云端API对话"""
        try:
            history = self._conversation_history.get(instance_id, [])

            conn = http.client.HTTPSConnection(SECOND_ME_API)
            path = f"/api/chat/{instance_id}"

            data = {
                "messages": history[-10:],  # 最近10条消息
                "metadata": {
                    "enable_l0_retrieval": True,
                    "role_id": "default_role",
                },
                "temperature": 0.5,
                "max_tokens": 2000,
                "stream": False,
            }

            headers = {"Content-Type": "application/json"}
            conn.request("POST", path, body=json.dumps(data), headers=headers)
            response = conn.getresponse()
            body = response.read().decode("utf-8")

            if response.status == 200:
                try:
                    result = json.loads(body)
                    return result.get("choices", [{}])[0].get("message", {}).get("content", body)
                except:
                    return body
            else:
                logger.warning(f"Second Me云端API返回 {response.status}: {body[:200]}")
                return f"[Second Me云端暂不可用，使用本地推理] {self._local_fallback(instance_id, message)}"

        except Exception as e:
            logger.error(f"Second Me云端API调用失败: {e}")
            return self._local_fallback(instance_id, message)

    def _chat_local(self, instance_id: str, message: str) -> str:
        """通过本地Second Me对话"""
        try:
            import httpx
            history = self._conversation_history.get(instance_id, [])

            resp = httpx.post(
                f"{self.local_url}/api/chat/{instance_id}",
                json={
                    "messages": history[-10:],
                    "temperature": 0.5,
                    "max_tokens": 2000,
                },
                timeout=60,
            )
            if resp.status_code == 200:
                return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                return self._local_fallback(instance_id, message)

        except Exception as e:
            logger.warning(f"本地Second Me连接失败: {e}")
            return self._local_fallback(instance_id, message)

    def _local_fallback(self, instance_id: str, message: str) -> str:
        """本地MIMO推理回退"""
        try:
            from llm import chat as mimo_chat

            history = self._conversation_history.get(instance_id, [])
            messages = history[-10:]

            return mimo_chat(messages, temperature=0.5)
        except Exception as e:
            return f"[推理失败: {e}]"

    def _build_training_prompt(
        self,
        name: str,
        role: str,
        expertise: list[str],
        knowledge: list[str],
        personality: str,
    ) -> str:
        """构建药物研发专属训练提示"""
        from digital_twin.roles import get_role

        try:
            role_config = get_role(role)
            system_prompt = role_config.system_prompt
        except:
            system_prompt = f"你是{name}，一位{role}。"

        prompt = f"""{system_prompt}

你的名字是{name}，你是一位{role}。

## 专业领域
{chr(10).join(f'- {e}' for e in expertise)}

## 性格特征
风险容忍度: {'保守' if personality == 'cautious' else '激进' if personality == 'aggressive' else '平衡'}

## 知识库
{chr(10).join(f'- {k}' for k in (knowledge or []))}
"""
        return prompt

    def list_instances(self) -> list[dict]:
        """列出所有实例"""
        return [
            {
                "instance_id": inst.instance_id,
                "name": inst.name,
                "role": inst.role,
                "description": inst.description,
                "status": inst.status,
            }
            for inst in self.instances.values()
        ]

    def get_share_url(self, instance_id: str) -> str:
        """获取分身分享链接"""
        if instance_id in self.instances:
            return f"{SECOND_ME_REGISTRY}/chat/{instance_id}"
        return ""

    def export_for_second_me(self, instance_id: str) -> dict:
        """
        导出为Second Me格式
        
        可以在Second Me平台上导入使用
        """
        inst = self.instances.get(instance_id)
        if not inst:
            return {"error": "实例不存在"}

        history = self._conversation_history.get(instance_id, [])

        return {
            "name": inst.name,
            "description": inst.description,
            "system_prompt": history[0]["content"] if history else "",
            "training_messages": history[1:] if len(history) > 1 else [],
            "metadata": {
                "domain": "drug_discovery",
                "role": inst.role,
                "platform": "DrugMind",
            },
        }
