#!/usr/bin/env python3
"""
DrugMind v2.0 — FastAPI Server
药物研发数字分身协作平台

独立服务入口，集成所有核心功能模块:
  - 数字分身引擎 (DigitalTwinEngine)
  - 讨论引擎 (DiscussionEngine)
  - 协作管理 (CollaborationManager)
  - 分析流水线 (AnalysisPipeline)
  - 分子服务 (MolecularService)
  - 化合物追踪 (CompoundTracker)
  - 靶点服务 (TargetService)
  - 用户管理 (UserManager)
  - 社区广场 (DiscussionHub)
  - 项目管理 (KanbanBoard)
  - SaaS服务 (TenantManager, StripeService, Marketplace, SSO)
  - MCP Server (Second Me集成)

启动方式:
  python server.py                     # 默认 0.0.0.0:8096
  python server.py --host 127.0.0.1 --port 8080
"""

import sys
import logging
import argparse
from pathlib import Path

# ─── 日志配置 ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("drugmind.server")

# ─── 项目根目录 & 数据目录 ─────────────────────────────────
BASE_DIR = Path(__file__).parent
STORAGE_DIR = str(BASE_DIR / "drugmind_data")
FRONTEND_DIR = BASE_DIR / "frontend"
DOCS_DIR = BASE_DIR / "docs"


# ══════════════════════════════════════════════════════════
# FastAPI Application
# ══════════════════════════════════════════════════════════

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="DrugMind API",
    description=(
        "药物研发数字分身协作平台\n\n"
        "5个专业AI数字分身(药物化学家、生物学家、药理学家、数据科学家、项目经理)"
        "全天候协作，覆盖靶点发现→先导优化→ADMET预测→虚拟筛选→数字孪生对接全流程。"
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════
# 全局引擎实例
# ══════════════════════════════════════════════════════════

twin_engine = None
discussion_engine = None
kanban = None
compound_tracker = None
user_mgr = None
discussion_hub = None
collab_mgr = None
pipeline_engine = None
second_me = None


def _init_engines(use_llm: bool = True):
    """初始化所有引擎"""
    global twin_engine, discussion_engine, kanban, compound_tracker
    global user_mgr, discussion_hub, collab_mgr, pipeline_engine, second_me

    from digital_twin.engine import DigitalTwinEngine
    from collaboration.discussion import DiscussionEngine
    from project.kanban import KanbanBoard
    from drug_modeling.compound_tracker import CompoundTracker
    from auth.user import UserManager
    from community.hub import DiscussionHub

    twin_engine = DigitalTwinEngine(storage_dir=STORAGE_DIR, use_llm=use_llm)
    discussion_engine = DiscussionEngine(twin_engine)
    kanban = KanbanBoard(f"{STORAGE_DIR}/projects")
    compound_tracker = CompoundTracker(f"{STORAGE_DIR}/compounds")
    user_mgr = UserManager(f"{STORAGE_DIR}/users")
    discussion_hub = DiscussionHub(f"{STORAGE_DIR}/discussions")

    # src/ 下的协作管理器和分析流水线
    from src.collaboration import CollaborationManager
    from src.analysis_pipeline import AnalysisPipeline
    collab_mgr = CollaborationManager()
    pipeline_engine = AnalysisPipeline()

    # Second Me 集成（可选）
    try:
        from second_me.integration import SecondMeIntegration
        second_me = SecondMeIntegration(mode="cloud")
    except Exception:
        second_me = None

    # 初始化 MCP Server
    try:
        from api.mcp_server import init_mcp
        init_mcp(twin_engine, discussion_engine, discussion_hub, user_mgr)
    except Exception as e:
        logger.warning(f"MCP Server 初始化跳过: {e}")

    logger.info("✅ 所有引擎初始化完成")


def _create_default_team():
    """创建默认数字分身团队"""
    for role_id, name in [
        ("medicinal_chemist", "张化学家"),
        ("biologist", "李生物"),
        ("pharmacologist", "王药理"),
        ("data_scientist", "赵数据"),
        ("project_lead", "刘项目"),
    ]:
        twin_engine.create_twin(role_id, name)
    logger.info("✅ 默认团队: 5个分身就绪")


# ══════════════════════════════════════════════════════════
# 路由 1: 健康检查 & 平台统计
# ══════════════════════════════════════════════════════════

@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "twins": len(twin_engine.list_twins()) if twin_engine else 0,
        "discussions": len(discussion_engine.sessions) if discussion_engine else 0,
        "users": len(user_mgr.users) if user_mgr else 0,
    }


