"""API路由处理函数"""
import json
import asyncio
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Query, Request
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
        prem = gold.get("premium") if gold else None
        score = calculate_score(macro, cb_events, price_hist, macro_hist, current_premium=prem)

    return {
        "updated_at": datetime.now().isoformat(),
        "prices": gold,
        "macro": macro,
        "score": score,
        "cb_events": cb_events,
    }


@router.get("/api/price-history")
def price_history(type: str = Query("daily", regex="^(intraday|5day|daily)$")):
    """金价数据，支持三种视图模式。

    - intraday: 今日分钟级 SGE Au99.99 实时数据 + 当前 XAU
    - 5day: 最近5天逐小时数据
    - daily: 全部日线 OHLC 数据
    """
    if type == "intraday":
        return {"type": type, "data": _get_intraday_data()}
    elif type == "5day":
        return {"type": type, "data": get_gold_price_history("1m", daily_only=True)}
    else:
        return {"type": type, "data": get_gold_price_history("5y")}


def _get_intraday_data() -> list[dict]:
    """获取今日分钟级AU9999数据 + 当前XAU"""
    try:
        import akshare as ak
        sge = ak.spot_quotations_sge(symbol="Au99.99")
        if sge is None or sge.empty:
            return []

        xau_usd = None
        try:
            xau_df = ak.futures_foreign_commodity_realtime(symbol=["XAU"])
            if xau_df is not None and not xau_df.empty:
                xau_usd = round(float(xau_df.iloc[0, 1]), 2)
        except Exception:
            pass

        records = []
        for _, row in sge.iterrows():
            t = str(row.iloc[1])  # time column (HH:MM:SS)
            price = float(row.iloc[2])  # current price
            records.append({
                "time": t,
                "au9999": price,
                "xau_usd": xau_usd,  # 当前XAU作为参考线
            })

        return records
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception(f"Intraday fetch failed: {e}")
        return []


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
                                     get_macro_history(90),
                                     current_premium=get_latest_gold_price().get("premium") if get_latest_gold_price() else None)
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


