"""三阶段双LLM辩论编排器"""
import json
import asyncio
import logging
from datetime import date

from llm.deepseek import chat as ds_chat
from llm.openai_client import chat as oai_chat

logger = logging.getLogger(__name__)

SYSTEM_ANALYST = """你是一位资深黄金投资分析师，拥有20年全球宏观交易经验。
请基于提供的市场数据进行分析。你的回答应该：
1. 数据驱动，引用具体数字
2. 考虑多空两面
3. 给出明确的方向判断
4. 指出你的判断可能出错的条件（预注册反驳）
5. 用中文回答，专业但不晦涩"""

SYSTEM_CHALLENGER = """你是黄金市场分析师，你的任务是审查另一位分析师的判断。
找出对方逻辑中的漏洞、被忽略的风险因素、或过于自信的结论。
如果你的判断和对方一致，也要指出即使是正确的方向也存在什么风险。
对事不对人，保持专业。用中文回答，简洁直接，不超过200字。"""

SYSTEM_CONVERGE = """你已看到对方的质疑。请基于以下信息给出你的最终判断：
1. 你原本的分析
2. 对方的质疑
现在修正你的结论，或者坚持并解释为什么对方的质疑不成立。
用中文给出最终判断，包含：方向、置信度(1-5星)、核心依据。不超过200字。"""


def _build_analysis_prompt(market_data: dict, score: dict,
                           history_context: str = "") -> str:
    """构建分析prompt"""
    prompt = f"""## 市场数据 ({date.today().isoformat()})

| 指标 | 当前值 | 方向 |
|------|--------|------|
| 国际金价 | ${market_data.get('xau_usd', 'N/A')}/oz | - |
| 国内金价 | ¥{market_data.get('au9999', 'N/A')}/g | - |
| USD/CNY | {market_data.get('usd_cny', 'N/A')} | - |
| 上海溢价 | ¥{market_data.get('premium', 'N/A')}/g | - |
| 10Y TIPS | {market_data.get('tips_10y', 'N/A')}% | - |
| 美元指数 | {market_data.get('dxy', 'N/A')} | - |
| SPDR持仓 | {market_data.get('spdr_tonnes', 'N/A')}吨 | - |
| COMEX净多头 | {market_data.get('cot_net_long', 'N/A')}合约 | - |
| VIX | {market_data.get('vix', 'N/A')} | - |

## 规则引擎参考
- 综合评分: {score['total_score']}/100
- 信号: {score['signal']}
- 置信度: {score['confidence']}

## 各指标评分
{json.dumps(score['indicator_scores'], ensure_ascii=False)}
"""
    if history_context:
        prompt += f"\n## 近期预测回顾\n{history_context}\n"

    prompt += """
请回答：
1. 明日金价方向（涨↑/跌↓/平→）及核心判断依据
2. 最大的利多因素（一个）和最大的利空因素（一个）
3. 置信度（1-5星），以及什么情况会证明你判断错误
"""
    return prompt


def _build_challenge_prompt(opponent_analysis: str, market_summary: str) -> str:
    return f"""## 市场概况
{market_summary}

## 对方分析
{opponent_analysis}

请审视对方分析：有逻辑漏洞吗？忽略了什么风险？过于自信吗？"""


def _build_converge_prompt(my_original: str, opponent_challenge: str,
                           market_summary: str) -> str:
    return f"""## 市场概况
{market_summary}

## 你的原始分析
{my_original}

## 对方的质疑
{opponent_challenge}

在对方质疑的基础上修正你的结论。如果同意质疑，修改判断；如果不同意，解释原因。"""


def _market_summary(market_data: dict) -> str:
    return f"金价${market_data.get('xau_usd','N/A')}, TIPS {market_data.get('tips_10y','N/A')}%, DXY {market_data.get('dxy','N/A')}"


async def run_debate(market_data: dict, score: dict,
                     history_context: str = "") -> dict:
    """执行三阶段双LLM辩论。

    Returns:
        dict: {consensus, direction, confidence, debate_transcript}
    """
    analysis_prompt = _build_analysis_prompt(market_data, score, history_context)

    # === 阶段一：独立分析（并行） ===
    logger.info("Debate phase 1: independent analysis")
    ds_analysis, oai_analysis = await asyncio.gather(
        ds_chat([{"role": "system", "content": SYSTEM_ANALYST},
                 {"role": "user", "content": analysis_prompt}]),
        oai_chat([{"role": "system", "content": SYSTEM_ANALYST},
                  {"role": "user", "content": analysis_prompt}]),
    )

    # === 阶段二：交叉质疑（串行） ===
    logger.info("Debate phase 2: cross-challenge")
    market_sum = _market_summary(market_data)
    ds_challenge = await ds_chat([
        {"role": "system", "content": SYSTEM_CHALLENGER},
        {"role": "user", "content": _build_challenge_prompt(oai_analysis, market_sum)},
    ])
    oai_challenge = await oai_chat([
        {"role": "system", "content": SYSTEM_CHALLENGER},
        {"role": "user", "content": _build_challenge_prompt(ds_analysis, market_sum)},
    ])

    # === 阶段三：修正收敛（并行） ===
    logger.info("Debate phase 3: converge")
    ds_final, oai_final = await asyncio.gather(
        ds_chat([{"role": "system", "content": SYSTEM_CONVERGE},
                 {"role": "user", "content": _build_converge_prompt(ds_analysis, oai_challenge, market_sum)}]),
        oai_chat([{"role": "system", "content": SYSTEM_CONVERGE},
                  {"role": "user", "content": _build_converge_prompt(oai_analysis, ds_challenge, market_sum)}]),
    )

    # === 裁决合并 ===
    consensus = _merge_conclusions(ds_final, oai_final)
    direction = _extract_direction(consensus)

    return {
        "consensus": consensus,
        "direction": direction,
        "confidence": score["confidence"],
        "debate_transcript": {
            "deepseek_analysis": ds_analysis,
            "openai_analysis": oai_analysis,
            "deepseek_challenge": ds_challenge,
            "openai_challenge": oai_challenge,
            "deepseek_final": ds_final,
            "openai_final": oai_final,
        },
    }


def _merge_conclusions(ds_final: str, oai_final: str) -> str:
    """合并两个模型的最终结论"""
    return f"## DeepSeek 最终判断\n{ds_final}\n\n## OpenAI 最终判断\n{oai_final}"


def _extract_direction(consensus: str) -> str:
    """从结论文本中提取方向判断"""
    text = consensus.lower()
    up_signals = ["涨↑", "看多", "上涨", "bullish", "利多", "偏多"]
    down_signals = ["跌↓", "看空", "下跌", "bearish", "利空", "偏空"]

    up_count = sum(1 for s in up_signals if s in consensus)
    down_count = sum(1 for s in down_signals if s in consensus)

    if up_count > down_count:
        return "up"
    elif down_count > up_count:
        return "down"
    return "flat"
