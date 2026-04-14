"""
DrugMind v2.0 — REST API
药物研发数字分身协作平台
"""

import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .mcp_server import router as mcp_router, init_mcp
from media import MimoMediaClient, MediaStore

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
second_me_bindings = None
h2a_store = None
drug_discovery_hub = None
blatant_why_adapter = None
medi_pharma_adapter = None
media_client = MimoMediaClient()
media_store = MediaStore()


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
    second_me_binding_store=None,
    agent_reg=None,
    skill_reg=None,
    tool_reg=None,
    project_memory_store=None,
    drug_discovery_engine=None,
    by_adapter=None,
    medi_pharma_engine=None,
    workflow_engine=None,
    h2a_threads=None,
):
    global twin_engine, discussion_engine, kanban, compound_tracker, user_mgr, discussion_hub, second_me
    global decision_logger, workspace_store, second_me_bindings, h2a_store
    global agent_registry, skill_registry, tool_registry, project_memory, workflow_orchestrator
    global drug_discovery_hub, blatant_why_adapter, medi_pharma_adapter
    twin_engine = twin
    discussion_engine = discussion
    decision_logger = decisions
    kanban = board
    workspace_store = project_workspaces
    compound_tracker = tracker
    user_mgr = users
    discussion_hub = hub
    second_me = sm_integration
    second_me_bindings = second_me_binding_store
    agent_registry = agent_reg
    skill_registry = skill_reg
    tool_registry = tool_reg
    project_memory = project_memory_store
    drug_discovery_hub = drug_discovery_engine
    blatant_why_adapter = by_adapter
    medi_pharma_adapter = medi_pharma_engine
    workflow_orchestrator = workflow_engine
    h2a_store = h2a_threads
    # 初始化MCP Server
    init_mcp(
        twin,
        discussion,
        hub,
        users,
        drug_discovery_engine,
        board,
        tracker,
        by_adapter,
        medi_pharma_engine,
    )


def _safe_timestamp(value: str) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def build_project_timeline(project_id: str, limit: int = 120) -> list[dict]:
    timeline: list[dict] = []
    workspace = workspace_store.get_workspace(project_id) if workspace_store else {}
    discussion_ids = set((workspace or {}).get("linked_discussions", []))

    if project_memory:
        for entry in project_memory.list_entries(project_id, limit=limit):
            timeline.append(
                {
                    "item_id": entry["entry_id"],
                    "item_type": "memory",
                    "timestamp": entry["created_at"],
                    "title": entry["title"],
                    "summary": entry["content"][:320],
                    "status": entry["memory_type"],
                    "actor": ", ".join(entry.get("related_agents", [])[:3]),
                    "source_id": entry["entry_id"],
                    "meta": {
                        "memory_type": entry["memory_type"],
                        "tags": entry.get("tags", []),
                        "related_compounds": entry.get("related_compounds", []),
                    },
                }
            )

    if decision_logger:
        for record in decision_logger.get_decision_history(project_id=project_id):
            timeline.append(
                {
                    "item_id": record["decision_id"],
                    "item_type": "decision",
                    "timestamp": record["timestamp"],
                    "title": f"{record['decision']} · {record['topic']}",
                    "summary": record["rationale"][:320],
                    "status": record["decision"],
                    "actor": ", ".join(record.get("participants", [])[:3]),
                    "source_id": record["decision_id"],
                    "meta": {
                        "confidence": record.get("confidence", 0.0),
                        "workflow_run_id": record.get("workflow_run_id", ""),
                        "conditions": record.get("conditions", []),
                        "dissenting": record.get("dissenting", []),
                    },
                }
            )

    if workflow_orchestrator:
        for run in workflow_orchestrator.list_runs(project_id=project_id):
            timeline.append(
                {
                    "item_id": run["run_id"],
                    "item_type": "workflow_run",
                    "timestamp": run["created_at"],
                    "title": f"Workflow started · {run['template_name']}",
                    "summary": run["topic"],
                    "status": run["status"],
                    "actor": run.get("created_by", ""),
                    "source_id": run["run_id"],
                    "meta": {
                        "template_id": run["template_id"],
                        "current_step_index": run.get("current_step_index", 0),
                        "linked_decisions": run.get("linked_decisions", []),
                        "linked_discussions": run.get("linked_discussions", []),
                    },
                }
            )
            for step in run.get("steps", []):
                step_timestamp = step.get("completed_at") or step.get("started_at") or run["created_at"]
                timeline.append(
                    {
                        "item_id": f"{run['run_id']}::{step['step_id']}",
                        "item_type": "workflow_step",
                        "timestamp": step_timestamp,
                        "title": f"{step['name']} · {step['owner_label'] or step['agent_id']}",
                        "summary": step.get("executor_summary") or step.get("output", "")[:320] or step["description"],
                        "status": step["status"],
                        "actor": step.get("owner_label") or step.get("owner_id") or step["agent_id"],
                        "source_id": run["run_id"],
                        "meta": {
                            "step_id": step["step_id"],
                            "agent_id": step["agent_id"],
                            "owner_type": step.get("owner_type", "agent"),
                            "owner_id": step.get("owner_id", ""),
                            "approval_required": step.get("approval_required", False),
                            "approval_status": step.get("approval_status", "not_required"),
                            "artifacts": step.get("artifacts", []),
                            "notes": step.get("notes", []),
                        },
                    }
                )
                for approval in step.get("approvals", []):
                    timeline.append(
                        {
                            "item_id": f"{run['run_id']}::{step['step_id']}::approval::{approval['timestamp']}",
                            "item_type": "approval",
                            "timestamp": approval["timestamp"],
                            "title": f"Approval · {step['name']}",
                            "summary": approval.get("note", ""),
                            "status": "approved" if approval.get("approved") else "rejected",
                            "actor": approval.get("approver_id", ""),
                            "source_id": run["run_id"],
                            "meta": {
                                "step_id": step["step_id"],
                                "approved": approval.get("approved", False),
                            },
                        }
                    )

    if drug_discovery_hub:
        for execution in drug_discovery_hub.list_executions(project_id=project_id, limit=limit):
            timeline.append(
                {
                    "item_id": execution["execution_id"],
                    "item_type": "capability_execution",
                    "timestamp": execution.get("updated_at") or execution.get("created_at", ""),
                    "title": f"Capability · {execution['capability_name']}",
                    "summary": execution.get("summary", "")[:320],
                    "status": execution.get("status", "completed"),
                    "actor": ", ".join(execution.get("related_agents", [])[:3]) or execution.get("triggered_by", ""),
                    "source_id": execution["execution_id"],
                    "meta": {
                        "capability_id": execution["capability_id"],
                        "related_compounds": execution.get("related_compounds", []),
                        "second_me_sync": execution.get("second_me_sync", {}),
                    },
                }
            )

    if second_me_bindings:
        for binding in second_me_bindings.list_bindings(project_id=project_id):
            timestamp = binding.get("last_synced_at") or binding.get("updated_at") or binding.get("created_at", "")
            timeline.append(
                {
                    "item_id": binding["binding_id"],
                    "item_type": "second_me",
                    "timestamp": timestamp,
                    "title": f"Second Me · {binding.get('display_name') or binding['instance_id']}",
                    "summary": binding.get("last_sync_summary", "") or "Second Me binding created",
                    "status": binding.get("status", "linked"),
                    "actor": binding.get("user_id", ""),
                    "source_id": binding["binding_id"],
                    "meta": {
                        "instance_id": binding["instance_id"],
                        "share_url": binding.get("share_url", ""),
                        "linked_workflows": binding.get("linked_workflows", []),
                    },
                }
            )

    if discussion_engine:
        for session_id in discussion_ids:
            session = discussion_engine.sessions.get(session_id)
            if not session:
                continue
            timeline.append(
                {
                    "item_id": session.session_id,
                    "item_type": "discussion",
                    "timestamp": session.created_at,
                    "title": f"Discussion · {session.topic}",
                    "summary": (session.summary or session.topic)[:320],
                    "status": session.status,
                    "actor": ", ".join(session.participants[:3]),
                    "source_id": session.session_id,
                    "meta": {
                        "participants": session.participants,
                        "messages_count": len(session.messages),
                    },
                }
            )

    if h2a_store:
        for thread in h2a_store.list_threads(project_id=project_id):
            timeline.append(
                {
                    "item_id": thread["thread_id"],
                    "item_type": "h2a_thread",
                    "timestamp": thread["created_at"],
                    "title": (
                        f"H2A Group · {thread['human_label']} ↔ {len(thread.get('agent_ids', []))} Agents"
                        if len(thread.get("agent_ids", [])) > 1
                        else f"H2A Thread · {thread['human_label']} ↔ {thread['agent_label']}"
                    ),
                    "summary": thread.get("title", ""),
                    "status": thread.get("status", "active"),
                    "actor": thread["human_label"],
                    "source_id": thread["thread_id"],
                    "meta": {
                        "agent_id": thread["agent_id"],
                        "agent_ids": thread.get("agent_ids", []),
                        "human_id": thread["human_id"],
                        "messages_count": len(thread.get("messages", [])),
                        "mode": thread.get("mode", "single"),
                    },
                }
            )
            for message in thread.get("messages", []):
                timeline.append(
                    {
                        "item_id": message["message_id"],
                        "item_type": "h2a_message",
                        "timestamp": message["created_at"],
                        "title": f"H2A · {message['sender_label']}",
                        "summary": message["content"][:320],
                        "status": message["sender_type"],
                        "actor": message["sender_label"],
                        "source_id": thread["thread_id"],
                        "meta": {
                            "thread_id": thread["thread_id"],
                            "agent_id": thread["agent_id"],
                            "agent_ids": thread.get("agent_ids", []),
                            "human_id": thread["human_id"],
                            "sender_type": message["sender_type"],
                            "mode": thread.get("mode", "single"),
                        },
                    }
                )

    timeline.sort(key=lambda item: _safe_timestamp(item["timestamp"]), reverse=True)
    return timeline[:limit]


