# 黄金投资决策网站 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从零搭建黄金投资决策网站：金价仪表盘+指标面板+规则打分+双LLM辩论+准确率曲线

**Architecture:** React+Vite+TypeScript静态前端通过REST API/SSE与Python FastAPI后端通信，后端定时从免费数据源抓取数据存入SQLite，规则引擎打分后由DeepSeek+OpenAI双模型辩论生成投资研判

**Tech Stack:** React 19, TypeScript, Vite 6, ECharts 6, Tailwind CSS 4, Python 3.12, FastAPI, SQLite, akshare, yfinance, apscheduler

---

## Phase 1: 项目基础设施

### Task 1: 初始化项目结构与Git仓库

**Files:**
- Create: `gold-backend/requirements.txt`
- Create: `gold-frontend/` (via Vite scaffold)
- Create: `.gitignore`

- [ ] **Step 1: 初始化Git仓库并创建基础文件**

```bash
cd F:/OneDrive/09Claud/03gold
git init
```

- [ ] **Step 2: 创建 .gitignore**

```
node_modules/
dist/
.env
__pycache__/
*.pyc
*.db
.superpowers/
.vite/
*.egg-info/
```

- [ ] **Step 3: 创建后端目录和requirements.txt**

```
fastapi==0.115.6
uvicorn==0.34.0
akshare==1.16.0
yfinance==0.2.54
pandas==2.2.3
apscheduler==3.11.0
python-dotenv==1.0.1
httpx==0.28.1
fredapi==0.5.3
openai==1.70.0
```

- [ ] **Step 4: 搭建前端脚手架**

```bash
cd F:/OneDrive/09Claud/03gold
npm create vite@latest gold-frontend -- --template react-ts
cd gold-frontend
npm install
npm install echarts echarts-for-react tailwindcss @tailwindcss/vite
```

- [ ] **Step 5: 验证前后端都能启动**

```bash
# 终端1: 后端 (在gold-backend/创建main.py后再测)
cd gold-backend
python -c "from fastapi import FastAPI; app=FastAPI(); print('FastAPI OK')"

# 终端2: 前端
cd gold-frontend
npm run dev
# 确认 Vite 开发服务器在 localhost:5173 启动
```

- [ ] **Step 6: 提交**

```bash
git add .gitignore gold-backend/requirements.txt gold-frontend/
git commit -m "chore: initialize project structure"
```

### Task 2: 后端骨架 — 配置、数据库模型、FastAPI入口

**Files:**
- Create: `gold-backend/config.py`
- Create: `gold-backend/db/__init__.py`
- Create: `gold-backend/db/models.py`
- Create: `gold-backend/main.py`

- [ ] **Step 1: 创建 config.py**

```python
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
```

- [ ] **Step 2: 创建 db/models.py**

```python
import sqlite3
import os

def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db(db_path: str):
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS gold_price (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL UNIQUE,
            xau_usd   REAL,
            au9999    REAL,
            usd_cny   REAL,
            premium   REAL
        );

        CREATE TABLE IF NOT EXISTS macro_indicators (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            date         DATE NOT NULL UNIQUE,
            tips_10y     REAL,
            dxy          REAL,
            spdr_tonnes  REAL,
            cot_net_long INTEGER,
            vix          REAL
        );

        CREATE TABLE IF NOT EXISTS cb_events (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date    DATE NOT NULL,
            country       TEXT DEFAULT 'CN',
            action        TEXT,
            amount_tonnes REAL,
            impact_score  REAL,
            source_url    TEXT,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS rule_scores (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            calc_time       DATETIME NOT NULL,
            total_score     INTEGER,
            signal          TEXT,
            confidence      REAL,
            indicator_scores TEXT,
            weights_used    TEXT
        );

        CREATE TABLE IF NOT EXISTS prediction_log (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            pred_date           DATE NOT NULL,
            target_date         DATE NOT NULL,
            predicted_direction TEXT,
            predicted_change_pct REAL,
            rule_score           INTEGER,
            llm_consensus        TEXT,
            debate_transcript    TEXT,
            actual_px_change     REAL,
            is_correct           INTEGER,
            error_reason         TEXT
        );
    """)

    conn.commit()
    conn.close()
```

- [ ] **Step 3: 创建 main.py**

```python
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import DB_PATH
from db.models import init_db

app = FastAPI(title="Gold Investment Dashboard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db(DB_PATH)
    print(f"Database initialized at {DB_PATH}")

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
```

- [ ] **Step 4: 创建 db/__init__.py**

```python
```

- [ ] **Step 5: 验证后端启动**

```bash
cd gold-backend
pip install -r requirements.txt
python main.py
# 访问 http://localhost:8000/health → {"status":"ok"}
# 确认 gold.db 文件已生成
```

- [ ] **Step 6: 提交**

```bash
git add gold-backend/
git commit -m "feat: backend skeleton with config, DB models, FastAPI entry"
```

---

## Phase 2: 数据层

### Task 3: 数据采集模块 — 金价与汇率

**Files:**
- Create: `gold-backend/fetchers/__init__.py`
- Create: `gold-backend/fetchers/gold_price.py`

- [ ] **Step 1: 创建 fetchers/gold_price.py**

```python
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
    
    Returns:
        dict: {timestamp, xau_usd, au9999, usd_cny, premium} 或 None
    """
    try:
        # akshare 黄金现货：国际+国内
        df = ak.spot_gold()
        if df is None or df.empty:
            logger.warning("akshare spot_gold returned empty")
            return None

        # 从DataFrame中提取数据
        xau_usd = None
        au9999 = None
        
        for _, row in df.iterrows():
            name = str(row.get("品种", ""))
            price = float(row.get("最新价", 0))
            if "伦敦" in name or "XAU" in name.upper() or "国际" in name:
                xau_usd = price
            elif "AU9999" in name or "Au99.99" in name or "黄金9999" in name:
                au9999 = price

        if xau_usd is None or au9999 is None:
            # 回退：如果品种名不匹配，尝试取前两行
            prices = df["最新价"].tolist()
            if len(prices) >= 2:
                xau_usd = float(prices[0])
                au9999 = float(prices[1])
            else:
                logger.warning(f"Cannot parse gold prices: {df.columns.tolist()}")
                return None

        # 汇率
        usd_cny = None
        try:
            fx_df = ak.fx_spot_quote()
            usd_cny_row = fx_df[fx_df["货币对"] == "美元人民币"]
            if not usd_cny_row.empty:
                usd_cny = float(usd_cny_row.iloc[0]["最新价"])
        except Exception:
            pass

        if usd_cny is None or usd_cny <= 0:
            logger.warning("Cannot fetch USD/CNY, setting to default 7.25")
            usd_cny = 7.25

        premium = _calculate_premium(au9999, xau_usd, usd_cny)

        now = datetime.now()
        # 如果是交易时段内的数据，按交易日期归因
        hour = now.hour
        if hour < 3:
            # 凌晨数据属于前一日夜盘
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
```

- [ ] **Step 2: 手动测试**

```bash
cd gold-backend
python -c "
from fetchers.gold_price import fetch_gold_price
result = fetch_gold_price()
print(result)
"
```

- [ ] **Step 3: 提交**

```bash
git add gold-backend/fetchers/
git commit -m "feat: gold price and FX data fetcher via akshare"
```

### Task 4: 数据采集模块 — 宏观指标

**Files:**
- Create: `gold-backend/fetchers/macro.py`

- [ ] **Step 1: 创建 fetchers/macro.py**

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add gold-backend/fetchers/macro.py
git commit -m "feat: macro indicators fetcher (TIPS, DXY, SPDR, VIX)"
```

### Task 5: 数据采集模块 — COT持仓与央行购金事件

**Files:**
- Create: `gold-backend/fetchers/cot.py`
- Create: `gold-backend/fetchers/cb_event.py`

- [ ] **Step 1: 创建 fetchers/cot.py**

```python
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
        dict: {report_date, net_long, long_positions, short_positions, spreading}
    """
    try:
        resp = httpx.get(COT_URL, timeout=30)
        resp.raise_for_status()

        # 在文件内容中定位黄金合约
        lines = resp.text.split("\n")
        gold_section_started = False
        for line in lines:
            if "GOLD" in line.upper() and "COMEX" in line:
                gold_section_started = True
            if gold_section_started and "COMMODITY" in line.upper():
                # 跳过表头后的数据行
                continue
            if gold_section_started and line.strip() and not line.startswith("-"):
                parts = line.split(",")
                if len(parts) >= 15:
                    try:
                        # COT disaggregated report格式:
                        # 列索引参考CFTC说明: Managed Money在col 8-11附近
                        # 简单解析: 查找"GOLD"和"CHICAGO MERCANTILE EXCHANGE"
                        market_name = parts[0].strip()
                        if "GOLD" in market_name.upper():
                            # 取所有Managed Money相关字段
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
```

- [ ] **Step 2: 创建 fetchers/cb_event.py**

```python
"""央行购金事件监听。

中国央行每月7-10日左右发布上月末官方储备资产数据。
监听窗口期: 每月7-12日，通过新浪财经/东方财富新闻RSS检测。
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
            resp = httpx.get(url, timeout=15)
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
                        "amount_tonnes": None,  # 需要从正文提取
                        "impact_score": 15.0,  # 默认影响分
                        "source_url": article.get("url", ""),
                        "title": title,
                    })
                    logger.info(f"CB event detected: {title}")
        except Exception as e:
            logger.exception(f"News source {url} failed: {e}")

    return events
