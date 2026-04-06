#!/usr/bin/env python3
"""
DrugMind v1.0 — 药物研发数字分身协作平台
Second Me for Pharma Teams

Usage:
    # 启动Web服务
    python main.py serve [--port 8096]

    # 创建数字分身
    python main.py twin --role medicinal_chemist --name "张博士"

    # 发起讨论
    python main.py discuss --topic "Compound #47 是否进入先导优化？" --twins chemist biologist

    # 创建项目
    python main.py project --name "MG新药" --target CHRM1 --disease "重症肌无力"

    # 查看角色
    python main.py roles
"""

import sys
import json
import logging
import argparse
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("drugmind")

STORAGE_DIR = "./drugmind_data"


def get_engines():
    """初始化所有引擎"""
    try:
        from openai import OpenAI
        llm = OpenAI(
            base_url="https://api.xiaomi.com/v1",
            api_key="placeholder"  # 使用MIMO API时配置
        )
    except:
        llm = None
        logger.warning("LLM未配置，使用模板回复模式")

    from digital_twin.engine import DigitalTwinEngine
    from collaboration.discussion import DiscussionEngine
    from project.kanban import KanbanBoard
    from drug_modeling.compound_tracker import CompoundTracker

    twin = DigitalTwinEngine(llm_client=llm, storage_dir=STORAGE_DIR)
    discussion = DiscussionEngine(twin)
    kanban = KanbanBoard(f"{STORAGE_DIR}/projects")
    tracker = CompoundTracker(f"{STORAGE_DIR}/compounds")

    return twin, discussion, kanban, tracker


def cmd_serve(args):
    """启动API服务"""
    import uvicorn
    from api.api import app, init_engines

    twin, discussion, kanban, tracker = get_engines()
    init_engines(twin, discussion, kanban, tracker)

    logger.info(f"🚀 DrugMind API启动: {args.host}:{args.port}")
    logger.info(f"📚 API文档: http://{args.host}:{args.port}/docs")
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


def cmd_twin(args):
    """创建数字分身"""
    twin, _, _, _ = get_engines()
    result = twin.create_twin(
        role_id=args.role,
        name=args.name,
        custom_expertise=args.expertise.split(",") if args.expertise else None
    )
    print(f"\n✅ 数字分身创建成功!")
    print(f"   {result['emoji']} {result['name']} ({result['role']})")
    print(f"   ID: {result['twin_id']}")


def cmd_discuss(args):
    """发起讨论"""
    twin, discussion, _, _ = get_engines()

    # 自动创建分身（如果不存在）
    twin_ids = []
    role_map = {"chemist": "medicinal_chemist", "bio": "biologist",
                "pharma": "pharmacologist", "data": "data_scientist",
                "lead": "project_lead"}

    for t in (args.twins or ["chemist", "biologist", "pharma"]):
        role_id = role_map.get(t, t)
        name = f"专家_{t}"
        twin.create_twin(role_id=role_id, name=name)
        twin_ids.append(f"{role_id}_{name}")

    # 创建讨论
    session = discussion.create_discussion(
        topic=args.topic,
        participant_ids=twin_ids,
        context=args.context or ""
    )

    print(f"\n{'='*60}")
    print(f"💬 讨论议题: {args.topic}")
    print(f"{'='*60}")

    # 运行讨论
    messages = discussion.run_round_robin(
        session_id=session.session_id,
        max_rounds=args.rounds
    )

    for msg in messages:
        print(f"\n{msg.emoji} **{msg.name}** ({msg.role}):")
        print(f"   {msg.content}")


def cmd_project(args):
    """创建项目"""
    _, _, kanban, _ = get_engines()
    project = kanban.create_project(
        project_id=args.name.lower().replace(" ", "_"),
        name=args.name,
        target=args.target or "",
        disease=args.disease or "",
    )
    print(f"\n✅ 项目创建: {project.name}")
    print(f"   靶点: {project.target or '待定'}")
    print(f"   疾病: {project.disease or '待定'}")


def cmd_roles(args):
    """查看角色"""
    from digital_twin.roles import list_roles
    roles = list_roles()
    print("\n📋 可用药物研发角色:")
    for r in roles:
        print(f"   {r['emoji']} {r['display_name']} ({r['role_id']})")
        print(f"      专长: {', '.join(r['expertise'][:3])}...")
        print(f"      风险容忍: {r['risk_tolerance']}/1.0")


def main():
    parser = argparse.ArgumentParser(
        prog="drugmind",
        description="DrugMind v1.0 — 药物研发数字分身协作平台"
    )
    subparsers = parser.add_subparsers(dest="command")

    # serve
    p = subparsers.add_parser("serve", help="启动API服务")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8096)
    p.add_argument("--reload", action="store_true")

    # twin
    p = subparsers.add_parser("twin", help="创建数字分身")
    p.add_argument("--role", required=True, help="角色ID")
    p.add_argument("--name", required=True, help="专家姓名")
    p.add_argument("--expertise", default="", help="额外专长(逗号分隔)")

    # discuss
    p = subparsers.add_parser("discuss", help="发起讨论")
    p.add_argument("--topic", required=True, help="讨论议题")
    p.add_argument("--twins", nargs="+", help="参与分身(chemist/bio/pharma/data/lead)")
    p.add_argument("--context", default="", help="背景信息")
    p.add_argument("--rounds", type=int, default=2, help="讨论轮数")

    # project
    p = subparsers.add_parser("project", help="创建项目")
    p.add_argument("--name", required=True, help="项目名称")
    p.add_argument("--target", default="", help="靶点")
    p.add_argument("--disease", default="", help="疾病")

    # roles
    subparsers.add_parser("roles", help="查看角色列表")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "serve": cmd_serve,
        "twin": cmd_twin,
        "discuss": cmd_discuss,
        "project": cmd_project,
        "roles": cmd_roles,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
