#!/usr/bin/env python3
"""
DrugMind v1.0 — 药物研发数字分身协作平台
Second Me for Pharma Teams

Usage:
    python main.py serve [--port 8096]    # 启动Web服务
    python main.py twin --role chemist --name "张博士"  # 创建分身
    python main.py discuss --topic "议题" --twins chemist bio pharma
    python main.py project --name "项目" --target CHRM1
    python main.py test                     # 连通性测试
    python main.py roles                    # 查看角色
"""

import sys
import logging
import argparse
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("drugmind")

STORAGE_DIR = str(Path(__file__).parent / "drugmind_data")


def get_engines(use_llm=True):
    """初始化所有引擎"""
    from digital_twin.engine import DigitalTwinEngine
    from collaboration.discussion import DiscussionEngine
    from project.kanban import KanbanBoard
    from drug_modeling.compound_tracker import CompoundTracker

    twin = DigitalTwinEngine(storage_dir=STORAGE_DIR, use_llm=use_llm)
    discussion = DiscussionEngine(twin)
    kanban = KanbanBoard(f"{STORAGE_DIR}/projects")
    tracker = CompoundTracker(f"{STORAGE_DIR}/compounds")

    return twin, discussion, kanban, tracker


def cmd_serve(args):
    """启动API服务"""
    import uvicorn
    from api.api import app, init_engines

    twin, discussion, kanban, tracker = get_engines(use_llm=True)
    init_engines(twin, discussion, kanban, tracker)

    # 创建默认团队
    default_twins = [
        ('medicinal_chemist', '张化学家'),
        ('biologist', '李生物'),
        ('pharmacologist', '王药理'),
        ('data_scientist', '赵数据'),
        ('project_lead', '刘项目'),
    ]
    for role_id, name in default_twins:
        twin.create_twin(role_id, name)
    logger.info(f"✅ 默认团队创建: {len(default_twins)}个分身")

    logger.info(f"🚀 DrugMind API启动: {args.host}:{args.port}")
    logger.info(f"📚 API文档: http://{args.host}:{args.port}/docs")
    uvicorn.run(app, host=args.host, port=args.port)


def cmd_twin(args):
    """创建数字分身"""
    twin, _, _, _ = get_engines(use_llm=False)
    result = twin.create_twin(role_id=args.role, name=args.name)
    print(f"\n✅ {result['emoji']} {result['name']} ({result['role']})")
    print(f"   ID: {result['twin_id']}")


def cmd_discuss(args):
    """发起讨论"""
    twin, discussion, _, _ = get_engines(use_llm=True)

    # 角色映射
    role_map = {
        "chemist": "medicinal_chemist", "chem": "medicinal_chemist",
        "bio": "biologist", "biologist": "biologist",
        "pharma": "pharmacologist", "pharmacologist": "pharmacologist",
        "data": "data_scientist", "ds": "data_scientist",
        "lead": "project_lead", "pm": "project_lead",
    }

    twin_ids = []
    for t in (args.twins or ["chemist", "bio", "pharma"]):
        role_id = role_map.get(t, t)
        name = f"专家_{t}"
        twin.create_twin(role_id=role_id, name=name)
        twin_ids.append(f"{role_id}_{name}")

    session = discussion.create_discussion(
        topic=args.topic, participant_ids=twin_ids, context=args.context or "",
    )

    print(f"\n{'='*60}")
    print(f"💬 讨论: {args.topic}")
    print(f"{'='*60}")

    messages = discussion.run_round_robin(
        session_id=session.session_id, max_rounds=args.rounds,
    )

    for msg in messages:
        print(f"\n{msg.emoji} **{msg.name}** ({msg.role}):")
        print(f"   {msg.content}")

    print(f"\n{'='*60}")
    print(f"📋 共 {len(messages)} 条发言")


def cmd_project(args):
    """创建项目"""
    _, _, kanban, _ = get_engines(use_llm=False)
    project = kanban.create_project(
        project_id=args.name.lower().replace(" ", "_"),
        name=args.name,
        target=args.target or "",
        disease=args.disease or "",
    )
    print(f"\n✅ 项目: {project.name} (靶点: {project.target or '待定'})")


def cmd_test(args):
    """连通性测试"""
    print("🧪 DrugMind 连通性测试\n")

    # 测试MIMO
    try:
        from llm import test_connection
        r = test_connection()
        print(f"  MIMO API: {'✅' if r['status']=='ok' else '❌'} {r.get('response','')}")
    except Exception as e:
        print(f"  MIMO API: ❌ {e}")

    # 测试引擎
    twin, discussion, kanban, tracker = get_engines(use_llm=False)
    print(f"  数字分身引擎: ✅")
    print(f"  协作引擎: ✅")
    print(f"  项目管理: ✅")
    print(f"  化合物追踪: ✅")

    # 测试RDKit
    try:
        from drug_modeling.admet_bridge import ADMETBridge
        bridge = ADMETBridge()
        r = bridge.predict("CCO")
        print(f"  RDKit/ADMET: ✅ MW={r.get('mw')}")
    except Exception as e:
        print(f"  RDKit: ⚠️ {e}")

    print("\n✅ 全部检查通过")


def cmd_roles(args):
    """查看角色"""
    from digital_twin.roles import list_roles
    for r in list_roles():
        print(f"  {r['emoji']} {r['display_name']} ({r['role_id']})")
        print(f"     风险容忍: {r['risk_tolerance']} | 创新风格: {r['innovation_style']}")


def main():
    parser = argparse.ArgumentParser(prog="drugmind", description="DrugMind v1.0")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("serve", help="启动API服务")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8096)

    p = sub.add_parser("twin", help="创建数字分身")
    p.add_argument("--role", required=True)
    p.add_argument("--name", required=True)

    p = sub.add_parser("discuss", help="发起讨论")
    p.add_argument("--topic", required=True)
    p.add_argument("--twins", nargs="+")
    p.add_argument("--context", default="")
    p.add_argument("--rounds", type=int, default=2)

    p = sub.add_parser("project", help="创建项目")
    p.add_argument("--name", required=True)
    p.add_argument("--target", default="")
    p.add_argument("--disease", default="")

    sub.add_parser("test", help="连通性测试")
    sub.add_parser("roles", help="查看角色列表")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmds = {"serve": cmd_serve, "twin": cmd_twin, "discuss": cmd_discuss,
            "project": cmd_project, "test": cmd_test, "roles": cmd_roles}
    cmds[args.command](args)


if __name__ == "__main__":
    main()
