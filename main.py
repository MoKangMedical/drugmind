#!/usr/bin/env python3
"""
DrugMind v2.0 — 药物研发人员的数字分身协作平台
"""

import sys
import logging
import argparse
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("drugmind")

STORAGE_DIR = str(Path(__file__).parent / "drugmind_data")


def get_engines(use_llm=True):
    from collaboration.decision_log import DecisionLogger
    from agents.registry import AgentRegistry
    from digital_twin.engine import DigitalTwinEngine
    from collaboration.discussion import DiscussionEngine
    from project.kanban import KanbanBoard
    from project.workspace import ProjectWorkspaceStore
    from drug_modeling.compound_tracker import CompoundTracker
    from auth.user import UserManager
    from community.hub import DiscussionHub
    from memory.project_memory import ProjectMemoryStore
    from second_me.integration import SecondMeIntegration
    from skills.registry import SkillRegistry
    from tools.registry import ToolRegistry
    from workflows.orchestrator import WorkflowOrchestrator

    twin = DigitalTwinEngine(storage_dir=STORAGE_DIR, use_llm=use_llm)
    discussion = DiscussionEngine(twin)
    decisions = DecisionLogger(f"{STORAGE_DIR}/decisions")
    kanban = KanbanBoard(f"{STORAGE_DIR}/projects")
    workspace_store = ProjectWorkspaceStore(f"{STORAGE_DIR}/platform/workspaces")
    tracker = CompoundTracker(f"{STORAGE_DIR}/compounds")
    users = UserManager(f"{STORAGE_DIR}/users")
    hub = DiscussionHub(f"{STORAGE_DIR}/discussions")
    sm = SecondMeIntegration(mode="cloud")
    agent_registry = AgentRegistry(f"{STORAGE_DIR}/platform/agents")
    skill_registry = SkillRegistry(f"{STORAGE_DIR}/platform/skills")
    tool_registry = ToolRegistry(f"{STORAGE_DIR}/platform/tools")
    project_memory = ProjectMemoryStore(f"{STORAGE_DIR}/platform/memory")
    workflow_orchestrator = WorkflowOrchestrator(
        f"{STORAGE_DIR}/platform/workflows",
        agent_registry=agent_registry,
        skill_registry=skill_registry,
        tool_registry=tool_registry,
    )

    return (
        twin,
        discussion,
        decisions,
        kanban,
        workspace_store,
        tracker,
        users,
        hub,
        sm,
        agent_registry,
        skill_registry,
        tool_registry,
        project_memory,
        workflow_orchestrator,
    )


def cmd_serve(args):
    import uvicorn
    from api.api import app, init_engines

    (
        twin,
        discussion,
        decisions,
        kanban,
        workspace_store,
        tracker,
        users,
        hub,
        sm,
        agent_registry,
        skill_registry,
        tool_registry,
        project_memory,
        workflow_orchestrator,
    ) = get_engines(use_llm=True)
    init_engines(
        twin,
        discussion,
        decisions,
        kanban,
        workspace_store,
        tracker,
        users,
        hub,
        sm,
        agent_registry,
        skill_registry,
        tool_registry,
        project_memory,
        workflow_orchestrator,
    )

    # 创建默认团队
    for role_id, name in [
        ('medicinal_chemist', '张化学家'), ('biologist', '李生物'),
        ('pharmacologist', '王药理'), ('data_scientist', '赵数据'),
        ('project_lead', '刘项目'),
    ]:
        twin.create_twin(role_id, name)
    logger.info("✅ 默认团队: 5个分身就绪")

    logger.info(f"🚀 DrugMind v2.0: http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


def cmd_test(args):
    print("🧪 DrugMind v2.0 测试\n")
    try:
        from llm import test_connection
        r = test_connection()
        print(f"  MIMO: {'✅' if r['status']=='ok' else '❌'}")
    except Exception as e:
        print(f"  MIMO: ❌ {e}")

    (
        twin,
        disc,
        decisions,
        kanban,
        workspace_store,
        tracker,
        users,
        hub,
        sm,
        agent_registry,
        skill_registry,
        tool_registry,
        project_memory,
        workflow_orchestrator,
    ) = get_engines(use_llm=False)
    print(f"  引擎: ✅ 数字分身/协作/项目/化合物/用户/社区")
    print(
        "  平台骨架: ✅ "
        f"agents={agent_registry.count()} "
        f"skills={skill_registry.count()} "
        f"tools={tool_registry.count()} "
        f"workflow_templates={len(workflow_orchestrator.templates)}"
    )
    print(
        "  项目上下文: ✅ "
        f"workspaces={workspace_store.count()} "
        f"decisions={decisions.count()} "
        f"projects={kanban.count()} "
        f"compounds={tracker.count()}"
    )

    try:
        from drug_modeling.admet_bridge import ADMETBridge
        r = ADMETBridge().predict("CCO")
        print(f"  RDKit: ✅ MW={r.get('mw')}")
    except Exception as e:
        print(f"  RDKit: ⚠️ {e}")

    print("\n✅ 全部通过")


def cmd_roles(args):
    from digital_twin.roles import list_roles
    for r in list_roles():
        print(f"  {r['emoji']} {r['display_name']} ({r['role_id']})")


def main():
    p = argparse.ArgumentParser(prog="drugmind")
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("serve")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=8096)

    sub.add_parser("test")
    sub.add_parser("roles")

    args = p.parse_args()
    if not args.cmd:
        p.print_help(); sys.exit(1)

    {"serve": cmd_serve, "test": cmd_test, "roles": cmd_roles}[args.cmd](args)


if __name__ == "__main__":
    main()
