"""
种子数据加载器
冷启动社群：预设讨论场景 + 自动生成AI讨论
"""

import logging
from .scenarios import SEED_DISCUSSIONS, SEED_ROLES, SEED_SCENARIOS

logger = logging.getLogger(__name__)


def seed_platform(twin_engine, discussion_hub, max_topics: int = 3):
    """
    加载种子数据到平台
    
    Args:
        twin_engine: 数字分身引擎
        discussion_hub: 公开讨论广场
        max_topics: 最多生成几个讨论（避免token消耗过多）
    """
    created = []

    # 1. 创建种子分身
    for role in SEED_ROLES:
        twin_engine.create_twin(
            role_id=role["role_id"],
            name=role["name"],
        )
    logger.info(f"✅ 创建 {len(SEED_ROLES)} 个种子分身")

    # 2. 生成种子讨论
    twin_ids = {r["role_id"]: f"{r['role_id']}_{r['name']}" for r in SEED_ROLES}

    for i, topic_data in enumerate(SEED_DISCUSSIONS[:max_topics]):
        # 创建公开讨论
        disc = discussion_hub.create(
            topic=topic_data["topic"],
            creator_id="drugmind_seed",
            creator_name="DrugMind官方",
            tags=topic_data["tags"],
            participants=[
                {"twin_id": tid, "name": r["name"], "role": r["role_id"], "emoji": r["emoji"]}
                for r, tid in zip(SEED_ROLES, twin_ids.values())
            ],
        )

        # 为每个角色生成一条讨论消息
        for role_id, twin_id in twin_ids.items():
            prompt = topic_data["prompts"].get(role_id, "")
            if prompt:
                full_prompt = f"话题：{topic_data['topic']}\n背景：{topic_data['context']}\n\n{prompt}"
                try:
                    resp = twin_engine.ask_twin(twin_id, full_prompt)
                    discussion_hub.add_message(disc.session_id, {
                        "twin_id": twin_id,
                        "name": resp.name,
                        "role": resp.role,
                        "emoji": resp.emoji,
                        "content": resp.message,
                        "timestamp": "",
                    })
                except Exception as e:
                    logger.warning(f"生成种子讨论失败 ({role_id}): {e}")

        created.append({
            "session_id": disc.session_id,
            "topic": disc.topic,
            "tags": disc.tags,
        })
        logger.info(f"📝 创建种子讨论: {disc.topic}")

    return {
        "twins_created": len(SEED_ROLES),
        "discussions_created": len(created),
        "discussions": created,
    }


def get_scenarios():
    """获取场景模板"""
    return SEED_SCENARIOS


def get_seed_topics():
    """获取种子话题列表"""
    return [
        {"topic": d["topic"], "tags": d["tags"], "context": d["context"][:100]}
        for d in SEED_DISCUSSIONS
    ]
