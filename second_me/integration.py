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
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
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
    expertise: list[str] = field(default_factory=list)
    knowledge: list[str] = field(default_factory=list)
    personality: str = "balanced"
    linked_user_id: str = ""
    linked_project_id: str = ""
    linked_twin_id: str = ""
    last_synced_at: str = ""
    last_message_at: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


class SecondMeIntegration:
    """
    Second Me集成层
    
    双模式：
    1. 云端模式 - 使用app.secondme.io的API
    2. 本地模式 - 连接本地部署的Second Me
    """

    def __init__(
        self,
        mode: str = "cloud",
        local_url: str = "http://localhost:8002",
        storage_dir: str = "./drugmind_data/second_me",
        registry_url: str = SECOND_ME_REGISTRY,
    ):
        self.mode = mode
        self.local_url = local_url
        self.registry_url = registry_url
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._instances_path = self.storage_dir / "instances.json"
        self._history_path = self.storage_dir / "history.json"
        self.instances: dict[str, SecondMeInstance] = {}
        self._conversation_history: dict[str, list] = {}
        self._load()

    def create_pharma_twin(
        self,
        name: str,
        role: str,
        expertise: list[str],
        knowledge: list[str] = None,
        personality: str = "balanced",
        user_id: str = "",
        project_id: str = "",
        local_twin_id: str = "",
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
            expertise=expertise,
            knowledge=knowledge or [],
            personality=personality,
            linked_user_id=user_id,
            linked_project_id=project_id,
            linked_twin_id=local_twin_id,
        )
        self.instances[instance_id] = instance

        # 构建对话历史
        self._conversation_history[instance_id] = [
            {"role": "system", "content": training_data}
        ]
        self._save()

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
        instance.last_message_at = datetime.now().isoformat()
        instance.updated_at = datetime.now().isoformat()
        self._save()

        return {
            "instance_id": instance_id,
            "name": instance.name,
            "role": instance.role,
            "message": response,
        }

    def describe_capabilities(self) -> dict:
        """Describe the current integration contract."""
        return {
            "mode": self.mode,
            "local_url": self.local_url,
            "registry_url": self.registry_url,
            "instances_count": len(self.instances),
            "features": [
                "pharma_twin_creation",
                "instance_chat",
                "project_context_sync",
                "implementation_blueprint_sync",
                "drug_discovery_capability_sync",
                "by_dmta_project_summary",
                "second_me_export",
                "share_url_generation",
                "durable_instance_storage",
            ],
        }

    def get_instance(self, instance_id: str) -> Optional[dict]:
        instance = self.instances.get(instance_id)
        return asdict(instance) if instance else None

    def sync_project_context(
        self,
        instance_id: str,
        *,
        project: Optional[dict] = None,
        workspace: Optional[dict] = None,
        memory_entries: Optional[list[dict]] = None,
        decisions: Optional[list[dict]] = None,
        workflow_run: Optional[dict] = None,
        sync_note: str = "",
    ) -> dict:
        """Attach project context to a Second Me instance as a durable sync snapshot."""
        instance = self.instances.get(instance_id)
        if not instance:
            return {"error": f"实例 {instance_id} 不存在"}

        memory_entries = memory_entries or []
        decisions = decisions or []
        sync_payload = {
            "project": project or {},
            "workspace": workspace or {},
            "memory_entries": memory_entries[:8],
            "decisions": decisions[:6],
            "workflow_run": workflow_run or {},
            "sync_note": sync_note,
            "synced_at": datetime.now().isoformat(),
        }
        snapshot_text = self._build_project_snapshot(sync_payload)
        self._conversation_history.setdefault(instance_id, []).append(
            {"role": "system", "content": snapshot_text}
        )
        instance.last_synced_at = sync_payload["synced_at"]
        instance.updated_at = sync_payload["synced_at"]
        instance.status = "synced"
        self._save()
        return {
            "instance_id": instance_id,
            "status": "synced",
            "mode": self.mode,
            "summary": snapshot_text[:320],
            "synced_at": sync_payload["synced_at"],
            "memory_entries_count": len(memory_entries),
            "decisions_count": len(decisions),
            "workflow_run_id": (workflow_run or {}).get("run_id", ""),
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
            asdict(inst)
            for inst in self.instances.values()
        ]

    def get_share_url(self, instance_id: str) -> str:
        """获取分身分享链接"""
        if instance_id in self.instances:
            instance = self.instances[instance_id]
            if not instance.public_url:
                instance.public_url = f"{self.registry_url}/chat/{instance_id}"
                instance.updated_at = datetime.now().isoformat()
                self._save()
            return instance.public_url
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

    def _build_project_snapshot(self, sync_payload: dict) -> str:
        project = sync_payload.get("project") or {}
        workspace = sync_payload.get("workspace") or {}
        memory_entries = sync_payload.get("memory_entries") or []
        decisions = sync_payload.get("decisions") or []
        workflow_run = sync_payload.get("workflow_run") or {}

        lines = [
            "## DrugMind Project Sync Snapshot",
            f"- synced_at: {sync_payload.get('synced_at', '')}",
            f"- project_id: {project.get('project_id', '')}",
            f"- project_name: {project.get('name', '')}",
            f"- stage: {project.get('stage', '')}",
            f"- target: {project.get('target', '')}",
            f"- disease: {project.get('disease', '')}",
        ]
        if workspace:
            lines.extend([
                f"- workspace_status: {workspace.get('status', '')}",
                f"- linked_discussions: {len(workspace.get('linked_discussions', []))}",
                f"- linked_workflows: {len(workspace.get('linked_workflows', []))}",
                f"- linked_decisions: {len(workspace.get('linked_decisions', []))}",
            ])
        if workflow_run:
            lines.extend([
                f"- workflow_run_id: {workflow_run.get('run_id', '')}",
                f"- workflow_template: {workflow_run.get('template_name', '')}",
                f"- workflow_status: {workflow_run.get('status', '')}",
            ])
        if sync_payload.get("sync_note"):
            lines.append(f"- note: {sync_payload['sync_note']}")

        if memory_entries:
            lines.append("### Key memory")
            for entry in memory_entries[:5]:
                lines.append(
                    f"- [{entry.get('memory_type', 'note')}] {entry.get('title', '')}: "
                    f"{(entry.get('content', '') or '')[:180]}"
                )
        if decisions:
            lines.append("### Key decisions")
            for decision in decisions[:4]:
                lines.append(
                    f"- {decision.get('topic', '')}: {decision.get('decision', '')} "
                    f"(confidence={decision.get('confidence', 0)})"
                )
        return "\n".join(lines)

    def _save(self):
        instances_payload = {
            instance_id: asdict(instance)
            for instance_id, instance in self.instances.items()
        }
        self._instances_path.write_text(json.dumps(instances_payload, ensure_ascii=False, indent=2))
        self._history_path.write_text(json.dumps(self._conversation_history, ensure_ascii=False, indent=2))

    def _load(self):
        if self._instances_path.exists():
            try:
                instances_data = json.loads(self._instances_path.read_text())
                self.instances = {
                    instance_id: SecondMeInstance(**payload)
                    for instance_id, payload in instances_data.items()
                }
            except Exception as exc:
                logger.warning("加载 Second Me instances 失败: %s", exc)
                self.instances = {}
        if self._history_path.exists():
            try:
                self._conversation_history = json.loads(self._history_path.read_text())
            except Exception as exc:
                logger.warning("加载 Second Me history 失败: %s", exc)
                self._conversation_history = {}
