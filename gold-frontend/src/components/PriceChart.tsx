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

  // 构建 OHLC + Volume 数据
  const dates = data.map(d => d.timestamp?.slice(0, 10) || '');
  const xauOhlc = data.map(d => [
    d.xau_open ?? d.xau_usd,
    d.xau_close ?? d.xau_usd,
    d.xau_low ?? d.xau_usd,
    d.xau_high ?? d.xau_usd,
  ]);
  const auClose = data.map(d => d.au9999);
  // 国内成交量(正数→横轴以上)，国际成交量(负数→横轴以下)
  const auVol = data.map(d => (d.au_vol ?? 0));
  const xauVol = data.map(d => -(d.xau_vol ?? 0));

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'cross' as const },
      backgroundColor: 'rgba(30,41,59,0.95)',
      borderColor: '#475569',
      textStyle: { color: '#f8fafc', fontSize: 11 },
    },
    axisPointer: { link: [{ xAxisIndex: 'all' }] },
    grid: [
      { left: 70, right: 25, top: 15, height: '52%' },
      { left: 70, right: 25, top: '70%', height: '26%' },
    ],
    xAxis: [
      {
        type: 'category' as const,
        data: dates,
        axisLabel: { color: '#64748b', fontSize: 10 },
        axisLine: { lineStyle: { color: '#334155' } },
        gridIndex: 0,
      },
      {
        type: 'category' as const,
        data: dates,
        axisLabel: { show: false },
        axisLine: { lineStyle: { color: '#334155' } },
        axisTick: { show: false },
        gridIndex: 1,
      },
    ],
    yAxis: [
      // 主图: 双轴
      {
        type: 'value' as const,
        name: 'USD/oz',
        nameTextStyle: { color: '#94a3b8', fontSize: 10 },
        axisLabel: { color: '#94a3b8', fontSize: 10, formatter: '${value}' },
        splitLine: { lineStyle: { color: '#1e293b' } },
        gridIndex: 0,
      },
      {
        type: 'value' as const,
        name: 'volume',
        nameTextStyle: { color: '#64748b', fontSize: 9 },
        axisLabel: {
          color: '#64748b', fontSize: 9,
          formatter: (v: number) => {
            const abs = Math.abs(v);
            return abs >= 1000 ? `${(abs / 1000).toFixed(0)}k` : `${abs}`;
          },
        },
        splitLine: { show: false },
        gridIndex: 1,
      },
    ],
    series: [
      // XAU K线 (蓝绿色阳线/红色阴线)
      {
        name: 'XAU/USD',
        type: 'candlestick',
        data: xauOhlc,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: '#22c55e',
          color0: '#ef4444',
          borderColor: '#22c55e',
          borderColor0: '#ef4444',
        },
      },
      // AU9999 收盘线 (蓝色)
      {
        name: 'AU9999',
        type: 'line',
        data: auClose,
        xAxisIndex: 0,
        yAxisIndex: 0,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#3b82f6', width: 1.8 },
      },
      // 国内成交量 (正数→横轴以上，绿色柱)
      {
        name: '国内成交量',
        type: 'bar',
        data: auVol.map((v: number) => ({
          value: v,
          itemStyle: { color: '#22c55e60' },
        })),
        xAxisIndex: 1,
        yAxisIndex: 1,
        barWidth: '60%',
      },
      // 国际成交量 (负数→横轴以下，红色柱)
      {
        name: '国际成交量',
        type: 'bar',
        data: xauVol.map((v: number, i: number) => ({
          value: v,
          itemStyle: { color: '#ef444460' },
        })),
        xAxisIndex: 1,
        yAxisIndex: 1,
        barWidth: '60%',
      },
    ],
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-400">{'\u{1F4C8}'} 金价走势</h3>
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
        <div className="h-96 flex items-center justify-center text-slate-500">{'加载中...'}</div>
      ) : (
        <ReactECharts option={option} style={{ height: 420 }} theme="dark" />
      )}
    </div>
  );
}
