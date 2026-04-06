"""
DrugMind v2.0 — REST API
药物研发数字分身协作平台
"""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

app = FastAPI(
    title="DrugMind API",
    description="药物研发人员的数字分身协作平台",
    version="2.0.0",
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

# 全局实例（main.py中初始化）
twin_engine = None
discussion_engine = None
kanban = None
compound_tracker = None
user_mgr = None
discussion_hub = None


def init_engines(twin, discussion, board, tracker, users, hub, sm_integration=None):
    global twin_engine, discussion_engine, kanban, compound_tracker, user_mgr, discussion_hub, second_me
    twin_engine = twin
    discussion_engine = discussion
    kanban = board
    compound_tracker = tracker
    user_mgr = users
    discussion_hub = hub
    second_me = sm_integration


# ──────────────────────────────────────────────
# 健康检查
# ──────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "twins": len(twin_engine.list_twins()) if twin_engine else 0,
        "discussions": len(discussion_engine.sessions) if discussion_engine else 0,
        "users": len(user_mgr.users) if user_mgr else 0,
    }


# ──────────────────────────────────────────────
# 用户系统
# ──────────────────────────────────────────────
@app.post("/api/v2/register")
async def register(data: dict):
    r = user_mgr.register(
        username=data["username"],
        email=data["email"],
        password=data["password"],
        display_name=data.get("display_name", ""),
        organization=data.get("organization", ""),
        title=data.get("title", ""),
    )
    if "error" in r:
        raise HTTPException(400, r["error"])
    return r


@app.post("/api/v2/login")
async def login(data: dict):
    r = user_mgr.login(data["username"], data["password"])
    if "error" in r:
        raise HTTPException(401, r["error"])
    return r


@app.get("/api/v2/users")
async def list_users():
    return {"users": user_mgr.list_users()}


@app.get("/api/v2/users/{user_id}")
async def get_user(user_id: str):
    p = user_mgr.get_profile(user_id)
    if not p:
        raise HTTPException(404, "用户不存在")
    return p


@app.put("/api/v2/users/{user_id}")
async def update_user(user_id: str, data: dict):
    ok = user_mgr.update_profile(user_id, **data)
    if not ok:
        raise HTTPException(404, "用户不存在")
    return {"status": "updated"}


# ──────────────────────────────────────────────
# 数字分身
# ──────────────────────────────────────────────
@app.get("/api/v2/roles")
async def list_roles():
    from digital_twin.roles import list_roles
    return {"roles": list_roles()}


@app.post("/api/v2/twins")
async def create_twin(data: dict):
    try:
        result = twin_engine.create_twin(
            role_id=data["role_id"],
            name=data["name"],
            custom_expertise=data.get("expertise"),
        )
        # 关联用户
        if data.get("user_id") and user_mgr:
            user = user_mgr.users.get(data["user_id"])
            if user:
                user.twins.append(result["twin_id"])
                user_mgr._save()
        return result
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/v2/twins")
async def list_twins():
    return {"twins": twin_engine.list_twins()}


@app.post("/api/v2/twins/{twin_id}/ask")
async def ask_twin(twin_id: str, data: dict):
    resp = twin_engine.ask_twin(
        twin_id=twin_id,
        question=data["question"],
        context=data.get("context", ""),
    )
    return {
        "twin_id": resp.twin_id, "name": resp.name, "role": resp.role,
        "emoji": resp.emoji, "message": resp.message, "confidence": resp.confidence,
    }


@app.post("/api/v2/twins/{twin_id}/teach")
async def teach_twin(twin_id: str, data: dict):
    twin_engine.teach_twin(twin_id, data["content"], data.get("source", ""))
    return {"status": "taught"}


@app.get("/api/v2/twins/{twin_id}/memory")
async def twin_memory(twin_id: str, q: str = ""):
    return {"memory": twin_engine.get_twin_memory(twin_id, q)}


# ──────────────────────────────────────────────
# 讨论
# ──────────────────────────────────────────────
@app.post("/api/v2/discussions")
async def create_discussion(data: dict):
    session = discussion_engine.create_discussion(
        topic=data["topic"],
        participant_ids=data["participant_ids"],
        context=data.get("context", ""),
    )
    return {"session_id": session.session_id, "topic": session.topic, "participants": len(session.participants)}


@app.post("/api/v2/discussions/{session_id}/run")
async def run_discussion(session_id: str, data: dict = None):
    data = data or {}
    messages = discussion_engine.run_round_robin(
        session_id=session_id,
        context=data.get("context", ""),
        max_rounds=data.get("max_rounds", 2),
    )
    return {
        "session_id": session_id,
        "count": len(messages),
        "messages": [{"emoji": m.emoji, "name": m.name, "role": m.role, "content": m.content, "timestamp": m.timestamp} for m in messages],
    }


@app.get("/api/v2/discussions/{session_id}")
async def get_discussion(session_id: str):
    return {"messages": discussion_engine.get_session_messages(session_id)}


@app.get("/api/v2/discussions/{session_id}/summary")
async def discussion_summary(session_id: str):
    return {"summary": discussion_engine.summarize_discussion(session_id)}


