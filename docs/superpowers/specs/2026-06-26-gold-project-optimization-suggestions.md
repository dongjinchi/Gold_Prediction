# Gold 投资决策网站优化建议

日期：2026-06-26

本文档汇总对当前项目后端、前端、文档与工程配置的只读审阅结果，按优先级整理为可执行优化建议。

## P0：应优先修复的正确性问题

### 1. 修复预测验证日期逻辑

- 相关位置：
  - `gold-backend/api/routes.py:199-202`
  - `gold-backend/scheduler_verify.py:31-39`
- 问题：`/api/analysis` 写入的 `target_date` 似乎是当天，但验证器按“预测日 → 目标日”做 T+1 回测。
- 影响：历史准确率可能失真，AI 分析和规则评分的表现评估不可信。
- 建议：
  - `target_date` 写入“明日”或“下一个交易日”。
  - 增加预测验证回归测试，覆盖 `pred_date`、`target_date`、实际价格对比逻辑。

### 2. 修复评分引擎上海溢价因子输入

- 相关位置：
  - `gold-backend/engine/scorer.py:185-186`
  - `gold-backend/api/routes.py:142-144`
- 问题：评分引擎从 `macro_data.get("premium")` 取溢价，但宏观指标表未必包含该字段，导致 premium 可能长期按 0 计算。
- 影响：6 因子评分中的上海溢价权重被浪费，最终买卖建议可能偏差。
- 建议：
  - 从最新金价快照或 price history 中读取/计算当前 premium。
  - 将 premium 显式传入评分引擎。
  - 增加单测验证 premium 非空、缺失、异常值三种情况。

### 3. 将 LLM 客户端改为真正异步

- 相关位置：
  - `gold-backend/llm/deepseek.py:17-38`
  - `gold-backend/llm/openai_client.py:17-38`
  - `gold-backend/llm/debate.py:120-125`
- 问题：`async def` 内部使用同步 OpenAI client，`asyncio.gather` 实际不能真正并发。
- 影响：分析接口响应慢，并发请求时可能阻塞 FastAPI 事件循环，SSE 体验变差。
- 建议：
  - 使用 `AsyncOpenAI`。
  - 增加 timeout、重试和错误结构化返回。
  - 对模型不可用、超时、限流等情况做清晰降级。

### 4. 修复前端“停止分析”按钮不可用

- 相关位置：`gold-frontend/src/components/AIAnalysisPanel.tsx:68-77`
- 问题：按钮逻辑是 `onClick={loading ? stop : start}`，但同时 `disabled={loading}`，导致加载时无法点击停止。
- 影响：用户无法中止长时间 LLM 流式分析。
- 建议：
  - loading 时保持按钮可点击。
  - loading 状态下文案改为“停止分析”。
  - stop 后关闭 EventSource 并恢复可再次分析状态。

## P1：明显提升稳定性和用户体验

### 5. 增强 SSE 前后端鲁棒性

- 相关位置：
  - `gold-backend/api/routes.py:169-209`
  - `gold-frontend/src/hooks/useSSE.ts:12-42`
  - `gold-frontend/src/api/client.ts:31-55`
- 问题：
  - 后端缺少 heartbeat。
  - 后端缺少断连检测。
  - 异常场景没有统一 SSE error 事件。
  - 前端 hook 没有卸载 cleanup。
  - 前端 `JSON.parse` 缺少保护。
- 建议：
  - 后端增加 heartbeat。
  - 后端使用 `request.is_disconnected()` 检测客户端断开。
  - 异常统一发送 `{ type: "error", message }` SSE 事件。
  - 前端 `useSSE` 增加 `useEffect` cleanup。
  - 前端解析失败时进入 error 状态，而不是破坏整体状态。

### 6. 提升数据采集可靠性

- 相关位置：
  - `gold-backend/fetchers/gold_price.py`
  - `gold-backend/fetchers/macro.py`
  - `gold-backend/fetchers/cb_event.py`
- 问题：
  - 汇率失败时静默回退到 `7.25`。
  - HTTP 请求缺少 `raise_for_status()`。
  - SPDR 持仓数据可能长期使用近似值。
  - 央行事件生成了 `event_id`，但缺少有效入库去重约束。
- 建议：
  - 请求增加重试、User-Agent 和超时。
  - 失败数据增加数据质量标记，不要伪装为真实数据。
  - 对关键外部数据加缓存。
  - 为央行事件增加唯一约束或去重逻辑。

### 7. 首页数据加载支持局部失败

