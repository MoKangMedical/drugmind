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
        )
        self.users[user_id] = user
        self._save()
        return {"user_id": user_id, "username": username, "status": "ok"}

    def login(self, username: str, password: str) -> dict:
        """登录"""
        for u in self.users.values():
            if u.username == username and u.password_hash == self._hash(password):
                u.last_active = datetime.now().isoformat()
                self._save()
                return {"user_id": u.user_id, "username": u.username, "status": "ok"}
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
             "title": u.title, "expertise": u.expertise, "reputation": u.reputation}
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