def build_project_workbench(project_id: str, timeline_limit: int = 120) -> dict:
    project = kanban.get_project(project_id) if kanban else None
    if not project:
        raise HTTPException(404, "项目不存在")

    return {
        "project": project,
        "workspace": workspace_store.get_workspace(project_id) if workspace_store else None,
        "implementation": drug_discovery_hub.get_project_implementation(project_id) if drug_discovery_hub else {},
        "compounds": compound_tracker.list_compounds(project_id=project_id) if compound_tracker else [],
        "workflow_runs": workflow_orchestrator.list_runs(project_id=project_id) if workflow_orchestrator else [],
        "workflow_templates": workflow_orchestrator.list_templates() if workflow_orchestrator else [],
        "second_me_bindings": second_me_bindings.list_bindings(project_id=project_id) if second_me_bindings else [],
        "h2a_threads": h2a_store.list_threads(project_id=project_id) if h2a_store else [],
        "timeline": build_project_timeline(project_id, limit=timeline_limit),
        "agents": agent_registry.list_agents(active_only=False) if agent_registry else [],
        "medi_pharma": medi_pharma_adapter.describe() if medi_pharma_adapter else {},
    }


def _build_bridge_project(data: dict) -> dict:
    project_id = data.get("project_id", "")
    project = kanban.get_project(project_id) if kanban and project_id else None
    if project:
        return project
    return {
        "project_id": project_id or "adhoc_medi_pharma",
        "name": data.get("name") or data.get("target") or data.get("disease") or "Ad Hoc MediPharma Request",
        "target": data.get("target", ""),
        "disease": data.get("disease", ""),
        "target_chembl_id": data.get("target_chembl_id", ""),
        "modality": data.get("modality", "small_molecule"),
    }


def _collect_bridge_compounds(project_id: str, data: dict) -> list[dict]:
    if project_id and compound_tracker:
        compounds = compound_tracker.list_compounds(project_id=project_id)
        if compounds:
            return compounds
    compounds = data.get("compounds", [])
    return compounds if isinstance(compounds, list) else []


def _run_medi_pharma_bridge(action: str, data: dict | None = None) -> dict:
    if not medi_pharma_adapter:
        raise HTTPException(503, "MediPharma adapter 未初始化")

    data = data or {}
    project_id = data.get("project_id", "")
    input_payload = data.get("input_payload")
    if not isinstance(input_payload, dict):
        input_payload = data
    project = _build_bridge_project({**data, **input_payload})
    compounds = _collect_bridge_compounds(project_id, data)

    if action in {"status", "probe_status"}:
        return medi_pharma_adapter.probe_status()
    if action == "health":
        return medi_pharma_adapter.health()
    if action == "ecosystem":
        return medi_pharma_adapter.ecosystem()
    if action in {"discover_targets", "target_discovery"}:
        return medi_pharma_adapter.discover_targets(project=project, input_payload=input_payload)
    if action in {"run_screening", "screening_run", "virtual_screening"}:
        return medi_pharma_adapter.run_screening(project=project, compounds=compounds, input_payload=input_payload)
    if action in {"generate", "molecule_generation"}:
        return medi_pharma_adapter.generate(project=project, input_payload=input_payload)
    if action in {"predict_admet", "admet_predict"}:
        return medi_pharma_adapter.predict_admet(smiles=input_payload.get("smiles", ""))
    if action in {"batch_predict_admet", "admet_batch"}:
        return medi_pharma_adapter.batch_predict_admet(compounds=compounds, input_payload=input_payload)
    if action in {"optimize", "lead_optimization"}:
        return medi_pharma_adapter.optimize(compounds=compounds, input_payload=input_payload)
    if action in {"run_pipeline", "pipeline_run"}:
        return medi_pharma_adapter.run_pipeline(project=project, input_payload=input_payload)
    if action in {"knowledge_report", "knowledge_engine"}:
        return medi_pharma_adapter.knowledge_report(project=project, input_payload=input_payload)
    raise HTTPException(400, f"未知 MediPharma action: {action}")


