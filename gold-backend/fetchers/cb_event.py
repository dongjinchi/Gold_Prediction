"""央行购金事件监听。

中国央行每月7-10日左右发布上月末官方储备资产数据。
监听窗口期: 每月7-12日，通过新浪财经新闻RSS检测。
"""
import logging
import hashlib
from datetime import date, datetime
import httpx

logger = logging.getLogger(__name__)

# 检测关键词
CB_BUY_KEYWORDS = [
    "央行增持黄金", "央行黄金储备增加", "央行购金",
    "黄金储备增加", "官方储备资产黄金", "央行连续",
    "central bank gold", "PBOC gold",
]

# 新浪财经黄金新闻RSS
NEWS_SOURCES = [
    "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num=20&r=0.5",
]


def _is_in_detection_window() -> bool:
    """判断当前是否在央行数据发布窗口期（每月7-12日）"""
    today = date.today()
    return 7 <= today.day <= 12


def _generate_event_id(title: str, event_date: str) -> str:
    content = f"{title}{event_date}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def detect_cb_events() -> list[dict]:
    """检测央行购金相关新闻。

    仅在窗口期（每月7-12日）执行。其余日期直接返回空列表。

    Returns:
        list[dict]: 检测到的购金事件列表
    """
    if not _is_in_detection_window():
        return []

    events = []
    today = date.today().isoformat()

    for url in NEWS_SOURCES:
        try:
            resp = httpx.get(url, timeout=15, headers={"User-Agent": "GoldDashboard/1.0"})
            resp.raise_for_status()
            data = resp.json()

            articles = data.get("result", {}).get("data", [])
            for article in articles:
                title = article.get("title", "")
                ctime = article.get("ctime", "")

                # 关键词匹配
                if any(kw in title for kw in CB_BUY_KEYWORDS):
                    event_id = _generate_event_id(title, today)
                    events.append({
                        "event_date": today,
                        "country": "CN",
                        "action": "buy",
                        "amount_tonnes": None,
                        "impact_score": 15.0,
                        "source_url": article.get("url", ""),
                        "title": title,
                    })
                    logger.info(f"CB event detected: {title}")
        except Exception as e:
            logger.exception(f"News source {url} failed: {e}")

    return events
