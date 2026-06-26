"""DeepSeek API 客户端（AsyncOpenAI，真正异步）"""
import logging
from openai import AsyncOpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

logger = logging.getLogger(__name__)

_client = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            timeout=20.0,
            max_retries=0,
        )
    return _client


async def chat(messages: list[dict], model: str = "deepseek-chat",
               temperature: float = 0.3, max_tokens: int = 1024) -> str:
    """调用DeepSeek Chat API（异步）。

    Returns:
        LLM回复文本，失败时返回 "[DeepSeek Error]: ..."
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
        logger.exception(f"DeepSeek API call failed: {e}")
        return f"[DeepSeek Error]: {str(e)}"