def _compose_h2a_context(project_id: str, thread: dict, question: str) -> str:
    project = kanban.get_project(project_id) if kanban else {}
    workspace = workspace_store.get_workspace(project_id) if workspace_store else {}
    memory_context = project_memory.get_context(project_id, query=question, limit=4) if project_memory else {"context_blocks": []}
    recent_messages = thread.get("messages", [])[-6:]
    transcript = "\n".join(
        f"{message['sender_label']} ({message['sender_type']}): {message['content']}"
        for message in recent_messages
    )
    memory_blocks = "\n".join(
        f"- {block['title']}: {block['content'][:220]}"
        for block in memory_context.get("context_blocks", [])
    )
    return (
        f"项目: {project.get('name', project_id)}\n"
        f"靶点: {project.get('target', 'N/A')} | 疾病: {project.get('disease', 'N/A')} | 阶段: {project.get('stage', 'N/A')}\n"
        f"Human: {thread.get('human_label', '')}\n"
        f"Agent: {thread.get('agent_label', '')}\n"
        f"Workspace members: {len(workspace.get('members', []))}\n"
        f"Recent transcript:\n{transcript or 'N/A'}\n\n"
        f"Relevant project memory:\n{memory_blocks or 'N/A'}"
    )


def _ensure_project_user_member(project_id: str, user_id: str) -> dict | None:
    if not user_mgr or not workspace_store or not user_id.startswith("user_"):
        return None
    profile = user_mgr.get_profile(user_id)
    if not profile:
        return None
    projects = list(profile.get("projects", []))
    if project_id not in projects:
        projects.append(project_id)
        user_mgr.update_profile(user_id, projects=projects)
        profile = user_mgr.get_profile(user_id) or profile
    workspace = workspace_store.get_workspace(project_id) or {}
    members = workspace.get("members", [])
    if any((member.get("user_id") or member.get("id")) == user_id for member in members):
        return profile
    workspace_store.add_member(
        project_id,
        {
            "user_id": profile["user_id"],
            "name": profile.get("display_name") or profile.get("username") or profile["user_id"],
            "role": profile.get("title") or "Workspace Member",
            "type": "user",
            "permissions": profile.get("permissions", ["h2a.chat", "workflow.view"]),
            "organization": profile.get("organization", ""),
        },
    )
    return profile


def _build_project_user_identity(project_id: str, user_id: str) -> dict:
    if not user_mgr:
        raise HTTPException(503, "用户系统未初始化")
    profile = user_mgr.get_profile(user_id)
    if not profile:
        raise HTTPException(404, "用户不存在")

    workspace_profile = _ensure_project_user_member(project_id, user_id)
    workspace = workspace_store.get_workspace(project_id) if workspace_store else {}
    members = (workspace or {}).get("members", [])
    membership = next(
        (
            member
            for member in members
            if (member.get("user_id") or member.get("id") or member.get("name")) == user_id
        ),
        {},
    )
    effective_permissions = sorted(
        set((profile or {}).get("permissions", [])) | set((membership or {}).get("permissions", []))
    )
    return {
        "project_id": project_id,
        "user": workspace_profile or profile,
        "workspace_member": membership,
        "effective_permissions": effective_permissions,
        "workspace_role": membership.get("role") or profile.get("title") or profile.get("system_role", "member"),
        "status": membership.get("status") or profile.get("status", "active"),
    }


def _run_h2a_exchange(thread_id: str, human_message: str) -> dict:
    if not h2a_store:
        raise HTTPException(503, "H2A store 未初始化")
    thread = h2a_store.get_thread(thread_id)
    if not thread:
        raise HTTPException(404, "H2A thread 不存在")

    h2a_store.add_message(
        thread_id,
        sender_type="human",
        sender_id=thread["human_id"],
        sender_label=thread["human_label"],
        content=human_message,
    )

    refreshed_thread = h2a_store.get_thread(thread_id)
    agent_messages = []
    rolling_context = _compose_h2a_context(thread["project_id"], refreshed_thread, human_message)
    for index, agent_id in enumerate(refreshed_thread.get("agent_ids", []) or [thread["agent_id"]]):
        agent = agent_registry.get_agent(agent_id) if agent_registry else None
        if not agent:
            continue
        response = twin_engine.ask_agent(
            agent_id=agent_id,
            question=human_message,
            context=rolling_context,
            agent_profile=agent,
        )
        sender_label = refreshed_thread.get("agent_labels", [thread["agent_label"]])[index] if refreshed_thread.get("agent_labels") else agent.get("name", agent_id)
        agent_message = h2a_store.add_message(
            thread_id,
            sender_type="agent",
            sender_id=agent_id,
            sender_label=sender_label,
            content=response.message,
            meta={
                "confidence": response.confidence,
                "reasoning": response.reasoning,
                "group_mode": refreshed_thread.get("mode", "single"),
            },
        )
        agent_messages.append(agent_message)
        rolling_context += f"\n{sender_label} (agent): {response.message}"

    if not agent_messages:
        raise HTTPException(404, "Agent 不存在")

    if project_memory:
        project_memory.add_entry(
            project_id=thread["project_id"],
            memory_type="h2a_group_exchange" if len(refreshed_thread.get("agent_ids", [])) > 1 else "h2a_exchange",
            title=f"H2A · {thread['human_label']} ↔ {', '.join(refreshed_thread.get('agent_labels', [])[:3])}",
            content="Human: " + human_message + "\n\n" + "\n\n".join(
                f"{message['sender_label']}: {message['content']}" for message in agent_messages
            ),
            tags=["h2a", *refreshed_thread.get("agent_ids", [])],
            source="api.h2a_exchange",
            author_id=thread["human_id"],
            related_agents=refreshed_thread.get("agent_ids", []),
        )

    return {
        "thread": h2a_store.get_thread(thread_id),
        "agent_message": agent_messages[-1],
        "agent_messages": agent_messages,
    }


# ──────────────────────────────────────────────
# 健康检查
# ──────────────────────────────────────────────
@app.get("/health")
async def health():
    medi_pharma_status = medi_pharma_adapter.probe_status() if medi_pharma_adapter else {"status": "disabled"}
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
        "registered_capabilities": drug_discovery_hub.count_capabilities() if drug_discovery_hub else 0,
        "workflow_runs": workflow_orchestrator.count_runs() if workflow_orchestrator else 0,
        "capability_executions": drug_discovery_hub.count_executions() if drug_discovery_hub else 0,
        "second_me_instances": len(second_me.instances) if second_me else 0,
        "second_me_bindings": second_me_bindings.count() if second_me_bindings else 0,
        "h2a_threads": h2a_store.count() if h2a_store else 0,
        "medi_pharma": medi_pharma_status,
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


