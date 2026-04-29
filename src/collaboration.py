"""
Collaboration Module — 协作模块
多人协作、任务分配、进度同步
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class TeamMember:
    """团队成员"""
    member_id: str
    name: str
    role: str
    expertise: List[str]
    availability: float = 1.0


@dataclass
class Task:
    """任务"""
    task_id: str
    title: str
    description: str
    assignee: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: float = 0.0
    updated_at: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    progress: float = 0.0


@dataclass
class Project:
    """项目"""
    project_id: str
    name: str
    description: str
    members: List[str] = field(default_factory=list)
    tasks: List[str] = field(default_factory=list)
    created_at: float = 0.0


class CollaborationManager:
    """协作管理器"""
    
    def __init__(self):
        self.members: Dict[str, TeamMember] = {}
        self.tasks: Dict[str, Task] = {}
        self.projects: Dict[str, Project] = {}
    
    def add_member(self, member: TeamMember):
        """添加团队成员"""
        self.members[member.member_id] = member
    
    def create_task(self, title: str, description: str, 
                    priority: str = "medium") -> Task:
        """创建任务"""
        task = Task(
            task_id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            priority=TaskPriority(priority),
            created_at=time.time(),
            updated_at=time.time()
        )
        self.tasks[task.task_id] = task
        return task
    
    def assign_task(self, task_id: str, member_id: str) -> bool:
        """分配任务"""
        if task_id not in self.tasks or member_id not in self.members:
            return False
        
        self.tasks[task_id].assignee = member_id
        self.tasks[task_id].status = TaskStatus.IN_PROGRESS
        self.tasks[task_id].updated_at = time.time()
        return True
    
    def update_progress(self, task_id: str, progress: float):
        """更新进度"""
        if task_id in self.tasks:
            self.tasks[task_id].progress = min(100.0, max(0.0, progress))
            self.tasks[task_id].updated_at = time.time()
            
            if progress >= 100.0:
                self.tasks[task_id].status = TaskStatus.COMPLETED
    
    def get_member_tasks(self, member_id: str) -> List[Task]:
        """获取成员任务"""
        return [
            task for task in self.tasks.values()
            if task.assignee == member_id
        ]
    
    def get_project_progress(self, project_id: str) -> Dict:
        """获取项目进度"""
        if project_id not in self.projects:
            return {}
        
        project = self.projects[project_id]
        tasks = [self.tasks[tid] for tid in project.tasks if tid in self.tasks]
        
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        
        return {
            "project_id": project_id,
            "total_tasks": total,
            "completed": completed,
            "progress": (completed / total * 100) if total > 0 else 0,
            "by_status": {
                status.value: sum(1 for t in tasks if t.status == status)
                for status in TaskStatus
            }
        }
    
    def create_project(self, name: str, description: str) -> Project:
        """创建项目"""
        project = Project(
            project_id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            created_at=time.time()
        )
        self.projects[project.project_id] = project
        return project
    
    def add_task_to_project(self, project_id: str, task_id: str):
        """添加任务到项目"""
        if project_id in self.projects and task_id in self.tasks:
            self.projects[project_id].tasks.append(task_id)
    
    def get_team_stats(self) -> Dict:
        """获取团队统计"""
        return {
            "total_members": len(self.members),
            "total_tasks": len(self.tasks),
            "total_projects": len(self.projects),
            "tasks_by_status": {
                status.value: sum(1 for t in self.tasks.values() if t.status == status)
                for status in TaskStatus
            }
        }
