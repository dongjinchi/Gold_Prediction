"""三阶段双LLM辩论编排器"""
import json
import asyncio
import logging
from datetime import date

from llm.deepseek import chat as ds_chat
from llm.openai_client import chat as oai_chat

logger = logging.getLogger(__name__)

SYSTEM_ANALYST = """你是一位资深黄金短线交易分析师，拥有20年全球宏观交易经验。
请基于提供的市场数据进行短线研判（持有期1-2天）。你的回答必须包含：

1. **明日涨跌判断**：明确给出涨↑/跌↓/平→，并引用2-3个关键数据支撑
2. **明日价格区间**：给出具体的预测价格区间（美元/盎司）
3. **持仓建议**：从以下选择一项——🟢买入/加仓 | 🔵持有/观望 | 🟡轻仓/减仓 | 🔴卖出/清仓，并说明理由
4. **风险提示**：指出可能推翻你判断的条件

用中文回答，专业但简洁，控制在200字以内。"""

SYSTEM_CHALLENGER = """你是黄金市场分析师，你的任务是审查另一位分析师的判断。
找出对方逻辑中的漏洞、被忽略的风险因素、或过于自信的结论。
如果你的判断和对方一致，也要指出即使是正确的方向也存在什么风险。
对事不对人，保持专业。用中文回答，简洁直接，不超过150字。"""

SYSTEM_CHALLENGER_R2 = """你已看到对方对你第一轮质疑的回应。现在进行第二轮深入辩论：
1. 对方是否回避了你的核心质疑？如果有，指出来
2. 对方提出的新论据你是否认可？为什么
3. 你现在是否调整自己的立场？如果调整，说明原因
用中文回答，100字以内。"""

SYSTEM_CONVERGE = """你已看到对方的质疑。请基于以下信息给出最终统一判断：
1. 你原本的分析
2. 对方的质疑

现在整合双方观点，给出一个综合结论。必须包含：
- 明日涨跌方向 + 预测价格区间
- 统一持仓建议（🟢买入/🔵持有/🟡减仓/🔴清仓）
- 综合置信度和核心依据
用中文，不超过150字。如果双方分歧大，注明分歧点。"""


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
请回答（每条不超过1行）：
1. 明日涨跌：涨↑ / 跌↓ / 平→（给出具体预测区间，如 $3980-$4010）
2. 持仓建议：🟢买入 / 🔵持有 / 🟡减仓 / 🔴清仓（附一句话理由）
3. 置信度：1-5星，什么情况下判断会错
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

    # === 阶段二：第一轮交叉质疑（串行） ===
    logger.info("Debate phase 2: cross-challenge round 1")
    market_sum = _market_summary(market_data)
    ds_r1 = await ds_chat([
        {"role": "system", "content": SYSTEM_CHALLENGER},
        {"role": "user", "content": _build_challenge_prompt(oai_analysis, market_sum)},
    ])
    oai_r1 = await oai_chat([
        {"role": "system", "content": SYSTEM_CHALLENGER},
        {"role": "user", "content": _build_challenge_prompt(ds_analysis, market_sum)},
    ])

    # === 阶段三：第二轮深入质疑（串行） ===
    logger.info("Debate phase 3: cross-challenge round 2")
    r2_prompt = f"## 对方第一轮质疑\n{ds_r1}\n\n请审视：对方是否回避了核心问题？你的立场是否需要调整？"
    ds_r2 = await ds_chat([
        {"role": "system", "content": SYSTEM_CHALLENGER_R2},
        {"role": "user", "content": r2_prompt},
    ])
    r2_oai_prompt = f"## 对方第一轮质疑\n{oai_r1}\n\n请审视：对方是否回避了核心问题？你的立场是否需要调整？"
    oai_r2 = await oai_chat([
        {"role": "system", "content": SYSTEM_CHALLENGER_R2},
        {"role": "user", "content": r2_oai_prompt},
    ])

    # === 阶段四：修正收敛（并行） ===
    logger.info("Debate phase 4: converge")
    ds_final, oai_final = await asyncio.gather(
        ds_chat([{"role": "system", "content": SYSTEM_CONVERGE},
                 {"role": "user", "content": _build_converge_prompt(ds_analysis, oai_r2, market_sum)}]),
        oai_chat([{"role": "system", "content": SYSTEM_CONVERGE},
                  {"role": "user", "content": _build_converge_prompt(oai_analysis, ds_r2, market_sum)}]),
    )

    # === 裁决合并 ===
    consensus = _merge_conclusions(ds_final, oai_final)
    direction = _extract_direction(consensus)
    position = _extract_position(consensus)

    return {
        "consensus": consensus,
        "direction": direction,
        "position": position,
        "confidence": score["confidence"],
        "debate_transcript": {
            "deepseek_analysis": ds_analysis,
            "openai_analysis": oai_analysis,
            "deepseek_challenge_r1": ds_r1,
            "openai_challenge_r1": oai_r1,
            "deepseek_challenge_r2": ds_r2,
            "openai_challenge_r2": oai_r2,
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
    if up_count > down_count: return "up"
    elif down_count > up_count: return "down"
    return "flat"


def _extract_position(consensus: str) -> str:
    """从结论文本中提取持仓建议"""
    if "买入" in consensus or "加仓" in consensus:
        return "buy"
    elif "清仓" in consensus or "卖出" in consensus:
        return "sell"
    elif "减仓" in consensus or "轻仓" in consensus:
        return "reduce"
    return "hold"
