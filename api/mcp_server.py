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
_drug_discovery_hub = None
_kanban = None
_compound_tracker = None
_blatant_why_adapter = None
_medi_pharma_adapter = None


def init_mcp(
    twin_engine,
    discussion_engine,
    discussion_hub,
    user_mgr,
    drug_discovery_hub=None,
    kanban=None,
    compound_tracker=None,
    blatant_why_adapter=None,
    medi_pharma_adapter=None,
):
    global _twin_engine, _discussion_engine, _discussion_hub, _user_mgr
    global _drug_discovery_hub, _kanban, _compound_tracker, _blatant_why_adapter, _medi_pharma_adapter
    _twin_engine = twin_engine
    _discussion_engine = discussion_engine
    _discussion_hub = discussion_hub
    _user_mgr = user_mgr
    _drug_discovery_hub = drug_discovery_hub
    _kanban = kanban
    _compound_tracker = compound_tracker
    _blatant_why_adapter = blatant_why_adapter
    _medi_pharma_adapter = medi_pharma_adapter


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
    },
    {
        "name": "drugmind_capabilities",
        "description": "查看DrugMind药物研发能力目录和实施蓝图。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "stage_id": {
                    "type": "string",
                    "description": "可选：按阶段过滤"
                },
                "category": {
                    "type": "string",
                    "description": "可选：按类别过滤"
                }
            }
        }
    },
    {
        "name": "drugmind_execute_capability",
        "description": "对指定项目执行 DrugMind capability，例如 hit triage、candidate nomination 或 SecondMe sync。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目ID"
                },
                "capability_id": {
                    "type": "string",
                    "description": "能力ID，例如 capability.hit_triage"
                },
                "input_payload": {
                    "type": "object",
                    "description": "可选运行时输入",
                    "default": {}
                },
                "sync_to_second_me": {
                    "type": "boolean",
                    "description": "是否同步到 SecondMe",
                    "default": False
                }
            },
            "required": ["project_id", "capability_id"]
        }
    },
    {
        "name": "drugmind_biologics_campaign",
        "description": "生成 BY 风格 biologics campaign 计划，包含 research→design→screen→rank 和 Tamarind 估算。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目ID"
                },
                "modality": {
                    "type": "string",
                    "description": "biologics / antibody / nanobody / protein",
                    "default": "nanobody"
                },
                "scaffolds": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "可选 scaffold 列表"
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "drugmind_structural_research",
        "description": "执行真实的结构生物学 research step，调用 UniProt / RCSB PDB / SAbDab 形成 target evidence bundle。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "可选项目ID；若不提供则需直接给 target"
                },
                "target": {
                    "type": "string",
                    "description": "靶点名称，例如 KRAS、EGFR"
                },
                "disease": {
                    "type": "string",
                    "description": "可选疾病上下文"
                },
                "modality": {
                    "type": "string",
                    "description": "small_molecule / biologics / antibody / nanobody / protein",
                    "default": "small_molecule"
                },
                "organism_id": {
                    "type": "integer",
                    "description": "NCBI taxonomy id，默认 9606",
                    "default": 9606
                },
                "pdb_rows": {
                    "type": "integer",
                    "description": "返回的结构数量",
                    "default": 6
                }
            }
        }
    },
    {
        "name": "drugmind_tamarind_job",
        "description": "直接提交、查询、轮询 Tamarind job。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "tools", "list_jobs", "get_job", "submit", "poll", "result"],
                    "description": "Tamarind 操作"
                },
                "job_name": {
                    "type": "string",
                    "description": "job 名称"
                },
                "job_type": {
                    "type": "string",
                    "description": "job 类型"
                },
                "settings": {
                    "type": "object",
                    "description": "submit 时的 settings"
                },
                "metadata": {
                    "type": "object",
                    "description": "submit 时附带 metadata"
                },
                "wait_for_completion": {
                    "type": "boolean",
                    "default": False
                },
                "timeout_seconds": {
                    "type": "integer",
                    "default": 900
                },
                "interval_seconds": {
                    "type": "integer",
                    "default": 20
                },
                "include_result": {
                    "type": "boolean",
                    "default": True
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "drugmind_medi_pharma",
        "description": "调用 MediPharma v2.0.0 能力，包括靶点发现、虚拟筛选、分子生成、ADMET、先导优化、全流水线和知识报告。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "status",
                        "health",
                        "ecosystem",
                        "discover_targets",
                        "run_screening",
                        "generate",
                        "predict_admet",
                        "batch_predict_admet",
                        "optimize",
                        "run_pipeline",
                        "knowledge_report"
                    ],
                    "description": "MediPharma 动作"
                },
                "project_id": {
                    "type": "string",
                    "description": "可选项目ID"
                },
                "input_payload": {
                    "type": "object",
                    "description": "请求体，字段跟 MediPharma 对应端点一致",
                    "default": {}
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "drugmind_mimo_media",
        "description": "使用小米 MIMO 生成音频或视频内容。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["audio_tts", "video_generate", "status"],
                    "description": "audio_tts 或 video_generate"
                },
                "text": {
                    "type": "string",
                    "description": "audio_tts 文本"
                },
                "prompt": {
                    "type": "string",
                    "description": "video_generate 提示词"
                },
                "voice": {
                    "type": "string",
                    "description": "音色"
                },
                "format": {
                    "type": "string",
                    "description": "音频格式，例如 mp3/wav"
                },
                "model": {
                    "type": "string",
                    "description": "模型名称"
                },
                "duration": {
                    "type": "integer",
                    "description": "视频时长（秒）"
                },
                "size": {
                    "type": "string",
                    "description": "视频尺寸，例如 1280x720"
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

    elif name == "drugmind_capabilities":
        if not _drug_discovery_hub:
            return {"content": [{"type": "text", "text": "Drug discovery hub 未初始化"}]}
        payload = {
            "capabilities": _drug_discovery_hub.list_capabilities(
                stage_id=arguments.get("stage_id", ""),
                category=arguments.get("category", ""),
            ),
            "blueprints": _drug_discovery_hub.list_blueprints(),
        }
        return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}]}

    elif name == "drugmind_execute_capability":
        if not _drug_discovery_hub:
            return {"content": [{"type": "text", "text": "Drug discovery hub 未初始化"}]}
        result = _drug_discovery_hub.execute_capability(
            arguments["project_id"],
            arguments["capability_id"],
            input_payload=arguments.get("input_payload", {}),
            triggered_by=user.get("name", "second_me") if user else "second_me",
            sync_to_second_me=bool(arguments.get("sync_to_second_me", False)),
        )
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}

    elif name == "drugmind_biologics_campaign":
        if not _blatant_why_adapter or not _kanban:
            return {"content": [{"type": "text", "text": "BY biologics adapter 未初始化"}]}
        project = _kanban.get_project(arguments["project_id"])
        if not project:
            return {"content": [{"type": "text", "text": "项目不存在"}]}
        result = _blatant_why_adapter.biologics_pipeline.build_campaign(
            project=project,
            modality=arguments.get("modality", project.get("modality", "nanobody")),
            scaffolds=arguments.get("scaffolds"),
        )
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}

    elif name == "drugmind_structural_research":
        if not _blatant_why_adapter:
            return {"content": [{"type": "text", "text": "BY structural research adapter 未初始化"}]}
        project_id = arguments.get("project_id", "")
        project = _kanban.get_project(project_id) if _kanban and project_id else None
        if not project:
            target = arguments.get("target", "").strip()
            if not target:
                return {"content": [{"type": "text", "text": "需要 project_id 或 target"}]}
            project = {
                "project_id": project_id or "adhoc_structural_research",
                "name": arguments.get("name") or target,
                "target": target,
                "disease": arguments.get("disease", ""),
                "modality": arguments.get("modality", "small_molecule"),
            }
        result = _blatant_why_adapter.run_target_research(
            project=project,
            modality=arguments.get("modality", project.get("modality", "small_molecule")),
            organism_id=int(arguments.get("organism_id", 9606)),
            pdb_rows=int(arguments.get("pdb_rows", 6)),
            sabdab_limit=int(arguments.get("sabdab_limit", 6)),
        )
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}

    elif name == "drugmind_tamarind_job":
        if not _blatant_why_adapter:
            return {"content": [{"type": "text", "text": "Tamarind client 未初始化"}]}
        action = arguments.get("action", "status")
        client = _blatant_why_adapter.tamarind_client
        if action == "status":
            result = client.probe_status()
        elif action == "tools":
            result = client.list_available_tools()
        elif action == "list_jobs":
            result = client.list_jobs(
                job_name=arguments.get("job_name", ""),
                status=arguments.get("status", ""),
                limit=int(arguments.get("limit", 50)),
            )
        elif action == "get_job":
            result = client.get_job(arguments.get("job_name", ""))
        elif action == "submit":
            result = client.submit_job(
                job_name=arguments.get("job_name", ""),
                job_type=arguments.get("job_type", ""),
                settings=arguments.get("settings") or {},
                metadata=arguments.get("metadata"),
                inputs=arguments.get("inputs"),
                wait_for_completion=bool(arguments.get("wait_for_completion", False)),
                poll_interval_seconds=int(arguments.get("interval_seconds", 20)),
                timeout_seconds=int(arguments.get("timeout_seconds", 900)),
                include_result=bool(arguments.get("include_result", True)),
            )
        elif action == "poll":
            result = client.poll_job(
                arguments.get("job_name", ""),
                interval_seconds=int(arguments.get("interval_seconds", 20)),
                timeout_seconds=int(arguments.get("timeout_seconds", 900)),
                include_result=bool(arguments.get("include_result", False)),
            )
        elif action == "result":
            result = client.get_result(arguments.get("job_name", ""), path=arguments.get("path", ""))
        else:
            result = {"error": f"未知 Tamarind action: {action}"}
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}

    elif name == "drugmind_medi_pharma":
        if not _medi_pharma_adapter:
            return {"content": [{"type": "text", "text": "MediPharma adapter 未初始化"}]}
        action = arguments.get("action", "status")
        input_payload = arguments.get("input_payload") or {}
        project_id = arguments.get("project_id", "")
        project = _kanban.get_project(project_id) if _kanban and project_id else None
        if not project:
            project = {
                "project_id": project_id or "adhoc_medi_pharma",
                "name": input_payload.get("name") or input_payload.get("target") or input_payload.get("disease") or "Ad Hoc MediPharma Request",
                "target": input_payload.get("target", ""),
                "disease": input_payload.get("disease", ""),
                "target_chembl_id": input_payload.get("target_chembl_id", ""),
                "modality": input_payload.get("modality", "small_molecule"),
            }
        compounds = _compound_tracker.list_compounds(project_id=project_id) if _compound_tracker and project_id else []
        if action in {"status", "probe_status"}:
            result = _medi_pharma_adapter.probe_status()
        elif action == "health":
            result = _medi_pharma_adapter.health()
        elif action == "ecosystem":
            result = _medi_pharma_adapter.ecosystem()
        elif action == "discover_targets":
            result = _medi_pharma_adapter.discover_targets(project=project, input_payload=input_payload)
        elif action == "run_screening":
            result = _medi_pharma_adapter.run_screening(project=project, compounds=compounds, input_payload=input_payload)
        elif action == "generate":
            result = _medi_pharma_adapter.generate(project=project, input_payload=input_payload)
        elif action == "predict_admet":
            result = _medi_pharma_adapter.predict_admet(smiles=input_payload.get("smiles", ""))
        elif action == "batch_predict_admet":
            result = _medi_pharma_adapter.batch_predict_admet(compounds=compounds, input_payload=input_payload)
        elif action == "optimize":
            result = _medi_pharma_adapter.optimize(compounds=compounds, input_payload=input_payload)
        elif action == "run_pipeline":
            result = _medi_pharma_adapter.run_pipeline(project=project, input_payload=input_payload)
        elif action == "knowledge_report":
            result = _medi_pharma_adapter.knowledge_report(project=project, input_payload=input_payload)
        else:
            result = {"status": "error", "error": f"未知 MediPharma action: {action}"}
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}

    elif name == "drugmind_mimo_media":
        from media import MimoMediaClient, MediaStore
        action = arguments.get("action", "status")
        client = MimoMediaClient()
        if action == "status":
            result = client.describe()
            return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
        if action == "audio_tts":
            text = arguments.get("text", "")
            if not text:
                return {"content": [{"type": "text", "text": "text 为必填"}]}
            result = client.synthesize_audio(
                text=text,
                voice=arguments.get("voice", "default"),
                response_format=arguments.get("format", "mp3"),
                speed=float(arguments.get("speed", 1.0)) if arguments.get("speed") is not None else 1.0,
                model=arguments.get("model", ""),
            )
            if result.get("status") != "ok":
                return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
            store = MediaStore()
            stored = store.save(result.get("audio", b""), suffix=f".{arguments.get('format', 'mp3')}", subdir="audio")
            return {"content": [{"type": "text", "text": json.dumps({"status": "ok", "media": stored}, ensure_ascii=False, indent=2)}]}
        if action == "video_generate":
            prompt = arguments.get("prompt", "")
            if not prompt:
                return {"content": [{"type": "text", "text": "prompt 为必填"}]}
            result = client.generate_video(
                prompt=prompt,
                model=arguments.get("model", ""),
                size=arguments.get("size", "1280x720"),
                duration=int(arguments.get("duration", 6)),
                fps=int(arguments.get("fps", 24)),
                seed=arguments.get("seed"),
            )
            return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
        return {"content": [{"type": "text", "text": f"未知 MIMO 媒体 action: {action}"}]}

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
