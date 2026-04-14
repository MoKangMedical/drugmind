"""
Persistent binding store for DrugMind <-> Second Me resources.
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
class SecondMeBinding:
    """Links a DrugMind project/user/twin to a Second Me instance."""

    binding_id: str
    instance_id: str
    local_twin_id: str = ""
    user_id: str = ""
    project_id: str = ""
    role_id: str = ""
    display_name: str = ""
    sync_strategy: str = "manual"
    status: str = "linked"
    share_url: str = ""
    last_synced_at: str = ""
    last_sync_summary: str = ""
    linked_memory_entries: list[str] = field(default_factory=list)
    linked_workflows: list[str] = field(default_factory=list)
    export_snapshot: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.binding_id:
            self.binding_id = f"smb_{uuid.uuid4().hex[:10]}"
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


class SecondMeBindingStore:
    """Stores durable associations for Second Me integrations."""

    def __init__(self, data_dir: str = "./drugmind_data/platform/second_me"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.data_dir / "bindings.json"
        self.bindings: dict[str, SecondMeBinding] = {}
        self._load()

    def list_bindings(
        self,
        project_id: str = "",
        user_id: str = "",
        instance_id: str = "",
    ) -> list[dict]:
        bindings = list(self.bindings.values())
        if project_id:
            bindings = [binding for binding in bindings if binding.project_id == project_id]
        if user_id:
            bindings = [binding for binding in bindings if binding.user_id == user_id]
        if instance_id:
            bindings = [binding for binding in bindings if binding.instance_id == instance_id]
        bindings.sort(key=lambda binding: binding.updated_at, reverse=True)
        return [asdict(binding) for binding in bindings]

    def get_binding(self, binding_id: str) -> Optional[dict]:
        binding = self.bindings.get(binding_id)
        return asdict(binding) if binding else None

    def upsert_binding(
        self,
        instance_id: str,
        local_twin_id: str = "",
        user_id: str = "",
        project_id: str = "",
        role_id: str = "",
        display_name: str = "",
        sync_strategy: str = "manual",
        status: str = "linked",
        share_url: str = "",
    ) -> dict:
        existing = self._find_existing(
            instance_id=instance_id,
            local_twin_id=local_twin_id,
            user_id=user_id,
            project_id=project_id,
        )
        if existing:
            if local_twin_id:
                existing.local_twin_id = local_twin_id
            if user_id:
                existing.user_id = user_id
            if project_id:
                existing.project_id = project_id
            if role_id:
                existing.role_id = role_id
            if display_name:
                existing.display_name = display_name
            if sync_strategy:
                existing.sync_strategy = sync_strategy
            if status:
                existing.status = status
            if share_url:
                existing.share_url = share_url
            existing.updated_at = datetime.now().isoformat()
            self._save()
            return asdict(existing)

        binding = SecondMeBinding(
            binding_id="",
            instance_id=instance_id,
            local_twin_id=local_twin_id,
            user_id=user_id,
            project_id=project_id,
            role_id=role_id,
            display_name=display_name,
            sync_strategy=sync_strategy,
            status=status,
            share_url=share_url,
        )
        self.bindings[binding.binding_id] = binding
        self._save()
        return asdict(binding)

    def mark_synced(
        self,
        binding_id: str,
        summary: str = "",
        memory_entry_id: str = "",
        workflow_run_id: str = "",
        share_url: str = "",
        export_snapshot: Optional[dict] = None,
    ) -> dict:
        binding = self._get(binding_id)
        binding.status = "synced"
        binding.last_synced_at = datetime.now().isoformat()
        if summary:
            binding.last_sync_summary = summary
        if memory_entry_id and memory_entry_id not in binding.linked_memory_entries:
            binding.linked_memory_entries.append(memory_entry_id)
        if workflow_run_id and workflow_run_id not in binding.linked_workflows:
            binding.linked_workflows.append(workflow_run_id)
        if share_url:
            binding.share_url = share_url
        if export_snapshot:
            binding.export_snapshot = export_snapshot
        binding.updated_at = datetime.now().isoformat()
        self._save()
        return asdict(binding)

    def count(self) -> int:
        return len(self.bindings)

    def _find_existing(
        self,
        instance_id: str,
        local_twin_id: str = "",
        user_id: str = "",
        project_id: str = "",
    ) -> Optional[SecondMeBinding]:
        for binding in self.bindings.values():
            if binding.instance_id != instance_id:
                continue
            if project_id and binding.project_id and binding.project_id != project_id:
                continue
            if user_id and binding.user_id and binding.user_id != user_id:
                continue
            if local_twin_id and binding.local_twin_id and binding.local_twin_id != local_twin_id:
                continue
            if project_id or user_id or local_twin_id:
                return binding
        return None

    def _get(self, binding_id: str) -> SecondMeBinding:
        binding = self.bindings.get(binding_id)
        if not binding:
            raise ValueError(f"Second Me binding 不存在: {binding_id}")
        return binding

    def _save(self):
        payload = {binding_id: asdict(binding) for binding_id, binding in self.bindings.items()}
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    def _load(self):
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            self.bindings = {
                binding_id: SecondMeBinding(**payload)
                for binding_id, payload in data.items()
            }
        except Exception as exc:
            logger.warning("加载 Second Me bindings 失败: %s", exc)
            self.bindings = {}