@app.get("/api/v2/stats", tags=["系统"])
async def platform_stats():
    """平台统计数据"""
    twins = twin_engine.list_twins() if twin_engine else []
    return {
        "twins_count": len(twins),
        "discussions_count": len(discussion_hub.discussions) if discussion_hub else 0,
        "users_count": len(user_mgr.users) if user_mgr else 0,
        "roles": 5,
        "collab_tasks": len(collab_mgr.tasks) if collab_mgr else 0,
        "compounds": len(compound_tracker.compounds) if compound_tracker else 0,
    }


# ══════════════════════════════════════════════════════════
# 路由 2: 用户系统
# ══════════════════════════════════════════════════════════

@app.post("/api/v2/register", tags=["用户"])
async def register(data: dict):
    """用户注册"""
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


@app.post("/api/v2/login", tags=["用户"])
async def login(data: dict):
    """用户登录"""
    r = user_mgr.login(data["username"], data["password"])
    if "error" in r:
        raise HTTPException(401, r["error"])
    return r


@app.get("/api/v2/users", tags=["用户"])
async def list_users():
    """列出所有用户"""
    return {"users": user_mgr.list_users()}


@app.get("/api/v2/users/{user_id}", tags=["用户"])
async def get_user(user_id: str):
    """获取用户详情"""
    p = user_mgr.get_profile(user_id)
    if not p:
        raise HTTPException(404, "用户不存在")
    return p


@app.put("/api/v2/users/{user_id}", tags=["用户"])
async def update_user(user_id: str, data: dict):
    """更新用户资料"""
    ok = user_mgr.update_profile(user_id, **data)
    if not ok:
        raise HTTPException(404, "用户不存在")
    return {"status": "updated"}


# ══════════════════════════════════════════════════════════
# 路由 3: 数字分身
# ══════════════════════════════════════════════════════════

@app.get("/api/v2/roles", tags=["数字分身"])
async def list_roles():
    """获取所有可用角色"""
    from digital_twin.roles import list_roles as _list_roles
    return {"roles": _list_roles()}


@app.post("/api/v2/twins", tags=["数字分身"])
async def create_twin(data: dict):
    """创建数字分身"""
    try:
        result = twin_engine.create_twin(
            role_id=data["role_id"],
            name=data["name"],
            custom_expertise=data.get("expertise"),
        )
        if data.get("user_id") and user_mgr:
            user = user_mgr.users.get(data["user_id"])
            if user:
                user.twins.append(result["twin_id"])
                user_mgr._save()
        return result
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/v2/twins", tags=["数字分身"])
async def list_twins():
    """列出所有数字分身"""
    return {"twins": twin_engine.list_twins()}


@app.post("/api/v2/twins/{twin_id}/ask", tags=["数字分身"])
async def ask_twin(twin_id: str, data: dict):
    """向指定分身提问"""
    resp = twin_engine.ask_twin(
        twin_id=twin_id,
        question=data["question"],
        context=data.get("context", ""),
    )
    return {
        "twin_id": resp.twin_id, "name": resp.name, "role": resp.role,
        "emoji": resp.emoji, "message": resp.message, "confidence": resp.confidence,
    }


@app.post("/api/v2/twins/{twin_id}/teach", tags=["数字分身"])
async def teach_twin(twin_id: str, data: dict):
    """教数字分身新知识"""
    twin_engine.teach_twin(twin_id, data["content"], data.get("source", ""))
    return {"status": "taught"}


@app.get("/api/v2/twins/{twin_id}/memory", tags=["数字分身"])
async def twin_memory(twin_id: str, q: str = ""):
    """获取分身记忆"""
    return {"memory": twin_engine.get_twin_memory(twin_id, q)}


# ══════════════════════════════════════════════════════════
# 路由 4: 多角色快捷问答
# ══════════════════════════════════════════════════════════