- 相关位置：`gold-frontend/src/hooks/useDashboard.ts:14-17`
- 问题：当前使用 `Promise.all`，历史准确率等次要接口失败会导致整个首页失败。
- 影响：一个非核心模块失败会拖垮主页面。
- 建议：
  - 主 dashboard 数据优先展示。
  - accuracy、history、analysis 等模块用独立状态或 `Promise.allSettled` 降级。
  - UI 上明确显示局部模块失败，而不是整页失败。

### 8. 优化图表包体和重绘成本

- 相关位置：`gold-frontend/src/components/PriceChart.tsx:36-160`
- 现象：构建结果显示单个 JS 包约 `1.35MB`，gzip 后约 `444KB`，ECharts 很可能是主要来源。
- 问题：
  - 每次 render 重建 chart option。
  - `notMerge={true}` 强制全量重绘。
- 建议：
  - 对 chart option 使用 `useMemo`。
  - 避免不必要的 `notMerge={true}`。
  - ECharts 按需注册或动态导入。
  - K 线、分时、5 日数据转换做缓存。

### 9. 为 SQLite 增加关键索引和唯一约束

- 相关位置：`gold-backend/db/models.py:15-77`
- 建议增加：
  - `gold_price(timestamp, source)` 索引或唯一约束。
  - `prediction_log(pred_date, target_date)` 索引或唯一约束。
  - `cb_events(event_id)` 唯一约束。
  - 常用查询字段如日期、指标名索引。
- 收益：
  - 避免重复数据。
  - 提升历史查询、回测和 dashboard 查询速度。
  - 降低调度任务重复写入风险。

## P2：工程质量、类型安全和可维护性

### 10. 收紧前端 TypeScript 类型

- 相关位置：
  - `gold-frontend/src/api/client.ts`
  - `gold-frontend/src/components/PriceChart.tsx`
  - `gold-frontend/tsconfig.app.json`
- 问题：存在较多 `any`，且 TypeScript strict 未开启。
- 建议：
  - 补齐 API response 类型。
  - 补齐 price history 类型。
  - 补齐 SSE event 类型。
  - 分阶段开启 `strict`。

### 11. 统一前端 API fetch 错误处理

- 相关位置：`gold-frontend/src/api/client.ts`
- 问题：多个请求未统一检查 `res.ok`。
- 建议封装 `request<T>()`：
  - 统一检查 HTTP 状态。
  - 统一解析错误信息。
  - 统一支持 timeout 或 abort。
  - 减少组件层重复处理。

### 12. 补齐测试体系

- 后端建议补充：
  - 评分引擎单测。
  - 预测验证回归测试。
  - fetcher mock 测试。
  - SSE 集成测试。
- 前端建议补充：
  - `useDashboard` 测试。
  - `useSSE` 测试。
  - API 错误处理测试。
  - 图表数据转换测试。
- 当前状态：前端 `npm run lint`、`npm run build` 可通过；后端缺少明确测试命令。

### 13. 强化调度器补缺口和并发控制

- 相关位置：`gold-backend/scheduler.py`
- 建议：
  - APScheduler job 增加 `misfire_grace_time`、`coalesce`、`max_instances`。
  - 启动时不仅检查“有没有最新金价”，还应检查历史缺口并增量 backfill。
  - 数据写入尽量批量化。

### 14. 完善文档和配置

- 相关位置：
  - `CLAUDE.md`
  - `gold-frontend/README.md`
  - 项目根目录
- 建议：
  - 增加 `.env.example`。
  - 明确 `FRED_API_KEY` 是可选项。
  - 明确 `DEEPSEEK_API_KEY` / `OPENAI_API_KEY` 缺失时 `/api/analysis` 的行为。
  - 更新 `gold-frontend/README.md`，避免继续保留 Vite 模板说明。
  - 在文档中补充 `npm run lint`、`npm run build`、后端暂无测试命令等验证方式。

## 建议实施顺序

1. 修复 P0 中的正确性问题：预测日期、premium 因子、停止按钮、SSE cleanup。
2. 改造 LLM 客户端：`AsyncOpenAI`、timeout、retry、结构化错误。
3. 加强数据采集可靠性和 SQLite 约束。
4. 优化前端类型、图表性能和 API 错误处理。
5. 补测试与文档，形成稳定交付流程。

## 推荐第一批改动

第一批建议控制范围，优先做以下 4 项：

1. 预测验证日期改为明日或下一个交易日。
2. 评分引擎显式接收 premium 输入。
3. 修复 AI 分析面板停止按钮。
4. 为 `useSSE` 增加卸载 cleanup 和 JSON 解析保护。

这 4 项收益高、范围清晰，适合作为第一轮优化提交。