@app.get("/api/v2/projects/{project_id}/identity/{user_id}")
async def get_project_user_identity(project_id: str, user_id: str):
    return _build_project_user_identity(project_id, user_id)


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
        "registered_capabilities": drug_discovery_hub.count_capabilities() if drug_discovery_hub else 0,
        "workflow_runs": workflow_orchestrator.count_runs() if workflow_orchestrator else 0,
        "capability_executions": drug_discovery_hub.count_executions() if drug_discovery_hub else 0,
        "second_me_instances": len(second_me.instances) if second_me else 0,
        "second_me_bindings": second_me_bindings.count() if second_me_bindings else 0,
        "h2a_threads": h2a_store.count() if h2a_store else 0,
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
        "drug_discovery": drug_discovery_hub.describe() if drug_discovery_hub else {},
        "workflow_templates": workflow_orchestrator.list_templates() if workflow_orchestrator else [],
        "workflow_runs": workflow_orchestrator.list_runs() if workflow_orchestrator else [],
        "blatant_why": blatant_why_adapter.describe() if blatant_why_adapter else {},
        "medi_pharma": medi_pharma_adapter.describe() if medi_pharma_adapter else {"status": "disabled"},
        "second_me": second_me.describe_capabilities() if second_me else {"mode": "disabled"},
        "second_me_bindings": second_me_bindings.list_bindings() if second_me_bindings else [],
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
# Drug Discovery Implementation
# ──────────────────────────────────────────────
@app.get("/api/v2/drug-discovery/capabilities")
async def list_drug_discovery_capabilities(stage_id: str = "", category: str = ""):
    if not drug_discovery_hub:
        raise HTTPException(503, "Drug discovery hub 未初始化")
    return {"capabilities": drug_discovery_hub.list_capabilities(stage_id=stage_id, category=category)}


@app.get("/api/v2/drug-discovery/blueprints")
async def list_drug_discovery_blueprints():
    if not drug_discovery_hub:
        raise HTTPException(503, "Drug discovery hub 未初始化")
    return {"blueprints": drug_discovery_hub.list_blueprints()}


