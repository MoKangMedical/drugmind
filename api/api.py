"""
DrugMind v2.0 — REST API
药物研发数字分身协作平台
"""

import logging
from dataclasses import asdict
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
decision_logger = None
kanban = None
workspace_store = None
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
    decisions,
    board,
    project_workspaces,
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
    global decision_logger, workspace_store
    global agent_registry, skill_registry, tool_registry, project_memory, workflow_orchestrator
    twin_engine = twin
    discussion_engine = discussion
    decision_logger = decisions
    kanban = board
    workspace_store = project_workspaces
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
        "projects": kanban.count() if kanban else 0,
        "workspaces": workspace_store.count() if workspace_store else 0,
        "decisions": decision_logger.count() if decision_logger else 0,
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
        "projects_count": kanban.count() if kanban else 0,
        "workspaces_count": workspace_store.count() if workspace_store else 0,
        "decisions_count": decision_logger.count() if decision_logger else 0,
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
    if data.get("project_id"):
        if workspace_store:
            workspace_store.link_discussion(data["project_id"], session.session_id)
        if project_memory:
            project_memory.add_entry(
                project_id=data["project_id"],
                memory_type="discussion",
                title=f"Discussion created: {data['topic']}",
                content=data.get("context", "") or data["topic"],
                tags=["discussion", "project"],
                source="api.create_discussion",
                related_agents=data["participant_ids"],
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
    default_agents = [agent["agent_id"] for agent in agent_registry.list_agents(category="domain")] if agent_registry else []
    enabled_skills = [skill["skill_id"] for skill in skill_registry.list_skills(category="drug_discovery")[:6]] if skill_registry else []
    enabled_tools = [tool["tool_id"] for tool in tool_registry.list_tools(enabled_only=True)] if tool_registry else []
    workspace = workspace_store.ensure_workspace(
        project_id=project.project_id,
        name=project.name,
        owner_id=data.get("owner_id", ""),
        default_agents=default_agents,
        enabled_skills=enabled_skills,
        enabled_tools=enabled_tools,
        tags=data.get("tags", []),
    ) if workspace_store else None
    if project_memory:
        brief_entry = project_memory.add_entry(
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
        if workspace_store and brief_entry:
            workspace_store.add_note(project.project_id, f"Project brief created: {brief_entry['entry_id']}")
    return {"project_id": project.project_id, "name": project.name, "workspace": workspace}


@app.get("/api/v2/projects")
async def list_projects(status: str = ""):
    return {"projects": kanban.list_projects(status=status)}


@app.get("/api/v2/projects/{project_id}")
async def get_project(project_id: str):
    project = kanban.get_project(project_id)
    if not project:
        raise HTTPException(404, "项目不存在")
    return {
        "project": project,
        "workspace": workspace_store.get_workspace(project_id) if workspace_store else None,
        "memory_stats": project_memory.stats(project_id) if project_memory else {},
        "decisions_count": decision_logger.count(project_id) if decision_logger else 0,
    }


@app.get("/api/v2/projects/board")
async def get_board():
    return kanban.get_board()


@app.get("/api/v2/projects/{project_id}/workspace")
async def get_project_workspace(project_id: str):
    if not workspace_store:
        raise HTTPException(503, "Project workspace 未初始化")
    workspace = workspace_store.get_workspace(project_id)
    if not workspace:
        raise HTTPException(404, "项目工作区不存在")
    return workspace


@app.put("/api/v2/projects/{project_id}/workspace")
async def update_project_workspace(project_id: str, data: dict):
    if not workspace_store:
        raise HTTPException(503, "Project workspace 未初始化")
    try:
        return workspace_store.update_workspace(project_id, **data)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/v2/projects/{project_id}/workspace/members")
async def add_project_workspace_member(project_id: str, data: dict):
    if not workspace_store:
        raise HTTPException(503, "Project workspace 未初始化")
    try:
        return workspace_store.add_member(project_id, data)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


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


@app.post("/api/v2/projects/{project_id}/decisions")
async def add_project_decision(project_id: str, data: dict):
    if not decision_logger:
        raise HTTPException(503, "Decision logger 未初始化")
    if not data.get("topic") or not data.get("decision") or not data.get("rationale"):
        raise HTTPException(400, "topic / decision / rationale 为必填")
    record = decision_logger.log_decision(
        project_id=project_id,
        topic=data["topic"],
        decision=data["decision"],
        rationale=data["rationale"],
        participants=data.get("participants", []),
        opinions=data.get("opinions", []),
        dissenting=data.get("dissenting", []),
        conditions=data.get("conditions", []),
        session_id=data.get("session_id", ""),
        confidence=data.get("confidence", 0.0),
        created_by=data.get("created_by", ""),
        workflow_run_id=data.get("workflow_run_id", ""),
        related_memory_entries=data.get("related_memory_entries", []),
        related_discussions=data.get("related_discussions", []),
    )
    kanban.add_decision(project_id, data["decision"], data["rationale"])
    if workspace_store:
        workspace_store.link_decision(project_id, record.decision_id)
    if project_memory:
        project_memory.add_entry(
            project_id=project_id,
            memory_type="decision",
            title=f"Decision: {data['decision']} - {data['topic']}",
            content=data["rationale"],
            tags=["decision", data["decision"]],
            source="api.add_project_decision",
            related_agents=data.get("participants", []),
        )
    if data.get("workflow_run_id") and workflow_orchestrator:
        workflow_orchestrator.link_artifact(
            data["workflow_run_id"],
            artifact_type="decision",
            artifact_id=record.decision_id,
            summary=data["decision"],
        )
    return asdict(record)


@app.get("/api/v2/projects/{project_id}/decisions")
async def list_project_decisions(project_id: str, topic_filter: str = ""):
    if not decision_logger:
        raise HTTPException(503, "Decision logger 未初始化")
    return {"decisions": decision_logger.get_decision_history(project_id=project_id, topic_filter=topic_filter)}


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
    if data.get("project_id"):
        kanban.link_compound(data["project_id"], comp.compound_id, comp.name)
        if workspace_store:
            workspace_store.link_compound(data["project_id"], comp.compound_id)
        if project_memory:
            project_memory.add_entry(
                project_id=data["project_id"],
                memory_type="compound",
                title=f"Compound added: {comp.name or comp.compound_id}",
                content=f"SMILES: {comp.smiles}",
                tags=["compound", comp.stage],
                source="api.add_compound",
                related_compounds=[comp.compound_id],
            )
    return {"compound_id": comp.compound_id}


@app.get("/api/v2/compounds/pipeline")
async def get_pipeline():
    return compound_tracker.get_pipeline()


@app.get("/api/v2/compounds")
async def list_compounds(project_id: str = "", stage: str = ""):
    return {"compounds": compound_tracker.list_compounds(project_id=project_id, stage=stage)}


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
    execution_context = data.get("execution_context", {})
    if project_memory:
        execution_context = {
            **execution_context,
            "memory_context": project_memory.get_context(data["project_id"], query=data.get("topic", ""), limit=6),
        }
    if workspace_store:
        execution_context["workspace"] = workspace_store.get_workspace(data["project_id"])
    try:
        run = workflow_orchestrator.start_run(
            template_id=data["template_id"],
            project_id=data["project_id"],
            topic=data["topic"],
            created_by=data.get("created_by", ""),
            context=data.get("context", {}),
            execution_context=execution_context,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if workspace_store:
        workspace_store.link_workflow(data["project_id"], run["run_id"])
    if project_memory:
        workflow_entry = project_memory.add_entry(
            project_id=data["project_id"],
            memory_type="workflow",
            title=f"Workflow started: {run['template_name']}",
            content=f"Workflow topic: {data['topic']}",
            tags=["workflow", run["template_id"]],
            source="api.start_workflow_run",
            related_agents=[step["agent_id"] for step in run["steps"]],
        )
        workflow_orchestrator.link_artifact(
            run["run_id"],
            artifact_type="memory",
            artifact_id=workflow_entry["entry_id"],
            summary=workflow_entry["title"],
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


@app.post("/api/v2/workflows/runs/{run_id}/context")
async def update_workflow_context(run_id: str, data: dict):
    if not workflow_orchestrator:
        raise HTTPException(503, "Workflow orchestrator 未初始化")
    try:
        return workflow_orchestrator.update_context(
            run_id=run_id,
            context_patch=data.get("context_patch", {}),
            note=data.get("note", ""),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


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
