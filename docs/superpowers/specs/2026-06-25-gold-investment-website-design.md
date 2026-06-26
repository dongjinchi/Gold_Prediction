# 黄金投资决策网站 — 系统设计文档

**日期**: 2026-06-25  
**状态**: 设计完成，待审核  
**目标用户**: 短线黄金投资者  
**核心定位**: 免费数据驱动 + 规则引擎 + 双LLM辩论协同的黄金投资决策工具

---

## 一、系统架构

### 1.1 整体架构

前后端分离架构：React 静态前端 + Python FastAPI 后端。

```
用户浏览器
    │
    ├── HTTP REST API ──→  Python FastAPI 后端
    │                            │
    └── SSE (流式) ──────────→   ├── 数据采集模块 (akshare/yfinance/FRED/CFTC)
                                 ├── 规则打分引擎 (6维加权评分)
                                 ├── 双LLM辩论引擎 (DeepSeek+OpenAI)
                                 ├── SQLite 数据库
                                 └── 定时任务调度器
```

### 1.2 部署策略

| 阶段 | 前端 | 后端 |
|------|------|------|
| 开发 | 本机 `npm run dev` | 本机 `python main.py` |
| 生产 | Cloudflare Pages (免费) | Railway/Render (免费额度) |

### 1.3 技术栈

| 层 | 选型 |
|----|------|
| 前端框架 | React 19 + TypeScript |
| 构建工具 | Vite 6 |
| 图表 | ECharts 6 (echarts-for-react) |
| 样式 | Tailwind CSS |
| HTTP/SSE | 原生 fetch + EventSource |
| 后端框架 | Python FastAPI |
| 数据库 | SQLite |
| 数据采集 | akshare + yfinance + FRED API + CFTC |
| LLM | DeepSeek API + OpenAI API |

---

## 二、核心功能模块

### 2.1 MVP 功能清单

| 功能 | 优先级 | 状态 |
|------|--------|------|
| 实时金价仪表盘（国际+国内+溢价+汇率+AI评分） | 🔴 必须 | 纳入MVP |
| 金价走势图（1M/3M/1Y/3Y/5Y + 叠加指标） | 🔴 必须 | 纳入MVP |
| 宏观指标面板（TIPS/DXY/SPDR/COT/溢价） | 🔴 必须 | 纳入MVP |
| AI综合研判（规则打分 + 双LLM辩论 + SSE流式） | 🔴 必须 | 纳入MVP |
| 风险信号面板（VIX/GPR/央行购金/中国储备） | 🟡 建议 | 纳入MVP |
| 历史预测准确率曲线 | 🔴 必须 | 纳入MVP |
| 价格预警通知 | ⚪ 未来 | 后续迭代 |
| 投资组合回测 | ⚪ 未来 | 后续迭代 |
| 新闻舆情聚合 | ⚪ 未来 | 后续迭代 |

---

## 三、数据层设计

### 3.1 数据源清单（全部免费）

| # | 数据源 | 覆盖指标 | 更新频率 | 获取方式 |
|---|--------|----------|----------|----------|
| 1 | **akshare** (主源) | 国际金价、国内金价AU9999、USD/CNY汇率、上海溢价、DXY | 每小时 | akshare Python库 |
| 2 | **yfinance** (辅源) | VIX、SPDR GLD持仓 | 每日 | yfinance Python库 |
| 3 | **FRED API** | 10Y TIPS收益率 (DFII10) | 每日 | 免费注册API Key |
| 4 | **CFTC官网** | COMEX黄金净多头持仓 | 每周六 | CSV下载+解析 |
| 5 | **新浪财经** | 央行购金事件（每月7-12号检测） | 事件驱动 | 关键词匹配新闻标题 |

### 3.2 数据采集定时策略

```
每小时整点       → 金价快照（国际/国内/汇率/溢价/DXY）
每日 09:00 CST  → TIPS / SPDR / VIX 日频数据
每周六 09:00    → COMEX COT 持仓报告
每月 7-12 号    → 央行购金事件检测（窗口期每日检查一次）
```

**反爬策略**: 每小时一次轮询（非每分钟），降低IP封禁风险。所有请求带合理 User-Agent，请求间隔加入随机抖动(±120秒)。

### 3.3 交易日时间处理

上金所交易日结构：
- 日盘：09:00-11:30, 13:30-15:30
- 夜盘：20:00-次日02:30（归属于次日）

