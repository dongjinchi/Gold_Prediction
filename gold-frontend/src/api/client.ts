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
