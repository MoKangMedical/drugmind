"""
DrugMind v2.0 — REST API
药物研发数字分身协作平台
"""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .mcp_server import router as mcp_router, init_mcp

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
agent_registry = None
skill_registry = None
tool_registry = None
project_memory = None
workflow_orchestrator = None


def init_engines(
    twin,
    discussion,
    board,
    tracker,
    users,
    hub,
    sm_integration=None,
    agent_reg=None,
    skill_reg=None,
    tool_reg=None,
    project_memory_store=None,
    workflow_engine=None,
):
    global twin_engine, discussion_engine, kanban, compound_tracker, user_mgr, discussion_hub, second_me
    global agent_registry, skill_registry, tool_registry, project_memory, workflow_orchestrator
    twin_engine = twin
    discussion_engine = discussion
    kanban = board
    compound_tracker = tracker
    user_mgr = users
    discussion_hub = hub
    second_me = sm_integration
    agent_registry = agent_reg
    skill_registry = skill_reg
    tool_registry = tool_reg
    project_memory = project_memory_store
    workflow_orchestrator = workflow_engine
    # 初始化MCP Server
    init_mcp(twin, discussion, hub, users)


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
        "registered_agents": agent_registry.count() if agent_registry else 0,
        "registered_skills": skill_registry.count() if skill_registry else 0,
        "registered_tools": tool_registry.count() if tool_registry else 0,
        "workflow_runs": workflow_orchestrator.count_runs() if workflow_orchestrator else 0,
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
# 快捷接口（微信小程序/Web前端）
# ──────────────────────────────────────────────

@app.post("/api/v2/quick-ask")
async def quick_ask(data: dict):
    """快捷AI提问 - 返回多角色回答"""
    question = data.get("question", "")
    context = data.get("context", "")
    roles = data.get("roles", ["medicinal_chemist", "biologist", "pharmacologist"])
    
    if not question:
        raise HTTPException(400, "问题不能为空")
    
    responses = []
    for role_id in roles:
        name_map = {
            "medicinal_chemist": "陈化学家",
            "biologist": "王生物",
            "pharmacologist": "李药理",
            "data_scientist": "赵数据",
            "project_lead": "刘总监",
        }
        emoji_map = {
            "medicinal_chemist": "🧪",
            "biologist": "🔬",
            "pharmacologist": "💊",
            "data_scientist": "📊",
            "project_lead": "📋",
        }
        twin_id = f"{role_id}_{name_map.get(role_id, role_id)}"
        try:
            resp = twin_engine.ask_twin(twin_id, question, context)
            responses.append({
                "role": role_id,
                "name": resp.name,
                "emoji": resp.emoji,
                "message": resp.message,
            })
        except Exception as e:
            responses.append({
                "role": role_id,
                "name": name_map.get(role_id, role_id),
                "emoji": emoji_map.get(role_id, "🤖"),
                "message": f"抱歉，我暂时无法回答这个问题。",
            })
    
    return {"responses": responses, "question": question}


@app.get("/api/v2/stats")
async def platform_stats():
    """平台统计数据"""
    twins = twin_engine.list_twins() if twin_engine else []
    return {
        "twins_count": len(twins),
        "discussions_count": len(discussion_hub.discussions) if discussion_hub else 0,
        "users_count": len(user_mgr.users) if user_mgr else 0,
        "roles": 5,
        "registered_agents": agent_registry.count() if agent_registry else 0,
        "registered_skills": skill_registry.count() if skill_registry else 0,
        "registered_tools": tool_registry.count() if tool_registry else 0,
        "workflow_runs": workflow_orchestrator.count_runs() if workflow_orchestrator else 0,
    }


# ──────────────────────────────────────────────
# 平台骨架
# ──────────────────────────────────────────────
@app.get("/api/v2/platform/overview")
async def platform_overview():
    return {
        "agents": agent_registry.list_agents(active_only=False) if agent_registry else [],
        "skills": skill_registry.list_skills() if skill_registry else [],
        "tools": tool_registry.list_tools(enabled_only=False) if tool_registry else [],
        "workflow_templates": workflow_orchestrator.list_templates() if workflow_orchestrator else [],
        "workflow_runs": workflow_orchestrator.list_runs() if workflow_orchestrator else [],
    }


@app.get("/api/v2/platform/agents")
async def list_platform_agents(category: str = "", active_only: bool = True):
    return {"agents": agent_registry.list_agents(category=category, active_only=active_only) if agent_registry else []}


@app.get("/api/v2/platform/agents/{agent_id}")
async def get_platform_agent(agent_id: str):
    if not agent_registry:
        raise HTTPException(503, "Agent registry 未初始化")
    agent = agent_registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(404, "Agent 不存在")
    return agent


@app.get("/api/v2/platform/skills")
async def list_platform_skills(category: str = ""):
    return {"skills": skill_registry.list_skills(category=category) if skill_registry else []}


@app.get("/api/v2/platform/tools")
async def list_platform_tools(tag: str = "", enabled_only: bool = True):
    return {"tools": tool_registry.list_tools(tag=tag, enabled_only=enabled_only) if tool_registry else []}


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
    if project_memory:
        project_memory.add_entry(
            project_id=project.project_id,
            memory_type="project_brief",
            title=f"{project.name} bootstrap",
            content=(
                f"Project created for target={project.target or 'N/A'}; "
                f"disease={project.disease or 'N/A'}; budget={project.budget_total}"
            ),
            tags=["bootstrap", "project"],
            source="api.create_project",
        )
    return {"project_id": project.project_id, "name": project.name}


@app.get("/api/v2/projects/board")
async def get_board():
    return kanban.get_board()


