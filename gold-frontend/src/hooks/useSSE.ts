import { useState, useRef, useCallback, useEffect } from 'react';
import type { SSEEvent } from '../types';
import { createSSEConnection } from '../api/client';

export function useSSE() {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [status, setStatus] = useState<string>('');
  const [dailyResult, setDailyResult] = useState<SSEEvent | null>(null);
  const [weeklyResult, setWeeklyResult] = useState<SSEEvent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sourceRef = useRef<EventSource | null>(null);
  const stoppedRef = useRef(false);

  // 卸载时关闭连接
  useEffect(() => {
    return () => {
      stoppedRef.current = true;
      if (sourceRef.current) {
        sourceRef.current.close();
        sourceRef.current = null;
      }
    };
  }, []);

  const connect = useCallback((type: 'daily' | 'weekly'): Promise<SSEEvent | null> => {
    return new Promise((resolve) => {
      if (stoppedRef.current) { resolve(null); return; }
      if (sourceRef.current) { sourceRef.current.close(); }

      const source = createSSEConnection(
        (event) => {
          setEvents(prev => [...prev, event]);
          if (event.type === 'status') {
            setStatus(event.message || event.phase || '');
          }
          if (event.type === 'result') {
            source.close();
            resolve(event);
          }
        },
        (err) => {
          console.error(`SSE ${type} error:`, err);
          setError(`${type === 'daily' ? '每日' : '一周'}研判连接中断`);
          resolve(null);
        },
        type
      );

      sourceRef.current = source;
    });
  }, []);

  const start = useCallback(async () => {
    setLoading(true);
    setEvents([]);
    setStatus('准备中...');
    setDailyResult(null);
    setWeeklyResult(null);
    setError(null);
    stoppedRef.current = false;

    // 第一步：每日研判
    setStatus('生成明日研判...');
    const daily = await connect('daily');
    if (stoppedRef.current || !daily) {
      if (!stoppedRef.current) setLoading(false);
      return;
    }
    setDailyResult(daily);

    // 第二步：一周趋势
    setStatus('生成一周趋势...');
    const weekly = await connect('weekly');
    if (stoppedRef.current) return;
    setWeeklyResult(weekly);
    setLoading(false);
    setStatus('分析完成');
  }, [connect]);

  const stop = useCallback(() => {
    stoppedRef.current = true;
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }
    setLoading(false);
  }, []);

  // 综合展示结果：优先用 daily，fallback weekly
  const result = dailyResult || weeklyResult;

  return { events, status, result, dailyResult, weeklyResult, loading, error, start, stop };
}
