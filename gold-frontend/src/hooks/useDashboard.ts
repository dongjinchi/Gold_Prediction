import { useState, useEffect, useCallback } from 'react';
import type { DashboardData, AccuracyStats } from '../types';
import { fetchDashboard, fetchAccuracy } from '../api/client';

export function useDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [accuracy, setAccuracy] = useState<AccuracyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [dash, acc] = await Promise.all([
        fetchDashboard(),
        fetchAccuracy(90),
      ]);
      setData(dash);
      setAccuracy(acc);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return { data, accuracy, loading, error, refresh: load };
}
