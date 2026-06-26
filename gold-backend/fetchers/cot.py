"""COMEX黄金期货COT持仓报告解析。

CFTC每周五发布，包含截至周二的数据。周末解析最新报告。
数据来源: https://www.cftc.gov/dea/futures/deacmxsf.htm
"""
import csv
import io
import logging
from datetime import date
import httpx

logger = logging.getLogger(__name__)

COT_URL = "https://www.cftc.gov/dea/newcot/c_disagg.txt"


def fetch_cot_net_long() -> dict | None:
    """解析CFTC COT报告，提取黄金期货Managed Money净多头。

    Returns:
        dict: {report_date, net_long}
    """
    try:
        resp = httpx.get(COT_URL, timeout=30, headers={"User-Agent": "GoldDashboard/1.0"})
        resp.raise_for_status()

        # 在文件内容中定位黄金合约
        lines = resp.text.split("\n")
        gold_section_started = False
        for line in lines:
            if "GOLD" in line.upper() and "COMEX" in line:
                gold_section_started = True
            if gold_section_started and "COMMODITY" in line.upper():
                continue
            if gold_section_started and line.strip() and not line.startswith("-"):
                parts = line.split(",")
                if len(parts) >= 15:
                    try:
                        market_name = parts[0].strip()
                        if "GOLD" in market_name.upper():
                            net_long = int(parts[8]) if parts[8].strip() else 0
                            return {
                                "report_date": parts[2].strip(),
                                "net_long": net_long,
                            }
                    except (ValueError, IndexError):
                        continue

        logger.warning("Gold contract not found in COT report")
        return None

    except Exception as e:
        logger.exception(f"fetch_cot_net_long failed: {e}")
        return None