@app.post("/api/v2/quick-ask", tags=["AI问答"])
async def quick_ask(data: dict):
    """快捷AI提问 — 同时向多个角色提问并返回各自回答"""
    question = data.get("question", "")
    context = data.get("context", "")
    roles = data.get("roles", ["medicinal_chemist", "biologist", "pharmacologist"])

    if not question:
        raise HTTPException(400, "问题不能为空")

    name_map = {
        "medicinal_chemist": "张化学家", "biologist": "李生物",
        "pharmacologist": "王药理", "data_scientist": "赵数据",
        "project_lead": "刘项目",
    }
    emoji_map = {
        "medicinal_chemist": "🧪", "biologist": "🔬",
        "pharmacologist": "💊", "data_scientist": "📊",
        "project_lead": "📋",
    }

    responses = []
    for role_id in roles:
        twin_id = f"{role_id}_{name_map.get(role_id, role_id)}"
        try:
            resp = twin_engine.ask_twin(twin_id, question, context)
            responses.append({
                "role": role_id, "name": resp.name,
                "emoji": resp.emoji, "message": resp.message,
            })
        except Exception:
            responses.append({
                "role": role_id, "name": name_map.get(role_id, role_id),
                "emoji": emoji_map.get(role_id, "🤖"),
                "message": "抱歉，我暂时无法回答这个问题。",
            })

    return {"responses": responses, "question": question}


# ══════════════════════════════════════════════════════════
# 路由 5: 讨论系统
# ══════════════════════════════════════════════════════════

@app.post("/api/v2/discussions", tags=["讨论"])
async def create_discussion(data: dict):
    """创建讨论会话"""
    session = discussion_engine.create_discussion(
        topic=data["topic"],
        participant_ids=data["participant_ids"],
        context=data.get("context", ""),
    )
    return {
        "session_id": session.session_id,
        "topic": session.topic,
        "participants": len(session.participants),
    }


@app.post("/api/v2/discussions/{session_id}/run", tags=["讨论"])
async def run_discussion(session_id: str, data: dict = None):
    """运行讨论（多轮发言）"""
    data = data or {}
    messages = discussion_engine.run_round_robin(
        session_id=session_id,
        context=data.get("context", ""),
        max_rounds=data.get("max_rounds", 2),
    )
    return {
        "session_id": session_id,
        "count": len(messages),
        "messages": [
            {
                "emoji": m.emoji, "name": m.name, "role": m.role,
                "content": m.content, "timestamp": m.timestamp,
            }
            for m in messages
        ],
    }


@app.get("/api/v2/discussions/{session_id}", tags=["讨论"])
async def get_discussion(session_id: str):
    """获取讨论消息"""
    return {"messages": discussion_engine.get_session_messages(session_id)}


@app.get("/api/v2/discussions/{session_id}/summary", tags=["讨论"])
async def discussion_summary(session_id: str):
    """获取讨论总结"""
    return {"summary": discussion_engine.summarize_discussion(session_id)}


# ══════════════════════════════════════════════════════════
# 路由 6: 社区讨论广场
# ══════════════════════════════════════════════════════════

@app.post("/api/v2/hub", tags=["社区"])
async def create_public_discussion(data: dict):
    """创建公开讨论"""
    disc = discussion_hub.create(
        topic=data["topic"],
        creator_id=data.get("creator_id", "anonymous"),
        creator_name=data.get("creator_name", "匿名用户"),
        tags=data.get("tags", []),
        participants=data.get("participants", []),
    )
    return {"session_id": disc.session_id, "topic": disc.topic}


@app.get("/api/v2/hub", tags=["社区"])
async def list_public_discussions(
    q: str = "", tag: str = "", limit: int = Query(default=20, le=100)
):
    """搜索/列出公开讨论"""
    return {"discussions": discussion_hub.search(q, tag, limit)}


@app.get("/api/v2/hub/trending", tags=["社区"])
async def trending_discussions():
    """热门讨论"""
    return {"trending": discussion_hub.trending()}


@app.get("/api/v2/hub/{session_id}", tags=["社区"])
async def get_public_discussion(session_id: str):
    """获取公开讨论详情"""
    d = discussion_hub.get(session_id)
    if not d:
        raise HTTPException(404, "讨论不存在")
    return d


@app.post("/api/v2/hub/{session_id}/like", tags=["社区"])
async def like_discussion(session_id: str):
    """点赞讨论"""
    discussion_hub.like(session_id)
    return {"status": "liked"}