**日期归因规则**: 夜盘数据归属到次日。例如周一晚上的夜盘K线标记为周二。

**数据流水线时间**：
| 时间 | 动作 |
|------|------|
| 16:00 CST | 日盘收盘后爬取完整交易日数据（昨日夜盘+今日日盘） |
| 18:00 CST | AI研判生成（基于16:00数据 + 最新国际盘面） |
| 20:00 CST | 夜盘开盘，用户参考预测操作（流动性最佳窗口） |

### 3.4 数据库表设计 (SQLite)

#### gold_price — 金价时间序列
```sql
CREATE TABLE gold_price (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL UNIQUE,
    xau_usd   REAL,           -- 国际金价美元/盎司
    au9999    REAL,           -- 国内金价元/克
    usd_cny   REAL,           -- 美元人民币汇率
    premium   REAL            -- 上海溢价元/克
);
```

#### macro_indicators — 宏观指标时间序列
```sql
CREATE TABLE macro_indicators (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         DATE NOT NULL UNIQUE,
    tips_10y     REAL,        -- 10年期TIPS收益率 %
    dxy          REAL,        -- 美元指数
    spdr_tonnes  REAL,        -- SPDR黄金持仓 吨
    cot_net_long INTEGER,     -- COMEX净多头 合约数
    vix          REAL         -- VIX恐慌指数
);
```

#### cb_events — 央行购金事件（事件驱动型）
```sql
CREATE TABLE cb_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    event_date    DATE NOT NULL,
    country       TEXT DEFAULT 'CN',
    action        TEXT,             -- 'buy' / 'sell'
    amount_tonnes REAL,
    impact_score  REAL,             -- 对评分引擎的冲击分
    source_url    TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### rule_scores — 规则引擎评分日志
```sql
CREATE TABLE rule_scores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    calc_time       DATETIME NOT NULL,
    total_score     INTEGER,       -- 综合评分 0-100
    signal          TEXT,          -- 极度看多|偏多|中性|偏空|极度看空
    confidence      REAL,          -- 置信度 0-1
    indicator_scores TEXT,         -- JSON: {"tips":18,"dxy":12,...}
    weights_used    TEXT           -- JSON: 当时使用的权重
);
```

#### prediction_log — 预测-验证闭环
```sql
CREATE TABLE prediction_log (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    pred_date          DATE NOT NULL,
    target_date        DATE NOT NULL,
    predicted_direction TEXT,           -- 'up' / 'down' / 'flat'
    predicted_change_pct REAL,
    rule_score          INTEGER,
    llm_consensus       TEXT,
    debate_transcript   TEXT,           -- JSON: 辩论全过程
    actual_px_change    REAL,           -- T+1回填
    is_correct          INTEGER,        -- 1=正确 0=错误
    error_reason        TEXT            -- 如果错误，原因分析
);
```

---

## 四、规则打分引擎

### 4.1 指标体系（5+1动态）

**五个连续指标（基础权重100%）**：

| # | 指标 | 方向 | 权重 | 评分逻辑 |
|---|------|------|------|----------|
| 1 | 10Y TIPS收益率 | TIPS↓→利多 | 28% | Δ变化映射：Δ<-0.5%→+20分, Δ>+0.5%→-20分 |
| 2 | 美元指数 DXY | DXY↓→利多 | 23% | 20日均线位置：跌破→+15分, 升破→-15分 |
| 3 | SPDR持仓变化 | 持仓↑→利多 | 17% | 5日净变化：连增→+12分, 连减→-12分 |
| 4 | COMEX净多头 | 极端高位→回调 | 15% | 历史分位数：<30分位→+12分, >80分位→-12分 |
| 5 | 上海溢价 | 溢价↑→偏强 | 17% | 偏离均值：>+1σ→+10分, <-1σ→-10分 |

**央行购金事件信号（动态叠加，0~20%）**：
- 平时权重为0，其余5个指标权重归一化到100%
- 事件触发时临时提升总分上限至120%（其中20%给事件信号）
- **信号衰减曲线**: T+0权重拉满(100%) → T+1衰减至50% → T+2衰减至25% → T+3基本归零
- 衰减函数: `weight_t = initial_weight × (0.5)^(days_elapsed / 2)`
- 事件源: 每月7-12号窗口期监控新浪财经/东方财富"央行黄金储备"新闻标题

### 4.2 综合打分区间

```
总分归一化到 0-100：

