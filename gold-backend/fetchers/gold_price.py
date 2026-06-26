"""金价与汇率数据采集。主源: akshare"""
from datetime import datetime, timedelta
import akshare as ak
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def _calculate_premium(au9999: float, xau_usd: float, usd_cny: float) -> float:
    """计算上海溢价(元/克)。

    国内理论金价 = 国际金价(美元/盎司) × 汇率 / 31.1035
    溢价 = 国内实际金价 - 国内理论金价
    """
    theoretical = xau_usd * usd_cny / 31.1035
    return round(au9999 - theoretical, 2)


def fetch_gold_price() -> dict | None:
    """抓取最新金价快照。

    使用 akshare 多个接口采集:
      - XAU/USD: futures_foreign_commodity_realtime (伦敦金)
      - Au99.99:  spot_quotations_sge (上海金交所)
      - USD/CNY:  fx_spot_quote

    Returns:
        dict: {timestamp, trade_date, xau_usd, au9999, usd_cny, premium} 或 None
    """
    try:
        # ---- 国际金价 XAU/USD (伦敦金) ----
        xau_df = ak.futures_foreign_commodity_realtime(symbol=["XAU"])
        if xau_df is None or xau_df.empty:
            logger.warning("futures_foreign_commodity_realtime(XAU) returned empty")
            return None

        # 列: 0=名称, 1=最新价, 2=人民币报价, ..., 12=更新时间, 13=日期
        xau_usd = float(xau_df.iloc[0, 1])
        logger.info(f"XAU/USD = {xau_usd}")

        # ---- 国内金价 Au99.99 (上海金交所实时行情) ----
        sge_df = ak.spot_quotations_sge(symbol="Au99.99")
        if sge_df is None or sge_df.empty:
            logger.warning("spot_quotations_sge(Au99.99) returned empty")
            return None

        # 列: 0=品种, 1=时间, 2=现价, 3=更新时间 — 取最后一条
        au9999 = float(sge_df.iloc[-1, 2])
        logger.info(f"Au99.99 = {au9999}")

        # ---- 汇率 USD/CNY ----
        usd_cny = None
        try:
            fx_df = ak.fx_spot_quote()
            # 列: 0=货币对, 1=昨收价/买入价, 2=最新价
            usd_cny_row = fx_df[fx_df.iloc[:, 0] == "USD/CNY"]
            if not usd_cny_row.empty:
                usd_cny = float(usd_cny_row.iloc[0, 2])
        except Exception:
            pass

        if usd_cny is None or usd_cny <= 0:
            logger.warning("Cannot fetch USD/CNY, setting to default 7.25")
            usd_cny = 7.25

        premium = _calculate_premium(au9999, xau_usd, usd_cny)

        now = datetime.now()
        # 凌晨数据属于前一日夜盘，按交易日期归因
        if now.hour < 3:
            trade_date = now - timedelta(days=1)
        else:
            trade_date = now

        return {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "trade_date": trade_date.strftime("%Y-%m-%d"),
            "xau_usd": round(xau_usd, 2),
            "au9999": round(au9999, 2),
            "usd_cny": round(usd_cny, 4),
            "premium": premium,
        }

    except Exception as e:
        logger.exception(f"fetch_gold_price failed: {e}")
        return None