@app.post("/api/v2/hub/{session_id}/reply", tags=["社区"])
async def reply_discussion(session_id: str, data: dict):
    """回复讨论"""
    discussion_hub.add_message(session_id, {
        "twin_id": data.get("twin_id", ""),
        "name": data.get("name", ""),
        "role": data.get("role", ""),
        "emoji": data.get("emoji", "💬"),
        "content": data.get("content", ""),
        "timestamp": "",
    })
    return {"status": "posted"}


# ══════════════════════════════════════════════════════════
# 路由 7: 药物分析流水线
# ══════════════════════════════════════════════════════════

@app.post("/api/v2/pipeline/run", tags=["分析流水线"])
async def run_pipeline(data: dict):
    """运行完整分析流水线: 预处理 → 特征工程 → 模型训练 → 评估"""
    from src.analysis_pipeline import AnalysisPipeline
    pipeline = AnalysisPipeline()
    result = pipeline.run(data.get("input_data", {}))
    return {
        "pipeline_id": result.pipeline_id,
        "status": result.status,
        "steps": result.steps,
        "output": result.output,
        "execution_time": round(result.execution_time, 4),
    }


@app.get("/api/v2/pipeline/status", tags=["分析流水线"])
async def pipeline_status():
    """获取当前流水线状态"""
    if pipeline_engine:
        return pipeline_engine.get_status()
    return {"status": "idle", "message": "没有正在运行的流水线"}


# ══════════════════════════════════════════════════════════
# 路由 8: 分子对接 & 数字孪生
# ══════════════════════════════════════════════════════════

@app.post("/api/v2/docking/simulate", tags=["分子对接"])
async def simulate_docking(data: dict):
    """模拟分子对接"""
    from src.digital_twin import (
        DigitalTwinEngine as SrcDigitalTwinEngine,
        Molecule, Target,
    )

    engine = SrcDigitalTwinEngine()

    # 添加分子
    mol_data = data.get("molecule", {})
    mol = Molecule(
        name=mol_data.get("name", "Unknown"),
        smiles=mol_data.get("smiles", ""),
        molecular_weight=mol_data.get("molecular_weight", 350),
        logp=mol_data.get("logp", 2.0),
        hbd=mol_data.get("hbd", 2),
        hba=mol_data.get("hba", 4),
        tpsa=mol_data.get("tpsa", 80),
    )
    engine.add_molecule(mol)

    # 添加靶点
    tgt_data = data.get("target", {})
    target = Target(
        name=tgt_data.get("name", "Unknown"),
        gene=tgt_data.get("gene", ""),
        pdb_id=tgt_data.get("pdb_id", ""),
        binding_site=tgt_data.get("binding_site", {}),
        druggability=tgt_data.get("druggability", 0.8),
    )
    engine.add_target(target)

    # 执行对接
    result = engine.simulate_docking(mol.name, target.name)
    return {
        "molecule": result.molecule,
        "target": result.target,
        "binding_affinity": result.binding_affinity,
        "ic50_estimate": result.ic50_estimate,
        "interactions": result.interactions,
        "pose": result.pose,
    }


@app.post("/api/v2/docking/virtual-screen", tags=["分子对接"])
async def virtual_screen(data: dict):
    """虚拟筛选 — 对多个分子与靶点进行打分排序"""
    from src.digital_twin import (
        DigitalTwinEngine as SrcDigitalTwinEngine,
        Molecule, Target,
    )

    engine = SrcDigitalTwinEngine()

    # 添加靶点
    tgt_data = data.get("target", {})
    target = Target(
        name=tgt_data.get("name", "Unknown"),
        gene=tgt_data.get("gene", ""),
        pdb_id=tgt_data.get("pdb_id", ""),
        binding_site=tgt_data.get("binding_site", {}),
        druggability=tgt_data.get("druggability", 0.8),
    )
    engine.add_target(target)

    # 添加候选分子
    for mol_data in data.get("molecules", []):
        mol = Molecule(
            name=mol_data.get("name", "Unknown"),
            smiles=mol_data.get("smiles", ""),
            molecular_weight=mol_data.get("molecular_weight", 350),
            logp=mol_data.get("logp", 2.0),
            hbd=mol_data.get("hbd", 2),
            hba=mol_data.get("hba", 4),
            tpsa=mol_data.get("tpsa", 80),
        )
        engine.add_molecule(mol)

    top_n = data.get("top_n", 10)
    results = engine.virtual_screen(target.name, top_n)
    return {"target": target.name, "screened": len(results), "results": results}


