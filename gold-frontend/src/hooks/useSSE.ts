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
