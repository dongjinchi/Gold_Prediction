"""API路由处理函数"""
import json
import asyncio
from datetime import date, datetime
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from config import DB_PATH
from db.queries import (
    get_latest_gold_price, get_gold_price_history,
    get_latest_macro, get_macro_history,
    get_recent_cb_events, get_latest_score,
    insert_rule_score, insert_prediction,
    get_prediction_history, get_accuracy_stats,
)
from engine.scorer import calculate_score
from llm.debate import run_debate

router = APIRouter()


@router.get("/api/dashboard")
def dashboard():
    """首页数据快照"""
    gold = get_latest_gold_price()
    macro = get_latest_macro()
    cb_events = get_recent_cb_events(30)
    score = get_latest_score()

    # 如果没有评分记录，实时计算
    if score is None and macro is not None:
        price_hist = get_gold_price_history("3m")
        macro_hist = get_macro_history(90)
        score = calculate_score(macro, cb_events, price_hist, macro_hist)

    return {
        "updated_at": datetime.now().isoformat(),
        "prices": gold,
        "macro": macro,
        "score": score,
        "cb_events": cb_events,
    }


@router.get("/api/price-history")
def price_history(period: str = Query("3m", regex="^(1m|3m|1y|3y|5y)$")):
    """金价历史数据"""
    return {
        "period": period,
        "data": get_gold_price_history(period),
    }


@router.get("/api/indicators")
def indicators():
    """宏观指标数据"""
    macro = get_latest_macro()
    history = get_macro_history(365)
    return {
        "latest": macro,
        "history": history,
    }


@router.get("/api/score")
def score():
    """最新规则打分"""
    result = get_latest_score()
    if result is None:
        # 实时计算
        macro = get_latest_macro()
        cb_events = get_recent_cb_events(30)
        if macro:
            result = calculate_score(macro, cb_events,
                                     get_gold_price_history("3m"),
                                     get_macro_history(90))
    return result


@router.get("/api/history/predictions")
def history_predictions(days: int = Query(90, ge=7, le=730)):
    """历史预测及准确率"""
    predictions = get_prediction_history(days)
    stats = get_accuracy_stats()
    return {
        "records": predictions,
        **stats,
    }


@router.post("/api/analysis")
async def analysis():
    """触发AI研判（SSE流式返回）"""
    gold = get_latest_gold_price()
    macro = get_latest_macro()
    cb_events = get_recent_cb_events(30)

    if macro is None:
        return {"error": "No macro data available. Run data fetcher first."}

    # 计算评分
    score_result = calculate_score(macro, cb_events,
                                   get_gold_price_history("3m"),
                                   get_macro_history(90))
    insert_rule_score(score_result)

    # 获取历史预测context
    stats = get_accuracy_stats()
    history_context = f"历史总准确率: {stats['total_accuracy']:.0%}, 近30日: {stats['rolling_30d_accuracy']:.0%}"

    # 合并market_data
    market_data = {**(gold or {}), **(macro or {})}

    async def event_stream():
        total_score = score_result["total_score"]
        signal = score_result["signal"]
        # 阶段一：评分完成
        yield f"event: status\ndata: {json.dumps({'phase': 'scoring', 'message': f'规则引擎: {total_score}分 {signal}', 'score': score_result}, ensure_ascii=False)}\n\n"

        # 阶段二：辩论
        yield f"event: status\ndata: {json.dumps({'phase': 'analysis', 'message': 'DeepSeek + OpenAI 独立分析中...'}, ensure_ascii=False)}\n\n"

        result = await run_debate(market_data, score_result, history_context)

        # 阶段三：结论
        transcript = result["debate_transcript"]
        ds_analysis = transcript["deepseek_analysis"][:200]
        oai_analysis = transcript["openai_analysis"][:200]
        ds_challenge = transcript["deepseek_challenge"][:150]
        oai_challenge = transcript["openai_challenge"][:150]
        yield f"event: partial\ndata: {json.dumps({'model': 'deepseek', 'content': ds_analysis}, ensure_ascii=False)}\n\n"
        yield f"event: partial\ndata: {json.dumps({'model': 'openai', 'content': oai_analysis}, ensure_ascii=False)}\n\n"
        yield f"event: status\ndata: {json.dumps({'phase': 'debate', 'message': '交叉辩论中...'}, ensure_ascii=False)}\n\n"
        yield f"event: partial\ndata: {json.dumps({'model': 'deepseek', 'content': ds_challenge}, ensure_ascii=False)}\n\n"
        yield f"event: partial\ndata: {json.dumps({'model': 'openai', 'content': oai_challenge}, ensure_ascii=False)}\n\n"
        yield f"event: status\ndata: {json.dumps({'phase': 'converge', 'message': '收敛一致，生成最终结论'}, ensure_ascii=False)}\n\n"

        consensus = result["consensus"]
        direction = result["direction"]
        confidence = result["confidence"]
        yield f"event: result\ndata: {json.dumps({'consensus': consensus, 'direction': direction, 'confidence': confidence, 'score': total_score}, ensure_ascii=False)}\n\n"

        # 保存预测记录
        insert_prediction({
            "pred_date": date.today().isoformat(),
            "target_date": date.today().isoformat(),
            "predicted_direction": direction,
            "predicted_change_pct": 0,
            "rule_score": total_score,
            "llm_consensus": consensus,
            "debate_transcript": transcript,
        })

    return StreamingResponse(event_stream(), media_type="text/event-stream")
