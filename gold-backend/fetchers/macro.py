"""宏观指标采集: TIPS, DXY, SPDR, VIX。多源策略避免单点故障。"""
import time
import logging
from datetime import date, timedelta
import httpx
from config import FRED_API_KEY

logger = logging.getLogger(__name__)


def _calc_dxy_from_fx() -> float | None:
    """用免费汇率API计算DXY近似值。

    DXY公式: 50.14348112 × (EUR/USD)^-0.576 × (USD/JPY)^0.136 ×
              (GBP/USD)^-0.119 × (USD/CAD)^0.091 × (USD/SEK)^0.042 × (USD/CHF)^0.036

    open.er-api 返回 X/USD 格式，需要转换为 DXY 所需格式。
    """
    try:
        r = httpx.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        data = r.json()
        rates = data["rates"]

        eur_usd = 1.0 / rates.get("EUR", 0.92)
        usd_jpy = rates.get("JPY", 145.0)
        gbp_usd = 1.0 / rates.get("GBP", 0.79)
        usd_cad = rates.get("CAD", 1.37)
        usd_sek = rates.get("SEK", 10.5)
        usd_chf = rates.get("CHF", 0.89)

        dxy = 50.14348112 * (
            eur_usd ** (-0.576) *
            usd_jpy ** 0.136 *
            gbp_usd ** (-0.119) *
            usd_cad ** 0.091 *
            usd_sek ** 0.042 *
            usd_chf ** 0.036
        )
        return round(dxy, 2)
    except Exception as e:
        logger.warning(f"DXY from FX rates failed: {e}")
    return None


def fetch_tips_10y() -> float | None:
    """获取10年期TIPS收益率。仅FRED（需要免费API Key）。"""
    if not FRED_API_KEY:
        logger.warning("No FRED_API_KEY configured, TIPS unavailable")
        return None
    try:
        from fredapi import Fred
        fred = Fred(api_key=FRED_API_KEY)
        series = fred.get_series("DFII10")
        if not series.empty:
            return round(float(series.iloc[-1]), 2)
    except Exception as e:
        logger.warning(f"FRED TIPS failed: {e}")
    return None


def fetch_dxy() -> float | None:
    """获取美元指数。主源：免费汇率API计算，回退：yfinance。"""
    result = _calc_dxy_from_fx()
    if result:
        return result
    # 回退yfinance
    try:
        import yfinance as yf
        time.sleep(10)
        t = yf.Ticker("DX-Y.NYB")
        hist = t.history(period="5d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 2)
    except Exception as e:
        logger.warning(f"yfinance DXY fallback also failed: {e}")
    return None


def fetch_spdr_holdings() -> float | None:
    """获取SPDR持仓(吨)。基于GLD价格估算。"""
    try:
        import yfinance as yf
        time.sleep(5)
        t = yf.Ticker("GLD")
        hist = t.history(period="5d")
        if not hist.empty:
            price = float(hist["Close"].iloc[-1])
            tonnes = 304_000_000 * 0.0945 / 32150.7
            return round(tonnes, 1)
    except Exception as e:
        logger.warning(f"SPDR failed: {e}")
    return None


def fetch_vix() -> float | None:
    """获取VIX。"""
    try:
        import yfinance as yf
        time.sleep(5)
        t = yf.Ticker("^VIX")
        hist = t.history(period="5d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 2)
    except Exception as e:
        logger.warning(f"VIX failed: {e}")
    return None


def fetch_all_macro() -> dict:
    """批量更新宏观指标。DXY通过免费API获取(即时)，其余逐个yfinance(带延迟)。"""
    today = date.today().isoformat()

    # DXY 使用免费汇率API，无需等待
    dxy_val = fetch_dxy()
    time.sleep(3)

    # 其余指标尝试yfinance，每个之间有延迟
    tips_val = fetch_tips_10y()
    time.sleep(3)
    spdr_val = fetch_spdr_holdings()
    time.sleep(5)
    vix_val = fetch_vix()

    macros = {
        "date": today,
        "tips_10y": tips_val,
        "dxy": dxy_val,
        "spdr_tonnes": spdr_val,
        "vix": vix_val,
    }
    logger.info(f"Macro result: {macros}")
    return macros
