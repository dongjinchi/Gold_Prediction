import { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import { fetchPriceHistory } from '../api/client';

type TimeRange = '1m' | '3m' | '1y' | '3y' | '5y';

export default function PriceChart() {
  const [timeRange, setTimeRange] = useState<TimeRange>('3m');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchPriceHistory(timeRange)
      .then(res => setData(res.data || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [timeRange]);

  const ranges: TimeRange[] = ['1m', '3m', '1y', '3y', '5y'];

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 20, right: 60, bottom: 30, left: 60 },
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: 'rgba(30,41,59,0.95)',
      borderColor: '#475569',
      textStyle: { color: '#f8fafc', fontSize: 12 },
    },
    xAxis: {
      type: 'category' as const,
      data: data.map(d => d.timestamp?.slice(0, 10) || ''),
      axisLabel: { color: '#94a3b8', fontSize: 10 },
      axisLine: { lineStyle: { color: '#334155' } },
    },
    yAxis: [
      {
        type: 'value' as const,
        name: 'USD/oz',
        nameTextStyle: { color: '#94a3b8' },
        axisLabel: { color: '#94a3b8', formatter: '${value}' },
        splitLine: { lineStyle: { color: '#1e293b' } },
      },
      {
        type: 'value' as const,
        name: '¥/g',
        nameTextStyle: { color: '#94a3b8' },
        axisLabel: { color: '#94a3b8', formatter: '¥{value}' },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: 'XAU/USD',
        type: 'line',
        data: data.map(d => d.xau_usd),
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#fbbf24', width: 2 },
        areaStyle: {
          color: {
            type: 'linear' as const, x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(251,191,36,0.3)' },
              { offset: 1, color: 'rgba(251,191,36,0.02)' },
            ],
          },
        },
      },
      {
        name: 'AU9999',
        type: 'line',
        yAxisIndex: 1,
        data: data.map(d => d.au9999),
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#f97316', width: 1.5 },
      },
    ],
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-400">📈 金价走势</h3>
        <div className="flex gap-1">
          {ranges.map(r => (
            <button
              key={r}
              onClick={() => setTimeRange(r)}
              className={`px-2.5 py-1 text-xs rounded-full transition ${
                timeRange === r
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}
            >
              {r === '1m' ? '1月' : r === '3m' ? '3月' : r === '1y' ? '1年' : r === '3y' ? '3年' : '5年'}
            </button>
          ))}
        </div>
      </div>
      {loading ? (
        <div className="h-72 flex items-center justify-center text-slate-500">加载中...</div>
      ) : (
        <ReactECharts option={option} style={{ height: 280 }} theme="dark" />
      )}
    </div>
  );
}