@router.get("/api/analysis")
async def analysis(request: Request, type: str = Query("daily", regex="^(daily|weekly)$")):
    """触发AI研判（SSE流式返回）。type=daily(明日) / weekly(一周趋势)。含心跳+断连检测。"""
    gold = get_latest_gold_price()
    macro = get_latest_macro()
    cb_events = get_recent_cb_events(30)

    if macro is None:
        # 尝试立刻获取宏观数据
        from db.queries import insert_macro
        from fetchers.macro import fetch_all_macro
        macro_data = fetch_all_macro()
        if macro_data:
            insert_macro(macro_data)
            macro = macro_data
        else:
            # SSE 格式错误事件，不是 JSON
            async def _err_stream():
                yield "event: error\\ndata: {\\\"message\\\": \\\"暂无宏观数据，请稍后重试\\\"}\\n\\n"
            return StreamingResponse(_err_stream(), media_type="text/event-stream")

    # 计算评分
    score_result = calculate_score(macro, cb_events,
                                   get_gold_price_history("3m"),
                                   get_macro_history(90),
                                   current_premium=gold.get("premium") if gold else None)
    insert_rule_score(score_result)

    # 获取历史预测context（含数值详情，供AI学习）
    stats = get_accuracy_stats()
    history_context = f"历史总准确率: {stats['total_accuracy']:.0%} ({stats['correct_count']}/{stats['total_count']}), 近30日: {stats['rolling_30d_accuracy']:.0%}"

    # 附上最近5次已验证预测的详细结果
    recent = get_prediction_history(30)
    if recent:
        history_context += "\n\n## 最近已验证预测记录（供校准参考）:\n"
        for r in recent[:5]:
            direction_label = {"up": "涨↑", "down": "跌↓", "flat": "平→"}.get(r["predicted_direction"], r["predicted_direction"])
            actual_str = f"{r['actual_px_change']:+.2f}%" if r.get("actual_px_change") is not None else "待验证"
            status = "✓" if r.get("is_correct") == 1 else "✗" if r.get("is_correct") == 0 else "?"
            history_context += (
                f"- {r['pred_date']}: 预测{direction_label}, 实际{actual_str} {status}"
            )
            if r.get("error_reason"):
                history_context += f" — {r['error_reason']}"
            history_context += "\n"

    # 合并market_data
    market_data = {**(gold or {}), **(macro or {})}

    async def event_stream():
        total_score = score_result["total_score"]
        signal = score_result["signal"]

        async def heartbeat():
            """每 10 秒发一次心跳，检测客户端是否断开"""
            while True:
                await asyncio.sleep(10)
                if await request.is_disconnected():
                    return
                yield f": heartbeat\n\n"

        # 阶段一：评分完成
        yield f"event: status\ndata: {json.dumps({'phase': 'scoring', 'message': f'规则引擎: {total_score}分 {signal}', 'score': score_result}, ensure_ascii=False)}\n\n"

        # 阶段二：辩论（并行跑辩论+心跳）
        yield f"event: status\ndata: {json.dumps({'phase': 'analysis', 'message': 'DeepSeek + OpenAI 独立分析中...'}, ensure_ascii=False)}\n\n"

        debate_task = asyncio.create_task(run_debate(market_data, score_result, history_context, mode=type))
        hb_gen = heartbeat()
        while not debate_task.done():
            try:
                hb_data = await asyncio.wait_for(hb_gen.__anext__(), timeout=1.0)
            except (asyncio.TimeoutError, StopAsyncIteration):
                break
            if hb_data:
                yield hb_data

        try:
            result = await debate_task
        except Exception as e:
            yield f"event: status\ndata: {json.dumps({'phase': 'error', 'message': f'辩论异常: {str(e)}'}, ensure_ascii=False)}\n\n"
            return

        # 流式推送辩论过程（两轮）
        transcript = result["debate_transcript"]
        yield f"event: partial\ndata: {json.dumps({'model': 'deepseek', 'content': transcript['deepseek_analysis'][:200]}, ensure_ascii=False)}\n\n"
        yield f"event: partial\ndata: {json.dumps({'model': 'openai', 'content': transcript['openai_analysis'][:200]}, ensure_ascii=False)}\n\n"
        yield f"event: status\ndata: {json.dumps({'phase': 'debate_r1', 'message': '第1轮交叉辩论...'}, ensure_ascii=False)}\n\n"
        yield f"event: partial\ndata: {json.dumps({'model': 'deepseek', 'content': transcript['deepseek_challenge_r1'][:150]}, ensure_ascii=False)}\n\n"
        yield f"event: partial\ndata: {json.dumps({'model': 'openai', 'content': transcript['openai_challenge_r1'][:150]}, ensure_ascii=False)}\n\n"
        yield f"event: status\ndata: {json.dumps({'phase': 'debate_r2', 'message': '第2轮深入辩论...'}, ensure_ascii=False)}\n\n"
        yield f"event: partial\ndata: {json.dumps({'model': 'deepseek', 'content': transcript['deepseek_challenge_r2'][:150]}, ensure_ascii=False)}\n\n"
        yield f"event: partial\ndata: {json.dumps({'model': 'openai', 'content': transcript['openai_challenge_r2'][:150]}, ensure_ascii=False)}\n\n"
        yield f"event: status\ndata: {json.dumps({'phase': 'converge', 'message': '两轮辩论完成，生成最终结论'}, ensure_ascii=False)}\n\n"

        consensus = result["consensus"]
        direction = result["direction"]
        position = result.get("position", "hold")
        weekly = result.get("weekly_direction", "flat")
        confidence = result["confidence"]
        yield f"event: result\ndata: {json.dumps({'consensus': consensus, 'direction': direction, 'weekly_direction': weekly, 'position': position, 'confidence': confidence, 'score': total_score}, ensure_ascii=False)}\n\n"

        # 保存预测记录
        insert_prediction({
            "pred_date": date.today().isoformat(),
            "target_date": (date.today() + timedelta(days=1)).isoformat(),
            "predicted_direction": direction,
            "predicted_change_pct": 0,
            "rule_score": total_score,
            "llm_consensus": consensus,
            "debate_transcript": transcript,
        })

    return StreamingResponse(event_stream(), media_type="text/event-stream")
