import os
from dotenv import load_dotenv

load_dotenv()

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "gold.db")

# FRED API（免费注册: https://fred.stlouisfed.org/docs/api/api_key.html）
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

# LLM API Keys
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = "https://api.openai.com/v1"

# 交易时段配置
TRADING_SESSION = {
    "day_open": "09:00",
    "day_morning_close": "11:30",
    "day_afternoon_open": "13:30",
    "day_close": "15:30",
    "night_open": "20:00",
    "night_close": "02:30",  # 次日
}

# 定时任务配置
FETCH_INTERVAL_MINUTES = 60  # 金价每小时抓取一次
DAILY_FETCH_HOUR = 9         # 日频数据北京时间9点抓取
AI_ANALYSIS_HOUR = 18        # AI研判北京时间18点生成