```

- [ ] **Step 3: 提交**

```bash
git add gold-backend/fetchers/cot.py gold-backend/fetchers/cb_event.py
git commit -m "feat: COT report parser and CB gold buying event detector"
```

### Task 6: 数据库查询层

**Files:**
- Create: `gold-backend/db/queries.py`

- [ ] **Step 1: 创建 db/queries.py**

```python
"""数据库查询接口"""
import sqlite3
import json
from datetime import date, datetime, timedelta
from config import DB_PATH
from db.models import get_connection


def insert_gold_price(data: dict) -> int:
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT OR REPLACE INTO gold_price (timestamp, xau_usd, au9999, usd_cny, premium)
           VALUES (?, ?, ?, ?, ?)""",
        (data["timestamp"], data["xau_usd"], data["au9999"],
         data["usd_cny"], data["premium"])
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def insert_macro(data: dict) -> int:
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT OR REPLACE INTO macro_indicators (date, tips_10y, dxy, spdr_tonnes, vix)
           VALUES (?, ?, ?, ?, ?)""",
        (data["date"], data["tips_10y"], data["dxy"],
         data["spdr_tonnes"], data["vix"])
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def update_macro_cot(report_date: str, net_long: int):
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE macro_indicators SET cot_net_long = ?
           WHERE date = (SELECT date FROM macro_indicators
                         WHERE date <= ? ORDER BY date DESC LIMIT 1)""",
        (net_long, report_date)
    )
    conn.commit()
    conn.close()


def insert_cb_event(event: dict) -> int:
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO cb_events (event_date, country, action, amount_tonnes, impact_score, source_url)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (event["event_date"], event.get("country", "CN"), event.get("action", "buy"),
         event.get("amount_tonnes"), event.get("impact_score", 15.0), event.get("source_url", ""))
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_latest_gold_price() -> dict | None:
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM gold_price ORDER BY timestamp DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_gold_price_history(period: str = "3m") -> list[dict]:
    """获取金价历史数据。

    Args:
        period: 1m, 3m, 1y, 3y, 5y
    """
    period_days = {
        "1m": 30, "3m": 90, "1y": 365,
        "3y": 1095, "5y": 1825,
    }
    days = period_days.get(period, 90)
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM gold_price WHERE timestamp >= ? ORDER BY timestamp ASC",
        (cutoff,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_macro() -> dict | None:
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM macro_indicators ORDER BY date DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_macro_history(days: int = 365) -> list[dict]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM macro_indicators WHERE date >= ? ORDER BY date ASC",
        (cutoff,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_cb_events(days: int = 30) -> list[dict]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM cb_events WHERE event_date >= ? ORDER BY event_date DESC",
        (cutoff,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_rule_score(data: dict) -> int:
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO rule_scores (calc_time, total_score, signal, confidence, indicator_scores, weights_used)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (data["calc_time"], data["total_score"], data["signal"],
         data["confidence"], json.dumps(data["indicator_scores"]),
         json.dumps(data["weights_used"]))
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_latest_score() -> dict | None:
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rule_scores ORDER BY calc_time DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["indicator_scores"] = json.loads(d["indicator_scores"])
        d["weights_used"] = json.loads(d["weights_used"])
        return d
    return None


def insert_prediction(data: dict) -> int:
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO prediction_log
           (pred_date, target_date, predicted_direction, predicted_change_pct,
            rule_score, llm_consensus, debate_transcript)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (data["pred_date"], data["target_date"], data["predicted_direction"],
         data.get("predicted_change_pct", 0), data["rule_score"],
         data["llm_consensus"], json.dumps(data.get("debate_transcript", {})))
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def backfill_prediction(pred_id: int, actual_change: float, is_correct: bool, error_reason: str = ""):
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE prediction_log
           SET actual_px_change = ?, is_correct = ?, error_reason = ?
           WHERE id = ?""",
        (actual_change, 1 if is_correct else 0, error_reason, pred_id)
    )
    conn.commit()
    conn.close()