@app.get("/api/v2/projects/{project_id}/implementation")
async def get_project_implementation(project_id: str):
    if not drug_discovery_hub:
        raise HTTPException(503, "Drug discovery hub 未初始化")
    try:
        return drug_discovery_hub.get_project_implementation(project_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/v2/projects/{project_id}/implementation/bootstrap")
async def bootstrap_project_implementation(project_id: str, data: dict = None):
    if not drug_discovery_hub:
        raise HTTPException(503, "Drug discovery hub 未初始化")
    data = data or {}
    try:
        return drug_discovery_hub.bootstrap_project(
            project_id,
            blueprint_id=data.get("blueprint_id", ""),
            activated_by=data.get("activated_by", ""),
            note=data.get("note", ""),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/v2/projects/{project_id}/capabilities/executions")
async def list_project_capability_executions(project_id: str, capability_id: str = "", limit: int = 50):
    if not drug_discovery_hub:
        raise HTTPException(503, "Drug discovery hub 未初始化")
    return {
        "project_id": project_id,
        "executions": drug_discovery_hub.list_executions(project_id=project_id, capability_id=capability_id, limit=limit),
    }


@app.post("/api/v2/projects/{project_id}/capabilities/{capability_id}/execute")
async def execute_project_capability(project_id: str, capability_id: str, data: dict = None):
    if not drug_discovery_hub:
        raise HTTPException(503, "Drug discovery hub 未初始化")
    data = data or {}
    try:
        return drug_discovery_hub.execute_capability(
            project_id,
            capability_id,
            input_payload=data.get("input_payload", {}),
            triggered_by=data.get("triggered_by", ""),
            sync_to_second_me=bool(data.get("sync_to_second_me", False)),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


# ──────────────────────────────────────────────
# BY Integration
# ──────────────────────────────────────────────
@app.get("/api/v2/integrations/blatant-why")
async def blatant_why_overview():
    if not blatant_why_adapter:
        raise HTTPException(503, "blatant-why adapter 未初始化")
    return blatant_why_adapter.describe()


@app.get("/api/v2/integrations/blatant-why/mcp-servers")
async def blatant_why_mcp_servers(domain: str = ""):
    if not blatant_why_adapter:
        raise HTTPException(503, "blatant-why adapter 未初始化")
    return {"servers": blatant_why_adapter.mcp_bridge.list_servers(domain=domain)}


@app.get("/api/v2/integrations/blatant-why/providers")
async def blatant_why_providers():
    if not blatant_why_adapter:
        raise HTTPException(503, "blatant-why adapter 未初始化")
    return blatant_why_adapter.mcp_bridge.describe()


@app.post("/api/v2/integrations/blatant-why/research")
async def blatant_why_target_research(data: dict):
    if not blatant_why_adapter:
        raise HTTPException(503, "blatant-why adapter 未初始化")
    project_id = data.get("project_id", "")
    project = kanban.get_project(project_id) if kanban and project_id else None
    if not project:
        target = data.get("target", "").strip()
        if not target:
            raise HTTPException(400, "需要 project_id 或 target")
        project = {
            "project_id": project_id or "adhoc_structural_research",
            "name": data.get("name") or target,
            "target": target,
            "disease": data.get("disease", ""),
            "modality": data.get("modality", "small_molecule"),
        }
    return blatant_why_adapter.run_target_research(
        project=project,
        modality=data.get("modality") or project.get("modality", "small_molecule"),
        organism_id=int(data.get("organism_id", 9606)),
        pdb_rows=int(data.get("pdb_rows", 6)),
        sabdab_limit=int(data.get("sabdab_limit", 6)),
    )


@app.post("/api/v2/integrations/blatant-why/screening")
async def blatant_why_screening(data: dict):
    if not blatant_why_adapter:
        raise HTTPException(503, "blatant-why adapter 未初始化")
    project_id = data.get("project_id", "")
    compounds = compound_tracker.list_compounds(project_id=project_id) if compound_tracker and project_id else data.get("compounds", [])
    if not compounds:
        raise HTTPException(400, "需要 project_id 或 compounds")
    project = kanban.get_project(project_id) if kanban and project_id else {"project_id": project_id, "name": data.get("name", "")}
    return blatant_why_adapter.run_small_molecule_screening(project=project, compounds=compounds)


@app.post("/api/v2/integrations/blatant-why/biologics-pipeline")
async def blatant_why_biologics_pipeline(data: dict):
    if not blatant_why_adapter:
        raise HTTPException(503, "blatant-why adapter 未初始化")
    project_id = data.get("project_id", "")
    project = kanban.get_project(project_id) if kanban and project_id else None
    if not project:
        raise HTTPException(404, "项目不存在")
    campaign = blatant_why_adapter.biologics_pipeline.build_campaign(
        project=project,
        modality=data.get("modality", project.get("modality", "nanobody")),
        scaffolds=data.get("scaffolds"),
        seeds=int(data.get("seeds", 8)),
        designs_per_seed=int(data.get("designs_per_seed", 8)),
        complexity=data.get("complexity", "standard"),
    )
    if not data.get("submit_job") and not data.get("tamarind_settings"):
        return campaign
    job_settings = data.get("tamarind_settings") or {
        "jobType": data.get("job_type", f"{data.get('modality', project.get('modality', 'nanobody'))}_design"),
        "settings": {
            "target": project.get("target", ""),
            "modality": data.get("modality", project.get("modality", "nanobody")),
            "scaffolds": campaign.get("scaffolds", []),
            "seeds": int(data.get("seeds", 8)),
            "designsPerSeed": int(data.get("designs_per_seed", 8)),
            "complexity": data.get("complexity", "standard"),
            **(data.get("job_settings", {}) or {}),
        },
    }
    job_submission = blatant_why_adapter.submit_tamarind_job(
        project=project,
        modality=data.get("modality", project.get("modality", "nanobody")),
        settings=job_settings,
        wait_for_completion=bool(data.get("wait_for_completion", False)),
        poll_interval_seconds=int(data.get("poll_interval_seconds", 20)),
        timeout_seconds=int(data.get("timeout_seconds", 900)),
    )
    return {
        "campaign": campaign,
        "tamarind_job": job_submission,
    }


# ──────────────────────────────────────────────
# MediPharma Integration
# ──────────────────────────────────────────────
@app.get("/api/v2/integrations/medi-pharma")
async def medi_pharma_overview():
    if not medi_pharma_adapter:
        raise HTTPException(503, "MediPharma adapter 未初始化")
    return medi_pharma_adapter.describe()


@app.get("/api/v2/integrations/medi-pharma/health")
async def medi_pharma_health():
    return _run_medi_pharma_bridge("health")


@app.get("/api/v2/integrations/medi-pharma/ecosystem")
async def medi_pharma_ecosystem():
    return _run_medi_pharma_bridge("ecosystem")


@app.post("/api/v2/integrations/medi-pharma/execute")
async def medi_pharma_execute(data: dict):
    action = data.get("action", "").strip()
    if not action:
        raise HTTPException(400, "action 为必填")
    return _run_medi_pharma_bridge(action, data)


@app.post("/api/v2/integrations/medi-pharma/targets/discover")
async def medi_pharma_discover_targets(data: dict):
    return _run_medi_pharma_bridge("discover_targets", data)


@app.post("/api/v2/integrations/medi-pharma/screening/run")
async def medi_pharma_screening_run(data: dict):
    return _run_medi_pharma_bridge("run_screening", data)


@app.post("/api/v2/integrations/medi-pharma/generate")
async def medi_pharma_generate(data: dict):
    return _run_medi_pharma_bridge("generate", data)


@app.post("/api/v2/integrations/medi-pharma/admet/predict")
async def medi_pharma_admet_predict(data: dict):
    return _run_medi_pharma_bridge("predict_admet", data)


@app.post("/api/v2/integrations/medi-pharma/admet/batch")
async def medi_pharma_admet_batch(data: dict):
    return _run_medi_pharma_bridge("batch_predict_admet", data)


@app.post("/api/v2/integrations/medi-pharma/optimize")
async def medi_pharma_optimize(data: dict):
    return _run_medi_pharma_bridge("optimize", data)


@app.post("/api/v2/integrations/medi-pharma/pipeline/run")
async def medi_pharma_pipeline_run(data: dict):
    return _run_medi_pharma_bridge("run_pipeline", data)


@app.post("/api/v2/integrations/medi-pharma/knowledge/report")
async def medi_pharma_knowledge_report(data: dict):
    return _run_medi_pharma_bridge("knowledge_report", data)


@app.get("/api/v2/integrations/tamarind/status")
async def tamarind_status():
    if not blatant_why_adapter:
        raise HTTPException(503, "Tamarind client 未初始化")
    return blatant_why_adapter.tamarind_client.probe_status()


@app.get("/api/v2/integrations/tamarind/tools")
async def tamarind_tools():
    if not blatant_why_adapter:
        raise HTTPException(503, "Tamarind client 未初始化")
    try:
        return blatant_why_adapter.tamarind_client.list_available_tools()
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/v2/integrations/tamarind/jobs")
async def tamarind_list_jobs(job_name: str = "", status: str = "", limit: int = 50):
    if not blatant_why_adapter:
        raise HTTPException(503, "Tamarind client 未初始化")
    try:
        return blatant_why_adapter.tamarind_client.list_jobs(job_name=job_name, status=status, limit=limit)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/v2/integrations/tamarind/jobs/{job_name}")
async def tamarind_get_job(job_name: str):
    if not blatant_why_adapter:
        raise HTTPException(503, "Tamarind client 未初始化")
    try:
        return blatant_why_adapter.tamarind_client.get_job(job_name)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/v2/integrations/tamarind/jobs")
async def tamarind_submit_job(data: dict):
    if not blatant_why_adapter:
        raise HTTPException(503, "Tamarind client 未初始化")
    job_name = data.get("job_name", "").strip()
    job_type = data.get("job_type", "").strip()
    settings = data.get("settings")
    if not job_name or not job_type or not isinstance(settings, dict):
        raise HTTPException(400, "job_name、job_type、settings 为必填")
    try:
        return blatant_why_adapter.tamarind_client.submit_job(
            job_name=job_name,
            job_type=job_type,
            settings=settings,
            metadata=data.get("metadata"),
            inputs=data.get("inputs"),
            wait_for_completion=bool(data.get("wait_for_completion", False)),
            poll_interval_seconds=int(data.get("poll_interval_seconds", 20)),
            timeout_seconds=int(data.get("timeout_seconds", 900)),
            include_result=bool(data.get("include_result", True)),
        )
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/v2/integrations/tamarind/jobs/{job_name}/poll")
async def tamarind_poll_job(job_name: str, data: dict = None):
    if not blatant_why_adapter:
        raise HTTPException(503, "Tamarind client 未初始化")
    data = data or {}
    try:
        return blatant_why_adapter.tamarind_client.poll_job(
            job_name,
            interval_seconds=int(data.get("interval_seconds", 20)),
            timeout_seconds=int(data.get("timeout_seconds", 900)),
            include_result=bool(data.get("include_result", False)),
        )
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/v2/integrations/tamarind/jobs/{job_name}/result")
async def tamarind_get_result(job_name: str, data: dict = None):
    if not blatant_why_adapter:
        raise HTTPException(503, "Tamarind client 未初始化")
    data = data or {}
    try:
        return blatant_why_adapter.tamarind_client.get_result(job_name, path=data.get("path", ""))
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


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
        modality=data.get("modality", "small_molecule"),
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
    implementation = (
        drug_discovery_hub.bootstrap_project(
            project.project_id,
            blueprint_id=data.get("blueprint_id", ""),
            activated_by=data.get("owner_id", "") or data.get("created_by", ""),
            note=data.get("implementation_note", ""),
        )
        if drug_discovery_hub
        else None
    )
    enabled_capabilities = ((implementation or {}).get("state") or {}).get("active_capabilities", [])
    if workspace_store and enabled_capabilities:
        workspace = workspace_store.update_workspace(
            project.project_id,
            enabled_capabilities=enabled_capabilities,
        )
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
    return {
        "project_id": project.project_id,
        "name": project.name,
        "modality": project.modality,
        "workspace": workspace,
        "implementation": implementation,
    }


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
        "implementation": drug_discovery_hub.get_project_implementation(project_id) if drug_discovery_hub else {},
        "memory_stats": project_memory.stats(project_id) if project_memory else {},
        "decisions_count": decision_logger.count(project_id) if decision_logger else 0,
        "second_me_bindings": second_me_bindings.list_bindings(project_id=project_id) if second_me_bindings else [],
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


@app.get("/api/v2/projects/{project_id}/timeline")
async def get_project_timeline(project_id: str, limit: int = 120):
    if not kanban:
        raise HTTPException(503, "Project board 未初始化")
    if not kanban.get_project(project_id):
        raise HTTPException(404, "项目不存在")
    return {
        "project_id": project_id,
        "timeline": build_project_timeline(project_id, limit=limit),
    }


@app.get("/api/v2/projects/{project_id}/workbench")
async def get_project_workbench(project_id: str, timeline_limit: int = 120):
    return build_project_workbench(project_id, timeline_limit=timeline_limit)


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


@app.get("/api/v2/projects/{project_id}/h2a/threads")
async def list_project_h2a_threads(project_id: str):
    if not h2a_store:
        raise HTTPException(503, "H2A store 未初始化")
    return {"project_id": project_id, "threads": h2a_store.list_threads(project_id=project_id)}


@app.post("/api/v2/projects/{project_id}/h2a/threads")
async def create_project_h2a_thread(project_id: str, data: dict):
    if not h2a_store:
        raise HTTPException(503, "H2A store 未初始化")
    agent_ids = data.get("agent_ids") or ([data["agent_id"]] if data.get("agent_id") else [])
    agent_ids = list(dict.fromkeys([agent_id for agent_id in agent_ids if agent_id]))
    if not data.get("human_id") or not agent_ids:
        raise HTTPException(400, "human_id 和 agent_ids / agent_id 为必填")

    agents = []
    for agent_id in agent_ids:
        agent = agent_registry.get_agent(agent_id) if agent_registry else None
        if not agent:
            raise HTTPException(404, f"Agent 不存在: {agent_id}")
        agents.append(agent)

    profile = _ensure_project_user_member(project_id, data["human_id"])
    human_label = (
        data.get("human_label")
        or (profile.get("display_name") if profile else "")
        or (profile.get("username") if profile else "")
        or data["human_id"]
    )

    thread = h2a_store.create_thread(
        project_id=project_id,
        human_id=data["human_id"],
        human_label=human_label,
        agent_id=agent_ids[0],
        agent_label=agents[0].get("name", agent_ids[0]),
        agent_ids=agent_ids,
        agent_labels=[agent.get("name", agent.get("agent_id", "")) for agent in agents],
        title=data.get("title", ""),
    )
    if data.get("message"):
        return _run_h2a_exchange(thread["thread_id"], data["message"])
    return {"thread": thread}


@app.get("/api/v2/h2a/threads/{thread_id}")
async def get_h2a_thread(thread_id: str):
    if not h2a_store:
        raise HTTPException(503, "H2A store 未初始化")
    thread = h2a_store.get_thread(thread_id)
    if not thread:
        raise HTTPException(404, "H2A thread 不存在")
    return thread


@app.post("/api/v2/h2a/threads/{thread_id}/messages")
async def send_h2a_message(thread_id: str, data: dict):
    if not data.get("message"):
        raise HTTPException(400, "message 不能为空")
    return _run_h2a_exchange(thread_id, data["message"])


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
    if drug_discovery_hub:
        execution_context["implementation"] = drug_discovery_hub.get_project_implementation(data["project_id"])
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

    if data.get("auto_execute"):
        try:
            execution = workflow_orchestrator.execute_current_step(
                run["run_id"],
                requested_by=data.get("created_by", "") or data.get("requested_by", "system"),
                input_payloads=data.get("input_payloads", {}),
                max_steps=max(1, int(data.get("max_steps", len(run["steps"]) or 1))),
                note=data.get("note", ""),
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return execution

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


@app.post("/api/v2/workflows/runs/{run_id}/execute")
async def execute_workflow_run(run_id: str, data: dict = None):
    if not workflow_orchestrator:
        raise HTTPException(503, "Workflow orchestrator 未初始化")
    data = data or {}
    try:
        return workflow_orchestrator.execute_current_step(
            run_id=run_id,
            requested_by=data.get("requested_by", ""),
            input_payloads=data.get("input_payloads", {}),
            max_steps=max(1, int(data.get("max_steps", 1))),
            note=data.get("note", ""),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/v2/workflows/runs/{run_id}/steps/{step_id}/execute")
async def execute_workflow_step(run_id: str, step_id: str, data: dict = None):
    if not workflow_orchestrator:
        raise HTTPException(503, "Workflow orchestrator 未初始化")
    data = data or {}
    try:
        return workflow_orchestrator.execute_step(
            run_id=run_id,
            step_id=step_id,
            input_payload=data.get("input_payload", {}),
            note=data.get("note", ""),
            requested_by=data.get("requested_by", ""),
            force_ai=bool(data.get("force_ai", False)),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/v2/workflows/runs/{run_id}/steps/{step_id}/assign")
async def assign_workflow_step(run_id: str, step_id: str, data: dict = None):
    if not workflow_orchestrator:
        raise HTTPException(503, "Workflow orchestrator 未初始化")
    data = data or {}
    if not data.get("owner_type") or not data.get("owner_id"):
        raise HTTPException(400, "owner_type / owner_id 为必填")
    try:
        return workflow_orchestrator.assign_step_owner(
            run_id=run_id,
            step_id=step_id,
            owner_type=data["owner_type"],
            owner_id=data["owner_id"],
            owner_label=data.get("owner_label", ""),
            assigned_by=data.get("assigned_by", ""),
            note=data.get("note", ""),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


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


@app.post("/api/v2/workflows/runs/{run_id}/steps/{step_id}/approve")
async def approve_workflow_step(run_id: str, step_id: str, data: dict = None):
    if not workflow_orchestrator:
        raise HTTPException(503, "Workflow orchestrator 未初始化")
    data = data or {}
    if "approved" not in data:
        raise HTTPException(400, "approved 为必填")
    try:
        run = workflow_orchestrator.approve_step(
            run_id=run_id,
            step_id=step_id,
            approved=bool(data.get("approved")),
            approver_id=data.get("approver_id", ""),
            note=data.get("note", ""),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if project_memory:
        step = next((item for item in run["steps"] if item["step_id"] == step_id), None)
        project_memory.add_entry(
            project_id=run["project_id"],
            memory_type="workflow_approval",
            title=f"Workflow approval: {step['name'] if step else step_id}",
            content=data.get("note", "") or ("approved" if data.get("approved") else "rejected"),
            tags=["workflow_approval", run["template_id"]],
            source="api.approve_workflow_step",
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
# Media (Audio / Video) via MIMO
# ──────────────────────────────────────────────
@app.get("/api/v2/media/status")
async def media_status():
    return media_client.describe()


@app.post("/api/v2/media/audio/tts")
async def media_tts(data: dict):
    text = (data.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "text 为必填")
    result = media_client.synthesize_audio(
        text=text,
        voice=data.get("voice", "default"),
        response_format=data.get("format", "mp3"),
        speed=float(data.get("speed", 1.0)),
        model=data.get("model", ""),
    )
    if result.get("status") != "ok":
        raise HTTPException(400, result.get("error") or "audio generation failed")
    audio_bytes = result.get("audio", b"")
    if not audio_bytes:
        raise HTTPException(500, "audio bytes missing")
    stored = media_store.save(
        audio_bytes,
        suffix=f".{data.get('format', 'mp3')}",
        subdir="audio",
    )
    return {
        "status": "ok",
        "media": stored,
        "content_type": result.get("content_type", "audio/mpeg"),
    }


@app.post("/api/v2/media/video/generate")
async def media_video_generate(data: dict):
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(400, "prompt 为必填")
    result = media_client.generate_video(
        prompt=prompt,
        model=data.get("model", ""),
        size=data.get("size", "1280x720"),
        duration=int(data.get("duration", 6)),
        fps=int(data.get("fps", 24)),
        seed=data.get("seed"),
    )
    if result.get("status") != "ok":
        raise HTTPException(400, result.get("error") or "video generation failed")
    response = result.get("response", {})
    data_list = response.get("data") if isinstance(response, dict) else None
    if isinstance(data_list, list) and data_list:
        first = data_list[0]
        if isinstance(first, dict) and first.get("b64_json"):
            import base64
            video_bytes = base64.b64decode(first["b64_json"])
            stored = media_store.save(video_bytes, suffix=".mp4", subdir="video")
            return {"status": "ok", "media": stored, "source": "b64_json"}
        if isinstance(first, dict) and first.get("url"):
            return {"status": "ok", "url": first["url"], "source": "url"}
    return {"status": "ok", "response": response, "source": "raw"}


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

@app.get("/api/v2/second-me/status")
async def second_me_status():
    """Second Me集成状态"""
    if not second_me:
        return {"status": "not_initialized", "instances": 0, "bindings": 0}
    return {
        "status": "ready",
        "capabilities": second_me.describe_capabilities(),
        "bindings": second_me_bindings.count() if second_me_bindings else 0,
    }


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
        user_id=data.get("user_id", ""),
        project_id=data.get("project_id", ""),
        local_twin_id=data.get("local_twin_id", ""),
    )
    if second_me_bindings:
        binding = second_me_bindings.upsert_binding(
            instance_id=result["instance_id"],
            local_twin_id=data.get("local_twin_id", ""),
            user_id=data.get("user_id", ""),
            project_id=data.get("project_id", ""),
            role_id=data.get("role", ""),
            display_name=data.get("name", ""),
            sync_strategy=data.get("sync_strategy", "manual"),
            share_url=second_me.get_share_url(result["instance_id"]),
        )
        result["binding"] = binding
    if workspace_store and data.get("project_id"):
        workspace_store.link_second_me_instance(data["project_id"], result["instance_id"])
        workspace_store.add_note(data["project_id"], f"Second Me instance linked: {result['instance_id']}")
    if project_memory and data.get("project_id"):
        result["memory_entry"] = project_memory.add_entry(
            project_id=data["project_id"],
            memory_type="second_me_binding",
            title=f"Second Me binding created: {data.get('name', result['instance_id'])}",
            content=(
                f"instance_id={result['instance_id']}; role={data.get('role', '')}; "
                f"user_id={data.get('user_id', '')}; twin_id={data.get('local_twin_id', '')}"
            ),
            tags=["second_me", "binding"],
            source="api.create_second_me_twin",
            author_id=data.get("user_id", ""),
            related_agents=[data.get("local_twin_id", "")] if data.get("local_twin_id") else [],
        )
    return result


@app.post("/api/v2/second-me/bindings")
async def bind_second_me_instance(data: dict):
    """绑定一个现有Second Me实例到用户/项目/DrugMind twin。"""
    if not second_me_bindings:
        raise HTTPException(503, "Second Me binding store 未初始化")
    if not data.get("instance_id"):
        raise HTTPException(400, "instance_id 为必填")
    if second_me and not second_me.get_instance(data["instance_id"]):
        raise HTTPException(404, "Second Me实例不存在")
    binding = second_me_bindings.upsert_binding(
        instance_id=data["instance_id"],
        local_twin_id=data.get("local_twin_id", ""),
        user_id=data.get("user_id", ""),
        project_id=data.get("project_id", ""),
        role_id=data.get("role_id", ""),
        display_name=data.get("display_name", ""),
        sync_strategy=data.get("sync_strategy", "manual"),
        status=data.get("status", "linked"),
        share_url=data.get("share_url", second_me.get_share_url(data["instance_id"]) if second_me else ""),
    )
    if workspace_store and data.get("project_id"):
        workspace_store.link_second_me_instance(data["project_id"], data["instance_id"])
    return binding


@app.get("/api/v2/second-me/bindings")
async def list_second_me_bindings(project_id: str = "", user_id: str = "", instance_id: str = ""):
    if not second_me_bindings:
        return {"bindings": []}
    return {"bindings": second_me_bindings.list_bindings(project_id=project_id, user_id=user_id, instance_id=instance_id)}


@app.get("/api/v2/second-me/bindings/{binding_id}")
async def get_second_me_binding(binding_id: str):
    if not second_me_bindings:
        raise HTTPException(503, "Second Me binding store 未初始化")
    binding = second_me_bindings.get_binding(binding_id)
    if not binding:
        raise HTTPException(404, "Second Me binding 不存在")
    return binding


@app.post("/api/v2/second-me/{instance_id}/chat")
async def chat_second_me(instance_id: str, data: dict):
    """与Second Me数字分身对话"""
    if not second_me:
        raise HTTPException(503, "Second Me集成未初始化")
    return second_me.chat(instance_id, data["message"])


@app.get("/api/v2/second-me")
async def list_second_me_instances(project_id: str = "", user_id: str = ""):
    """列出Second Me实例"""
    if not second_me:
        return {"instances": [], "status": "not_initialized"}
    instances = second_me.list_instances()
    if project_id:
        instances = [item for item in instances if item.get("linked_project_id") == project_id]
    if user_id:
        instances = [item for item in instances if item.get("linked_user_id") == user_id]
    return {"instances": instances}


@app.get("/api/v2/projects/{project_id}/second-me")
async def list_project_second_me(project_id: str):
    if not second_me_bindings:
        return {"project_id": project_id, "bindings": [], "instances": []}
    bindings = second_me_bindings.list_bindings(project_id=project_id)
    instance_ids = {binding["instance_id"] for binding in bindings}
    instances = [
        second_me.get_instance(instance_id)
        for instance_id in instance_ids
        if second_me and second_me.get_instance(instance_id)
    ]
    return {"project_id": project_id, "bindings": bindings, "instances": instances}


@app.post("/api/v2/projects/{project_id}/second-me/sync")
async def sync_project_to_second_me(project_id: str, data: dict):
    """将项目上下文同步到指定的Second Me实例。"""
    if not second_me:
        raise HTTPException(503, "Second Me集成未初始化")
    if not second_me_bindings:
        raise HTTPException(503, "Second Me binding store 未初始化")
    instance_id = data.get("instance_id")
    if not instance_id:
        raise HTTPException(400, "instance_id 为必填")
    instance = second_me.get_instance(instance_id)
    if not instance:
        raise HTTPException(404, "Second Me实例不存在")

    project = kanban.get_project(project_id) if kanban else None
    if not project:
        raise HTTPException(404, "项目不存在")
    if drug_discovery_hub:
        project = {
            **project,
            "implementation": drug_discovery_hub.get_project_implementation(project_id),
        }
    if blatant_why_adapter:
        project["blatant_why"] = blatant_why_adapter.build_dmta_blueprint(project=project)
    workspace = workspace_store.get_workspace(project_id) if workspace_store else {}
    memory_entries = project_memory.list_entries(project_id, limit=data.get("memory_limit", 8)) if project_memory else []
    decisions = decision_logger.get_decision_history(project_id=project_id)[:data.get("decision_limit", 6)] if decision_logger else []
    workflow_run = None
    if data.get("workflow_run_id") and workflow_orchestrator:
        workflow_run = workflow_orchestrator.get_run(data["workflow_run_id"])

    sync_result = second_me.sync_project_context(
        instance_id,
        project=project,
        workspace=workspace,
        memory_entries=memory_entries,
        decisions=decisions,
        workflow_run=workflow_run,
        sync_note=data.get("sync_note", ""),
    )
    if "error" in sync_result:
        raise HTTPException(400, sync_result["error"])

    share_url = second_me.get_share_url(instance_id)
    binding = second_me_bindings.upsert_binding(
        instance_id=instance_id,
        local_twin_id=data.get("local_twin_id", instance.get("linked_twin_id", "")),
        user_id=data.get("user_id", instance.get("linked_user_id", "")),
        project_id=project_id,
        role_id=instance.get("role", ""),
        display_name=instance.get("name", ""),
        sync_strategy=data.get("sync_strategy", "project_context"),
        status="synced",
        share_url=share_url,
    )

    memory_entry = None
    if project_memory:
        memory_entry = project_memory.add_entry(
            project_id=project_id,
            memory_type="second_me_sync",
            title=f"Second Me sync: {instance.get('name', instance_id)}",
            content=sync_result.get("summary", ""),
            tags=["second_me", "sync", instance_id],
            source="api.sync_project_to_second_me",
            author_id=data.get("user_id", instance.get("linked_user_id", "")),
            related_agents=[binding.get("local_twin_id", "")] if binding.get("local_twin_id") else [],
        )
    if workspace_store:
        workspace_store.link_second_me_instance(project_id, instance_id)
        workspace_store.add_note(project_id, f"Second Me synced: {instance_id}")
    if data.get("workflow_run_id") and workflow_orchestrator and memory_entry:
        workflow_orchestrator.link_artifact(
            data["workflow_run_id"],
            artifact_type="memory",
            artifact_id=memory_entry["entry_id"],
            summary=f"Second Me sync for {instance_id}",
        )

    synced_binding = second_me_bindings.mark_synced(
        binding["binding_id"],
        summary=sync_result.get("summary", ""),
        memory_entry_id=(memory_entry or {}).get("entry_id", ""),
        workflow_run_id=data.get("workflow_run_id", ""),
        share_url=share_url,
        export_snapshot=second_me.export_for_second_me(instance_id),
    )
    return {
        "project_id": project_id,
        "instance": instance,
        "binding": synced_binding,
        "sync_result": sync_result,
        "memory_entry": memory_entry,
    }


@app.get("/api/v2/second-me/{instance_id}/export")
async def export_second_me(instance_id: str):
    """导出为Second Me格式"""
    if not second_me:
        raise HTTPException(503, "Second Me集成未初始化")
    exported = second_me.export_for_second_me(instance_id)
    if second_me_bindings:
        for binding in second_me_bindings.list_bindings(instance_id=instance_id):
            second_me_bindings.mark_synced(
                binding["binding_id"],
                summary="Export snapshot refreshed",
                share_url=second_me.get_share_url(instance_id),
                export_snapshot=exported,
            )
    return exported


@app.get("/api/v2/second-me/{instance_id}/share")
async def share_second_me(instance_id: str):
    """获取分享链接"""
    if not second_me:
        raise HTTPException(503, "Second Me集成未初始化")
    url = second_me.get_share_url(instance_id)
    if second_me_bindings:
        for binding in second_me_bindings.list_bindings(instance_id=instance_id):
            second_me_bindings.mark_synced(
                binding["binding_id"],
                summary=binding.get("last_sync_summary", ""),
                share_url=url,
            )
    return {"url": url}


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


@app.get("/demo-reel.html", response_class=HTMLResponse)
async def demo_reel_page():
    f = FRONTEND_DIR / "demo-reel.html"
    if f.exists():
        return HTMLResponse(content=f.read_text(encoding="utf-8"))
    raise HTTPException(404)


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


@app.get("/media/{path:path}")
async def media_file(path: str):
    f = FRONTEND_DIR / "media" / path
    if f.exists():
        return FileResponse(f)
    raise HTTPException(404)


@app.get("/media/generated/{path:path}")
async def generated_media_file(path: str):
    f = media_store.base_dir / path
    if f.exists():
        return FileResponse(f)
    raise HTTPException(404)
