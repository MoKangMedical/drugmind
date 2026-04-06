"""
FastAPI路由
DrugMind REST API
"""

import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .models import (
    CreateTwinRequest, AskTwinRequest, TeachTwinRequest,
    CreateDiscussionRequest, RunDiscussionRequest, DebateRequest,
    CreateProjectRequest, AddCompoundRequest,
    HealthResponse,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="DrugMind API",
    description="药物研发数字分身协作平台 — Second Me for Pharma",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局引擎实例（在main.py中初始化）
twin_engine = None
discussion_engine = None
kanban = None
compound_tracker = None


def init_engines(engine, discussion, board, tracker):
    """初始化引擎"""
    global twin_engine, discussion_engine, kanban, compound_tracker
    twin_engine = engine
    discussion_engine = discussion
    kanban = board
    compound_tracker = tracker


# ===== 健康检查 =====
@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        twins_count=len(twin_engine.list_twins()) if twin_engine else 0,
        discussions_count=len(discussion_engine.sessions) if discussion_engine else 0,
        projects_count=len(kanban.projects) if kanban else 0,
    )


# ===== 角色列表 =====
@app.get("/api/v1/roles")
async def list_roles():
    """列出所有可用角色"""
    from digital_twin.roles import list_roles
    return {"roles": list_roles()}


# ===== 数字分身 =====
@app.post("/api/v1/twins/create")
async def create_twin(req: CreateTwinRequest):
    """创建数字分身"""
    try:
        result = twin_engine.create_twin(
            role_id=req.role_id,
            name=req.name,
            custom_expertise=req.custom_expertise
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/twins")
async def list_twins():
    """列出所有数字分身"""
    return {"twins": twin_engine.list_twins()}


@app.post("/api/v1/twins/ask")
async def ask_twin(req: AskTwinRequest):
    """向数字分身提问"""
    try:
        response = twin_engine.ask_twin(
            twin_id=req.twin_id,
            question=req.question,
            context=req.context
        )
        return {
            "twin_id": response.twin_id,
            "name": response.name,
            "role": response.role,
            "emoji": response.emoji,
            "message": response.message,
            "confidence": response.confidence,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/twins/teach")
async def teach_twin(req: TeachTwinRequest):
    """教数字分身新知识"""
    try:
        twin_engine.teach_twin(
            twin_id=req.twin_id,
            content=req.content,
            source=req.source
        )
        return {"status": "taught", "twin_id": req.twin_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/twins/{twin_id}/memory")
async def get_twin_memory(twin_id: str, query: str = ""):
    """获取分身记忆"""
    return {"memory": twin_engine.get_twin_memory(twin_id, query)}


# ===== 讨论 =====
@app.post("/api/v1/discussions/create")
async def create_discussion(req: CreateDiscussionRequest):
    """创建讨论会话"""
    try:
        session = discussion_engine.create_discussion(
            topic=req.topic,
            participant_ids=req.participant_ids,
            context=req.context
        )
        return {
            "session_id": session.session_id,
            "topic": session.topic,
            "participants": len(session.participants),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/discussions/run")
async def run_discussion(req: RunDiscussionRequest):
    """执行讨论（轮询模式）"""
    try:
        messages = discussion_engine.run_round_robin(
            session_id=req.session_id,
            context=req.context,
            max_rounds=req.max_rounds
        )
        return {
            "session_id": req.session_id,
            "messages_count": len(messages),
            "messages": [
                {
                    "emoji": m.emoji,
                    "name": m.name,
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp,
                }
                for m in messages
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/discussions/debate")
async def run_debate(req: DebateRequest):
    """角色辩论"""
    try:
        result = discussion_engine.run_debate(
            session_id=req.session_id,
            question=req.question,
            context=req.context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/discussions/{session_id}/messages")
async def get_discussion_messages(session_id: str):
    """获取讨论消息"""
    return {"messages": discussion_engine.get_session_messages(session_id)}


@app.get("/api/v1/discussions/{session_id}/summary")
async def get_discussion_summary(session_id: str):
    """获取讨论摘要"""
    summary = discussion_engine.summarize_discussion(session_id)
    return {"summary": summary}


@app.get("/api/v1/discussions")
async def list_discussions():
    """列出所有讨论"""
    return {"sessions": discussion_engine.list_sessions()}


# ===== 项目管理 =====
@app.post("/api/v1/projects/create")
async def create_project(req: CreateProjectRequest):
    """创建项目"""
    try:
        project = kanban.create_project(
            project_id=req.project_id,
            name=req.name,
            target=req.target,
            disease=req.disease,
            budget=req.budget
        )
        return {"project_id": project.project_id, "name": project.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/projects/board")
async def get_board():
    """获取项目看板"""
    return kanban.get_board()


@app.post("/api/v1/projects/{project_id}/advance")
async def advance_project(project_id: str, compound_id: str = ""):
    """推进项目阶段"""
    kanban.advance_stage(project_id, compound_id)
    return {"status": "advanced"}


# ===== 化合物 =====
@app.post("/api/v1/compounds/add")
async def add_compound(req: AddCompoundRequest):
    """添加化合物"""
    try:
        comp = compound_tracker.add_compound(
            compound_id=req.compound_id,
            smiles=req.smiles,
            name=req.name,
            project_id=req.project_id
        )
        return {"compound_id": comp.compound_id, "smiles": comp.smiles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/compounds/pipeline")
async def get_pipeline():
    """获取化合物管线"""
    return compound_tracker.get_pipeline()


# ===== WebSocket实时讨论 =====
@app.websocket("/ws/discuss/{session_id}")
async def websocket_discussion(websocket: WebSocket, session_id: str):
    """WebSocket实时讨论"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            twin_id = data.get("twin_id", "")
            message = data.get("message", "")

            if twin_id and message:
                response = twin_engine.ask_twin(twin_id, message)
                await websocket.send_json({
                    "twin_id": response.twin_id,
                    "name": response.name,
                    "role": response.role,
                    "emoji": response.emoji,
                    "message": response.message,
                })
    except WebSocketDisconnect:
        logger.info(f"WebSocket断开: {session_id}")
