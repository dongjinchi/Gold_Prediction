"""定时任务调度：数据采集 + AI研判"""
import logging
import random
from datetime import datetime, date
from apscheduler.schedulers.background import BackgroundScheduler

from config import DB_PATH
from db.models import init_db
from db.queries import (
    insert_gold_price, insert_macro, insert_cb_event, update_macro_cot,
    get_latest_gold_price
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


@scheduler.scheduled_job("cron", hour="7-22", minute="0")
def job_fetch_gold_price():
    """每小时抓取金价（07:00-22:00）"""
    logger.info("Job: fetch gold price")
    data = fetch_gold_price()
    if data:
        insert_gold_price(data)
        logger.info(f"Gold price saved: XAU={data['xau_usd']}, AU9999={data['au9999']}")
    else:
        logger.warning("Gold price fetch returned None")


@scheduler.scheduled_job("cron", hour="9", minute="5")
def job_fetch_macro():
    """每日09:05抓取宏观指标"""
    logger.info("Job: fetch macro indicators")
    data = fetch_all_macro()
    if data:
        insert_macro(data)
        logger.info(f"Macro saved: {data}")


@scheduler.scheduled_job("cron", day_of_week="sat", hour="9", minute="30")
def job_fetch_cot():
    """每周六09:30抓取COT持仓"""
    logger.info("Job: fetch COT report")
    result = fetch_cot_net_long()
    if result:
        update_macro_cot(result["report_date"], result["net_long"])
        logger.info(f"COT saved: net_long={result['net_long']}")


@scheduler.scheduled_job("cron", day="7-12", hour="18", minute="0")
def job_detect_cb_events():
    """每月7-12日18:00检测央行购金事件"""
    logger.info("Job: detect CB gold buying events")
    events = detect_cb_events()
    for event in events:
        insert_cb_event(event)
        logger.info(f"CB event saved: {event.get('title', '')}")


from scheduler_verify import verify_yesterday_predictions


@scheduler.scheduled_job("cron", hour="9", minute="15")
def job_verify_predictions():
    """每日09:15回填昨日预测结果"""
    logger.info("Job: verify yesterday predictions")
    verify_yesterday_predictions()


def start_scheduler():
    """启动所有定时任务"""
    init_db(DB_PATH)
    # 启动时立即执行一次数据抓取（如果数据库为空）
    latest = get_latest_gold_price()
    if latest is None:
        logger.info("Database empty, running initial data fetch...")
        job_fetch_gold_price()
        job_fetch_macro()
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped")
