# Cloudflare Pages 黑屏问题复盘

日期：2026-06-29

## 问题现象

访问线上地址 `https://gold-prediction.pages.dev/` 时，页面显示为黑色背景，没有数据、图表或其它可见内容。

## 影响范围

- 影响前端首屏渲染。
- 后端 Railway API 实际可访问，`/health` 和 `/api/dashboard` 均返回成功。
- Cloudflare Pages 的 HTML、JS、CSS 静态资源也能正常加载。

## 根因

生产后端 `/api/dashboard` 当前返回的 `prices` 数据中，以下字段可能为 `null`：

```json
{
  "usd_cny": null,
  "premium": null
}
```

但前端 `PriceTickerBar` 组件把它们当作必定存在的数字处理：

```tsx
prices.usd_cny.toFixed(4)
prices.premium.toFixed(1)
```

当字段为 `null` 时，React 首屏渲染抛出运行时错误：

```text
TypeError: Cannot read properties of null (reading 'toFixed')
```

因此整个 React 应用未能完成渲染，用户看到的就是一片黑色背景。

## 修复内容

提交：`51a2602 fix: handle missing ticker price fields`

修改文件：

- `gold-frontend/src/components/PriceTickerBar.tsx`
- `gold-frontend/src/types/index.ts`

修复方式：

1. 将 `GoldPrice` 类型中的字段改为允许 `null`：

```ts
usd_cny: number | null;
premium: number | null;
```

2. 在行情栏渲染时增加空值处理：

```tsx
value={prices.usd_cny != null ? prices.usd_cny.toFixed(4) : '—'}
```

```tsx
value={prices.premium != null ? `${prices.premium > 0 ? '+' : ''}${prices.premium.toFixed(1)} ¥/g` : '—'}
```

这样当汇率或上海溢价暂时缺失时，前端显示 `—`，不会导致页面崩溃。

## 验证记录

已完成以下验证：

1. 线上后端接口验证：
   - `https://web-production-536ee.up.railway.app/health` 返回 `200`
   - `https://web-production-536ee.up.railway.app/api/dashboard` 返回 `200` 且包含行情数据

2. CORS 验证：
   - 后端允许 `https://gold-prediction.pages.dev` 来源访问

3. 复现验证：
   - 使用 `usd_cny: null` 和 `premium: null` 的数据渲染 `PriceTickerBar`
   - 修复前确认会触发 `.toFixed()` 读取 `null` 的错误

4. 修复后验证：
   - 空值渲染验证通过：`SSR_NULL_PRICE_RENDER_OK`
   - 前端构建通过：`npm --prefix gold-frontend run build`

## 部署触发

已将修复提交并 push 到 GitHub：

```bash
git push origin main
```

Cloudflare Pages 如果绑定了 GitHub `main` 分支，会在 push 后自动触发重新部署。

## 后续建议

1. 前端所有来自 API 的字段都应按真实后端契约处理，尤其是免费数据源可能缺失的字段。
2. 对行情、宏观指标、预测历史等组件统一采用 `null` 安全显示策略。
3. 后续可以增加前端回归测试，覆盖 API 返回部分字段为空时页面仍可正常渲染。
