import type { DashboardData, AccuracyStats, ScoreResult, SSEEvent, GoldPrice } from '../types';

// 开发环境通过 Vite proxy 走 /api，生产环境直接用 Railway 域名
const BASE = import.meta.env.PROD
  ? 'https://web-production-536ee.up.railway.app/api'
  : '/api';

/** 统一请求封装：自动检查 HTTP 状态码并解析错误信息 */
async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, init);
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try { const err = await res.json(); msg = err.detail || err.message || msg; } catch {}
    throw new Error(msg);
  }
  return res.json();
}

export function fetchDashboard(): Promise<DashboardData> {
  return request('/dashboard');
}

export function fetchPriceHistory(type: string = 'daily'): Promise<{ type: string; data: GoldPrice[] }> {
  return request(`/price-history?type=${type}`);
}

export function fetchIndicators(): Promise<{ latest: any; history: any[] }> {
  return request('/indicators');
}

export function fetchScore(): Promise<ScoreResult> {
  return request('/score');
}

export function fetchAccuracy(days: number = 90): Promise<AccuracyStats> {
  return request(`/history/predictions?days=${days}`);
}

export function createSSEConnection(
  onEvent: (event: SSEEvent) => void,
  onError?: (err: Event) => void,
  type: 'daily' | 'weekly' = 'daily'
): EventSource {
  const source = new EventSource(`${BASE}/analysis?type=${type}`);

  source.addEventListener('status', (e) => {
    try { const data = JSON.parse(e.data); onEvent({ type: 'status', ...data }); }
    catch (err) { console.warn('SSE status parse failed:', err); }
  });

  source.addEventListener('partial', (e) => {
    try { const data = JSON.parse(e.data); onEvent({ type: 'partial', ...data }); }
    catch (err) { console.warn('SSE partial parse failed:', err); }
  });

  source.addEventListener('result', (e) => {
    try { const data = JSON.parse(e.data); onEvent({ type: 'result', ...data }); }
    catch (err) { console.warn('SSE result parse failed:', err); }
  });

  source.onerror = (err) => {
    if (onError) onError(err);
    source.close();
  };

  return source;
}
