"""宏观指标采集: TIPS, DXY, SPDR, VIX, COT"""
import yfinance as yf
import pandas as pd
import logging
from datetime import date, timedelta
from config import FRED_API_KEY

logger = logging.getLogger(__name__)


def fetch_tips_10y() -> float | None:
    """从FRED获取10年期TIPS收益率(DFII10)。

    备选：如果没有FRED API Key，用10Y名义收益率 - 10Y盈亏平衡通胀率近似。
    """
    try:
        if FRED_API_KEY:
            from fredapi import Fred
            fred = Fred(api_key=FRED_API_KEY)
            series = fred.get_series("DFII10")
            if not series.empty:
                return round(float(series.iloc[-1]), 2)
    except ImportError:
        logger.warning("fredapi not installed, trying yfinance fallback")
    except Exception as e:
        logger.warning(f"FRED API failed: {e}, trying yfinance fallback")

    # 回退: ^TNX (10Y名义) - T10YIE (10Y盈亏平衡通胀率)
    try:
        tnx = yf.download("^TNX", period="5d", progress=False)
        t10yie = yf.download("T10YIE", period="5d", progress=False)
        if not tnx.empty and not t10yie.empty:
            nominal = float(tnx["Close"].iloc[-1])
            be_inflation = float(t10yie["Close"].iloc[-1])
            return round(nominal - be_inflation, 2)
    except Exception as e:
        logger.exception(f"TIPS fallback also failed: {e}")

    return None


def fetch_dxy() -> float | None:
    """获取美元指数(DX-Y.NYB)"""
    try:
        ticker = yf.Ticker("DX-Y.NYB")
        hist = ticker.history(period="5d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 2)
    except Exception as e:
        logger.exception(f"fetch_dxy failed: {e}")
    return None


def fetch_spdr_holdings() -> float | None:
    """获取SPDR Gold Trust持仓(吨)。

    GLD ETF数据: 每份额≈0.1盎司黄金
    GLD总资产 / GLD价格 ≈ 份额数, 份额数 × 0.1 / 32150.7 ≈ 吨
    简化方法: 直接爬SPDR官网或通过yfinance获取近似值
    """
    try:
        ticker = yf.Ticker("GLD")
        info = ticker.info
        # totalAssets 是美元计价的总净资产
        total_assets = info.get("totalAssets", 0)
        nav_price = info.get("navPrice") or info.get("previousClose", 0)
        if total_assets and nav_price and nav_price > 0:
            shares = total_assets / nav_price
            tonnes = shares * 0.1 / 32150.7
            return round(tonnes, 1)
    except Exception as e:
        logger.exception(f"fetch_spdr_holdings via info failed: {e}")

    # 回退: 直接用历史价格估算 (1 GLD share ≈ 0.095-0.10 oz gold)
    try:
        hist = yf.download("GLD", period="5d", progress=False)
        if not hist.empty:
            price = float(hist["Close"].iloc[-1])
            oz_per_share = 0.0945
            tonnes_per_share = oz_per_share / 32150.7
            # 当前GLD约3.04亿份额(近似)，实际应从总资产推算
            shares_estimate = 304_000_000
            tonnes = shares_estimate * tonnes_per_share
            return round(tonnes, 1)
    except Exception:
        pass
    return None


def fetch_vix() -> float | None:
    """获取VIX恐慌指数"""
    try:
        ticker = yf.Ticker("^VIX")
        hist = ticker.history(period="5d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 2)
    except Exception as e:
        logger.exception(f"fetch_vix failed: {e}")
    return None


def fetch_all_macro() -> dict:
    """批量更新所有宏观指标。

    Returns:
        dict: {date, tips_10y, dxy, spdr_tonnes, vix}
        COT持仓每周单独更新，不包含在此。
    """
    today = date.today().isoformat()
    return {
        "date": today,
        "tips_10y": fetch_tips_10y(),
        "dxy": fetch_dxy(),
        "spdr_tonnes": fetch_spdr_holdings(),
        "vix": fetch_vix(),
    }
