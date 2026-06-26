import type { DashboardData, AccuracyStats, ScoreResult, SSEEvent } from '../types';

const BASE = '/api';

export async function fetchDashboard(): Promise<DashboardData> {
  const res = await fetch(`${BASE}/dashboard`);
  if (!res.ok) throw new Error(`Dashboard fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchPriceHistory(type: string = 'daily'): Promise<{ type: string; data: any[] }> {
  const res = await fetch(`${BASE}/price-history?type=${type}`);
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
