"""三阶段双LLM辩论编排器"""
import json
import asyncio
import logging
from datetime import date

from llm.deepseek import chat as ds_chat
from llm.openai_client import chat as oai_chat

logger = logging.getLogger(__name__)

SYSTEM_ANALYST_DAILY = """你是一位资深黄金短线交易分析师。
基于市场数据，给出明日交易预判。必须包含：
1. 明日涨跌：涨↑/跌↓/平→，预测价格区间($)，引用关键数据
2. 持仓建议：🟢加仓/🔵持有/🟡减仓/🔴清仓，说明理由
3. 风险提示：可能推翻判断的条件
用中文，简洁，150字以内。"""

SYSTEM_ANALYST_WEEKLY = """你是一位黄金周度策略分析师。你的任务是预判未来5个交易日的走势。
重要：不要回答明日涨跌（已另行分析），只聚焦一周维度。
基于以下逻辑分析：
- 当前趋势的持续性（技术面+资金面能否延续）
- 本周有无关键事件（美联储讲话/数据发布/央行购金窗口）
- 持仓拥挤度是否暗示反转

必须包含：
1. 本周趋势：涨↑/跌↓/先涨后跌/先跌后涨/震荡→，预测周度价格区间($)
2. 核心逻辑：驱动本周走势的1个最关键因素
3. 操作节奏：周初还是周末更适合操作

用中文，简洁，120字以内。"""

SYSTEM_CHALLENGER = """你是黄金市场分析师，审查另一位分析师对明日+1周的判断。
找出对方在短期和中期维度上的逻辑漏洞、被忽略的风险因素、或过于自信的结论。
对事不对人，用中文回答，简洁直接，不超过150字。"""

SYSTEM_CHALLENGER_R2 = """你已看到对方的回应。进行第二轮深入辩论：
1. 对方是否回避了核心质疑？
2. 对方的论据你是否认可？
3. 你的立场是否需要调整？
用中文回答，100字以内。"""

SYSTEM_CONVERGE = """基于双方辩论，给出最终统一判断。用中文，不超过150字。"""


def _build_analysis_prompt(market_data: dict, score: dict,
                           history_context: str = "", mode: str = "daily") -> str:
    """构建分析prompt。mode: daily/weekly"""
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

    if mode == "daily":
        prompt += """
请回答：
1. 明日涨跌：涨↑/跌↓/平→，预测区间($)，核心依据
2. 持仓建议：🟢加仓/🔵持有/🟡减仓/🔴清仓，理由
3. 置信度：1-5星，反转条件
"""
    else:
        prompt += """
注意：不要回答明日涨跌。只分析未来一周（5个交易日）：
1. 本周趋势：涨/跌/震荡（给出周度区间），核心驱动
2. 本周关键事件或变量
3. 周初vs周末操作建议
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
                     history_context: str = "", mode: str = "daily") -> dict:
    """执行双LLM辩论。

    Args:
        mode: "daily" (明日短线) 或 "weekly" (一周趋势)

    Returns:
        dict: {consensus, direction, weekly_direction, confidence, debate_transcript}
    """
    system = SYSTEM_ANALYST_DAILY if mode == "daily" else SYSTEM_ANALYST_WEEKLY
    analysis_prompt = _build_analysis_prompt(market_data, score, history_context, mode)

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
    weekly_dir = _extract_weekly(consensus)

    return {
        "consensus": consensus,
        "direction": direction,
        "weekly_direction": weekly_dir,
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


def _extract_weekly(consensus: str) -> str:
    """从结论文本中提取一周趋势"""
    # 在一周趋势附近查找涨/跌/震荡
    if "一周" in consensus or "周度" in consensus or "5日" in consensus:
        if "涨" in consensus:
            return "up"
        elif "跌" in consensus:
            return "down"
    return "flat"