def get_prediction_history(days: int = 90) -> list[dict]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT * FROM prediction_log
           WHERE pred_date >= ? AND actual_px_change IS NOT NULL
           ORDER BY pred_date DESC""",
        (cutoff,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_accuracy_stats() -> dict:
    """计算准确率统计"""
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()

    # 总准确率
    cursor.execute(
        "SELECT COUNT(*) as total, SUM(is_correct) as correct FROM prediction_log WHERE is_correct IS NOT NULL"
    )
    row = cursor.fetchone()
    total = row["total"] or 0
    correct = row["correct"] or 0

    # 滚动30日准确率
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    cursor.execute(
        "SELECT COUNT(*) as total, SUM(is_correct) as correct FROM prediction_log WHERE pred_date >= ? AND is_correct IS NOT NULL",
        (cutoff,)
    )
    row30 = cursor.fetchone()
    total30 = row30["total"] or 0
    correct30 = row30["correct"] or 0

    conn.close()

    return {
        "total_count": total,
        "correct_count": correct,
        "total_accuracy": round(correct / total, 3) if total > 0 else 0,
        "rolling_30d_count": total30,
        "rolling_30d_correct": correct30,
        "rolling_30d_accuracy": round(correct30 / total30, 3) if total30 > 0 else 0,
    }
```

- [ ] **Step 2: 提交**

```bash
git add gold-backend/db/queries.py
git commit -m "feat: database query layer for all tables"
```

### Task 7: 定时任务调度器

**Files:**
- Create: `gold-backend/scheduler.py`
- Modify: `gold-backend/main.py` (在startup中启动调度器)

- [ ] **Step 1: 创建 scheduler.py**

```python
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


@scheduler.scheduled_job("cron", hour="7-22", minute=f"*/60+{_jitter()}")
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
```

- [ ] **Step 2: 修改 main.py — 在startup事件中启动调度器**

在 `main.py` 的 import 区域添加：
```python
from scheduler import start_scheduler, stop_scheduler
```

修改 startup 函数：
```python
@app.on_event("startup")
def startup():
    init_db(DB_PATH)
    start_scheduler()
    print(f"Database initialized at {DB_PATH}")
    print("Scheduler started")

@app.on_event("shutdown")
def shutdown():
    stop_scheduler()
```

- [ ] **Step 3: 提交**

```bash
git add gold-backend/scheduler.py gold-backend/main.py
git commit -m "feat: scheduled data fetching jobs via apscheduler"
```

---

## Phase 3: 规则引擎与LLM

### Task 8: 规则打分引擎

**Files:**
- Create: `gold-backend/engine/__init__.py`
- Create: `gold-backend/engine/scorer.py`
- Create: `gold-backend/engine/weights.py`

- [ ] **Step 1: 创建 engine/weights.py**

```python
"""指标权重管理"""

# 初始权重（根据设计文档）
DEFAULT_WEIGHTS = {
    "tips_10y": 0.28,
    "dxy": 0.23,
    "spdr": 0.17,
    "cot": 0.15,
    "premium": 0.17,
}

WEIGHT_LIMITS = {
    "min": 0.05,
    "max": 0.40,
}


def get_weights() -> dict:
    """获取当前权重。后续可从rule_scores表读取最新权重。"""
    return DEFAULT_WEIGHTS.copy()


def adapt_weights(accuracy_map: dict[str, float]) -> dict:
    """根据各指标方向准确率动态调整权重。

    Args:
        accuracy_map: {"tips_10y": 0.72, "dxy": 0.65, ...}

    Returns:
        调整后的权重字典
    """
    current = get_weights()
    adjustments = {}

    avg_acc = sum(accuracy_map.values()) / len(accuracy_map) if accuracy_map else 0.5

    for key, current_w in current.items():
        acc = accuracy_map.get(key, avg_acc)
        if acc > avg_acc + 0.05:
            adjustments[key] = current_w + 0.02
        elif acc < avg_acc - 0.05:
            adjustments[key] = current_w - 0.02
        else:
            adjustments[key] = current_w

    # Clamp权重
    for key in adjustments:
        adjustments[key] = max(WEIGHT_LIMITS["min"], min(WEIGHT_LIMITS["max"], adjustments[key]))

    # 归一化到100%
    total = sum(adjustments.values())
    for key in adjustments:
        adjustments[key] = round(adjustments[key] / total, 4)

    return adjustments
```

- [ ] **Step 2: 创建 engine/scorer.py**

```python
"""六维指标加权评分引擎"""
import logging
from datetime import datetime
from engine.weights import get_weights

logger = logging.getLogger(__name__)


def _score_tips(tips_10y: float, tips_20d_avg: float | None) -> tuple[int, float]:
    """TIPS收益率评分。下降→利多黄金。
    
    Returns: (分数, 方向: 1=利多, -1=利空, 0=中性)
    """
    if tips_20d_avg is None:
        return 0, 0
    delta = tips_10y - tips_20d_avg
    if delta < -0.5:
        return 20, 1
    elif delta < -0.2:
        return 10, 1
    elif delta > 0.5:
        return -20, -1
    elif delta > 0.2:
        return -10, -1
    else:
        return 0, 0


def _score_dxy(dxy: float, dxy_20d_avg: float | None) -> tuple[int, float]:
    """美元指数评分。下降→利多黄金。"""
    if dxy_20d_avg is None:
        return 0, 0
    delta = dxy - dxy_20d_avg
    if delta < -1.5:
        return 15, 1
    elif delta < -0.5:
        return 8, 1
    elif delta > 1.5:
        return -15, -1
    elif delta > 0.5:
        return -8, -1
    else:
        return 0, 0


def _score_spdr(current: float, avg_5d: float | None) -> tuple[int, float]:
    """SPDR持仓变化评分。增持→利多。"""
    if avg_5d is None:
        return 0, 0
    delta = current - avg_5d
    if delta > 5:
        return 12, 1
    elif delta > 1:
        return 6, 1
    elif delta < -5:
        return -12, -1
    elif delta < -1:
        return -6, -1
    else:
        return 0, 0


def _score_cot(net_long_percentile: float | None) -> tuple[int, float]:
    """COMEX持仓评分。极端高位→回调风险（逆向信号）。"""
    if net_long_percentile is None:
        return 0, 0
    if net_long_percentile < 30:
        return 12, 1
    elif net_long_percentile > 80:
        return -12, -1
    else:
        return 0, 0


def _score_premium(premium: float, premium_mean: float | None, premium_std: float | None) -> tuple[int, float]:
    """上海溢价评分。溢价高于均值+1σ→国内需求旺盛→利多。"""
    if premium_mean is None or premium_std is None or premium_std == 0:
        return 0, 0
    z_score = (premium - premium_mean) / premium_std
    if z_score > 1.0:
        return 10, 1
    elif z_score < -1.0:
        return -10, -1
    else:
        return 0, 0


def _score_cb_event(cb_decay_weight: float, cb_action: str) -> tuple[int, float]:
    """央行购金事件评分。买入事件→脉冲式利多，按衰减权重计分。"""
    if cb_decay_weight <= 0:
        return 0, 0
    base_score = 20
    score = base_score * cb_decay_weight
    if cb_action == "buy":
        return int(score), 1
    elif cb_action == "sell":
        return -int(score), -1
    return 0, 0


def _calc_cb_decay_weight(event_date_str: str) -> float:
    """计算央行购金事件衰减权重。
    
    decay = 0.5^(days_elapsed / 2), days_elapsed=0时权重=1.0
    """
    try:
        event_date = datetime.strptime(event_date_str, "%Y-%m-%d")
        days_elapsed = (datetime.now() - event_date).days
        if days_elapsed < 0:
            return 1.0
        return max(0, 0.5 ** (days_elapsed / 2))
    except Exception:
        return 0.0


def calculate_score(macro_data: dict, cb_events: list[dict],
                    price_history: list[dict] | None = None,
                    macro_history: list[dict] | None = None) -> dict:
    """计算综合评分。

    Args:
        macro_data: 最新宏观指标 (from get_latest_macro)
        cb_events: 近期央行购金事件列表
        price_history: 历史金价 (用于计算溢价均值和标准差)
        macro_history: 历史宏观指标 (用于计算20日均值)

    Returns:
        dict: {total_score, signal, confidence, indicator_scores, weights_used}
    """
    weights = get_weights()

    # 从历史数据计算参考值
    tips_20d_avg = None
    dxy_20d_avg = None
    spdr_5d_avg = None
    premium_mean = None
    premium_std = None

    if macro_history and len(macro_history) >= 20:
        tips_vals = [r["tips_10y"] for r in macro_history[-20:] if r["tips_10y"] is not None]
        dxy_vals = [r["dxy"] for r in macro_history[-20:] if r["dxy"] is not None]
        if tips_vals:
            tips_20d_avg = sum(tips_vals) / len(tips_vals)
        if dxy_vals:
            dxy_20d_avg = sum(dxy_vals) / len(dxy_vals)

    if macro_history and len(macro_history) >= 5:
        spdr_vals = [r["spdr_tonnes"] for r in macro_history[-5:] if r["spdr_tonnes"] is not None]
        if spdr_vals:
            spdr_5d_avg = sum(spdr_vals) / len(spdr_vals)

    if price_history and len(price_history) >= 20:
        premiums = [r["premium"] for r in price_history[-20:] if r.get("premium") is not None]
        if premiums:
            premium_mean = sum(premiums) / len(premiums)
            variance = sum((p - premium_mean) ** 2 for p in premiums) / len(premiums)
            premium_std = variance ** 0.5

    # COT分位数：简化处理，从macro_history中计算
    cot_percentile = None
    if macro_data and macro_data.get("cot_net_long") is not None:
        if macro_history:
            cot_vals = sorted([r["cot_net_long"] for r in macro_history
                               if r.get("cot_net_long") is not None])
            if cot_vals:
                rank = sum(1 for v in cot_vals if v <= macro_data["cot_net_long"])
                cot_percentile = (rank / len(cot_vals)) * 100

    # 央行事件衰减权重
    cb_decay = 0.0
    cb_action = "buy"
    if cb_events:
        latest_cb = max(cb_events, key=lambda e: e["event_date"])
        cb_decay = _calc_cb_decay_weight(latest_cb["event_date"])
        cb_action = latest_cb.get("action", "buy")

    # 逐项评分
    tips_score, tips_dir = _score_tips(
        macro_data.get("tips_10y") or 0, tips_20d_avg)
    dxy_score, dxy_dir = _score_dxy(
        macro_data.get("dxy") or 100, dxy_20d_avg)
    spdr_score, spdr_dir = _score_spdr(
        macro_data.get("spdr_tonnes") or 800, spdr_5d_avg)
    cot_score, cot_dir = _score_cot(cot_percentile)
    premium_score, premium_dir = _score_premium(
        macro_data.get("premium") or 0, premium_mean, premium_std)
    cb_score, cb_dir = _score_cb_event(cb_decay, cb_action)

    indicator_scores = {
        "tips_10y": tips_score,
        "dxy": dxy_score,
        "spdr": spdr_score,
        "cot": cot_score,
        "premium": premium_score,
        "cb_event": cb_score,
    }

    directions = {
        "tips_10y": tips_dir,
        "dxy": dxy_dir,
        "spdr": spdr_dir,
        "cot": cot_dir,
        "premium": premium_dir,
        "cb_event": cb_dir,
    }

    # 加权计算总分
    total = 0
    for key, score in indicator_scores.items():
        if key == "cb_event":
            # 事件指标独立叠加
            w_cb = weights.get("premium", 0.17)
            total += score * (cb_decay * w_cb * 5)
        else:
            total += score * weights.get(key, 0.15)

    # 归一化到0-100
    total = max(0, min(100, total + 50))

    # 信号判断
    if total >= 80:
        signal = "极度看多"
    elif total >= 60:
        signal = "偏多"
    elif total >= 40:
        signal = "中性"
    elif total >= 20:
        signal = "偏空"
    else:
        signal = "极度看空"

    # 置信度(方向一致性)
    dirs = [v for v in directions.values() if v != 0]
    if dirs:
        max_dir_count = max(dirs.count(1), dirs.count(-1))
        confidence = round(max_dir_count / len(dirs), 2)
    else:
        confidence = 0.5

    return {
        "calc_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_score": int(total),
        "signal": signal,
        "confidence": confidence,
        "indicator_scores": indicator_scores,
        "weights_used": weights,
    }
```

- [ ] **Step 3: 提交**

```bash
git add gold-backend/engine/
git commit -m "feat: rule scoring engine with 6-factor weighted model"
```

### Task 9: LLM客户端适配器

**Files:**
- Create: `gold-backend/llm/__init__.py`
- Create: `gold-backend/llm/deepseek.py`
- Create: `gold-backend/llm/openai_client.py`

- [ ] **Step 1: 创建 llm/deepseek.py**

```python
"""DeepSeek API 客户端"""
import logging
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

logger = logging.getLogger(__name__)

_client = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    return _client


async def chat(messages: list[dict], model: str = "deepseek-chat",
               temperature: float = 0.3, max_tokens: int = 1024) -> str:
    """调用DeepSeek Chat API。

    Args:
        messages: OpenAI格式的消息列表
        model: 模型名称
        temperature: 创造性控制
        max_tokens: 最大输出token

    Returns:
        LLM回复文本
    """
    client = get_client()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.exception(f"DeepSeek API call failed: {e}")
        return f"[DeepSeek Error]: {str(e)}"
```

- [ ] **Step 2: 创建 llm/openai_client.py**

```python
"""OpenAI API 客户端"""
import logging
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_BASE_URL

logger = logging.getLogger(__name__)

_client = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    return _client


async def chat(messages: list[dict], model: str = "gpt-4o-mini",
               temperature: float = 0.3, max_tokens: int = 1024) -> str:
    """调用OpenAI Chat API。

    Args:
        messages: OpenAI格式的消息列表
        model: 模型名称（默认gpt-4o-mini 降低成本）
        temperature: 创造性控制
        max_tokens: 最大输出token

    Returns:
        LLM回复文本
    """
    client = get_client()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.exception(f"OpenAI API call failed: {e}")
        return f"[OpenAI Error]: {str(e)}"
```

- [ ] **Step 3: 提交**

```bash
git add gold-backend/llm/
git commit -m "feat: DeepSeek and OpenAI API client adapters"
```

### Task 10: 双LLM辩论引擎

**Files:**
- Create: `gold-backend/llm/debate.py`

- [ ] **Step 1: 创建 llm/debate.py**

```python
"""三阶段双LLM辩论编排器"""
import json
import asyncio
import logging
from datetime import date

from llm.deepseek import chat as ds_chat
from llm.openai_client import chat as oai_chat

logger = logging.getLogger(__name__)

SYSTEM_ANALYST = """你是一位资深黄金投资分析师，拥有20年全球宏观交易经验。
请基于提供的市场数据进行分析。你的回答应该：
1. 数据驱动，引用具体数字
2. 考虑多空两面
3. 给出明确的方向判断
4. 指出你的判断可能出错的条件（预注册反驳）
5. 用中文回答，专业但不晦涩"""

SYSTEM_CHALLENGER = """你是黄金市场分析师，你的任务是审查另一位分析师的判断。
找出对方逻辑中的漏洞、被忽略的风险因素、或过于自信的结论。
如果你的判断和对方一致，也要指出即使是正确的方向也存在什么风险。
对事不对人，保持专业。用中文回答，简洁直接，不超过200字。"""

SYSTEM_CONVERGE = """你已看到对方的质疑。请基于以下信息给出你的最终判断：
1. 你原本的分析
2. 对方的质疑
现在修正你的结论，或者坚持并解释为什么对方的质疑不成立。
用中文给出最终判断，包含：方向、置信度(1-5星)、核心依据。不超过200字。"""


def _build_analysis_prompt(market_data: dict, score: dict,
                           history_context: str = "") -> str:
    """构建分析prompt"""
    prompt = f"""## 市场数据 ({date.today().isoformat()})

