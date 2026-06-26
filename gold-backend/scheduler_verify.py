"""每日预测验证：T+1回填实际涨跌。存储详细数值供AI学习。"""
import logging
from datetime import date, timedelta
from config import DB_PATH
from db.queries import get_prediction_history, backfill_prediction, get_gold_price_history

logger = logging.getLogger(__name__)


def verify_yesterday_predictions():
    """回填昨日预测的实际结果，包括涨跌方向+幅度+误差分析"""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    predictions = get_prediction_history(2, include_unverified=True)

    price_history = get_gold_price_history("1m")
    if not price_history or len(price_history) < 2:
        logger.warning("Not enough price data for verification")
        return

    # 按日期索引金价
    prices_by_date = {}
    for p in price_history:
        d = p["timestamp"][:10] if isinstance(p["timestamp"], str) else str(p["timestamp"])[:10]
        if d not in prices_by_date:
            prices_by_date[d] = p

    for pred in predictions:
        if pred.get("actual_px_change") is not None:
            continue

        target = pred["target_date"]
        pred_date = pred["pred_date"]
        today_price = prices_by_date.get(target)
        yesterday_price = prices_by_date.get(pred_date)

        if today_price and yesterday_price:
            actual_change = round(
                (today_price["au9999"] - yesterday_price["au9999"]) / yesterday_price["au9999"] * 100, 2
            )
            predicted_dir = pred["predicted_direction"]

            # 方向判断
            dir_match = (predicted_dir == "up" and actual_change > 0) or \
                        (predicted_dir == "down" and actual_change < 0)

            # 构建详细的错误分析（含具体数值，供AI学习）
            if dir_match:
                is_correct = True
                error_reason = f"✓ 预测{predicted_dir}正确, 实际{actual_change:+.2f}%, 幅度{abs(actual_change):.2f}%"
            else:
                is_correct = False
                error_reason = (
                    f"✗ 预测方向'{predicted_dir}', 实际金价变化{actual_change:+.2f}%, "
                    f"方向相反, 误差幅度{abs(actual_change):.2f}%"
                )

            backfill_prediction(pred["id"], actual_change, is_correct, error_reason)
            logger.info(f"Verified pred#{pred['id']}: {'✓' if is_correct else '✗'} {error_reason}")
