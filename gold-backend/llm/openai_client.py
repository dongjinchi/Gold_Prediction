"""OpenAI API 客户端（AsyncOpenAI，真正异步）"""
import logging
from openai import AsyncOpenAI
from config import OPENAI_API_KEY, OPENAI_BASE_URL

logger = logging.getLogger(__name__)

_client = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            timeout=5.0,
            max_retries=0,
        )
    return _client


async def chat(messages: list[dict], model: str = "gpt-4o-mini",
               temperature: float = 0.3, max_tokens: int = 1024) -> str:
    """调用OpenAI Chat API（异步）。

    Returns:
        LLM回复文本，失败时返回 "[OpenAI Error]: ..."
    """
    client = get_client()
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.exception(f"OpenAI API call failed: {e}")
        return f"[OpenAI Error]: {str(e)}"
