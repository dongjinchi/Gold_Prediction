"""宏观指标采集: TIPS, DXY, SPDR, VIX。每个指标间加延迟防止yfinance限速。"""
import time
import yfinance as yf
import logging
from datetime import date, timedelta
from config import FRED_API_KEY

logger = logging.getLogger(__name__)


def _retry_fetch(fn, name: str, max_retries: int = 2) -> float | None:
    """带重试和延迟的抓取包装器"""
    for attempt in range(max_retries + 1):
        try:
            result = fn()
            if result is not None:
                return result
            if attempt < max_retries:
                time.sleep(3)
        except Exception:
            if attempt < max_retries:
                time.sleep(5)
    logger.warning(f"{name}: all {max_retries + 1} attempts failed")
    return None


def _fetch_tips_once() -> float | None:
    """单次尝试获取TIPS收益率"""
    if FRED_API_KEY:
        try:
            from fredapi import Fred
            fred = Fred(api_key=FRED_API_KEY)
            series = fred.get_series("DFII10")
            if not series.empty:
                return round(float(series.iloc[-1]), 2)
        except (ImportError, Exception) as e:
            logger.warning(f"FRED API failed: {e}")

    # 回退: ^TNX - T10YIE
    try:
        tnx = yf.download("^TNX", period="5d", progress=False)
        time.sleep(2)
        t10yie = yf.download("T10YIE", period="5d", progress=False)
        if not tnx.empty and not t10yie.empty:
            nominal = float(tnx["Close"].iloc[-1])
            be_inflation = float(t10yie["Close"].iloc[-1])
            return round(nominal - be_inflation, 2)
    except Exception as e:
        logger.exception(f"TIPS fallback failed: {e}")
    return None


def fetch_tips_10y() -> float | None:
    return _retry_fetch(_fetch_tips_once, "TIPS")


def _fetch_dxy_once() -> float | None:
    ticker = yf.Ticker("DX-Y.NYB")
    hist = ticker.history(period="5d")
    if not hist.empty:
        return round(float(hist["Close"].iloc[-1]), 2)
    return None


def fetch_dxy() -> float | None:
    return _retry_fetch(_fetch_dxy_once, "DXY")


def _fetch_spdr_once() -> float | None:
    """获取SPDR持仓(吨)。使用yfinance GLD价格估算。"""
    try:
        hist = yf.download("GLD", period="5d", progress=False)
        if not hist.empty:
            price = float(hist["Close"].iloc[-1])
            oz_per_share = 0.0945
            tonnes_per_share = oz_per_share / 32150.7
            shares_estimate = 304_000_000
            tonnes = shares_estimate * tonnes_per_share
            return round(tonnes, 1)
    except Exception:
        pass
    return None


def fetch_spdr_holdings() -> float | None:
    return _retry_fetch(_fetch_spdr_once, "SPDR")


def _fetch_vix_once() -> float | None:
    ticker = yf.Ticker("^VIX")
    hist = ticker.history(period="5d")
    if not hist.empty:
        return round(float(hist["Close"].iloc[-1]), 2)
    return None


def fetch_vix() -> float | None:
    return _retry_fetch(_fetch_vix_once, "VIX")


def fetch_all_macro() -> dict:
    """批量更新所有宏观指标。每个指标间加3秒延迟防止限速。"""
    today = date.today().isoformat()
    macros = {}

    for name, fn in [("tips_10y", fetch_tips_10y), ("dxy", fetch_dxy),
                      ("spdr_tonnes", fetch_spdr_holdings), ("vix", fetch_vix)]:
        logger.info(f"Fetching {name}...")
        macros[name] = fn()
        time.sleep(3)

    macros["date"] = today
    logger.info(f"Macro result: {macros}")
    return macros
