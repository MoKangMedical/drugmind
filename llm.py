"""
DrugMind LLM集成 - 小米MIMO API
"""

import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

# MIMO配置
MIMO_BASE_URL = os.getenv("MIMO_BASE_URL", "https://api.xiaomimimo.com/v1")
MIMO_API_KEY = os.getenv("MIMO_API_KEY", "")
MIMO_MODEL = os.getenv("MIMO_MODEL", "mimo-v2-pro")


def get_mimo_client() -> OpenAI:
    """获取MIMO客户端"""
    return OpenAI(base_url=MIMO_BASE_URL, api_key=MIMO_API_KEY)


def chat(
    messages: list[dict],
    model: str = "",
    temperature: float = 0.4,
    max_tokens: int = 1024,
) -> str:
    """
    调用MIMO聊天

    Args:
        messages: OpenAI格式的消息列表
        model: 模型名称
        temperature: 温度
        max_tokens: 最大token数
    """
    client = get_mimo_client()
    model = model or MIMO_MODEL

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.error(f"MIMO API调用失败: {e}")
        raise


def test_connection() -> dict:
    """测试MIMO连接"""
    try:
        resp = chat(
            [{"role": "user", "content": "Say OK in one word."}],
            temperature=0.1,
            max_tokens=10,
        )
        return {"status": "ok", "response": resp}
    except Exception as e:
        return {"status": "error", "error": str(e)}
