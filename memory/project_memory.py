"""
Persistent project memory store.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ProjectMemoryEntry:
    """A reusable project memory artifact."""

    entry_id: str
    project_id: str
    memory_type: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    source: str = ""
    author_id: str = ""
    related_agents: list[str] = field(default_factory=list)
    related_compounds: list[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self):
        if not self.entry_id:
            self.entry_id = f"mem_{uuid.uuid4().hex[:10]}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class ProjectMemoryStore:
    """Stores evidence, notes, decisions, and workflow artifacts by project."""

    def __init__(self, data_dir: str = "./drugmind_data/platform/memory"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.data_dir / "project_memory.json"
        self.entries: dict[str, ProjectMemoryEntry] = {}
        self._load()

    def add_entry(
        self,
        project_id: str,
        memory_type: str,
        title: str,
        content: str,
        tags: list[str] | None = None,
        source: str = "",
        author_id: str = "",
        related_agents: list[str] | None = None,
        related_compounds: list[str] | None = None,
    ) -> dict:
        entry = ProjectMemoryEntry(
            entry_id="",
            project_id=project_id,
            memory_type=memory_type,
            title=title,
            content=content,
            tags=tags or [],
            source=source,
            author_id=author_id,
            related_agents=related_agents or [],
            related_compounds=related_compounds or [],
        )
        self.entries[entry.entry_id] = entry
        self._save()
        return asdict(entry)

    def list_entries(
        self,
        project_id: str,
        memory_type: str = "",
        query: str = "",
        limit: int = 50,
    ) -> list[dict]:
        query_lc = query.lower().strip()
        entries = [
            entry for entry in self.entries.values()
            if entry.project_id == project_id and (not memory_type or entry.memory_type == memory_type)
        ]
        if query_lc:
            entries = [
                entry for entry in entries
                if query_lc in entry.title.lower()
                or query_lc in entry.content.lower()
                or any(query_lc in tag.lower() for tag in entry.tags)
            ]
        entries.sort(key=lambda entry: entry.created_at, reverse=True)
        return [asdict(entry) for entry in entries[:limit]]

    def get_context(self, project_id: str, query: str = "", limit: int = 8) -> dict:
        entries = self.list_entries(project_id, query=query, limit=limit)
        context_blocks = [
            {
                "title": entry["title"],
                "memory_type": entry["memory_type"],
                "content": entry["content"],
                "tags": entry["tags"],
            }
            for entry in entries
        ]
        return {
            "project_id": project_id,
            "entries": entries,
            "context_blocks": context_blocks,
        }

    def stats(self, project_id: str) -> dict:
        project_entries = [entry for entry in self.entries.values() if entry.project_id == project_id]
        by_type: dict[str, int] = {}
        for entry in project_entries:
            by_type[entry.memory_type] = by_type.get(entry.memory_type, 0) + 1
        return {
            "project_id": project_id,
            "entries": len(project_entries),
            "by_type": by_type,
        }

    def count(self) -> int:
        return len(self.entries)

    def _save(self):
        data = {entry_id: asdict(entry) for entry_id, entry in self.entries.items()}
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load(self):
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            self.entries = {
                entry_id: ProjectMemoryEntry(**payload)
                for entry_id, payload in data.items()
            }
        except Exception as exc:
            logger.warning("加载 project memory 失败: %s", exc)
            self.entries = {}