0-20   🔴 极度看空
20-40  🟠 偏空
40-60  🟡 中性
60-80  🟢 偏多
80-100 🟢 极度看多

置信度 = 各指标方向一致性比例（6个同向=高置信，3同向3反向=低置信）
```

### 4.3 权重自适应学习

```
每30天执行一次:
  1. 回测 prediction_log 中各指标的方向准确率
  2. 准确率高的指标 +2%权重，低的 -2%
  3. 单指标权重下限 5%，上限 40%（防过拟合）
  4. 权重变动记录到 rule_scores.weights_used
```

---

## 五、双LLM辩论协议

### 5.1 三阶段流程

```
阶段一：独立分析（并行）
  DeepSeek ← 市场数据 + 评分结果 → OpenAI
  各自独立输出：方向判断 + 核心依据 + 置信度
  🔒 彼此不知道对方结论

阶段二：交叉质疑（串行，1轮）
  交换结论 → 各自找出对方逻辑漏洞
  "对方可能忽略了什么风险？"
  ⚡ 仅1轮互驳，不无限循环

阶段三：修正收敛（并行）
  在质疑基础上各自修正结论
  后端比对两份结论差异度:
    差异小 → 合并输出统一结论
    差异大 → 标注分歧，人工参考

输出: 方向判断 + 综合结论 + 置信度 + 辩论摘要
```

### 5.2 成本估算

| 阶段 | 调用次数 | Token估算 |
|------|----------|-----------|
| 阶段一 | 2次(并行) | ~800 each |
| 阶段二 | 2次(串行) | ~600 each |
| 阶段三 | 2次(并行) | ~400 each |
| **合计** | **6次调用** | **~3,600 tokens** |
| **费用** | | **≈ ¥0.08/次** |

如每日调用10次 ≈ ¥0.80/天 ≈ ¥24/月。

### 5.3 预测-验证-学习闭环

```
T日 18:00: AI研判 → 写入 prediction_log (预测部分)
T+1日 09:00: 回填实际涨跌 → 比对结果 → is_correct
             ↓ 如果错误
             将历史预测+错误原因注入下次LLM的prompt context
             "你上次预测涨，实际跌了2%，忽略了X因素"
             ↓
每30天: 回测所有预测 → 权重自适应调优
```

**不需要自己部署模型。** 通过 prompt注入 和 权重自适应 两层机制实现"越用越准"。

---

## 六、API 接口设计

### 6.1 端点清单

| 方法 | 端点 | 用途 | 响应时间 |
|------|------|------|----------|
| GET | `/api/dashboard` | 首页数据快照（全部面板） | <50ms |
| GET | `/api/price-history` | 金价历史 + 叠加指标 | <100ms |
| | | 参数: `period=1m\|3m\|1y\|3y\|5y`, `overlay=tips\|dxy\|cot\|all` | |
| GET | `/api/indicators` | 宏观指标详细数据 | <50ms |
| GET | `/api/score` | 最新规则打分结果 | <10ms |
| POST | `/api/analysis` | **触发AI研判（SSE流式）** | 8-15s |
| GET | `/api/history/predictions` | 历史预测记录及准确率统计 | <50ms |
| | | 返回: `{records:[], rolling_30d_accuracy:0.xx, total_accuracy:0.xx, total_count:N, correct_count:N}` | |

### 6.2 SSE 流式事件类型

```
event: status   → 阶段切换提示（"规则打分完成" / "DeepSeek分析中"）
event: partial  → 辩论过程实时文字流
event: result   → 最终统一结论 JSON
```

### 6.3 CORS 配置

开发环境允许 localhost:5173 跨域，生产环境仅允许 Cloudflare Pages 域名。

---

## 七、前端设计

### 7.1 首页布局

```
┌─────────────── 价格滚动条（常驻深色背景）──────────────────┐
│ 国际金价 │ 国内金价 │ USD/CNY │ 上海溢价 │ AI综合评分      │
├──────────────────┬─────────────────────────────────────────┤
│                  │                                         │
│  金价走势图       │  宏观指标卡片列                          │
│  (ECharts)       │  TIPS / DXY / SPDR / COT / 溢价         │
│  [1M|3M|1Y|3Y|5Y]│                                         │
│  [叠加:TIPS|DXY] │                                         │
│                  │                                         │
├──────────────────┴─────────────────────────────────────────┤
│  历史预测准确率曲线（折叠面板，展开后为ECharts折线图）       │
│  滚动30日方向准确率 + 累计准确率 + 正确/错误数量             │
├──────────────────┬─────────────────────────────────────────┤
│                                                             │
│  AI投资研判面板                                    │ 风险信号│
│  评分圆环 + 双模型辩论SSE流 + 最终结论               │ VIX    │
│  [生成AI研判]  按钮                                  │ GPR    │
│                                                     │ 央行   │
│                                                     │ 储备   │
└─────────────────────────────────────────────────────┴────────┘
```

### 7.2 响应式策略

- 桌面端(≥1280px): 左右双栏 + 底部分栏，图表高度280px
- 移动端(<768px): 单栏垂直堆叠，价格条横向滑动，图表全宽

### 7.3 组件树

```
App
├── PriceTickerBar (5个价格卡片横排，纯展示)
├── PriceChart
│   ├── TimeRangeSelector (1M/3M/1Y/3Y/5Y)
│   ├── OverlayToggle (TIPS/DXY/COT)
│   └── EChartsWrapper (封装echarts实例)
├── MacroCardList
│   └── MacroCard ×5 (单指标卡片)
├── AccuracyChart (历史预测准确率折线图，折叠面板，数据来自 /api/history/predictions)
├── AIAnalysisPanel
│   ├── RuleScoreBadge (评分圆环)
│   ├── AnalysisButton (触发SSE)
│   ├── DebateStreamView (SSE实时流)
│   └── ConsensusCard (最终结论)
└── RiskPanel
    └── RiskChip ×4 (风险信号)
