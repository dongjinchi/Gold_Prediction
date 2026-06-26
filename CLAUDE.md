# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gold investment decision-support website. Displays Chinese gold price trends, macro indicators, and AI-powered analysis using a rule scoring engine + dual-LLM (DeepSeek + OpenAI) debate. All data from free sources.

## Architecture

```
gold-backend/ (Python FastAPI :8000)
  ├── api/routes.py         — 7 REST endpoints + SSE streaming
  ├── engine/scorer.py      — 6-factor weighted scoring engine (TIPS/DXY/SPDR/COT/premium/CB-events)
  ├── llm/debate.py         — 2-round dual-LLM debate orchestrator
  ├── fetchers/             — akshare/yfinance/FRED/CFTC data collectors
  ├── db/models.py          — SQLite schema (5 tables: gold_price, macro_indicators, cb_events, rule_scores, prediction_log)
  ├── scheduler.py          — apscheduler jobs (trading-hours-only gold, daily macro, weekly COT, monthly CB)
  └── scheduler_verify.py   — T+1 prediction backfill
gold-frontend/ (React+Vite+TypeScript :5173)
  ├── src/api/client.ts     — fetch wrappers + SSE factory
  ├── src/hooks/            — useDashboard, useSSE
  └── src/components/       — PriceChart (3-tab), PriceTickerBar, MacroCardList, AIAnalysisPanel, AccuracyChart, RiskPanel
```

Vite proxies `/api` → `localhost:8000` in development.

## Key Commands

```bash
# Backend
cd gold-backend
pip install -r requirements.txt
python main.py              # http://localhost:8000, auto-creates DB + backfills history on first run

# Frontend
cd gold-frontend
npm install
npm run dev                 # http://localhost:5173
npm run build               # production build (tsc -b + vite build)

# Verification
curl http://localhost:8000/health
curl http://localhost:8000/api/dashboard
```

## Configuration

Environment variables in `gold-backend/.env`:
```
DEEPSEEK_API_KEY=sk-xxx
OPENAI_API_KEY=sk-xxx
FRED_API_KEY=xxx          # free from stlouisfed.org, enables TIPS data
```

## Data Sources (all free)

| Source | Indicators | Method |
|--------|-----------|--------|
| akshare | International/domestic gold spot, USD/CNY | `spot_quotations_sge`, `futures_foreign_commodity_realtime` |
| akshare | SHFE gold futures volume (AU0) | `futures_main_sina` |
| akshare | COMEX + SGE daily OHLC history | `futures_foreign_hist` + `spot_hist_sge` |
| FRED API | 10Y TIPS yield (DFII10) | `fredapi` |
| open.er-api | DXY (computed from FX basket) | free REST API |
| yfinance | VIX, SPDR holdings (rate-limited, retry with 30s+ delays) | fallback |
| Sina Finance | PBOC gold buying events (monthly window 7th-12th) | news RSS keywords |

**Trading schedule**: SGE day 09:00-15:30, night 20:00-02:30 (next day). Gold price fetched hourly during trading hours only. Night session data attributed to next calendar day.

## Chart System (PriceChart.tsx)

Three-tab design: 分时 (intraday SGE minute data) / 5日 (daily OHLC K-line) / 日K (full daily candlestick + zoom slider).
- Left y-axis: AU9999 ¥/g (blue)
- Right y-axis: XAU/USD $/oz (yellow, dashed or solid)
- Volume panel below K-line chart, sourced from SHFE AU0 futures
- Slider controls both main chart + volume panel synchronously
- NOT using ECharts `theme="dark"` as the only theme parameter — all colors are manually specified

## LLM Debate Flow

```
Phase 1: DeepSeek + OpenAI analyze independently (parallel)
Phase 2: Cross-challenge Round 1 — each reviews the other's analysis (serial)
Phase 3: Cross-challenge Round 2 — deeper rebuttal (serial)
Phase 4: Convergence — final unified conclusion (parallel)
```

SSE events stream: `status` (phase changes) → `partial` (model excerpts) → `result` (consensus + direction + position).

## Scoring Engine

6-factor weighted model: TIPS (28%), DXY (23%), SPDR (17%), COT (15%), premium (17%), CB events (0-20% dynamic pulse with 2-day half-life). Initial weights adapt every 30 days based on historical directional accuracy. Score normalizes to 0-100, mapped to 5 signal levels.

## Database Notes

- `gold_price` table stores both hourly snapshots (from live fetcher) and daily OHLC records (from backfill, timestamp = `YYYY-MM-DD 00:00:00`)
- `daily_only=True` filter returns only OHLC records (timestamps ending in `00:00:00`)
- DB is auto-created on first run; historical backfill runs automatically if table is empty
- yfinance rate-limit: yfinance-only indicators (VIX, SPDR) may be null until rate-limit window resets (~hours)
