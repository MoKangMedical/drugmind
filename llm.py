"""
DrugMind LLM integration.

Default provider: DeepSeek OpenAI-compatible API.
"""

import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")
LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL",
    os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
)
LLM_API_KEY = os.getenv(
    "LLM_API_KEY",
    os.getenv("DEEPSEEK_API_KEY", ""),
)
LLM_MODEL = os.getenv(
    "LLM_MODEL",
    os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"),
)


def get_llm_client() -> OpenAI:
    """Create the configured OpenAI-compatible LLM client."""
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY / DEEPSEEK_API_KEY is not configured.")
    return OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


def get_mimo_client() -> OpenAI:
    """Backward-compatible alias for older imports."""
    return get_llm_client()


def chat(
    messages: list[dict],
    model: str = "",
    temperature: float = 0.4,
    max_tokens: int = 2048,
) -> str:
    """Call the configured chat model."""
    client = get_llm_client()
    model = model or LLM_MODEL

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.error("%s API call failed: %s", LLM_PROVIDER, e)
        raise


def test_connection() -> dict:
    """Test the configured LLM connection."""
    try:
        resp = chat(
            [{"role": "user", "content": "Say OK in one word."}],
            temperature=0.1,
            max_tokens=10,
        )
        return {
            "status": "ok",
            "provider": LLM_PROVIDER,
            "model": LLM_MODEL,
            "base_url": LLM_BASE_URL,
            "response": resp,
        }
    except Exception as e:
        return {
            "status": "error",
            "provider": LLM_PROVIDER,
            "model": LLM_MODEL,
            "base_url": LLM_BASE_URL,
            "error": str(e),
        }