| 指标 | 当前值 | 方向 |
|------|--------|------|
| 国际金价 | ${market_data.get('xau_usd', 'N/A')}/oz | - |
| 国内金价 | ¥{market_data.get('au9999', 'N/A')}/g | - |
| USD/CNY | {market_data.get('usd_cny', 'N/A')} | - |
| 上海溢价 | ¥{market_data.get('premium', 'N/A')}/g | - |
| 10Y TIPS | {market_data.get('tips_10y', 'N/A')}% | - |
| 美元指数 | {market_data.get('dxy', 'N/A')} | - |
| SPDR持仓 | {market_data.get('spdr_tonnes', 'N/A')}吨 | - |
| COMEX净多头 | {market_data.get('cot_net_long', 'N/A')}合约 | - |
| VIX | {market_data.get('vix', 'N/A')} | - |

## 规则引擎参考
- 综合评分: {score['total_score']}/100
- 信号: {score['signal']}
- 置信度: {score['confidence']}

## 各指标评分
{json.dumps(score['indicator_scores'], ensure_ascii=False)}
"""
    if history_context:
        prompt += f"\n## 近期预测回顾\n{history_context}\n"

    prompt += """
请回答：
1. 明日金价方向（涨↑/跌↓/平→）及核心判断依据
2. 最大的利多因素（一个）和最大的利空因素（一个）
3. 置信度（1-5星），以及什么情况会证明你判断错误
"""
    return prompt


def _build_challenge_prompt(opponent_analysis: str, market_summary: str) -> str:
    return f"""## 市场概况
{market_summary}

## 对方分析
{opponent_analysis}

请审视对方分析：有逻辑漏洞吗？忽略了什么风险？过于自信吗？"""


def _build_converge_prompt(my_original: str, opponent_challenge: str,
                           market_summary: str) -> str:
    return f"""## 市场概况
{market_summary}

## 你的原始分析
{my_original}

## 对方的质疑
{opponent_challenge}

