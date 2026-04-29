"""
DrugMind MCP Server
标准MCP协议端点，接入Second Me平台

支持:
- tools/list: 返回可用工具列表
- tools/call: 执行工具调用

Second Me平台通过此端点将用户请求转发到DrugMind
"""

import json
import logging
import httpx
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp", tags=["MCP"])

# Second Me用户信息API
SECOND_ME_USERINFO_URL = "https://api.mindverse.com/gate/lab/api/secondme/user/info"

# 全局引用（main.py初始化时设置）
_twin_engine = None
_discussion_engine = None
_discussion_hub = None
_user_mgr = None


def init_mcp(twin_engine, discussion_engine, discussion_hub, user_mgr):
    global _twin_engine, _discussion_engine, _discussion_hub, _user_mgr
    _twin_engine = twin_engine
    _discussion_engine = discussion_engine
    _discussion_hub = discussion_hub
    _user_mgr = user_mgr


# ──────────────────────────────────────────────
# Second Me用户认证
# ──────────────────────────────────────────────
async def get_second_me_user(request: Request) -> Optional[dict]:
    """从Bearer Token获取Second Me用户信息"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None

    token = auth.replace("Bearer ", "")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                SECOND_ME_USERINFO_URL,
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                user_info = data.get("data", {})
                return {
                    "userId": user_info.get("userId"),
                    "name": user_info.get("name", ""),
                    "avatar": user_info.get("avatar", ""),
                }
    except Exception as e:
        logger.warning(f"Second Me用户认证失败: {e}")
    return None


# ──────────────────────────────────────────────
# MCP端点
# ──────────────────────────────────────────────
TOOLS = [
    {
        "name": "drugmind_ask",
        "description": "向DrugMind数字分身提问。可以问任意药物研发相关问题，系统会从药物化学、生物学、药理学、数据科学、项目管理五个角度给出专业回答。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "你的药物研发问题"
                },
                "roles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要咨询的角色（可选）：medicinal_chemist, biologist, pharmacologist, data_scientist, project_lead",
                    "default": ["medicinal_chemist", "biologist", "pharmacologist"]
                },
                "context": {
                    "type": "string",
                    "description": "额外背景信息（可选）",
                    "default": ""
                }
            },
            "required": ["question"]
        }
    },
    {
        "name": "drugmind_discuss",
        "description": "发起药物研发团队讨论。5个专业数字分身会围绕议题进行多角度讨论，形成共识。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "讨论议题，例如：'Compound #47 是否进入先导优化？'"
                },
                "context": {
                    "type": "string",
                    "description": "背景信息：化合物数据、实验结果等",
                    "default": ""
                },
                "rounds": {
                    "type": "integer",
                    "description": "讨论轮数（1-3）",
                    "default": 1
                }
            },
            "required": ["topic"]
        }
    },
    {
        "name": "drugmind_admet",
        "description": "快速评估化合物的ADMET性质（分子量、logP、氢键、TPSA、QED、Lipinski违规数）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "smiles": {
                    "type": "string",
                    "description": "化合物的SMILES表达式"
                }
            },
            "required": ["smiles"]
        }
    },
    {
        "name": "drugmind_scenario",
        "description": "获取药物研发场景模板和检查清单（新靶点评估、先导优化、Go/No-Go决策等）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scenario": {
                    "type": "string",
                    "description": "场景名称：target_evaluation, lead_optimization, go_nogo",
                    "enum": ["target_evaluation", "lead_optimization", "go_nogo"]
                }
            },
            "required": ["scenario"]
        }
    },
    {
        "name": "drugmind_compound",
        "description": "管理化合物管线：添加化合物、查看管线状态。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作：add（添加）或 pipeline（查看管线）",
                    "enum": ["add", "pipeline"]
                },
                "compound_id": {
                    "type": "string",
                    "description": "化合物编号（添加时必填）"
                },
                "smiles": {
                    "type": "string",
                    "description": "SMILES表达式（添加时必填）"
                },
                "name": {
                    "type": "string",
                    "description": "化合物名称",
                    "default": ""
                }
            },
            "required": ["action"]
        }
    }
]


@router.post("")
async def mcp_endpoint(request: Request):
    """
    MCP JSON-RPC端点
    
    支持:
    - tools/list: 返回可用工具
    - tools/call: 执行工具
    """
    try:
        body = await request.json()
    except:
        return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}, status_code=400)

    method = body.get("method")
    req_id = body.get("id", "1")

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}

    elif method == "tools/call":
        params = body.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        # 可选：Second Me用户认证
        user = await get_second_me_user(request)

        try:
            result = await _call_tool(tool_name, arguments, user)
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as e:
            logger.error(f"工具调用失败 {tool_name}: {e}")
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": f"调用失败: {str(e)}"}]}}

    else:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}},
            status_code=400,
        )


# ──────────────────────────────────────────────
# 工具实现
# ──────────────────────────────────────────────
async def _call_tool(name: str, arguments: dict, user: Optional[dict] = None) -> dict:
    """执行MCP工具调用"""

    user_prefix = f"（来自Second Me用户 {user['name']}）" if user and user.get("name") else ""

    if name == "drugmind_ask":
        question = arguments["question"]
        roles = arguments.get("roles", ["medicinal_chemist", "biologist", "pharmacologist"])
        context = arguments.get("context", "")

        role_map = {
            "medicinal_chemist": "medicinal_chemist",
            "biologist": "biologist",
            "pharmacologist": "pharmacologist",
            "data_scientist": "data_scientist",
            "project_lead": "project_lead",
        }

        responses = []
        for role_id in roles:
            mapped = role_map.get(role_id, role_id)
            twin_id = f"{mapped}_{_get_twin_name(mapped)}"
            try:
                resp = _twin_engine.ask_twin(twin_id, f"{user_prefix}{question}", context)
                responses.append(f"{resp.emoji} **{resp.name}** ({resp.role}):\n{resp.message}")
            except Exception as e:
                responses.append(f"⚠️ {role_id}: 回复失败 ({e})")

        return {"content": [{"type": "text", "text": "\n\n---\n\n".join(responses)}]}

    elif name == "drugmind_discuss":
        topic = arguments["topic"]
        context = arguments.get("context", "")
        rounds = min(arguments.get("rounds", 1), 3)

        # 创建分身
        all_twin_ids = []
        role_data = [
            ("medicinal_chemist", "张化学家"), ("biologist", "李生物"),
            ("pharmacologist", "王药理"), ("data_scientist", "赵数据"),
            ("project_lead", "刘项目"),
        ]
        for role_id, name in role_data:
            _twin_engine.create_twin(role_id, name)
            all_twin_ids.append(f"{role_id}_{name}")

        session = _discussion_engine.create_discussion(
            topic=f"{user_prefix}{topic}",
            participant_ids=all_twin_ids,
            context=context,
        )
        messages = _discussion_engine.run_round_robin(
            session.session_id, context, max_rounds=rounds,
        )

        text = f"# 💬 讨论: {topic}\n\n"
        for m in messages:
            text += f"{m.emoji} **{m.name}** ({m.role}):\n{m.message}\n\n---\n\n"
        text += f"📊 共 {len(messages)} 条发言，{rounds} 轮讨论"

        return {"content": [{"type": "text", "text": text}]}

    elif name == "drugmind_admet":
        smiles = arguments["smiles"]
        from drug_modeling.admet_bridge import ADMETBridge
        bridge = ADMETBridge()
        result = bridge.predict(smiles)

        if "error" in result:
            return {"content": [{"type": "text", "text": f"❌ {result['error']}"}]}

        text = f"## 🧪 ADMET 快速评估\n\n"
        text += f"| 指标 | 值 | 评价 |\n|------|------|------|\n"
        text += f"| 分子量 (MW) | {result.get('mw')} | {'✅ <500' if result.get('mw', 999) < 500 else '⚠️ >500'} |\n"
        text += f"| logP | {result.get('logp')} | {'✅ 0-5' if 0 <= result.get('logp', 99) <= 5 else '⚠️ 超出范围'} |\n"
        text += f"| HBD | {result.get('hbd')} | {'✅ ≤5' if result.get('hbd', 99) <= 5 else '⚠️ >5'} |\n"
        text += f"| HBA | {result.get('hba')} | {'✅ ≤10' if result.get('hba', 99) <= 10 else '⚠️ >10'} |\n"
        text += f"| TPSA | {result.get('tpsa')} | {'✅ <140' if result.get('tpsa', 999) < 140 else '⚠️ >140'} |\n"
        text += f"| QED | {result.get('qed')} | {'✅ >0.5' if result.get('qed', 0) > 0.5 else '⚠️ <0.5'} |\n"
        text += f"| SA Score | {result.get('sa_score')} | {'✅ <5' if result.get('sa_score', 99) < 5 else '⚠️ 合成较难'} |\n"
        text += f"| Lipinski违规 | {result.get('lipinski_violations')} | {'✅ 0' if result.get('lipinski_violations', 1) == 0 else '⚠️ 有违规'} |\n"

        return {"content": [{"type": "text", "text": text}]}

    elif name == "drugmind_scenario":
        from seeds.scenarios import SEED_SCENARIOS
        scenario_map = {
            "target_evaluation": 0,
            "lead_optimization": 1,
            "go_nogo": 2,
        }
        idx = scenario_map.get(arguments.get("scenario", ""), 0)
        if idx < len(SEED_SCENARIOS):
            s = SEED_SCENARIOS[idx]
            text = f"## 📋 {s['name']}\n\n{s['description']}\n\n"
            for i, item in enumerate(s["checklist"], 1):
                text += f"{i}. {item}\n"
            return {"content": [{"type": "text", "text": text}]}

        return {"content": [{"type": "text", "text": "未知场景"}]}

    elif name == "drugmind_compound":
        action = arguments.get("action", "pipeline")

        if action == "add":
            from drug_modeling.compound_tracker import CompoundTracker
            tracker = CompoundTracker()
            tracker.add_compound(
                compound_id=arguments.get("compound_id", ""),
                smiles=arguments.get("smiles", ""),
                name=arguments.get("name", ""),
            )
            return {"content": [{"type": "text", "text": f"✅ 化合物 {arguments.get('compound_id')} 已添加"}]}

        elif action == "pipeline":
            from drug_modeling.compound_tracker import CompoundTracker
            tracker = CompoundTracker()
            pipeline = tracker.get_pipeline()
            text = "## 📊 化合物管线\n\n"
            for stage, compounds in pipeline.items():
                text += f"**{stage}**: {len(compounds)} 个化合物\n"
            return {"content": [{"type": "text", "text": text or "管线为空"}]}

    return {"content": [{"type": "text", "text": f"未知工具: {name}"}]}


def _get_twin_name(role_id: str) -> str:
    """获取分身默认名称"""
    names = {
        "medicinal_chemist": "张化学家",
        "biologist": "李生物",
        "pharmacologist": "王药理",
        "data_scientist": "赵数据",
        "project_lead": "刘项目",
    }
    return names.get(role_id, "未知")
