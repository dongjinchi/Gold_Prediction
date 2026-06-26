"""DeepSeek API 客户端"""
import logging
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

logger = logging.getLogger(__name__)

_client = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    return _client


async def chat(messages: list[dict], model: str = "deepseek-chat",
               temperature: float = 0.3, max_tokens: int = 1024) -> str:
    """调用DeepSeek Chat API。

    Args:
        messages: OpenAI格式的消息列表
        model: 模型名称
        temperature: 创造性控制
        max_tokens: 最大输出token

    Returns:
        LLM回复文本
    """
    client = get_client()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.exception(f"DeepSeek API call failed: {e}")
        return f"[DeepSeek Error]: {str(e)}"
