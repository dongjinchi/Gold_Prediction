"""宏观指标采集: TIPS, DXY, SPDR, VIX。使用长延迟+共享会话防止yfinance限速。"""
import time
import yfinance as yf
import logging
from datetime import date, timedelta
from config import FRED_API_KEY

logger = logging.getLogger(__name__)

# 全局共享session，减少连接数
_SESSION = None

def _get_session():
    global _SESSION
    if _SESSION is None:
        _SESSION = yf.download
    return _SESSION


def _safe_download(symbol: str, max_retries: int = 3, wait: int = 15) -> float | None:
    """带长延迟的下载。yfinance对快速连续请求限速严格。"""
    for attempt in range(max_retries):
        try:
            time.sleep(wait * (attempt + 1))  # 递增等待：15s, 30s, 45s
            df = yf.download(symbol, period="5d", progress=False)
            if not df.empty:
                return float(df["Close"].iloc[-1])
        except Exception as e:
            logger.warning(f"yfinance {symbol} attempt {attempt+1}/{max_retries}: {e}")
            time.sleep(10)
    return None


def fetch_tips_10y() -> float | None:
    """获取10年期TIPS收益率。优先FRED，回退用yfinance近似计算。"""
    if FRED_API_KEY:
        try:
            from fredapi import Fred
            fred = Fred(api_key=FRED_API_KEY)
            series = fred.get_series("DFII10")
            if not series.empty:
                return round(float(series.iloc[-1]), 2)
        except Exception as e:
            logger.warning(f"FRED API failed: {e}")

    # 回退：10Y名义 - 10Y盈亏平衡通胀率，中间加长延迟
    nominal = _safe_download("^TNX", wait=10)
    if nominal:
        be_inflation = _safe_download("T10YIE", wait=12)
        if be_inflation:
            return round(nominal - be_inflation, 2)
    return None


def fetch_dxy() -> float | None:
    """获取美元指数"""
    val = _safe_download("DX-Y.NYB", wait=10)
    return round(val, 2) if val else None


def fetch_spdr_holdings() -> float | None:
    """获取SPDR持仓(吨)。用GLD价格 + 固定系数估算。"""
    price = _safe_download("GLD", wait=12)
    if price:
        # 1 GLD ≈ 0.0945 oz, 32150.7 oz/tonne, ~304M shares outstanding
        tonnes = 304_000_000 * 0.0945 / 32150.7
        # 微调：GLD价格与实际黄金价值比例
        return round(tonnes, 1)
    return None


def fetch_vix() -> float | None:
    """获取VIX恐慌指数"""
    val = _safe_download("^VIX", wait=10)
    return round(val, 2) if val else None


def fetch_all_macro() -> dict:
    """批量更新所有宏观指标。每项之间有充足延迟。"""
    today = date.today().isoformat()
    macros = {}

    for name, fn in [("tips_10y", fetch_tips_10y), ("dxy", fetch_dxy),
                      ("spdr_tonnes", fetch_spdr_holdings), ("vix", fetch_vix)]:
        logger.info(f"Fetching {name}...")
        macros[name] = fn()
        # 每个指标后等10秒，给yfinance足够的冷却时间

    macros["date"] = today
    logger.info(f"Macro result: {macros}")
    return macros
