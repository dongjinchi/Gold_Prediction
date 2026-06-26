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
