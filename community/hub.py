"""
DrugMind 公共讨论室
公开讨论、围观、归档
"""

import json
import uuid
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PublicDiscussion:
    """公开讨论"""
    session_id: str
    topic: str
    creator_id: str
    creator_name: str
    tags: list[str] = field(default_factory=list)
    participants: list[dict] = field(default_factory=list)  # {twin_id, name, role, emoji}
    messages: list[dict] = field(default_factory=list)
    views: int = 0
    likes: int = 0
    status: str = "open"  # open / completed / locked
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


class DiscussionHub:
    """讨论中心 - 公开讨论广场"""

    def __init__(self, data_dir: str = "./drugmind_data/discussions"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.discussions: dict[str, PublicDiscussion] = {}
        self._load()

    def create(
        self,
        topic: str,
        creator_id: str,
        creator_name: str,
        tags: list[str] = None,
        participants: list[dict] = None,
    ) -> PublicDiscussion:
        """创建公开讨论"""
        disc = PublicDiscussion(
            session_id=f"disc_{uuid.uuid4().hex[:8]}",
            topic=topic,
            creator_id=creator_id,
            creator_name=creator_name,
            tags=tags or [],
            participants=participants or [],
        )
        self.discussions[disc.session_id] = disc
        self._save()
        return disc

    def add_message(self, session_id: str, message: dict):
        """添加消息"""
        disc = self.discussions.get(session_id)
        if disc:
            disc.messages.append(message)
            disc.updated_at = datetime.now().isoformat()
            self._save()

    def like(self, session_id: str):
        """点赞"""
        disc = self.discussions.get(session_id)
        if disc:
            disc.likes += 1
            self._save()

    def view(self, session_id: str):
        """浏览"""
        disc = self.discussions.get(session_id)
        if disc:
            disc.views += 1
            self._save()

    def search(self, query: str = "", tag: str = "", limit: int = 20) -> list[dict]:
        """搜索讨论"""
        results = []
        for disc in self.discussions.values():
            if query and query.lower() not in disc.topic.lower():
                continue
            if tag and tag not in disc.tags:
                continue
            results.append({
                "session_id": disc.session_id,
                "topic": disc.topic,
                "creator_name": disc.creator_name,
                "tags": disc.tags,
                "participants_count": len(disc.participants),
                "messages_count": len(disc.messages),
                "views": disc.views,
                "likes": disc.likes,
                "status": disc.status,
                "created_at": disc.created_at,
            })
        # Sort by newest or most popular
        results.sort(key=lambda x: x["created_at"], reverse=True)
        return results[:limit]

    def get(self, session_id: str) -> dict | None:
        """获取讨论详情"""
        disc = self.discussions.get(session_id)
        if disc:
            disc.views += 1
            self._save()
            return asdict(disc)
        return None

    def feed(self, limit: int = 20) -> list[dict]:
        """首页feed"""
        return self.search(limit=limit)

    def trending(self, limit: int = 10) -> list[dict]:
        """热门讨论"""
        discs = sorted(self.discussions.values(), key=lambda d: d.likes + d.views * 0.1, reverse=True)
        return [
            {"session_id": d.session_id, "topic": d.topic, "likes": d.likes, "views": d.views}
            for d in discs[:limit]
        ]

    def _save(self):
        data = {k: asdict(v) for k, v in self.discussions.items()}
        path = self.data_dir / "public_discussions.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load(self):
        path = self.data_dir / "public_discussions.json"
        if path.exists():
            data = json.loads(path.read_text())
            self.discussions = {k: PublicDiscussion(**v) for k, v in data.items()}