在对方质疑的基础上修正你的结论。如果同意质疑，修改判断；如果不同意，解释原因。"""


def _market_summary(market_data: dict) -> str:
    return f"金价${market_data.get('xau_usd','N/A')}, TIPS {market_data.get('tips_10y','N/A')}%, DXY {market_data.get('dxy','N/A')}"


async def run_debate(market_data: dict, score: dict,
                     history_context: str = "") -> dict:
    """执行三阶段双LLM辩论。

    Returns:
        dict: {consensus, direction, confidence, debate_transcript}
    """
    analysis_prompt = _build_analysis_prompt(market_data, score, history_context)

    # === 阶段一：独立分析（并行） ===
    logger.info("Debate phase 1: independent analysis")
    ds_analysis, oai_analysis = await asyncio.gather(
        ds_chat([{"role": "system", "content": SYSTEM_ANALYST},
                 {"role": "user", "content": analysis_prompt}]),
        oai_chat([{"role": "system", "content": SYSTEM_ANALYST},
                  {"role": "user", "content": analysis_prompt}]),
    )

    # === 阶段二：交叉质疑（串行） ===
    logger.info("Debate phase 2: cross-challenge")
    market_sum = _market_summary(market_data)
    ds_challenge = await ds_chat([
        {"role": "system", "content": SYSTEM_CHALLENGER},
        {"role": "user", "content": _build_challenge_prompt(oai_analysis, market_sum)},
    ])
    oai_challenge = await oai_chat([
        {"role": "system", "content": SYSTEM_CHALLENGER},
        {"role": "user", "content": _build_challenge_prompt(ds_analysis, market_sum)},
    ])

    # === 阶段三：修正收敛（并行） ===
    logger.info("Debate phase 3: converge")
    ds_final, oai_final = await asyncio.gather(
        ds_chat([{"role": "system", "content": SYSTEM_CONVERGE},
                 {"role": "user", "content": _build_converge_prompt(ds_analysis, oai_challenge, market_sum)}]),
        oai_chat([{"role": "system", "content": SYSTEM_CONVERGE},
                  {"role": "user", "content": _build_converge_prompt(oai_analysis, ds_challenge, market_sum)}]),
    )

    # === 裁决合并 ===
    consensus = _merge_conclusions(ds_final, oai_final)
    direction = _extract_direction(consensus)

    return {
        "consensus": consensus,
        "direction": direction,
        "confidence": score["confidence"],
        "debate_transcript": {
            "deepseek_analysis": ds_analysis,
            "openai_analysis": oai_analysis,
            "deepseek_challenge": ds_challenge,
            "openai_challenge": oai_challenge,
            "deepseek_final": ds_final,
            "openai_final": oai_final,
        },
    }


def _merge_conclusions(ds_final: str, oai_final: str) -> str:
    """合并两个模型的最终结论"""
    # 简单策略：拼接两份结论
    return f"## DeepSeek 最终判断\n{ds_final}\n\n## OpenAI 最终判断\n{oai_final}"


def _extract_direction(consensus: str) -> str:
    """从结论文本中提取方向判断"""
    text = consensus.lower()
    up_signals = ["涨↑", "看多", "上涨", "bullish", "利多", "偏多"]
    down_signals = ["跌↓", "看空", "下跌", "bearish", "利空", "偏空"]

    up_count = sum(1 for s in up_signals if s in consensus)
    down_count = sum(1 for s in down_signals if s in consensus)

    if up_count > down_count:
        return "up"
    elif down_count > up_count:
        return "down"
    return "flat"


async def run_debate_streaming(market_data: dict, score: dict,
                               history_context: str = "") -> dict:
    """执行辩论并返回结构化结果（供SSE流式推送）。
    
    与run_debate功能相同，但返回结构包含中间阶段的文本，
    供前端逐阶段展示。
    """
    result = await run_debate(market_data, score, history_context)
    return result
```

- [ ] **Step 2: 提交**

```bash
git add gold-backend/llm/debate.py
git commit -m "feat: three-stage dual-LLM debate orchestrator"
```

---

## Phase 4: API层

### Task 11: REST API路由

**Files:**
- Create: `gold-backend/api/__init__.py`
- Create: `gold-backend/api/routes.py`
- Modify: `gold-backend/main.py` (注册路由)

- [ ] **Step 1: 创建 api/routes.py**

```python
"""API路由处理函数"""
import json
import asyncio
from datetime import date, datetime
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from config import DB_PATH
from db.queries import (
    get_latest_gold_price, get_gold_price_history,
    get_latest_macro, get_macro_history,
    get_recent_cb_events, get_latest_score,
    insert_rule_score, insert_prediction,
    get_prediction_history, get_accuracy_stats,
)
from engine.scorer import calculate_score
from llm.debate import run_debate

router = APIRouter()


@router.get("/api/dashboard")
def dashboard():
    """首页数据快照"""
    gold = get_latest_gold_price()
    macro = get_latest_macro()
    cb_events = get_recent_cb_events(30)
    score = get_latest_score()

    # 如果没有评分记录，实时计算
    if score is None and macro is not None:
        price_hist = get_gold_price_history("3m")
        macro_hist = get_macro_history(90)
        score = calculate_score(macro, cb_events, price_hist, macro_hist)

    return {
        "updated_at": datetime.now().isoformat(),
        "prices": gold,
        "macro": macro,
        "score": score,
        "cb_events": cb_events,
    }


@router.get("/api/price-history")
def price_history(period: str = Query("3m", regex="^(1m|3m|1y|3y|5y)$")):
    """金价历史数据"""
    return {
        "period": period,
        "data": get_gold_price_history(period),
    }


@router.get("/api/indicators")
def indicators():
    """宏观指标数据"""
    macro = get_latest_macro()
    history = get_macro_history(365)
    return {
        "latest": macro,
        "history": history,
    }


@router.get("/api/score")
def score():
    """最新规则打分"""
    result = get_latest_score()
    if result is None:
        # 实时计算
        macro = get_latest_macro()
        cb_events = get_recent_cb_events(30)
        if macro:
            result = calculate_score(macro, cb_events,
                                     get_gold_price_history("3m"),
                                     get_macro_history(90))
    return result


@router.get("/api/history/predictions")
def history_predictions(days: int = Query(90, ge=7, le=730)):
    """历史预测及准确率"""
    predictions = get_prediction_history(days)
    stats = get_accuracy_stats()
    return {
        "records": predictions,
        **stats,
    }


@router.post("/api/analysis")
async def analysis():
    """触发AI研判（SSE流式返回）"""
    gold = get_latest_gold_price()
    macro = get_latest_macro()
    cb_events = get_recent_cb_events(30)

    if macro is None:
        return {"error": "No macro data available. Run data fetcher first."}

    # 计算评分
    score_result = calculate_score(macro, cb_events,
                                   get_gold_price_history("3m"),
                                   get_macro_history(90))
    insert_rule_score(score_result)

    # 获取历史预测context
    stats = get_accuracy_stats()
    history_context = f"历史总准确率: {stats['total_accuracy']:.0%}, 近30日: {stats['rolling_30d_accuracy']:.0%}"

    # 合并market_data
    market_data = {**(gold or {}), **(macro or {})}

    async def event_stream():
        # 阶段一：评分完成
        yield f"event: status\ndata: {json.dumps({'phase': 'scoring', 'message': f'规则引擎: {score_result[\"total_score\"]}分 {score_result[\"signal\"]}', 'score': score_result}, ensure_ascii=False)}\n\n"

        # 阶段二：辩论
        yield f"event: status\ndata: {json.dumps({'phase': 'analysis', 'message': 'DeepSeek + OpenAI 独立分析中...'}, ensure_ascii=False)}\n\n"

        result = await run_debate(market_data, score_result, history_context)

        # 阶段三：结论
        transcript = result["debate_transcript"]
        yield f"event: partial\ndata: {json.dumps({'model': 'deepseek', 'content': transcript['deepseek_analysis'][:200]}, ensure_ascii=False)}\n\n"
        yield f"event: partial\ndata: {json.dumps({'model': 'openai', 'content': transcript['openai_analysis'][:200]}, ensure_ascii=False)}\n\n"
        yield f"event: status\ndata: {json.dumps({'phase': 'debate', 'message': '交叉辩论中...'}, ensure_ascii=False)}\n\n"
        yield f"event: partial\ndata: {json.dumps({'model': 'deepseek', 'content': transcript['deepseek_challenge'][:150]}, ensure_ascii=False)}\n\n"
        yield f"event: partial\ndata: {json.dumps({'model': 'openai', 'content': transcript['openai_challenge'][:150]}, ensure_ascii=False)}\n\n"
        yield f"event: status\ndata: {json.dumps({'phase': 'converge', 'message': '收敛一致，生成最终结论'}, ensure_ascii=False)}\n\n"

        yield f"event: result\ndata: {json.dumps({'consensus': result['consensus'], 'direction': result['direction'], 'confidence': result['confidence'], 'score': score_result['total_score']}, ensure_ascii=False)}\n\n"

        # 保存预测记录
        insert_prediction({
            "pred_date": date.today().isoformat(),
            "target_date": date.today().isoformat(),
            "predicted_direction": result["direction"],
            "predicted_change_pct": 0,
            "rule_score": score_result["total_score"],
            "llm_consensus": result["consensus"],
            "debate_transcript": transcript,
        })

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 2: 修改 main.py — 注册路由**

在路由导入之后添加：
```python
from api.routes import router
app.include_router(router)
```

- [ ] **Step 3: 提交**

```bash
git add gold-backend/api/ gold-backend/main.py
git commit -m "feat: REST API routes and SSE analysis endpoint"
```

---

## Phase 5: 前端

### Task 12: 前端基础设施 — Tailwind + 类型 + API客户端

**Files:**
- Modify: `gold-frontend/vite.config.ts`
- Modify: `gold-frontend/src/index.css`
- Create: `gold-frontend/src/types/index.ts`
- Create: `gold-frontend/src/api/client.ts`

- [ ] **Step 1: 配置 vite.config.ts (Tailwind + 代理)**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
```

- [ ] **Step 2: 配置Tailwind — 更新 src/index.css**

```css
@import "tailwindcss";

:root {
  --gold: #fbbf24;
  --gold-dark: #b45309;
  --bg-dark: #0f172a;
  --bg-card: #1e293b;
}

body {
  background: #0f172a;
  color: #f8fafc;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
```

- [ ] **Step 3: 创建类型定义 src/types/index.ts**

```typescript
export interface GoldPrice {
  id: number;
  timestamp: string;
  xau_usd: number;
  au9999: number;
  usd_cny: number;
  premium: number;
}

export interface MacroIndicator {
  id: number;
  date: string;
  tips_10y: number | null;
  dxy: number | null;
  spdr_tonnes: number | null;
  cot_net_long: number | null;
  vix: number | null;
}

export interface ScoreResult {
  calc_time: string;
  total_score: number;
  signal: string;
  confidence: number;
  indicator_scores: Record<string, number>;
  weights_used: Record<string, number>;
}

export interface CBEvent {
  id: number;
  event_date: string;
  country: string;
  action: string;
  amount_tonnes: number | null;
  impact_score: number;
  source_url: string;
}

export interface DashboardData {
  updated_at: string;
  prices: GoldPrice | null;
  macro: MacroIndicator | null;
  score: ScoreResult | null;
  cb_events: CBEvent[];
}

export interface AccuracyStats {
  records: PredictionRecord[];
  total_count: number;
  correct_count: number;
  total_accuracy: number;
  rolling_30d_count: number;
  rolling_30d_correct: number;
  rolling_30d_accuracy: number;
}

export interface PredictionRecord {
  id: number;
  pred_date: string;
  target_date: string;
  predicted_direction: string;
  predicted_change_pct: number;
  rule_score: number;
  llm_consensus: string;
  actual_px_change: number | null;
  is_correct: number | null;
  error_reason: string | null;
}

export interface SSEEvent {
  type: 'status' | 'partial' | 'result';
  phase?: string;
  message?: string;
  model?: string;
  content?: string;
  consensus?: string;
  direction?: string;
  confidence?: number;
  score?: number;
}
```

- [ ] **Step 4: 创建 API客户端 src/api/client.ts**

```typescript
import type { DashboardData, AccuracyStats, ScoreResult, SSEEvent } from '../types';

const BASE = '/api';

export async function fetchDashboard(): Promise<DashboardData> {
  const res = await fetch(`${BASE}/dashboard`);
  if (!res.ok) throw new Error(`Dashboard fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchPriceHistory(period: string): Promise<{ period: string; data: any[] }> {
  const res = await fetch(`${BASE}/price-history?period=${period}`);
  return res.json();
}

export async function fetchIndicators(): Promise<{ latest: any; history: any[] }> {
  const res = await fetch(`${BASE}/indicators`);
  return res.json();
}

export async function fetchScore(): Promise<ScoreResult> {
  const res = await fetch(`${BASE}/score`);
  return res.json();
}

export async function fetchAccuracy(days: number = 90): Promise<AccuracyStats> {
  const res = await fetch(`${BASE}/history/predictions?days=${days}`);
  return res.json();
}

export function createSSEConnection(
  onEvent: (event: SSEEvent) => void,
  onError?: (err: Event) => void
): EventSource {
  const source = new EventSource(`${BASE}/analysis`);

  source.addEventListener('status', (e) => {
    const data = JSON.parse(e.data);
    onEvent({ type: 'status', ...data });
  });

  source.addEventListener('partial', (e) => {
    const data = JSON.parse(e.data);
    onEvent({ type: 'partial', ...data });
  });

  source.addEventListener('result', (e) => {
    const data = JSON.parse(e.data);
    onEvent({ type: 'result', ...data });
  });

  source.onerror = (err) => {
    if (onError) onError(err);
    source.close();
  };

  return source;
}
```

- [ ] **Step 5: 提交**

```bash
git add gold-frontend/
git commit -m "feat: frontend base config, types, and API client"
```

### Task 13: 自定义Hook

**Files:**
- Create: `gold-frontend/src/hooks/useDashboard.ts`
- Create: `gold-frontend/src/hooks/useSSE.ts`

- [ ] **Step 1: 创建 hooks/useDashboard.ts**

```typescript
import { useState, useEffect, useCallback } from 'react';
import type { DashboardData, AccuracyStats } from '../types';
import { fetchDashboard, fetchAccuracy } from '../api/client';

export function useDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [accuracy, setAccuracy] = useState<AccuracyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [dash, acc] = await Promise.all([
        fetchDashboard(),
        fetchAccuracy(90),
      ]);
      setData(dash);
      setAccuracy(acc);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return { data, accuracy, loading, error, refresh: load };
}
```

- [ ] **Step 2: 创建 hooks/useSSE.ts**

```typescript
import { useState, useRef, useCallback } from 'react';
import type { SSEEvent } from '../types';
import { createSSEConnection } from '../api/client';

export function useSSE() {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [status, setStatus] = useState<string>('');
  const [result, setResult] = useState<SSEEvent | null>(null);
  const [loading, setLoading] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);

  const start = useCallback(() => {
    setLoading(true);
    setEvents([]);
    setStatus('连接中...');
    setResult(null);

    if (sourceRef.current) {
      sourceRef.current.close();
    }

    const source = createSSEConnection(
      (event) => {
        setEvents(prev => [...prev, event]);
        if (event.type === 'status') {
          setStatus(event.message || event.phase || '');
        }
        if (event.type === 'result') {
          setResult(event);
          setLoading(false);
          source.close();
        }
      },
      (err) => {
        console.error('SSE error:', err);
        setStatus('连接失败');
        setLoading(false);
      }
    );

    sourceRef.current = source;
  }, []);

  const stop = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }
    setLoading(false);
  }, []);

  return { events, status, result, loading, start, stop };
}
```

- [ ] **Step 3: 提交**

```bash
git add gold-frontend/src/hooks/
git commit -m "feat: useDashboard and useSSE custom hooks"
```

### Task 14: 展示组件 — PriceTickerBar, MacroCardList, RiskPanel

**Files:**
- Create: `gold-frontend/src/components/PriceTickerBar.tsx`
- Create: `gold-frontend/src/components/MacroCardList.tsx`
- Create: `gold-frontend/src/components/RiskPanel.tsx`

- [ ] **Step 1: 创建 PriceTickerBar.tsx**

```tsx
import type { GoldPrice, ScoreResult } from '../types';

function TickerItem({ label, value, change, color = 'text-yellow-400' }: {
  label: string; value: string; change?: string; color?: string;
}) {
  return (
    <div className="text-center px-3">
      <div className="text-xs text-slate-400 whitespace-nowrap">{label}</div>
      <div className={`text-lg font-bold ${color}`}>{value}</div>
      {change && <div className="text-xs text-green-400">{change}</div>}
    </div>
  );
}

export default function PriceTickerBar({ prices, score }: {
  prices: GoldPrice | null;
  score: ScoreResult | null;
}) {
  if (!prices) return null;

  const signalColors: Record<string, string> = {
    '极度看多': 'text-green-400',
    '偏多': 'text-green-300',
    '中性': 'text-yellow-400',
    '偏空': 'text-orange-400',
    '极度看空': 'text-red-400',
  };

  return (
    <div className="bg-slate-900 border-b border-slate-700 py-3">
      <div className="max-w-7xl mx-auto flex justify-around items-center flex-wrap gap-y-2">
        <TickerItem label="国际金价 XAU/USD" value={`$${prices.xau_usd.toFixed(2)}`} />
        <TickerItem label="国内金价 AU9999" value={`¥${prices.au9999.toFixed(2)}/g`} />
        <TickerItem label="USD/CNY" value={prices.usd_cny.toFixed(4)} color="text-slate-200" />
        <TickerItem
          label="上海溢价"
          value={`¥${prices.premium.toFixed(1)}/g`}
          color={prices.premium > 0 ? 'text-green-400' : 'text-red-400'}
        />
        {score && (
          <div className="text-center px-3">
            <div className="text-xs text-slate-400">AI综合评分</div>
            <div className="text-2xl font-extrabold text-yellow-400">{score.total_score}</div>
            <div className={`text-xs ${signalColors[score.signal] || 'text-slate-400'}`}>
              {score.signal}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 创建 MacroCardList.tsx**

```tsx
import type { MacroIndicator } from '../types';

function MacroCard({ name, value, unit, signal, detail }: {
  name: string; value: string; unit: string; signal?: 'bullish' | 'bearish' | 'neutral' | 'crowded';
  detail?: string;
}) {
  const signalColor = {
    bullish: 'text-green-400',
    bearish: 'text-red-400',
    neutral: 'text-yellow-400',
    crowded: 'text-orange-400',
  };

  return (
    <div className="flex justify-between items-center p-3 bg-slate-800 rounded-lg hover:bg-slate-700 transition">
      <div>
        <div className="text-sm font-medium">{name}</div>
        {detail && <div className="text-xs text-slate-500">{detail}</div>}
      </div>
      <div className="text-right">
        <div className="text-lg font-bold">{value}</div>
        {signal && (
          <div className={`text-xs ${signalColor[signal]}`}>
            {signal === 'bullish' ? '▼ 利好' : signal === 'bearish' ? '▲ 利空' : signal === 'crowded' ? '⚠ 拥挤' : '— 中性'}
          </div>
        )}
      </div>
    </div>
  );
}

export default function MacroCardList({ macro }: { macro: MacroIndicator | null }) {
  if (!macro) return null;

  const cards = [
    { name: '10Y TIPS', value: `${macro.tips_10y?.toFixed(2) ?? '-'}%`, unit: '%', detail: '实际利率' },
    { name: '美元指数 DXY', value: macro.dxy?.toFixed(2) ?? '-', unit: '', detail: '计价货币' },
    { name: 'SPDR持仓', value: `${macro.spdr_tonnes?.toFixed(1) ?? '-'}t`, unit: 't', detail: '黄金ETF' },
    { name: 'COMEX净多头', value: macro.cot_net_long != null ? `${(macro.cot_net_long / 1000).toFixed(0)}k` : '-', unit: '', detail: '投机仓位' },
    { name: 'VIX', value: macro.vix?.toFixed(1) ?? '-', unit: '', detail: '恐慌指数' },
  ];

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold text-slate-400 mb-1">🏦 宏观驱动指标</h3>
      {cards.map(c => (
        <MacroCard key={c.name} {...c} />
      ))}
    </div>
  );
}
```

- [ ] **Step 3: 创建 RiskPanel.tsx**

```tsx
import type { MacroIndicator, CBEvent } from '../types';

function RiskChip({ label, value, status }: {
  label: string; value: string; status: 'low' | 'normal' | 'high' | 'active';
}) {
  const bg = {
    low: 'bg-emerald-900/30 text-emerald-400 border-emerald-800',
    normal: 'bg-slate-800 text-slate-300 border-slate-700',
    high: 'bg-orange-900/30 text-orange-400 border-orange-800',
    active: 'bg-blue-900/30 text-blue-400 border-blue-800',
  };

  return (
    <div className={`flex justify-between items-center p-3 rounded-lg border ${bg[status]}`}>
      <span className="text-sm">{label}</span>
      <span className="font-semibold">{value}</span>
    </div>
  );
}

export default function RiskPanel({ macro, cbEvents }: {
  macro: MacroIndicator | null;
  cbEvents: CBEvent[];
}) {
  if (!macro) return null;

  const hasActiveCB = cbEvents.length > 0 &&
    (new Date().getTime() - new Date(cbEvents[0].event_date).getTime()) < 3 * 86400000;

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold text-slate-400 mb-1">⚠️ 风险信号</h3>
      <RiskChip
        label="VIX 恐慌指数"
        value={macro.vix != null ? `${macro.vix.toFixed(1)}` : '-'}
        status={(macro.vix ?? 0) > 25 ? 'high' : 'low'}
      />
      <RiskChip
        label="COMEX投机拥挤"
        value={macro.cot_net_long != null ? `${(macro.cot_net_long / 1000).toFixed(0)}k` : '-'}
        status="normal"
      />
      <RiskChip
        label="央行购金事件"
        value={hasActiveCB ? '🟢 活跃' : '⚪ 静默'}
        status={hasActiveCB ? 'active' : 'normal'}
      />
      <RiskChip
        label="上海溢价"
        value="--"
        status="normal"
      />
    </div>
  );
}
```

- [ ] **Step 4: 提交**

```bash
git add gold-frontend/src/components/PriceTickerBar.tsx gold-frontend/src/components/MacroCardList.tsx gold-frontend/src/components/RiskPanel.tsx
git commit -m "feat: PriceTickerBar, MacroCardList, RiskPanel components"
```

### Task 15: PriceChart — ECharts走势图

**Files:**
- Create: `gold-frontend/src/components/PriceChart.tsx`

- [ ] **Step 1: 创建 PriceChart.tsx**

```tsx
import { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import { fetchPriceHistory } from '../api/client';

type TimeRange = '1m' | '3m' | '1y' | '3y' | '5y';

export default function PriceChart() {
  const [timeRange, setTimeRange] = useState<TimeRange>('3m');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchPriceHistory(timeRange)
      .then(res => setData(res.data || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [timeRange]);

  const ranges: TimeRange[] = ['1m', '3m', '1y', '3y', '5y'];

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 20, right: 60, bottom: 30, left: 60 },
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: 'rgba(30,41,59,0.95)',
      borderColor: '#475569',
      textStyle: { color: '#f8fafc', fontSize: 12 },
    },
    xAxis: {
      type: 'category' as const,
      data: data.map(d => d.timestamp?.slice(0, 10) || ''),
      axisLabel: { color: '#94a3b8', fontSize: 10 },
      axisLine: { lineStyle: { color: '#334155' } },
    },
    yAxis: [
      {
        type: 'value' as const,
        name: 'USD/oz',
        nameTextStyle: { color: '#94a3b8' },
        axisLabel: { color: '#94a3b8', formatter: '${value}' },
        splitLine: { lineStyle: { color: '#1e293b' } },
      },
      {
        type: 'value' as const,
        name: '¥/g',
        nameTextStyle: { color: '#94a3b8' },
        axisLabel: { color: '#94a3b8', formatter: '¥{value}' },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: 'XAU/USD',
        type: 'line',
        data: data.map(d => d.xau_usd),
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#fbbf24', width: 2 },
        areaStyle: {
          color: {
            type: 'linear' as const, x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(251,191,36,0.3)' },
              { offset: 1, color: 'rgba(251,191,36,0.02)' },
            ],
          },
        },
      },
      {
        name: 'AU9999',
        type: 'line',
        yAxisIndex: 1,
        data: data.map(d => d.au9999),
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#f97316', width: 1.5 },
      },
    ],
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-400">📈 金价走势</h3>
        <div className="flex gap-1">
          {ranges.map(r => (
            <button
              key={r}
              onClick={() => setTimeRange(r)}
              className={`px-2.5 py-1 text-xs rounded-full transition ${
                timeRange === r
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}
            >
              {r === '1m' ? '1月' : r === '3m' ? '3月' : r === '1y' ? '1年' : r === '3y' ? '3年' : '5年'}
            </button>
          ))}
        </div>
      </div>
      {loading ? (
        <div className="h-72 flex items-center justify-center text-slate-500">加载中...</div>
      ) : (
        <ReactECharts option={option} style={{ height: 280 }} theme="dark" />
      )}
    </div>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add gold-frontend/src/components/PriceChart.tsx
git commit -m "feat: PriceChart component with ECharts and time range selector"
```

### Task 16: AIAnalysisPanel — SSE流式辩论展示

**Files:**
- Create: `gold-frontend/src/components/AIAnalysisPanel.tsx`
- Create: `gold-frontend/src/components/DebateStreamView.tsx`

- [ ] **Step 1: 创建 DebateStreamView.tsx**

```tsx
import { useEffect, useRef } from 'react';
import type { SSEEvent } from '../types';

export default function DebateStreamView({ events, status }: {
  events: SSEEvent[];
  status: string;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  return (
    <div className="bg-slate-900 rounded-lg p-3 max-h-80 overflow-y-auto text-sm">
      <div className="text-blue-400 mb-2">🔄 {status}</div>
      {events
        .filter(e => e.type === 'partial' || e.type === 'status')
        .map((e, i) => (
          <div key={i} className={`mb-2 pb-2 border-b border-slate-800 ${
            e.model === 'deepseek' ? 'text-emerald-400' : 'text-violet-400'
          }`}>
            {e.type === 'status' && (
              <div className="text-slate-500 text-xs">--- {e.message} ---</div>
            )}
            {e.model && (
              <div className="text-xs font-semibold mb-1">
                {e.model === 'deepseek' ? '🤖 DeepSeek' : '🧠 OpenAI'}
              </div>
            )}
            {e.content && <div className="text-slate-300 text-xs leading-relaxed">{e.content}</div>}
          </div>
        ))}
      <div ref={bottomRef} />
    </div>
  );
}
```

- [ ] **Step 2: 创建 AIAnalysisPanel.tsx**

```tsx
import type { ScoreResult } from '../types';
import { useSSE } from '../hooks/useSSE';
import DebateStreamView from './DebateStreamView';

function ScoreBadge({ score }: { score: ScoreResult }) {
  const colors: Record<string, string> = {
    '极度看多': 'bg-green-600',
    '偏多': 'bg-green-500',
    '中性': 'bg-yellow-500',
    '偏空': 'bg-orange-500',
    '极度看空': 'bg-red-600',
  };

  return (
    <div className="flex items-center gap-4 p-4 bg-slate-800 rounded-lg">
      <div className="relative w-16 h-16 flex items-center justify-center">
        <svg className="w-16 h-16 -rotate-90" viewBox="0 0 36 36">
          <circle cx="18" cy="18" r="15.5" fill="none" stroke="#334155" strokeWidth="3" />
          <circle cx="18" cy="18" r="15.5" fill="none" stroke="#fbbf24"
            strokeWidth="3" strokeDasharray={`${score.total_score} 100`}
            strokeLinecap="round" />
        </svg>
        <span className="absolute text-lg font-bold text-yellow-400">{score.total_score}</span>
      </div>
      <div>
        <span className={`px-2 py-0.5 rounded text-xs font-semibold text-white ${colors[score.signal] || 'bg-slate-500'}`}>
          {score.signal}
        </span>
        <div className="text-xs text-slate-400 mt-1">
          置信度: {(score.confidence * 100).toFixed(0)}%
        </div>
      </div>
    </div>
  );
}

export default function AIAnalysisPanel({ score }: { score: ScoreResult | null }) {
  const { events, status, result, loading, start, stop } = useSSE();

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-slate-400">🧠 AI投资研判</h3>

      {score && <ScoreBadge score={score} />}

      <button
        onClick={loading ? stop : start}
        disabled={loading}
        className={`py-2 px-4 rounded-lg font-medium text-sm transition ${
          loading
            ? 'bg-red-600/20 text-red-400 border border-red-800'
            : 'bg-blue-600 hover:bg-blue-500 text-white'
        }`}
      >
        {loading ? '⏹ 停止' : '🚀 生成AI研判'}
      </button>

      {events.length > 0 && <DebateStreamView events={events} status={status} />}

      {result && (
        <div className="bg-emerald-900/20 border border-emerald-800 rounded-lg p-4">
          <div className="text-xs text-emerald-400 mb-1">📋 最终结论</div>
          <div className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
            {result.consensus}
          </div>
          {result.direction && (
            <div className="mt-2 flex gap-2 text-xs">
              <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                方向: {{ up: '涨↑', down: '跌↓', flat: '平→' }[result.direction]}
              </span>
              <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                置信度: {((result.confidence ?? 0) * 100).toFixed(0)}%
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: 提交**

```bash
git add gold-frontend/src/components/AIAnalysisPanel.tsx gold-frontend/src/components/DebateStreamView.tsx
git commit -m "feat: AI analysis panel with SSE streaming debate display"
```

### Task 17: AccuracyChart — 历史预测准确率

**Files:**
- Create: `gold-frontend/src/components/AccuracyChart.tsx`

- [ ] **Step 1: 创建 AccuracyChart.tsx**

```tsx
import { useState } from 'react';
import ReactECharts from 'echarts-for-react';
import type { AccuracyStats } from '../types';

export default function AccuracyChart({ accuracy }: { accuracy: AccuracyStats | null }) {
  const [expanded, setExpanded] = useState(false);

  if (!accuracy || accuracy.total_count === 0) {
    return (
      <div className="p-3 bg-slate-800/50 rounded-lg text-center text-xs text-slate-500">
        暂无预测记录 — 生成AI研判并等待T+1验证后显示
      </div>
    );
  }

  const dailyData: { date: string; correct: number }[] = [];
  const records = accuracy.records || [];
  let runningCorrect = 0;
  let runningTotal = 0;

  [...records].reverse().forEach(r => {
    runningTotal++;
    if (r.is_correct === 1) runningCorrect++;
    dailyData.push({
      date: r.pred_date,
      correct: runningTotal > 0 ? runningCorrect / runningTotal : 0,
    });
  });

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 10, right: 20, bottom: 25, left: 45 },
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: 'rgba(30,41,59,0.95)',
      borderColor: '#475569',
      textStyle: { color: '#f8fafc', fontSize: 11 },
      formatter: (params: any) => {
        const val = params[0]?.value;
        return `累计准确率: ${(val * 100).toFixed(0)}%`;
      },
    },
    xAxis: {
      type: 'category' as const,
      data: dailyData.map(d => d.date?.slice(5) || ''),
      axisLabel: { color: '#64748b', fontSize: 9 },
      axisLine: { lineStyle: { color: '#334155' } },
    },
    yAxis: {
      type: 'value' as const,
      min: 0,
      max: 1,
      axisLabel: { color: '#64748b', fontSize: 10, formatter: (v: number) => `${(v * 100).toFixed(0)}%` },
      splitLine: { lineStyle: { color: '#1e293b' } },
    },
    series: [{
      name: '累计准确率',
      type: 'line',
      data: dailyData.map(d => d.correct),
      smooth: false,
      symbol: 'none',
      lineStyle: { color: '#22c55e', width: 1.5 },
      markLine: {
            silent: true,
            data: [{ yAxis: 0.5, label: { formatter: '50%', color: '#64748b', fontSize: 10 }, lineStyle: { color: '#475569', type: 'dashed' } }],
      },
    }],
  };

  return (
    <div className="border border-slate-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 bg-slate-800 hover:bg-slate-700 transition text-left"
      >
        <div>
          <span className="text-sm font-semibold text-slate-300">📊 历史预测准确率</span>
          <span className="ml-2 text-xs text-slate-500">
            {accuracy.total_count}次预测
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="text-green-400">
            累计 {(accuracy.total_accuracy * 100).toFixed(0)}%
          </span>
          <span className="text-blue-400">
            30日 {(accuracy.rolling_30d_accuracy * 100).toFixed(0)}%
          </span>
          <span className="text-slate-500">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {expanded && (
        <div className="p-3 bg-slate-900">
          <div className="flex gap-4 mb-3 text-xs">
            <div className="px-3 py-1.5 bg-slate-800 rounded">
              <span className="text-slate-400">总次数 </span>
              <span className="text-white font-semibold">{accuracy.total_count}</span>
            </div>
            <div className="px-3 py-1.5 bg-slate-800 rounded">
              <span className="text-slate-400">正确 </span>
              <span className="text-green-400 font-semibold">{accuracy.correct_count}</span>
            </div>
            <div className="px-3 py-1.5 bg-slate-800 rounded">
              <span className="text-slate-400">错误 </span>
              <span className="text-red-400 font-semibold">{accuracy.total_count - accuracy.correct_count}</span>
            </div>
          </div>
          <ReactECharts option={option} style={{ height: 180 }} theme="dark" />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add gold-frontend/src/components/AccuracyChart.tsx
git commit -m "feat: historical prediction accuracy chart"
```

---

## Phase 6: 组装与集成

### Task 18: App.tsx 组装所有组件

**Files:**
- Modify: `gold-frontend/src/App.tsx`
- Create: `gold-frontend/src/App.css` (可选，如果不用可以删除)

- [ ] **Step 1: 重写 App.tsx**

```tsx
import { useDashboard } from './hooks/useDashboard';
import PriceTickerBar from './components/PriceTickerBar';
import PriceChart from './components/PriceChart';
import MacroCardList from './components/MacroCardList';
import AIAnalysisPanel from './components/AIAnalysisPanel';
import AccuracyChart from './components/AccuracyChart';
import RiskPanel from './components/RiskPanel';

export default function App() {
  const { data, accuracy, loading, error, refresh } = useDashboard();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="text-yellow-400 text-4xl mb-4">🥇</div>
          <div className="text-slate-400">加载黄金投资数据...</div>
          <div className="text-xs text-slate-600 mt-2">首次启动可能需要等待数据抓取</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-400 text-lg mb-2">加载失败</div>
          <div className="text-slate-500 text-sm mb-4">{error}</div>
          <button onClick={refresh} className="px-4 py-2 bg-blue-600 rounded-lg text-sm hover:bg-blue-500">
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950">
      <PriceTickerBar prices={data?.prices ?? null} score={data?.score ?? null} />

      <main className="max-w-7xl mx-auto p-4 space-y-4">
        {/* Row 1: Chart + Macro */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-lg p-4">
            <PriceChart />
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <MacroCardList macro={data?.macro ?? null} />
          </div>
        </div>

        {/* Accuracy Chart */}
        <AccuracyChart accuracy={accuracy} />

        {/* Row 3: AI + Risk */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-lg p-4">
            <AIAnalysisPanel score={data?.score ?? null} />
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <RiskPanel macro={data?.macro ?? null} cbEvents={data?.cb_events ?? []} />
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-xs text-slate-600 py-4 border-t border-slate-800">
          <p>⚠️ 以上AI分析不构成投资建议，仅供研究参考</p>
          <p className="mt-1">数据来源: akshare | yfinance | FRED | CFTC | 新浪财经</p>
        </div>
      </main>
    </div>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add gold-frontend/src/App.tsx
git commit -m "feat: assemble all components in App.tsx"
```

### Task 19: 后端每日回填预测验证

**Files:**
- Create: `gold-backend/scheduler_verify.py`
- Modify: `gold-backend/scheduler.py` (注册验证任务)

- [ ] **Step 1: 创建 scheduler_verify.py**

```python
"""每日预测验证：T+1回填实际涨跌"""
import logging
from datetime import date, timedelta
from config import DB_PATH
from db.queries import get_prediction_history, backfill_prediction, get_gold_price_history

logger = logging.getLogger(__name__)


def verify_yesterday_predictions():
    """回填昨日预测的实际结果"""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    predictions = get_prediction_history(2)
    
    # 获取昨日金价变化
    price_history = get_gold_price_history("1m")
    if not price_history or len(price_history) < 2:
        logger.warning("Not enough price data for verification")
        return

    # 取昨日和前一日的au9999
    prices_by_date = {}
    for p in price_history:
        d = p["timestamp"][:10] if isinstance(p["timestamp"], str) else str(p["timestamp"])[:10]
        if d not in prices_by_date:
            prices_by_date[d] = p

    for pred in predictions:
        if pred.get("actual_px_change") is not None:
            continue  # 已经验证过

        target = pred["target_date"]
        pred_date = pred["pred_date"]

        # 获取预测日和目标日的金价
        today_price = prices_by_date.get(target)
        yesterday_price = prices_by_date.get(pred_date)

        if today_price and yesterday_price:
            actual_change = ((today_price["au9999"] - yesterday_price["au9999"]) / yesterday_price["au9999"]) * 100
            actual_change = round(actual_change, 2)

            predicted_dir = pred["predicted_direction"]
            if (predicted_dir == "up" and actual_change > 0) or \
               (predicted_dir == "down" and actual_change < 0):
                is_correct = True
                error_reason = ""
            else:
                is_correct = False
                error_reason = f"预测{predicted_dir}, 实际变化{actual_change:+.2f}%"

            backfill_prediction(pred["id"], actual_change, is_correct, error_reason)
            logger.info(f"Verified prediction {pred['id']}: {'✓' if is_correct else '✗'} ({actual_change:+.2f}%)")
```

- [ ] **Step 2: 在 scheduler.py 中添加验证任务**

在scheduler.py末尾添加：
```python
from scheduler_verify import verify_yesterday_predictions

@scheduler.scheduled_job("cron", hour="9", minute="15")
def job_verify_predictions():
    """每日09:15回填昨日预测结果"""
    logger.info("Job: verify yesterday predictions")
    verify_yesterday_predictions()
```

- [ ] **Step 3: 提交**

```bash
git add gold-backend/scheduler_verify.py gold-backend/scheduler.py
git commit -m "feat: daily prediction verification and backfill"
```

### Task 20: 端到端验证与README

**Files:**
- Create: `README.md`

- [ ] **Step 1: 创建 README.md**

```markdown
# 黄金投资决策网站

免费数据驱动的黄金投资辅助决策工具。规则引擎 + DeepSeek/OpenAI双模型辩论。

## 快速开始

### 1. 环境变量
在 `gold-backend/.env` 中配置：
```
DEEPSEEK_API_KEY=sk-xxx
OPENAI_API_KEY=sk-xxx
FRED_API_KEY=xxx  # 可选，免费注册: https://fred.stlouisfed.org/docs/api/api_key.html
```

### 2. 启动后端
```bash
cd gold-backend
pip install -r requirements.txt
python main.py
# → http://localhost:8000
# 首次启动自动创建数据库并执行初始数据抓取
```

### 3. 启动前端
```bash
cd gold-frontend
npm install
npm run dev
# → http://localhost:5173
```

### 4. API检查
```bash
curl http://localhost:8000/health           # {"status":"ok"}
curl http://localhost:8000/api/dashboard     # 首页数据快照
```

## 技术栈
- **前端**: React 19 + Vite 6 + TypeScript + ECharts + Tailwind CSS
- **后端**: Python FastAPI + SQLite + akshare + yfinance
- **AI**: DeepSeek API + OpenAI API 双模型辩论
- **定时任务**: apscheduler

## 免责声明
本网站提供的所有分析和预测仅供参考研究，不构成投资建议。
```

- [ ] **Step 2: 端到端验证**

启动后端：
```bash
cd gold-backend
python main.py
# 确认 http://localhost:8000/health → {"status":"ok"}
# 确认 http://localhost:8000/api/dashboard 返回数据
```

启动前端：
```bash
cd gold-frontend
npm run dev
# 确认 http://localhost:5173 能加载页面
# 确认 PriceTickerBar 显示数据
# 确认 PriceChart 显示图表
```

- [ ] **Step 3: 最终提交**

```bash
git add README.md
git commit -m "docs: README with quickstart instructions"
```

---

## 实施顺序依赖

```
Task 1 (Project Init)
  ├── Task 2 (Backend Skeleton)
  │     ├── Task 3 (Gold Price Fetcher)
  │     ├── Task 4 (Macro Fetcher)
  │     ├── Task 5 (COT + CB Event Fetcher)
  │     ├── Task 6 (DB Queries)
  │     └── Task 7 (Scheduler)
  ├── Task 8 (Scoring Engine)
  ├── Task 9 (LLM Clients)
  ├── Task 10 (Debate Engine)
  ├── Task 11 (API Routes)
  ├── Task 12 (Frontend Base)
  │     └── Task 13 (Hooks)
  │           ├── Task 14 (Display Components)
  │           ├── Task 15 (PriceChart)
  │           ├── Task 16 (AIAnalysisPanel)
  │           └── Task 17 (AccuracyChart)
  ├── Task 18 (App.tsx Assembly)
  ├── Task 19 (Verification Scheduler)
  └── Task 20 (README + E2E)
```

Tasks 3-7可并行，Tasks 14-17可并行。
