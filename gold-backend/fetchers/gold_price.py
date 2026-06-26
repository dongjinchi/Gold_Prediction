"""金价与汇率数据采集。主源: akshare (历史OHLC + 实时)。"""
from datetime import datetime, timedelta
import akshare as ak
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def _calculate_premium(au_close: float, xau_close: float, usd_cny: float) -> float:
    theoretical = xau_close * usd_cny / 31.1035
    return round(au_close - theoretical, 2)


def _get_usd_cny() -> float:
    try:
        fx_df = ak.fx_spot_quote()
        row = fx_df[fx_df.iloc[:, 0] == "USD/CNY"]
        if not row.empty:
            return round(float(row.iloc[0, 2]), 4)
    except Exception:
        pass
    return 7.2500


def fetch_gold_price() -> dict | None:
    """抓取最新金价快照（每小时交易时段调用）。实时数据无OHLC。"""
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
        trade_date = now - timedelta(days=1) if now.hour < 3 else now
        ts = now.strftime("%Y-%m-%d %H:00:00")

        return {
            "timestamp": ts, "trade_date": trade_date.strftime("%Y-%m-%d"),
            "xau_usd": xau_usd, "au9999": au9999,
            "xau_open": None, "xau_high": None, "xau_low": None, "xau_vol": None,
            "au_open": None, "au_high": None, "au_low": None,
            "usd_cny": usd_cny, "premium": premium,
        }
    except Exception as e:
        logger.exception(f"fetch_gold_price failed: {e}")
        return None


def _fetch_shfe_vol_map() -> dict[str, float]:
    """获取上期所黄金主力合约(AU0)日成交量。"""
    try:
        df = ak.futures_main_sina(symbol="AU0")
        vol_map = {}
        for _, row in df.iterrows():
            d = str(row.iloc[0])[:10]
            vol = float(row.iloc[5])  # 成交量列
            if vol > 0:
                vol_map[d] = vol
        logger.info(f"SHFE volume: {len(vol_map)} records")
        return vol_map
    except Exception as e:
        logger.warning(f"SHFE volume fetch failed: {e}")
        return {}


def fetch_gold_history() -> list[dict] | None:
    """回填历史金价日线OHLC+成交量数据。合并COMEX + SGE + SHFE成交量。"""
    try:
        comex = ak.futures_foreign_hist(symbol="XAU")
        comex_map = {}
        for _, row in comex.iterrows():
            d = str(row["date"])[:10]
            comex_map[d] = {
                "open": float(row["open"]), "high": float(row["high"]),
                "low": float(row["low"]), "close": float(row["close"]),
                "volume": float(row.get("volume", 0)) or 0,
            }
        logger.info(f"COMEX OHLC: {len(comex_map)} records")

        sge = ak.spot_hist_sge(symbol="Au99.99")
        sge_map = {}
        for _, row in sge.iterrows():
            d = str(row["date"])[:10]
            sge_map[d] = {
                "open": float(row["open"]), "high": float(row["high"]),
                "low": float(row["low"]), "close": float(row["close"]),
            }
        logger.info(f"SGE OHLC: {len(sge_map)} records")

        # 上期所黄金期货成交量
        au_vol_map = _fetch_shfe_vol_map()

        usd_cny = _get_usd_cny()
        records = []
        for d in sorted(set(comex_map) & set(sge_map)):
            cx = comex_map[d]
            sa = sge_map[d]
            premium = _calculate_premium(sa["close"], cx["close"], usd_cny)
            records.append({
                "timestamp": d + " 00:00:00",
                "xau_usd": round(cx["close"], 2),
                "xau_open": round(cx["open"], 2),
                "xau_high": round(cx["high"], 2),
                "xau_low": round(cx["low"], 2),
                "xau_vol": int(cx["volume"]),
                "au9999": round(sa["close"], 2),
                "au_open": round(sa["open"], 2),
                "au_high": round(sa["high"], 2),
                "au_low": round(sa["low"], 2),
                "au_vol": int(au_vol_map.get(d, 0)),
                "usd_cny": usd_cny,
                "premium": premium,
            })

        logger.info(f"Merged OHLC+Vol history: {len(records)} records")
        return records
    except Exception as e:
        logger.exception(f"fetch_gold_history failed: {e}")
        return None
