"""
数字分身知识记忆系统
基于Second Me的HMM（层级记忆建模）理念
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """单条记忆"""
    content: str
    memory_type: str  # knowledge / experience / decision / insight
    source: str = ""
    importance: float = 0.5  # 0-1
    timestamp: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class HierarchicalMemory:
    """
    层级记忆系统 (HMM)
    受Second Me论文启发 (arXiv:2503.08102)

    三层记忆：
    - L0: 原始数据（上传的文件、对话记录）
    - L1: 结构化知识（提取的实体、关系、事实）
    - L2: 高层洞察（模式、经验、判断规则）
    """

    def __init__(self, storage_dir: str = "./memory"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.l0_raw: list[MemoryEntry] = []       # 原始记忆
        self.l1_structured: list[MemoryEntry] = [] # 结构化知识
        self.l2_insights: list[MemoryEntry] = []   # 高层洞察

    def add_raw(self, content: str, source: str = "", tags: list[str] = None):
        """添加原始记忆 (L0)"""
        entry = MemoryEntry(
            content=content,
            memory_type="raw",
            source=source,
            tags=tags or [],
            importance=0.3
        )
        self.l0_raw.append(entry)

        # 自动提取结构化知识
        if len(content) > 100:
            self._extract_structured(content, source, tags)

    def add_knowledge(self, content: str, source: str = "", importance: float = 0.7):
        """添加结构化知识 (L1)"""
        entry = MemoryEntry(
            content=content,
            memory_type="knowledge",
            source=source,
            importance=importance
        )
        self.l1_structured.append(entry)

    def add_insight(self, content: str, tags: list[str] = None):
        """添加高层洞察 (L2)"""
        entry = MemoryEntry(
            content=content,
            memory_type="insight",
            importance=0.9,
            tags=tags or []
        )
        self.l2_insights.append(entry)

    def add_decision(self, decision: str, rationale: str, context: str = ""):
        """添加决策记忆"""
        content = f"决策: {decision}\n理由: {rationale}"
        if context:
            content += f"\n背景: {context}"

        entry = MemoryEntry(
            content=content,
            memory_type="decision",
            importance=0.8,
            tags=["decision"]
        )
        self.l1_structured.append(entry)

    def retrieve(
        self,
        query: str = "",
        memory_type: str = "all",
        max_entries: int = 10
    ) -> list[MemoryEntry]:
        """
        检索记忆
        简化版：基于关键词匹配（生产环境应用向量检索）
        """
        all_entries = []

        if memory_type in ("all", "insight"):
            all_entries.extend(self.l2_insights)
        if memory_type in ("all", "knowledge"):
            all_entries.extend(self.l1_structured)
        if memory_type in ("all", "raw"):
            all_entries.extend(self.l0_raw)

        if not query:
            # 返回最重要的记忆
            all_entries.sort(key=lambda e: e.importance, reverse=True)
            return all_entries[:max_entries]

        # 关键词匹配
        query_lower = query.lower()
        scored = []
        for entry in all_entries:
            score = 0
            content_lower = entry.content.lower()
            for word in query_lower.split():
                if word in content_lower:
                    score += 1
            # 加权重要性
            score *= entry.importance
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:max_entries]]

    def get_context_for_discussion(self, topic: str) -> str:
        """为讨论获取相关上下文"""
        relevant = self.retrieve(topic, max_entries=5)
        if not relevant:
            return ""

        context_parts = ["## 相关记忆和知识\n"]
        for entry in relevant:
            context_parts.append(f"- [{entry.memory_type}] {entry.content[:200]}")

        return "\n".join(context_parts)

    def _extract_structured(self, content: str, source: str, tags: list[str]):
        """从原始内容提取结构化知识（简化版）"""
        # 提取关键段落
        lines = content.split("\n")
        key_lines = [l.strip() for l in lines if len(l.strip()) > 30][:5]

        for line in key_lines:
            entry = MemoryEntry(
                content=line,
                memory_type="knowledge",
                source=source,
                importance=0.5,
                tags=tags or []
            )
            self.l1_structured.append(entry)

    def save(self, twin_id: str):
        """持久化记忆"""
        data = {
            "l0_raw": [asdict(e) for e in self.l0_raw[-200:]],  # 保留最近200条
            "l1_structured": [asdict(e) for e in self.l1_structured[-200:]],
            "l2_insights": [asdict(e) for e in self.l2_insights],
        }
        path = self.storage_dir / f"{twin_id}_memory.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def load(self, twin_id: str):
        """加载记忆"""
        path = self.storage_dir / f"{twin_id}_memory.json"
        if path.exists():
            data = json.loads(path.read_text())
            self.l0_raw = [MemoryEntry(**e) for e in data.get("l0_raw", [])]
            self.l1_structured = [MemoryEntry(**e) for e in data.get("l1_structured", [])]
            self.l2_insights = [MemoryEntry(**e) for e in data.get("l2_insights", [])]