# ══════════════════════════════════════════════════════════
# 路由 9: ADMET & 分子服务
# ══════════════════════════════════════════════════════════

@app.post("/api/v2/admet", tags=["分子服务"])
async def predict_admet(data: dict):
    """ADMET预测（分子量、logP、氢键、TPSA、QED、Lipinski等）"""
    from drug_modeling.molecular_service import get_mol_service
    return get_mol_service().predict_admet(data["smiles"])


@app.post("/api/v2/molecule/sdf", tags=["分子服务"])
async def get_molecule_sdf(data: dict):
    """SMILES → 3D SDF 坐标"""
    from drug_modeling.molecular_service import get_mol_service
    return get_mol_service().smiles_to_sdf(data["smiles"])


@app.post("/api/v2/molecule/info", tags=["分子服务"])
async def get_molecule_info(data: dict):
    """获取分子信息（名称、分子式等）"""
    from drug_modeling.molecular_service import get_mol_service
    return get_mol_service().get_mol_info(data["smiles"])


# ══════════════════════════════════════════════════════════
# 路由 10: 靶点发现
# ══════════════════════════════════════════════════════════

@app.get("/api/v2/targets/search", tags=["靶点服务"])
async def search_targets(q: str = "", limit: int = 10):
    """搜索疾病相关靶点 (OpenTargets + ChEMBL)"""
    if not q:
        raise HTTPException(400, "Query parameter 'q' required")
    from drug_modeling.target_service import get_target_service
    return get_target_service().search_targets(q, limit)


@app.get("/api/v2/targets/{target_id}", tags=["靶点服务"])
async def get_target_detail(target_id: str):
    """获取靶点详细信息"""
    from drug_modeling.target_service import get_target_service
    return get_target_service().get_target_detail(target_id)


@app.get("/api/v2/targets/{target_id}/compounds", tags=["靶点服务"])
async def get_target_compounds(target_id: str, limit: int = 10):
    """获取靶点相关化合物"""
    from drug_modeling.target_service import get_target_service
    return get_target_service().search_compounds(target_id, limit)


# ══════════════════════════════════════════════════════════
# 路由 11: 协作管理
# ══════════════════════════════════════════════════════════

@app.post("/api/v2/collab/members", tags=["协作"])
async def add_team_member(data: dict):
    """添加团队成员"""
    from src.collaboration import TeamMember
    member = TeamMember(
        member_id=data.get("member_id", f"m_{len(collab_mgr.members)}"),
        name=data["name"],
        role=data["role"],
        expertise=data.get("expertise", []),
        availability=data.get("availability", 1.0),
    )
    collab_mgr.add_member(member)
    return {"member_id": member.member_id, "name": member.name}


@app.post("/api/v2/collab/tasks", tags=["协作"])
async def create_task(data: dict):
    """创建协作任务"""
    task = collab_mgr.create_task(
        title=data["title"],
        description=data.get("description", ""),
        priority=data.get("priority", "medium"),
    )
    return {
        "task_id": task.task_id,
        "title": task.title,
        "status": task.status.value,
        "priority": task.priority.value,
    }


@app.post("/api/v2/collab/tasks/{task_id}/assign", tags=["协作"])
async def assign_task(task_id: str, data: dict):
    """分配任务给成员"""
    ok = collab_mgr.assign_task(task_id, data["member_id"])
    if not ok:
        raise HTTPException(400, "任务或成员不存在")
    return {"status": "assigned"}


@app.post("/api/v2/collab/tasks/{task_id}/progress", tags=["协作"])
async def update_task_progress(task_id: str, data: dict):
    """更新任务进度"""
    collab_mgr.update_progress(task_id, data["progress"])
    return {"status": "updated"}


@app.get("/api/v2/collab/stats", tags=["协作"])
async def collab_stats():
    """获取团队协作统计"""
    return collab_mgr.get_team_stats()


# ══════════════════════════════════════════════════════════
# 路由 12: 项目管理
# ══════════════════════════════════════════════════════════

