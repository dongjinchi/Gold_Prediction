"""六维指标加权评分引擎"""
import logging
from datetime import datetime
from engine.weights import get_weights

logger = logging.getLogger(__name__)


def _score_tips(tips_10y: float, tips_20d_avg: float | None) -> tuple[int, float]:
    """TIPS收益率评分。下降→利多黄金。

    Returns: (分数, 方向: 1=利多, -1=利空, 0=中性)
    """
    if tips_20d_avg is None:
        return 0, 0
    delta = tips_10y - tips_20d_avg
    if delta < -0.5:
        return 20, 1
    elif delta < -0.2:
        return 10, 1
    elif delta > 0.5:
        return -20, -1
    elif delta > 0.2:
        return -10, -1
    else:
        return 0, 0


def _score_dxy(dxy: float, dxy_20d_avg: float | None) -> tuple[int, float]:
    """美元指数评分。下降→利多黄金。"""
    if dxy_20d_avg is None:
        return 0, 0
    delta = dxy - dxy_20d_avg
    if delta < -1.5:
        return 15, 1
    elif delta < -0.5:
        return 8, 1
    elif delta > 1.5:
        return -15, -1
    elif delta > 0.5:
        return -8, -1
    else:
        return 0, 0


def _score_spdr(current: float, avg_5d: float | None) -> tuple[int, float]:
    """SPDR持仓变化评分。增持→利多。"""
    if avg_5d is None:
        return 0, 0
    delta = current - avg_5d
    if delta > 5:
        return 12, 1
    elif delta > 1:
        return 6, 1
    elif delta < -5:
        return -12, -1
    elif delta < -1:
        return -6, -1
    else:
        return 0, 0


def _score_cot(net_long_percentile: float | None) -> tuple[int, float]:
    """COMEX持仓评分。极端高位→回调风险（逆向信号）。"""
    if net_long_percentile is None:
        return 0, 0
    if net_long_percentile < 30:
        return 12, 1
    elif net_long_percentile > 80:
        return -12, -1
    else:
        return 0, 0


def _score_premium(premium: float, premium_mean: float | None, premium_std: float | None) -> tuple[int, float]:
    """上海溢价评分。溢价高于均值+1σ→国内需求旺盛→利多。"""
    if premium_mean is None or premium_std is None or premium_std == 0:
        return 0, 0
    z_score = (premium - premium_mean) / premium_std
    if z_score > 1.0:
        return 10, 1
    elif z_score < -1.0:
        return -10, -1
    else:
        return 0, 0


def _score_cb_event(cb_decay_weight: float, cb_action: str) -> tuple[int, float]:
    """央行购金事件评分。买入事件→脉冲式利多，按衰减权重计分。"""
    if cb_decay_weight <= 0:
        return 0, 0
    base_score = 20
    score = base_score * cb_decay_weight
    if cb_action == "buy":
        return int(score), 1
    elif cb_action == "sell":
        return -int(score), -1
    return 0, 0


def _calc_cb_decay_weight(event_date_str: str) -> float:
    """计算央行购金事件衰减权重。

    decay = 0.5^(days_elapsed / 2), days_elapsed=0时权重=1.0
    """
    try:
        event_date = datetime.strptime(event_date_str, "%Y-%m-%d")
        days_elapsed = (datetime.now() - event_date).days
        if days_elapsed < 0:
            return 1.0
        return max(0, 0.5 ** (days_elapsed / 2))
    except Exception:
        return 0.0


