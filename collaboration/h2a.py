"""
Human-to-Agent conversation threads.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class H2AMessage:
    message_id: str
    thread_id: str
    sender_type: str
    sender_id: str
    sender_label: str
    content: str
    created_at: str = ""
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.message_id:
            self.message_id = f"h2a_msg_{uuid.uuid4().hex[:10]}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class H2AThread:
    thread_id: str
    project_id: str
    title: str
    human_id: str
    human_label: str
    agent_id: str
    agent_label: str
    agent_ids: list[str] = field(default_factory=list)
    agent_labels: list[str] = field(default_factory=list)
    mode: str = "single"
    status: str = "active"
    messages: list[H2AMessage] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.thread_id:
            self.thread_id = f"h2a_{uuid.uuid4().hex[:10]}"
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if not self.agent_ids and self.agent_id:
            self.agent_ids = [self.agent_id]
        if not self.agent_labels and self.agent_label:
            self.agent_labels = [self.agent_label]
        if self.agent_ids and not self.agent_id:
            self.agent_id = self.agent_ids[0]
        if self.agent_labels and not self.agent_label:
            self.agent_label = self.agent_labels[0]
        if len(self.agent_ids) > 1:
            self.mode = "group"
        self.messages = [
            message if isinstance(message, H2AMessage) else H2AMessage(**message)
            for message in self.messages
        ]


class H2AThreadStore:
    """Persistent project-scoped human to agent threads."""

    def __init__(self, data_dir: str = "./drugmind_data/platform/h2a"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.data_dir / "threads.json"
        self.threads: dict[str, H2AThread] = {}
        self._load()

    def create_thread(
        self,
        *,
        project_id: str,
        human_id: str,
        human_label: str,
        agent_id: str = "",
        agent_label: str = "",
        agent_ids: list[str] | None = None,
        agent_labels: list[str] | None = None,
        title: str = "",
    ) -> dict:
        resolved_agent_ids = agent_ids or ([agent_id] if agent_id else [])
        resolved_agent_labels = agent_labels or ([agent_label] if agent_label else [])
        thread = H2AThread(
            thread_id="",
            project_id=project_id,
            title=title or (
                f"{human_label} ↔ {resolved_agent_labels[0]}"
                if len(resolved_agent_labels) <= 1
                else f"{human_label} ↔ {len(resolved_agent_labels)} Agents"
            ),
            human_id=human_id,
            human_label=human_label,
            agent_id=resolved_agent_ids[0] if resolved_agent_ids else "",
            agent_label=resolved_agent_labels[0] if resolved_agent_labels else "",
            agent_ids=resolved_agent_ids,
            agent_labels=resolved_agent_labels,
            mode="group" if len(resolved_agent_ids) > 1 else "single",
        )
        self.threads[thread.thread_id] = thread
        self._save()
        return asdict(thread)

    def get_thread(self, thread_id: str) -> Optional[dict]:
        thread = self.threads.get(thread_id)
        return asdict(thread) if thread else None

    def list_threads(self, project_id: str = "", status: str = "") -> list[dict]:
        threads = list(self.threads.values())
        if project_id:
            threads = [thread for thread in threads if thread.project_id == project_id]
        if status:
            threads = [thread for thread in threads if thread.status == status]
        threads.sort(key=lambda thread: thread.updated_at, reverse=True)
        return [asdict(thread) for thread in threads]

    def add_message(
        self,
        thread_id: str,
        *,
        sender_type: str,
        sender_id: str,
        sender_label: str,
        content: str,
        meta: dict | None = None,
    ) -> dict:
        thread = self._get(thread_id)
        message = H2AMessage(
            message_id="",
            thread_id=thread_id,
            sender_type=sender_type,
            sender_id=sender_id,
            sender_label=sender_label,
            content=content,
            meta=meta or {},
        )
        thread.messages.append(message)
        thread.updated_at = message.created_at
        self._save()
        return asdict(message)

    def count(self) -> int:
        return len(self.threads)

    def _get(self, thread_id: str) -> H2AThread:
        thread = self.threads.get(thread_id)
        if not thread:
            raise ValueError(f"H2A thread 不存在: {thread_id}")
        return thread

    def _save(self):
        payload = {thread_id: asdict(thread) for thread_id, thread in self.threads.items()}
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    def _load(self):
        if not self._path.exists():
            return
        try:
            payload = json.loads(self._path.read_text())
            self.threads = {
                thread_id: H2AThread(**thread_payload)
                for thread_id, thread_payload in payload.items()
            }
        except Exception as exc:
            logger.warning("加载 H2A threads 失败: %s", exc)
            self.threads = {}
