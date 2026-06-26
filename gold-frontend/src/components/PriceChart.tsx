import { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import { fetchPriceHistory } from '../api/client';

type ChartType = 'intraday' | '5day' | 'daily';

export default function PriceChart() {
  const [chartType, setChartType] = useState<ChartType>('intraday');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchPriceHistory(chartType)
      .then(res => setData(res.data || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [chartType]);

  const tabs: { key: ChartType; label: string }[] = [
    { key: 'intraday', label: '分时' },
    { key: '5day', label: '5日' },
    { key: 'daily', label: '日K' },
  ];

  const buildOption = () => {
    const isDaily = chartType === 'daily';
    const isIntraday = chartType === 'intraday';

    const xLabels = isIntraday
      ? data.map(d => d.time?.slice(0, 5) || '')
      : data.map(d => {
          const t = d.timestamp || d.time || '';
          return isDaily ? t.slice(5, 10) : t.slice(5, 16);
        });

    // 国内金价 AU9999
    const auClose = data.map(d => d.au9999);
    // 国际金价 XAU/USD
    const xauClose = data.map(d => d.xau_usd);
    // AU K线 OHLC (日K)
    const auK = data.map(d => [
      d.au_open ?? d.au9999 ?? null,
      d.au_close ?? d.au9999 ?? null,
      d.au_low ?? d.au9999 ?? null,
      d.au_high ?? d.au9999 ?? null,
    ]);
    // 成交量
    const volData = data.map(d => d.xau_vol ?? 0);

    const series: any[] = [];

    if (isDaily) {
      // 日K: 国内金价蜡烛图 + 国际金价线 + 成交量
      const upColor = '#ef4444';
      const downColor = '#22c55e';

      series.push({
        name: 'AU9999',
        type: 'candlestick',
        data: auK,
        yAxisIndex: 0,
        itemStyle: {
          color: upColor, color0: downColor,
          borderColor: upColor, borderColor0: downColor,
        },
      });
      // 国际金价黄色线 (右轴)
      series.push({
        name: 'XAU/USD',
        type: 'line',
        data: xauClose,
        yAxisIndex: 2,
        smooth: false,
        symbol: 'none',
        lineStyle: { color: '#fbbf24', width: 1.2 },
      });
      // 成交量柱
      series.push({
        name: 'Volume',
        type: 'bar',
        data: volData.map((v: number, i: number) => ({
          value: v,
          itemStyle: {
            color: (auK[i] && auK[i][1] >= auK[i][0]) ? '#ef444460' : '#22c55e60',
          },
        })),
        yAxisIndex: 1,
        barWidth: '60%',
      });
    } else {
      // 分时/5日: 国内金价蓝色线 + 国际金价黄色虚线(右轴)
      series.push({
        name: 'AU9999',
        type: 'line',
        data: auClose,
        yAxisIndex: 0,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#3b82f6', width: 1.8 },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(59,130,246,0.15)' },
              { offset: 1, color: 'rgba(59,130,246,0.01)' },
            ],
          },
        },
      });
      series.push({
        name: 'XAU/USD',
        type: 'line',
        data: xauClose,
        yAxisIndex: 2,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#fbbf24', width: 1.5, type: 'dashed' },
      });
    }

    const option: any = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis' as const,
        backgroundColor: 'rgba(30,41,59,0.95)',
        borderColor: '#475569',
        textStyle: { color: '#f8fafc', fontSize: 11 },
      },
      legend: {
        show: false,
      },
      grid: { left: 65, right: 70, top: 15, bottom: isDaily ? 75 : 40 },
      xAxis: {
        type: 'category' as const,
        data: xLabels,
        axisLabel: {
          color: '#64748b', fontSize: 9,
          interval: isIntraday ? Math.floor(xLabels.length / 8) : 'auto',
        },
        axisLine: { lineStyle: { color: '#334155' } },
      },
      yAxis: [
        // 左轴: 国内金价 AU9999 (元/克)
        {
          type: 'value' as const,
          name: '¥/g',
          nameTextStyle: { color: '#3b82f6', fontSize: 10 },
          axisLabel: { color: '#3b82f6', fontSize: 10 },
          splitLine: { lineStyle: { color: '#1e293b' } },
          scale: true,
        },
        // 隐藏轴: 成交量
        {
          type: 'value' as const,
          axisLabel: { show: false },
          splitLine: { show: false },
          scale: true,
        },
        // 右轴: 国际金价 XAU/USD ($/oz)
        {
          type: 'value' as const,
          name: '$/oz',
          nameTextStyle: { color: '#fbbf24', fontSize: 10 },
          axisLabel: { color: '#fbbf24', fontSize: 10 },
          splitLine: { show: false },
          scale: true,
        },
      ],
      series,
      dataZoom: isDaily ? [
        {
          type: 'slider' as const,
          xAxisIndex: 0,
          start: 0,
          end: 100,
          height: 25,
          bottom: 8,
          backgroundColor: '#1e293b',
          dataBackground: { lineStyle: { color: '#475569' }, areaStyle: { color: '#334155' } },
          selectedDataBackground: { lineStyle: { color: '#fbbf24' }, areaStyle: { color: '#fbbf2460' } },
          handleStyle: { color: '#fbbf24' },
          textStyle: { color: '#94a3b8', fontSize: 9 },
        },
        { type: 'inside' as const, xAxisIndex: 0 },
      ] : [],
    };
    return option;
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-400">{'\u{1F4C8}'} 金价走势</h3>
        <div className="flex gap-0.5 bg-slate-800 rounded-lg p-0.5">
          {tabs.map(t => (
            <button
              key={t.key}
              onClick={() => setChartType(t.key)}
              className={`px-3 py-1 text-xs rounded-md transition ${
                chartType === t.key
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
      {loading ? (
        <div className="h-80 flex items-center justify-center text-slate-500">{'加载中...'}</div>
      ) : (
        <ReactECharts option={buildOption()} style={{ height: 400 }} theme="dark" notMerge={true} />
      )}
      <div className="flex justify-between mt-1 text-xs text-slate-600">
        {chartType === 'intraday' && <span>蓝色 AU9999 · 黄色虚线 XAU/USD (右轴)</span>}
        {chartType === '5day'   && <span>蓝色 AU9999 · 黄色虚线 XAU/USD (右轴)</span>}
        {chartType === 'daily'  && <span>红涨绿跌 AU9999 · 黄线 XAU (右轴) · 滑块缩放时Y轴同步</span>}
      </div>
    </div>
  );
}
