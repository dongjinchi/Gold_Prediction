"""数据库查询接口"""
import sqlite3
import json
from datetime import date, datetime, timedelta
from config import DB_PATH
from db.models import get_connection


def insert_gold_price(data: dict) -> int:
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT OR REPLACE INTO gold_price (timestamp, xau_usd, au9999, usd_cny, premium)
           VALUES (?, ?, ?, ?, ?)""",
        (data["timestamp"], data["xau_usd"], data["au9999"],
         data["usd_cny"], data["premium"])
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def insert_macro(data: dict) -> int:
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT OR REPLACE INTO macro_indicators (date, tips_10y, dxy, spdr_tonnes, vix)
           VALUES (?, ?, ?, ?, ?)""",
        (data["date"], data["tips_10y"], data["dxy"],
         data["spdr_tonnes"], data["vix"])
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def update_macro_cot(report_date: str, net_long: int):
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE macro_indicators SET cot_net_long = ?
           WHERE date = (SELECT date FROM macro_indicators
                         WHERE date <= ? ORDER BY date DESC LIMIT 1)""",
        (net_long, report_date)
    )
    conn.commit()
    conn.close()


def insert_cb_event(event: dict) -> int:
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO cb_events (event_date, country, action, amount_tonnes, impact_score, source_url)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (event["event_date"], event.get("country", "CN"), event.get("action", "buy"),
         event.get("amount_tonnes"), event.get("impact_score", 15.0), event.get("source_url", ""))
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_latest_gold_price() -> dict | None:
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM gold_price ORDER BY timestamp DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_gold_price_history(period: str = "3m") -> list[dict]:
    """获取金价历史数据。

    Args:
        period: 1m, 3m, 1y, 3y, 5y
    """
    period_days = {
        "1m": 30, "3m": 90, "1y": 365,
        "3y": 1095, "5y": 1825,
    }
    days = period_days.get(period, 90)
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM gold_price WHERE timestamp >= ? ORDER BY timestamp ASC",
        (cutoff,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_macro() -> dict | None:
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM macro_indicators ORDER BY date DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_macro_history(days: int = 365) -> list[dict]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM macro_indicators WHERE date >= ? ORDER BY date ASC",
        (cutoff,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_cb_events(days: int = 30) -> list[dict]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM cb_events WHERE event_date >= ? ORDER BY event_date DESC",
        (cutoff,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_rule_score(data: dict) -> int:
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO rule_scores (calc_time, total_score, signal, confidence, indicator_scores, weights_used)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (data["calc_time"], data["total_score"], data["signal"],
         data["confidence"], json.dumps(data["indicator_scores"]),
         json.dumps(data["weights_used"]))
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_latest_score() -> dict | None:
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rule_scores ORDER BY calc_time DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["indicator_scores"] = json.loads(d["indicator_scores"])
        d["weights_used"] = json.loads(d["weights_used"])
        return d
    return None


def insert_prediction(data: dict) -> int:
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO prediction_log
           (pred_date, target_date, predicted_direction, predicted_change_pct,
            rule_score, llm_consensus, debate_transcript)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (data["pred_date"], data["target_date"], data["predicted_direction"],
         data.get("predicted_change_pct", 0), data["rule_score"],
         data["llm_consensus"], json.dumps(data.get("debate_transcript", {})))
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def backfill_prediction(pred_id: int, actual_change: float, is_correct: bool, error_reason: str = ""):
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE prediction_log
           SET actual_px_change = ?, is_correct = ?, error_reason = ?
           WHERE id = ?""",
        (actual_change, 1 if is_correct else 0, error_reason, pred_id)
    )
    conn.commit()
    conn.close()


def get_prediction_history(days: int = 90) -> list[dict]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT * FROM prediction_log
           WHERE pred_date >= ? AND actual_px_change IS NOT NULL
           ORDER BY pred_date DESC""",
        (cutoff,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_accuracy_stats() -> dict:
    """计算准确率统计"""
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()

    # 总准确率
    cursor.execute(
        "SELECT COUNT(*) as total, SUM(is_correct) as correct FROM prediction_log WHERE is_correct IS NOT NULL"
    )
    row = cursor.fetchone()
    total = row["total"] or 0
    correct = row["correct"] or 0

    # 滚动30日准确率
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    cursor.execute(
        "SELECT COUNT(*) as total, SUM(is_correct) as correct FROM prediction_log WHERE pred_date >= ? AND is_correct IS NOT NULL",
        (cutoff,)
    )
    row30 = cursor.fetchone()
    total30 = row30["total"] or 0
    correct30 = row30["correct"] or 0

    conn.close()

    return {
        "total_count": total,
        "correct_count": correct,
        "total_accuracy": round(correct / total, 3) if total > 0 else 0,
        "rolling_30d_count": total30,
        "rolling_30d_correct": correct30,
        "rolling_30d_accuracy": round(correct30 / total30, 3) if total30 > 0 else 0,
    }