@app.post("/api/v2/projects", tags=["项目"])
async def create_project(data: dict):
    """创建药物研发项目"""
    project = kanban.create_project(
        project_id=data.get("project_id", data["name"].lower().replace(" ", "_")),
        name=data["name"],
        target=data.get("target", ""),
        disease=data.get("disease", ""),
        budget=data.get("budget", 0),
    )
    return {"project_id": project.project_id, "name": project.name}


@app.get("/api/v2/projects/board", tags=["项目"])
async def get_board():
    """获取项目看板"""
    return kanban.get_board()


# ══════════════════════════════════════════════════════════
# 路由 13: 化合物管线
# ══════════════════════════════════════════════════════════

@app.post("/api/v2/compounds", tags=["化合物"])
async def add_compound(data: dict):
    """添加化合物"""
    comp = compound_tracker.add_compound(
        compound_id=data["compound_id"],
        smiles=data["smiles"],
        name=data.get("name", ""),
        project_id=data.get("project_id", ""),
    )
    return {"compound_id": comp.compound_id}


@app.get("/api/v2/compounds/pipeline", tags=["化合物"])
async def get_pipeline():
    """获取化合物管线"""
    return compound_tracker.get_pipeline()


# ══════════════════════════════════════════════════════════
# 路由 14: SaaS服务（租户、定价、市场）
# ══════════════════════════════════════════════════════════

PLANS = {
    "starter": {
        "name": "Starter", "price": 299, "seats": 5,
        "features": [
            "Target knowledge graph", "Literature auto-aggregation",
            "Basic collaboration space", "ADMET quick assessment",
        ],
    },
    "team": {
        "name": "Team", "price": 499, "seats": -1,
        "features": [
            "Everything in Starter", "Digital twin simulation",
            "Pipeline progress tracking", "AI decision recommendations",
            "External data integration",
        ],
        "popular": True,
    },
    "enterprise": {
        "name": "Enterprise", "price": 799, "seats": -1,
        "features": [
            "Everything in Team", "Private deployment", "SSO integration",
            "Dedicated customer success", "Custom development", "SLA guarantee",
        ],
    },
}


@app.get("/api/v2/plans", tags=["SaaS"])
async def get_plans():
    """获取定价方案"""
    return {"plans": PLANS}


@app.post("/api/v2/trial", tags=["SaaS"])
async def apply_trial(data: dict):
    """申请免费试用"""
    name = data.get("name", "")
    size = data.get("size", 10)
    if not name:
        raise HTTPException(400, "Team name required")
    plan_key = "starter" if size <= 5 else ("team" if size <= 50 else "enterprise")
    plan = PLANS[plan_key]
    monthly = size * plan["price"]
    return {
        "name": name, "plan": plan["name"], "seats": size,
        "monthly_fee": monthly, "annual_fee": monthly * 12, "trial_days": 14,
    }


@app.post("/api/v2/tenants", tags=["SaaS"])
async def create_tenant(data: dict):
    """创建租户"""
    from api.saas import get_tenant_manager
    tenant = get_tenant_manager().create(
        name=data["name"],
        plan=data.get("plan", "starter"),
        owner_id=data.get("owner_id", "anonymous"),
    )
    return {"tenant_id": tenant.tenant_id, "name": tenant.name, "plan": tenant.plan}


@app.get("/api/v2/tenants", tags=["SaaS"])
async def list_tenants():
    """列出所有租户"""
    from api.saas import get_tenant_manager
    return {"tenants": get_tenant_manager().list_all()}


@app.get("/api/v2/marketplace", tags=["SaaS"])
async def marketplace_search(q: str = "", role: str = "", limit: int = 20):
    """搜索分身市场"""
    from api.saas import get_marketplace
    return {"twins": get_marketplace().search(q, role, limit)}


@app.get("/api/v2/marketplace/trending", tags=["SaaS"])
async def marketplace_trending():
    """热门分身"""
    from api.saas import get_marketplace
    return {"twins": get_marketplace().trending()}


# ══════════════════════════════════════════════════════════
# 路由 15: 种子数据 & 场景模板
# ══════════════════════════════════════════════════════════

@app.post("/api/v2/seed", tags=["种子数据"])
async def run_seed(data: dict = None):
    """加载种子数据（创建预设讨论和分身）"""
    data = data or {}
    from seeds.loader import seed_platform
    result = seed_platform(
        twin_engine, discussion_hub,
        max_topics=data.get("max_topics", 3),
    )
    return result


