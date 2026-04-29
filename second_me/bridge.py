"""
DrugMind - Second Me集成层
桥接Second Me的数字分身能力
"""

import logging
import json
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SecondMeBridge:
    """
    Second Me桥接器
    与mindverse/Second-Me平台集成

    Second Me提供：
    - 个人知识训练（HMM记忆建模）
    - 人格一致性（Me-Alignment）
    - 去中心化网络（分身间通信）

    DrugMind在此基础上添加：
    - 药物研发垂直领域角色
    - 结构化讨论和辩论
    - 药物建模工具集成
    """

    def __init__(self, second_me_url: str = "http://localhost:8082"):
        self.second_me_url = second_me_url
        self.connected = False

    def check_connection(self) -> bool:
        """检查Second Me连接"""
        try:
            import httpx
            resp = httpx.get(f"{self.second_me_url}/api/health", timeout=5)
            self.connected = resp.status_code == 200
            return self.connected
        except:
            self.connected = False
            return False

    def create_pharma_twin(
        self,
        name: str,
        role: str,
        knowledge_files: list[str] = None,
        memories: list[str] = None
    ) -> dict:
        """
        在Second Me上创建药物研发分身

        Args:
            name: 专家姓名
            role: 药物研发角色
            knowledge_files: 知识文件列表
            memories: 经验记忆列表
        """
        # 构建药物研发专属的训练数据
        training_data = self._build_training_data(name, role, knowledge_files, memories)

        if self.connected:
            return self._register_with_second_me(training_data)
        else:
            # 离线模式：本地存储
            return {
                "status": "offline_mode",
                "twin_id": f"{role}_{name}",
                "training_data": training_data,
                "note": "Second Me未连接，使用本地模式。运行 'make start' 启动Second Me。"
            }

    def _build_training_data(
        self,
        name: str,
        role: str,
        knowledge_files: list[str],
        memories: list[str]
    ) -> dict:
        """构建训练数据"""
        from digital_twin.roles import get_role

        role_config = get_role(role)

        return {
            "name": name,
            "role": role,
            "system_prompt": role_config.system_prompt,
            "expertise": role_config.expertise,
            "personality": role_config.personality,
            "knowledge_files": knowledge_files or [],
            "memories": memories or [],
            "domain": "drug_discovery",
        }

    def _register_with_second_me(self, training_data: dict) -> dict:
        """在Second Me上注册分身"""
        try:
            import httpx
            resp = httpx.post(
                f"{self.second_me_url}/api/twins",
                json=training_data,
                timeout=30
            )
            return resp.json()
        except Exception as e:
            logger.error(f"Second Me注册失败: {e}")
            return {"error": str(e)}

    def send_discussion_to_second_me(
        self,
        twin_id: str,
        message: str,
        context: str = ""
    ) -> Optional[str]:
        """发送讨论消息到Second Me分身"""
        if not self.connected:
            return None

        try:
            import httpx
            resp = httpx.post(
                f"{self.second_me_url}/api/chat",
                json={
                    "twin_id": twin_id,
                    "message": message,
                    "context": context
                },
                timeout=60
            )
            return resp.json().get("response", "")
        except Exception as e:
            logger.warning(f"Second Me对话失败: {e}")
            return None