def calculate_score(macro_data: dict, cb_events: list[dict],
                    price_history: list[dict] | None = None,
                    macro_history: list[dict] | None = None) -> dict:
    """计算综合评分。

    Args:
        macro_data: 最新宏观指标 (from get_latest_macro)
        cb_events: 近期央行购金事件列表
        price_history: 历史金价 (用于计算溢价均值和标准差)
        macro_history: 历史宏观指标 (用于计算20日均值)

    Returns:
        dict: {total_score, signal, confidence, indicator_scores, weights_used}
    """
    weights = get_weights()

    # 从历史数据计算参考值
    tips_20d_avg = None
    dxy_20d_avg = None
    spdr_5d_avg = None
    premium_mean = None
    premium_std = None

    if macro_history and len(macro_history) >= 20:
        tips_vals = [r["tips_10y"] for r in macro_history[-20:] if r["tips_10y"] is not None]
        dxy_vals = [r["dxy"] for r in macro_history[-20:] if r["dxy"] is not None]
        if tips_vals:
            tips_20d_avg = sum(tips_vals) / len(tips_vals)
        if dxy_vals:
            dxy_20d_avg = sum(dxy_vals) / len(dxy_vals)

    if macro_history and len(macro_history) >= 5:
        spdr_vals = [r["spdr_tonnes"] for r in macro_history[-5:] if r["spdr_tonnes"] is not None]
        if spdr_vals:
            spdr_5d_avg = sum(spdr_vals) / len(spdr_vals)

    if price_history and len(price_history) >= 20:
        premiums = [r["premium"] for r in price_history[-20:] if r.get("premium") is not None]
        if premiums:
            premium_mean = sum(premiums) / len(premiums)
            variance = sum((p - premium_mean) ** 2 for p in premiums) / len(premiums)
            premium_std = variance ** 0.5

    # COT分位数：简化处理，从macro_history中计算
    cot_percentile = None
    if macro_data and macro_data.get("cot_net_long") is not None:
        if macro_history:
            cot_vals = sorted([r["cot_net_long"] for r in macro_history
                               if r.get("cot_net_long") is not None])
            if cot_vals:
                rank = sum(1 for v in cot_vals if v <= macro_data["cot_net_long"])
                cot_percentile = (rank / len(cot_vals)) * 100

    # 央行事件衰减权重
    cb_decay = 0.0
    cb_action = "buy"
    if cb_events:
        latest_cb = max(cb_events, key=lambda e: e["event_date"])
        cb_decay = _calc_cb_decay_weight(latest_cb["event_date"])
        cb_action = latest_cb.get("action", "buy")

    # 逐项评分
    tips_score, tips_dir = _score_tips(
        macro_data.get("tips_10y") or 0, tips_20d_avg)
    dxy_score, dxy_dir = _score_dxy(
        macro_data.get("dxy") or 100, dxy_20d_avg)
    spdr_score, spdr_dir = _score_spdr(
        macro_data.get("spdr_tonnes") or 800, spdr_5d_avg)
    cot_score, cot_dir = _score_cot(cot_percentile)
    premium_score, premium_dir = _score_premium(
        macro_data.get("premium") or 0, premium_mean, premium_std)
    cb_score, cb_dir = _score_cb_event(cb_decay, cb_action)

    indicator_scores = {
        "tips_10y": tips_score,
        "dxy": dxy_score,
        "spdr": spdr_score,
        "cot": cot_score,
        "premium": premium_score,
        "cb_event": cb_score,
    }

    directions = {
        "tips_10y": tips_dir,
        "dxy": dxy_dir,
        "spdr": spdr_dir,
        "cot": cot_dir,
        "premium": premium_dir,
        "cb_event": cb_dir,
    }

    # 加权计算总分
    total = 0
    for key, score in indicator_scores.items():
        if key == "cb_event":
            w_cb = weights.get("premium", 0.17)
            total += score * (cb_decay * w_cb * 5)
        else:
            total += score * weights.get(key, 0.15)

    # 归一化到0-100
    total = max(0, min(100, total + 50))

    # 信号判断
    if total >= 80:
        signal = "极度看多"
    elif total >= 60:
        signal = "偏多"
    elif total >= 40:
        signal = "中性"
    elif total >= 20:
        signal = "偏空"
    else:
        signal = "极度看空"

    # 置信度(方向一致性)
    dirs = [v for v in directions.values() if v != 0]
    if dirs:
        max_dir_count = max(dirs.count(1), dirs.count(-1))
        confidence = round(max_dir_count / len(dirs), 2)
    else:
        confidence = 0.5

    return {
        "calc_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_score": int(total),
        "signal": signal,
        "confidence": confidence,
        "indicator_scores": indicator_scores,
        "weights_used": weights,
    }