@app.post("/api/v2/projects/{project_id}/memory")
async def add_project_memory(project_id: str, data: dict):
    if not project_memory:
        raise HTTPException(503, "Project memory 未初始化")
    if not data.get("title") or not data.get("content"):
        raise HTTPException(400, "title 和 content 不能为空")
    entry = project_memory.add_entry(
        project_id=project_id,
        memory_type=data.get("memory_type", "note"),
        title=data["title"],
        content=data["content"],
        tags=data.get("tags", []),
        source=data.get("source", ""),
        author_id=data.get("author_id", ""),
        related_agents=data.get("related_agents", []),
        related_compounds=data.get("related_compounds", []),
    )
    return entry


@app.get("/api/v2/projects/{project_id}/memory")
async def list_project_memory(project_id: str, memory_type: str = "", query: str = "", limit: int = 50):
    if not project_memory:
        raise HTTPException(503, "Project memory 未初始化")
    return {
        "project_id": project_id,
        "entries": project_memory.list_entries(project_id, memory_type=memory_type, query=query, limit=limit),
        "stats": project_memory.stats(project_id),
    }


@app.get("/api/v2/projects/{project_id}/memory/context")
async def get_project_memory_context(project_id: str, query: str = "", limit: int = 8):
    if not project_memory:
        raise HTTPException(503, "Project memory 未初始化")
    return project_memory.get_context(project_id, query=query, limit=limit)


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
# Workflow骨架
# ──────────────────────────────────────────────
@app.get("/api/v2/workflows/templates")
async def list_workflow_templates(category: str = ""):
    if not workflow_orchestrator:
        raise HTTPException(503, "Workflow orchestrator 未初始化")
    return {"templates": workflow_orchestrator.list_templates(category=category)}


@app.post("/api/v2/workflows/runs")
async def start_workflow_run(data: dict):
    if not workflow_orchestrator:
        raise HTTPException(503, "Workflow orchestrator 未初始化")
    if not data.get("template_id") or not data.get("project_id") or not data.get("topic"):
        raise HTTPException(400, "template_id / project_id / topic 为必填")
    try:
        run = workflow_orchestrator.start_run(
            template_id=data["template_id"],
            project_id=data["project_id"],
            topic=data["topic"],
            created_by=data.get("created_by", ""),
            context=data.get("context", {}),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if project_memory:
        project_memory.add_entry(
            project_id=data["project_id"],
            memory_type="workflow",
            title=f"Workflow started: {run['template_name']}",
            content=f"Workflow topic: {data['topic']}",
            tags=["workflow", run["template_id"]],
            source="api.start_workflow_run",
            related_agents=[step["agent_id"] for step in run["steps"]],
        )
    return run


@app.get("/api/v2/workflows/runs")
async def list_workflow_runs(project_id: str = "", status: str = ""):
    if not workflow_orchestrator:
        raise HTTPException(503, "Workflow orchestrator 未初始化")
    return {"runs": workflow_orchestrator.list_runs(project_id=project_id, status=status)}


@app.get("/api/v2/workflows/runs/{run_id}")
async def get_workflow_run(run_id: str):
    if not workflow_orchestrator:
        raise HTTPException(503, "Workflow orchestrator 未初始化")
    run = workflow_orchestrator.get_run(run_id)
    if not run:
        raise HTTPException(404, "Workflow run 不存在")
    return run


@app.post("/api/v2/workflows/runs/{run_id}/steps/{step_id}/complete")
async def complete_workflow_step(run_id: str, step_id: str, data: dict = None):
    if not workflow_orchestrator:
        raise HTTPException(503, "Workflow orchestrator 未初始化")
    data = data or {}
    try:
        run = workflow_orchestrator.complete_step(
            run_id=run_id,
            step_id=step_id,
            output=data.get("output", ""),
            note=data.get("note", ""),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if project_memory:
        step = next((item for item in run["steps"] if item["step_id"] == step_id), None)
        project_memory.add_entry(
            project_id=run["project_id"],
            memory_type="workflow_step",
            title=f"Workflow step completed: {step['name'] if step else step_id}",
            content=data.get("output", "") or data.get("note", "") or "Step completed",
            tags=["workflow_step", run["template_id"]],
            source="api.complete_workflow_step",
            related_agents=[step["agent_id"]] if step else [],
        )
    return run


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
# 种子数据 & 场景模板
# ──────────────────────────────────────────────

@app.post("/api/v2/seed")
async def run_seed(data: dict = None):
    """加载种子数据（创建预设讨论和分身）"""
    data = data or {}
    from seeds.loader import seed_platform
    result = seed_platform(
        twin_engine,
        discussion_hub,
        max_topics=data.get("max_topics", 3),
    )
    return result


@app.get("/api/v2/scenarios")
async def list_scenarios():
    """获取讨论场景模板"""
    from seeds.loader import get_scenarios
    return {"scenarios": get_scenarios()}


@app.get("/api/v2/topics")
async def list_topics():
    """获取种子话题"""
    from seeds.loader import get_seed_topics
    return {"topics": get_seed_topics()}



# MCP Server路由
app.include_router(mcp_router)


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


@app.get("/css/{path:path}")
async def css_file(path: str):
    f = FRONTEND_DIR / "css" / path
    if f.exists():
        return FileResponse(f, media_type="text/css")
    raise HTTPException(404)


@app.get("/js/{path:path}")
async def js_file(path: str):
    f = FRONTEND_DIR / "js" / path
    if f.exists():
        return FileResponse(f, media_type="application/javascript")
    raise HTTPException(404)


@app.get("/img/{path:path}")
async def img_file(path: str):
    f = FRONTEND_DIR / "img" / path
    if f.exists():
        return FileResponse(f)
    raise HTTPException(404)