```

### 7.4 数据流

- 单向数据流：App 顶层 fetch → state → props 逐级下传
- 无全局状态管理库（项目规模不需要 Redux/Zustand）
- SSE 连接由 AIAnalysisPanel 内部管理

---

## 八、后端模块结构

```
gold-backend/
├── main.py              # FastAPI 入口，路由注册
├── config.py            # API密钥、数据源URL、交易时段配置
├── requirements.txt
├── fetchers/
│   ├── gold_price.py    # 金价/汇率/溢价 (akshare)
│   ├── macro.py         # TIPS/DXY/SPDR/VIX (yfinance+FRED)
│   ├── cot.py           # COMEX COT持仓 (CFTC CSV)
│   └── cb_event.py      # 央行购金事件 (新浪财经RSS)
├── engine/
│   ├── scorer.py        # 规则打分引擎
│   └── weights.py       # 权重管理+自适应
├── llm/
│   ├── debate.py        # 三阶段辩论编排
│   ├── deepseek.py      # DeepSeek API 适配
│   └── openai_client.py # OpenAI API 适配
├── db/
│   ├── models.py        # SQLite 表定义
│   └── queries.py       # 数据查询接口
├── api/
│   └── routes.py        # 路由处理函数
└── scheduler.py         # 定时任务调度（apscheduler）
```

---

## 九、前端目录结构

```
gold-frontend/
├── index.html
├── package.json
├── vite.config.ts           # 代理配置（dev → localhost:8000）
├── tsconfig.json
├── tailwind.config.js
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── api/
│   │   └── client.ts        # fetch 封装 + SSE 工厂
│   ├── hooks/
│   │   ├── useDashboard.ts  # 数据获取hook
│   │   └── useSSE.ts        # SSE流管理hook
│   ├── components/
│   │   ├── PriceTickerBar.tsx
│   │   ├── PriceChart.tsx
│   │   ├── MacroCardList.tsx
│   │   ├── AccuracyChart.tsx
│   │   ├── AIAnalysisPanel.tsx
│   │   ├── DebateStreamView.tsx
│   │   └── RiskPanel.tsx
│   ├── styles/
│   │   └── global.css       # Tailwind + 自定义主题色
│   └── types/
│       └── index.ts         # TypeScript 类型定义
```

---

## 十、安全与风险

- **免责声明**: AI研判页面显著位置标注"以下为AI分析，不构成投资建议"
- **API密钥**: DeepSeek/OpenAI的key仅存在后端 config.py，不暴露给前端
- **CORS**: 生产环境严格限制允许域名
- **频率限制**: `/api/analysis` 加简单限流（同一IP每分钟最多3次，防止意外超量调用消耗token）

---

## 十一、后续迭代方向

1. 价格预警通知（邮件/微信推送）
2. DeepSeek微调（累积500+标注数据后）
3. 移动端PWA支持
