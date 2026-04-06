"""
FastAPI数据模型
"""

from typing import Optional
from pydantic import BaseModel, Field


# ===== 数字分身 =====
class CreateTwinRequest(BaseModel):
    role_id: str = Field(..., description="角色ID: medicinal_chemist/biologist/pharmacologist/data_scientist/project_lead")
    name: str = Field(..., description="专家姓名")
    custom_expertise: list[str] = Field(default_factory=list)


class AskTwinRequest(BaseModel):
    twin_id: str = Field(..., description="分身ID")
    question: str = Field(..., description="问题")
    context: str = Field("", description="额外上下文")


class TeachTwinRequest(BaseModel):
    twin_id: str = Field(..., description="分身ID")
    content: str = Field(..., description="知识内容")
    source: str = Field("", description="来源")


# ===== 讨论 =====
class CreateDiscussionRequest(BaseModel):
    topic: str = Field(..., description="讨论议题")
    participant_ids: list[str] = Field(..., description="参与者分身ID列表")
    context: str = Field("", description="背景信息")


class RunDiscussionRequest(BaseModel):
    session_id: str = Field(..., description="讨论会话ID")
    context: str = Field("", description="额外背景")
    max_rounds: int = Field(2, description="最大讨论轮数")


class DebateRequest(BaseModel):
    session_id: str = Field(..., description="讨论会话ID")
    question: str = Field(..., description="辩论问题")
    context: str = Field("", description="背景")


# ===== 项目管理 =====
class CreateProjectRequest(BaseModel):
    project_id: str = Field(..., description="项目ID")
    name: str = Field(..., description="项目名称")
    target: str = Field("", description="靶点")
    disease: str = Field("", description="疾病")
    budget: float = Field(0, description="预算")


# ===== 化合物 =====
class AddCompoundRequest(BaseModel):
    compound_id: str = Field(..., description="化合物ID")
    smiles: str = Field(..., description="SMILES")
    name: str = Field("", description="名称")
    project_id: str = Field("", description="所属项目")


# ===== 通用 =====
class HealthResponse(BaseModel):
    status: str
    version: str
    twins_count: int
    discussions_count: int
    projects_count: int