@app.get("/api/v2/scenarios", tags=["种子数据"])
async def list_scenarios():
    """获取讨论场景模板"""
    from seeds.loader import get_scenarios
    return {"scenarios": get_scenarios()}


@app.get("/api/v2/topics", tags=["种子数据"])
async def list_topics():
    """获取种子话题"""
    from seeds.loader import get_seed_topics
    return {"topics": get_seed_topics()}


# ══════════════════════════════════════════════════════════
# Second Me 集成
# ══════════════════════════════════════════════════════════

@app.post("/api/v2/second-me/create", tags=["Second Me"])
async def create_second_me_twin(data: dict):
    """在Second Me上创建药物研发数字分身"""
    if not second_me:
        raise HTTPException(503, "Second Me集成未初始化")
    return second_me.create_pharma_twin(
        name=data["name"], role=data["role"],
        expertise=data.get("expertise", []),
        knowledge=data.get("knowledge", []),
        personality=data.get("personality", "balanced"),
    )


@app.post("/api/v2/second-me/{instance_id}/chat", tags=["Second Me"])
async def chat_second_me(instance_id: str, data: dict):
    """与Second Me数字分身对话"""
    if not second_me:
        raise HTTPException(503, "Second Me集成未初始化")
    return second_me.chat(instance_id, data["message"])


@app.get("/api/v2/second-me", tags=["Second Me"])
async def list_second_me_instances():
    """列出Second Me实例"""
    if not second_me:
        return {"instances": [], "status": "not_initialized"}
    return {"instances": second_me.list_instances()}


# ══════════════════════════════════════════════════════════
# WebSocket 实时讨论
# ══════════════════════════════════════════════════════════

@app.websocket("/ws/{session_id}")
async def ws_discussion(websocket: WebSocket, session_id: str):
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
                    "twin_id": response.twin_id, "name": response.name,
                    "role": response.role, "emoji": response.emoji,
                    "message": response.message,
                })
    except WebSocketDisconnect:
        pass


# ══════════════════════════════════════════════════════════
# MCP Server (挂载独立路由)
# ══════════════════════════════════════════════════════════

try:
    from api.mcp_server import router as mcp_router
    app.include_router(mcp_router)
except ImportError:
    logger.warning("MCP Server路由未加载")


# ══════════════════════════════════════════════════════════
# 前端 & 静态文件
# ══════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse, tags=["前端"])
async def index():
    """主页"""
    f = FRONTEND_DIR / "index.html"
    if f.exists():
        return HTMLResponse(content=f.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>DrugMind</h1><p>前端文件未找到</p>")


@app.get("/css/{path:path}", tags=["前端"])
async def css_file(path: str):
    """CSS静态文件"""
    f = FRONTEND_DIR / "css" / path
    if f.exists():
        return FileResponse(f, media_type="text/css")
    raise HTTPException(404)


@app.get("/js/{path:path}", tags=["前端"])
async def js_file(path: str):
    """JS静态文件"""
    f = FRONTEND_DIR / "js" / path
    if f.exists():
        return FileResponse(f, media_type="application/javascript")
    raise HTTPException(404)


@app.get("/img/{path:path}", tags=["前端"])
async def img_file(path: str):
    """图片静态文件"""
    f = FRONTEND_DIR / "img" / path
    if f.exists():
        return FileResponse(f)
    raise HTTPException(404)


# ══════════════════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        prog="drugmind-server",
        description="DrugMind v2.0 — 药物研发数字分身协作平台",
    )
    parser.add_argument("--host", default="0.0.0.0", help="绑定地址 (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8096, help="端口 (default: 8096)")
    parser.add_argument("--no-llm", action="store_true", help="禁用LLM（仅用模板回复）")
    parser.add_argument("--no-team", action="store_true", help="不自动创建默认团队")
    args = parser.parse_args()

    # 初始化引擎
    _init_engines(use_llm=not args.no_llm)

    # 创建默认团队
    if not args.no_team:
        _create_default_team()

    # 启动
    import uvicorn
    logger.info(f"🚀 DrugMind v2.0 server: http://{args.host}:{args.port}")
    logger.info(f"📖 API文档: http://{args.host}:{args.port}/docs")
    logger.info(f"📋 ReDoc:   http://{args.host}:{args.port}/redoc")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
