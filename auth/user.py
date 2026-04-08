"""
DrugMind - 用户系统
注册/登录/档案管理
"""

import json
import hashlib
import uuid
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class UserProfile:
    """用户档案"""
    user_id: str
    username: str
    email: str
    password_hash: str
    display_name: str = ""
    avatar_emoji: str = "👨‍🔬"
    organization: str = ""
    title: str = ""
    system_role: str = "member"
    status: str = "active"
    permissions: list[str] = field(default_factory=list)
    expertise: list[str] = field(default_factory=list)
    bio: str = ""
    papers: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    twins: list[str] = field(default_factory=list)  # 创建的分身ID
    reputation: float = 0.0
    created_at: str = ""
    last_active: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_active:
            self.last_active = self.created_at
        if not self.permissions:
            self.permissions = default_permissions_for_role(self.system_role)


def default_permissions_for_role(system_role: str) -> list[str]:
    role_permissions = {
        "admin": [
            "project.read",
            "project.write",
            "workflow.view",
            "workflow.execute",
            "workflow.approve",
            "workspace.manage",
            "h2a.chat",
        ],
        "lead": [
            "project.read",
            "project.write",
            "workflow.view",
            "workflow.execute",
            "workflow.approve",
            "h2a.chat",
        ],
        "member": [
            "project.read",
            "workflow.view",
            "h2a.chat",
        ],
        "viewer": [
            "project.read",
            "workflow.view",
        ],
    }
    return list(role_permissions.get(system_role or "member", role_permissions["member"]))


class UserManager:
    """用户管理器"""

    def __init__(self, data_dir: str = "./drugmind_data/users"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.users: dict[str, UserProfile] = {}
        self._load()

    def register(self, username: str, email: str, password: str, **kwargs) -> dict:
        """注册"""
        # 检查重复
        for u in self.users.values():
            if u.username == username:
                return {"error": "用户名已存在"}
            if u.email == email:
                return {"error": "邮箱已注册"}

        user_id = f"user_{uuid.uuid4().hex[:8]}"
        user = UserProfile(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=self._hash(password),
            display_name=kwargs.get("display_name", username),
            organization=kwargs.get("organization", ""),
            title=kwargs.get("title", ""),
            avatar_emoji=kwargs.get("avatar_emoji", "👨‍🔬"),
            system_role=kwargs.get("system_role", "member"),
            status=kwargs.get("status", "active"),
            permissions=kwargs.get("permissions", []),
            expertise=kwargs.get("expertise", []),
            bio=kwargs.get("bio", ""),
        )
        self.users[user_id] = user
        self._save()
        return {
            "user_id": user_id,
            "username": username,
            "display_name": user.display_name,
            "system_role": user.system_role,
            "permissions": user.permissions,
            "status": "ok",
        }

    def login(self, username: str, password: str) -> dict:
        """登录"""
        for u in self.users.values():
            if u.username == username and u.password_hash == self._hash(password):
                u.last_active = datetime.now().isoformat()
                self._save()
                return {
                    "user_id": u.user_id,
                    "username": u.username,
                    "display_name": u.display_name,
                    "system_role": u.system_role,
                    "permissions": u.permissions,
                    "status": "ok",
                }
        return {"error": "用户名或密码错误"}

    def get_profile(self, user_id: str) -> dict | None:
        """获取档案"""
        u = self.users.get(user_id)
        if u:
            d = asdict(u)
            del d["password_hash"]
            return d
        return None

    def update_profile(self, user_id: str, **kwargs) -> bool:
        """更新档案"""
        u = self.users.get(user_id)
        if not u:
            return False
        for k, v in kwargs.items():
            if hasattr(u, k) and k not in ("user_id", "password_hash", "created_at"):
                setattr(u, k, v)
        self._save()
        return True

    def list_users(self, limit: int = 50) -> list[dict]:
        """用户列表"""
        users = sorted(self.users.values(), key=lambda u: u.reputation, reverse=True)
        return [
            {"user_id": u.user_id, "username": u.username, "display_name": u.display_name,
             "avatar_emoji": u.avatar_emoji, "organization": u.organization,
             "title": u.title, "system_role": u.system_role, "status": u.status,
             "permissions": u.permissions, "expertise": u.expertise, "reputation": u.reputation}
            for u in users[:limit]
        ]

    def _hash(self, password: str) -> str:
        return hashlib.sha256(f"drugmind:{password}".encode()).hexdigest()

    def _save(self):
        data = {k: asdict(v) for k, v in self.users.items()}
        path = self.data_dir / "users.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load(self):
        path = self.data_dir / "users.json"
        if path.exists():
            data = json.loads(path.read_text())
            self.users = {k: UserProfile(**v) for k, v in data.items()}
