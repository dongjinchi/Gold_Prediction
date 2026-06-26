"""定时任务调度：数据采集 + AI研判"""
import logging
import random
from datetime import datetime, date
from apscheduler.schedulers.background import BackgroundScheduler

from config import DB_PATH
from db.models import init_db
from db.queries import (
    insert_gold_price, insert_macro, insert_cb_event, update_macro_cot,
    get_latest_gold_price, upsert_daily_ohlc
)
from fetchers.gold_price import fetch_gold_price
from fetchers.macro import fetch_all_macro
from fetchers.cot import fetch_cot_net_long
from fetchers.cb_event import detect_cb_events

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

scheduler = BackgroundScheduler(timezone="Asia/Shanghai")


def _jitter(minutes: int = 2) -> int:
    """随机延迟(秒)，避免定时触发的爬虫被识别"""
    return random.randint(0, minutes * 60)


# 上金所交易时段（北京时间）：
#   日盘上午: 09:00-11:30 → 抓取 9,10,11 点
#   日盘下午: 13:30-15:30 → 抓取 13,14,15 点
#   夜盘:     20:00-02:30 → 抓取 20,21,22,23,0,1,2 点
# 休盘时段不抓取，减少请求量避免反爬

def _add_trading_jobs():
    """注册交易时段内的多个定时任务"""
    for hour in [9, 10, 11, 13, 14, 15, 20, 21, 22, 23, 0, 1, 2]:
        scheduler.add_job(
            job_fetch_gold_price,
            "cron",
            hour=str(hour),
            minute="0",
            id=f"fetch_gold_{hour}",
            replace_existing=True,
            misfire_grace_time=300,
            coalesce=True,
            max_instances=1,
        )


def job_fetch_gold_price():
    """抓取金价（仅在交易时段被调度）"""
    logger.info("Job: fetch gold price")
    data = fetch_gold_price()
    if data:
        insert_gold_price(data)
        upsert_daily_ohlc(data)
        logger.info(f"Gold price saved: XAU={data['xau_usd']}, AU9999={data['au9999']}")
    else:
        logger.warning("Gold price fetch returned None")


def job_fetch_macro():
    """每日09:05抓取宏观指标"""
    logger.info("Job: fetch macro indicators")
    data = fetch_all_macro()
    if data:
        insert_macro(data)
        logger.info(f"Macro saved: {data}")


def job_fetch_cot():
    """每周六09:30抓取COT持仓"""
    logger.info("Job: fetch COT report")
    result = fetch_cot_net_long()
    if result:
        update_macro_cot(result["report_date"], result["net_long"])
        logger.info(f"COT saved: net_long={result['net_long']}")


def job_detect_cb_events():
    """每月7-12日18:00检测央行购金事件"""
    logger.info("Job: detect CB gold buying events")
    events = detect_cb_events()
    for event in events:
        insert_cb_event(event)
        logger.info(f"CB event saved: {event.get('title', '')}")


from scheduler_verify import verify_yesterday_predictions


def job_verify_predictions():
    """每日09:15回填昨日预测结果"""
    logger.info("Job: verify yesterday predictions")
    verify_yesterday_predictions()


def start_scheduler():
    """启动所有定时任务。首次运行自动回填历史金价数据。"""
    init_db(DB_PATH)
    _add_trading_jobs()

    # 注册宏规定时任务（带防抖/漏触发保护）
    job_opts = dict(misfire_grace_time=600, coalesce=True, max_instances=1, replace_existing=True)
    scheduler.add_job(job_fetch_macro, "cron", hour="9", minute="5", id="fetch_macro", **job_opts)
    scheduler.add_job(job_fetch_cot, "cron", day_of_week="sat", hour="9", minute="30", id="fetch_cot", **job_opts)
    scheduler.add_job(job_detect_cb_events, "cron", day="7-12", hour="18", minute="0", id="detect_cb", **job_opts)
    scheduler.add_job(job_verify_predictions, "cron", hour="9", minute="15", id="verify_pred", **job_opts)

    # 如果数据库几乎没有数据（历史未回填），则自动回填
    latest = get_latest_gold_price()
    if latest is None:
        logger.info("First run: backfilling historical gold price data...")
        from db.queries import insert_gold_price
        from fetchers.gold_price import fetch_gold_history
        records = fetch_gold_history()
        if records:
            for r in records:
                insert_gold_price(r)
            logger.info(f"Backfilled {len(records)} historical gold records")

    # 检查今天是否有数据，没有则立刻抓取
    from datetime import date
    today_str = date.today().isoformat()
    if latest and latest["timestamp"][:10] != today_str:
        logger.info("No data for today, fetching now...")
        job_fetch_gold_price()
        job_fetch_macro()

    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped")