# ──────────────────────────────────────────────
# 公开讨论广场
# ──────────────────────────────────────────────
@app.post("/api/v2/hub")
async def create_public_discussion(data: dict):
    disc = discussion_hub.create(
        topic=data["topic"],
        creator_id=data.get("creator_id", "anonymous"),
        creator_name=data.get("creator_name", "匿名用户"),
        tags=data.get("tags", []),
        participants=data.get("participants", []),
    )
    return {"session_id": disc.session_id, "topic": disc.topic}


@app.get("/api/v2/hub")
async def list_public_discussions(q: str = "", tag: str = "", limit: int = 20):
    return {"discussions": discussion_hub.search(q, tag, limit)}


@app.get("/api/v2/hub/trending")
async def trending_discussions():
    return {"trending": discussion_hub.trending()}


@app.get("/api/v2/hub/{session_id}")
async def get_public_discussion(session_id: str):
    d = discussion_hub.get(session_id)
    if not d:
        raise HTTPException(404, "讨论不存在")
    return d


@app.post("/api/v2/hub/{session_id}/like")
async def like_discussion(session_id: str):
    discussion_hub.like(session_id)
    return {"status": "liked"}


@app.post("/api/v2/hub/{session_id}/reply")
async def reply_discussion(session_id: str, data: dict):
    discussion_hub.add_message(session_id, {
        "twin_id": data.get("twin_id", ""),
        "name": data.get("name", ""),
        "role": data.get("role", ""),
        "emoji": data.get("emoji", "💬"),
        "content": data.get("content", ""),
        "timestamp": "",
    })
    return {"status": "posted"}


# ──────────────────────────────────────────────
# 项目管理
# ──────────────────────────────────────────────
@app.post("/api/v2/projects")
async def create_project(data: dict):
    project = kanban.create_project(
        project_id=data.get("project_id", data["name"].lower().replace(" ", "_")),
        name=data["name"],
        target=data.get("target", ""),
        disease=data.get("disease", ""),
        budget=data.get("budget", 0),
    )
    return {"project_id": project.project_id, "name": project.name}


@app.get("/api/v2/projects/board")
async def get_board():
    return kanban.get_board()


# ──────────────────────────────────────────────
# 化合物
# ──────────────────────────────────────────────
@app.post("/api/v2/compounds")
async def add_compound(data: dict):
    comp = compound_tracker.add_compound(
        compound_id=data["compound_id"],
        smiles=data["smiles"],
        name=data.get("name", ""),
        project_id=data.get("project_id", ""),
    )
    return {"compound_id": comp.compound_id}


@app.get("/api/v2/compounds/pipeline")
async def get_pipeline():
    return compound_tracker.get_pipeline()


# ──────────────────────────────────────────────
# ADMET
# ──────────────────────────────────────────────
@app.post("/api/v2/admet")
async def predict_admet(data: dict):
    from drug_modeling.admet_bridge import ADMETBridge
    bridge = ADMETBridge()
    return bridge.predict(data["smiles"])


# ──────────────────────────────────────────────
# WebSocket
# ──────────────────────────────────────────────
@app.websocket("/ws/{session_id}")
async def ws_discussion(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            twin_id = data.get("twin_id", "")
            message = data.get("message", "")
            if twin_id and message:
                response = twin_engine.ask_twin(twin_id, message)
                await websocket.send_json({
                    "twin_id": response.twin_id, "name": response.name,
                    "role": response.role, "emoji": response.emoji,
                    "message": response.message,
                })
    except WebSocketDisconnect:
        pass


# ──────────────────────────────────────────────
# Second Me集成
# ──────────────────────────────────────────────
second_me = None  # 在init_engines中设置

@app.post("/api/v2/second-me/create")
async def create_second_me_twin(data: dict):
    """在Second Me上创建药物研发数字分身"""
    if not second_me:
        raise HTTPException(503, "Second Me集成未初始化")
    result = second_me.create_pharma_twin(
        name=data["name"],
        role=data["role"],
        expertise=data.get("expertise", []),
        knowledge=data.get("knowledge", []),
        personality=data.get("personality", "balanced"),
    )
    return result

@app.post("/api/v2/second-me/{instance_id}/chat")
async def chat_second_me(instance_id: str, data: dict):
    """与Second Me数字分身对话"""
    if not second_me:
        raise HTTPException(503, "Second Me集成未初始化")
    result = second_me.chat(instance_id, data["message"])
    return result

@app.get("/api/v2/second-me")
async def list_second_me_instances():
    """列出Second Me实例"""
    if not second_me:
        return {"instances": [], "status": "not_initialized"}
    return {"instances": second_me.list_instances()}

@app.get("/api/v2/second-me/{instance_id}/export")
async def export_second_me(instance_id: str):
    """导出为Second Me格式"""
    if not second_me:
        raise HTTPException(503, "Second Me集成未初始化")
    return second_me.export_for_second_me(instance_id)

@app.get("/api/v2/second-me/{instance_id}/share")
async def share_second_me(instance_id: str):
    """获取分享链接"""
    if not second_me:
        raise HTTPException(503, "Second Me集成未初始化")
    return {"url": second_me.get_share_url(instance_id)}


# ──────────────────────────────────────────────
# 前端页面
# ──────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@app.get("/", response_class=HTMLResponse)
async def index():
    f = FRONTEND_DIR / "index.html"
    if f.exists():
        return HTMLResponse(content=f.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>DrugMind</h1><p>前端文件未找到</p>")
