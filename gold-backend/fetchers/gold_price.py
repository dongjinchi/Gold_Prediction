"""金价与汇率数据采集。主源: akshare (历史+实时)。"""
from datetime import datetime, timedelta
import akshare as ak
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def _calculate_premium(au9999: float, xau_usd: float, usd_cny: float) -> float:
    theoretical = xau_usd * usd_cny / 31.1035
    return round(au9999 - theoretical, 2)


def _get_usd_cny() -> float:
    """获取当前USD/CNY汇率，失败返回默认值"""
    try:
        fx_df = ak.fx_spot_quote()
        row = fx_df[fx_df.iloc[:, 0] == "USD/CNY"]
        if not row.empty:
            return round(float(row.iloc[0, 2]), 4)
    except Exception:
        pass
    return 7.2500


def fetch_gold_price() -> dict | None:
    """抓取最新金价快照（每小时交易时段调用）。"""
    try:
        xau_df = ak.futures_foreign_commodity_realtime(symbol=["XAU"])
        if xau_df is None or xau_df.empty:
            return None
        xau_usd = round(float(xau_df.iloc[0, 1]), 2)

        sge_df = ak.spot_quotations_sge(symbol="Au99.99")
        if sge_df is None or sge_df.empty:
            return None
        au9999 = round(float(sge_df.iloc[-1, 2]), 2)

        usd_cny = _get_usd_cny()
        premium = _calculate_premium(au9999, xau_usd, usd_cny)

        now = datetime.now()
        if now.hour < 3:
            trade_date = now - timedelta(days=1)
        else:
            trade_date = now

        # 整点时间戳（防止同小时内多次抓取产生重复记录）
        ts = now.strftime("%Y-%m-%d %H:00:00")
        return {
            "timestamp": ts,
            "trade_date": trade_date.strftime("%Y-%m-%d"),
            "xau_usd": xau_usd,
            "au9999": au9999,
            "usd_cny": usd_cny,
            "premium": premium,
        }
    except Exception as e:
        logger.exception(f"fetch_gold_price failed: {e}")
        return None


def fetch_gold_history() -> list[dict] | None:
    """回填历史金价日线数据。合并COMEX国际金价+SGE国内金价+汇率。

    COMEX数据最早到2005年，SGE数据最早到2016年。
    以SGE数据为准（两者都有的日期才输出），计算每日溢价。
    """
    try:
        # COMEX XAU 历史日线 (open/high/low/close)
        comex = ak.futures_foreign_hist(symbol="XAU")
        comex_cols = {"date": comex.columns[0], "close": comex.columns[4]}
        comex_map = {}
        for _, row in comex.iterrows():
            d = str(row[comex_cols["date"]])[:10]
            price = float(row[comex_cols["close"]])
            if price > 0:
                comex_map[d] = price
        logger.info(f"COMEX history: {len(comex_map)} records")

        # SGE Au99.99 历史日线 (open/close/low/high)
        sge = ak.spot_hist_sge(symbol="Au99.99")
        sge_map = {}
        for _, row in sge.iterrows():
            d = str(row["date"])[:10]
            price = float(row["close"])
            if price > 0:
                sge_map[d] = price
        logger.info(f"SGE history: {len(sge_map)} records")

        # 用当前汇率填充（历史汇率单独获取成本高，近似处理）
        usd_cny = _get_usd_cny()

        records = []
        for d in sorted(set(comex_map) & set(sge_map)):
            xau = comex_map[d]
            au = sge_map[d]
            premium = _calculate_premium(au, xau, usd_cny)
            records.append({
                "timestamp": d + " 00:00:00",
                "trade_date": d,
                "xau_usd": round(xau, 2),
                "au9999": round(au, 2),
                "usd_cny": usd_cny,
                "premium": premium,
            })

        logger.info(f"Merged history: {len(records)} records")
        return records
    except Exception as e:
        logger.exception(f"fetch_gold_history failed: {e}")
        return None
