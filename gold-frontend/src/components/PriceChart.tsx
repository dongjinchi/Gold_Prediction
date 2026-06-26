import { useState, useEffect, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { fetchPriceHistory } from '../api/client';
import type { GoldPrice } from '../types';

type ChartType = 'intraday' | '5day' | 'daily';

function fmtDate(ts: string, withTime?: boolean): string {
  const d = ts.slice(5, 10);
  if (withTime && ts.length >= 16) return d + ' ' + ts.slice(11, 16);
  return d;
}

export default function PriceChart() {
  const [chartType, setChartType] = useState<ChartType>('intraday');
  const [data, setData] = useState<GoldPrice[]>([]);
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

  const isDaily = chartType === 'daily';
  const isIntraday = chartType === 'intraday';
  const showVol = chartType === '5day' || isDaily;

  const option = useMemo(() => {
    if (data.length === 0 && chartType !== 'intraday') return {}; // 数据未就绪时返回空option

    return (() => {

    const xLabels = isIntraday
      ? data.map(d => (d.time || '').slice(0, 5))
      : data.map(d => fmtDate(d.timestamp || '', !isDaily));

    const auClose = data.map(d => d.au9999);
    const xauClose = data.map(d => d.xau_usd);
    const auK = data.map(d => [
      d.au_open ?? d.au9999 ?? null,
      d.au_close ?? d.au9999 ?? null,
      d.au_low ?? d.au9999 ?? null,
      d.au_high ?? d.au9999 ?? null,
    ]);
    const volData = data.map(d => d.au_vol ?? d.xau_vol ?? 0);
    const upColor = '#ef4444';
    const downColor = '#22c55e';

    // --- 主图 series ---
    const mainSeries: any[] = [];
    if (isIntraday) {
      // 分时: 仅蓝线+黄虚线
      mainSeries.push({
        name: 'AU9999', type: 'line', data: auClose, xAxisIndex: 0, yAxisIndex: 0,
        smooth: true, symbol: 'none', lineStyle: { color: '#3b82f6', width: 1.8 },
        areaStyle: {
          color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [{ offset: 0, color: 'rgba(59,130,246,0.15)' }, { offset: 1, color: 'rgba(59,130,246,0.01)' }] }
        },
      });
      mainSeries.push({
        name: 'XAU/USD', type: 'line', data: xauClose, xAxisIndex: 0, yAxisIndex: 2,
        smooth: true, symbol: 'none', lineStyle: { color: '#fbbf24', width: 1.5, type: 'dashed' },
      });
    } else {
      // 5日 + 日K: K线 + 蓝线收盘 + 黄线XAU
      mainSeries.push({
        name: 'AU9999', type: 'candlestick', data: auK, xAxisIndex: 0, yAxisIndex: 0,
        itemStyle: { color: upColor, color0: downColor, borderColor: upColor, borderColor0: downColor },
      });
      mainSeries.push({
        name: 'AU9999 close', type: 'line', data: auClose, xAxisIndex: 0, yAxisIndex: 0,
        smooth: false, symbol: 'none', lineStyle: { color: '#3b82f6', width: 1.2 },
      });
      mainSeries.push({
        name: 'XAU/USD', type: 'line', data: xauClose, xAxisIndex: 0, yAxisIndex: 2,
        smooth: false, symbol: 'none', lineStyle: { color: '#fbbf24', width: 1.2, type: isDaily ? 'solid' : 'dashed' },
      });
    }

    // --- 成交量 series ---
    const volSeries: any[] = [{
      name: '成交量', type: 'bar', data: volData.map((v: number, i: number) => {
        // 成交量颜色统一用 K线逻辑（close vs open），与蜡烛图颜色一致
        const isUp = auK[i] && auK[i][1] >= auK[i][0];
        return { value: v, itemStyle: { color: isUp ? '#ef444480' : '#22c55e80' } };
      }), xAxisIndex: 1, yAxisIndex: 1, barWidth: '60%',
    }];

    const option: any = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis' as const,
        backgroundColor: 'rgba(30,41,59,0.95)',
        borderColor: '#475569',
        textStyle: { color: '#f8fafc', fontSize: 11 },
      },
      axisPointer: showVol ? { link: [{ xAxisIndex: 'all' }] } : undefined,
      grid: showVol
        ? [
            { left: 65, right: 70, top: 15, height: '55%' },
            { left: 65, right: 70, top: '73%', height: '12%' },
          ]
        : [{ left: 65, right: 70, top: 15, bottom: 40 }],
      xAxis: [
        {
          type: 'category' as const, data: xLabels, gridIndex: 0,
          axisLabel: { color: '#64748b', fontSize: 9, interval: isIntraday ? Math.floor(xLabels.length / 8) : 'auto' },
          axisLine: { lineStyle: { color: '#334155' } },
          axisTick: { show: false },
        },
        {
          type: 'category' as const, data: xLabels, gridIndex: showVol ? 1 : 0,
          show: showVol,
          axisLabel: { show: false },
          axisLine: { lineStyle: { color: '#334155' } },
          axisTick: { show: false },
        },
      ],
      yAxis: [
        // 0: 左轴 ¥/g (始终存在)
        { type: 'value' as const, gridIndex: 0, name: '¥/g', nameTextStyle: { color: '#3b82f6', fontSize: 10 }, axisLabel: { color: '#3b82f6', fontSize: 10 }, splitLine: { lineStyle: { color: '#1e293b' } }, scale: true },
        // 1: 成交量(手) — 始终声明，无成交量时隐藏
        { type: 'value' as const, gridIndex: showVol ? 1 : 0, name: '手', show: showVol, nameTextStyle: { color: '#64748b', fontSize: 9 }, axisLabel: { color: '#64748b', fontSize: 8, show: showVol, formatter: (v: number) => v >= 10000 ? `${(v/10000).toFixed(1)}万` : `${v}` }, splitLine: { show: false }, scale: true },
        // 2: 右轴 $/oz (始终存在)
        { type: 'value' as const, gridIndex: 0, name: '$/oz', nameTextStyle: { color: '#fbbf24', fontSize: 10 }, axisLabel: { color: '#fbbf24', fontSize: 10 }, splitLine: { show: false }, scale: true },
      ],
      series: [...mainSeries, ...volSeries],
      dataZoom: isDaily ? [
        { type: 'slider' as const, xAxisIndex: [0, 1], start: 0, end: 100, height: 22, bottom: 5,
          backgroundColor: '#1e293b', dataBackground: { lineStyle: { color: '#475569' }, areaStyle: { color: '#334155' } },
          selectedDataBackground: { lineStyle: { color: '#fbbf24' }, areaStyle: { color: '#fbbf2460' } },
          handleStyle: { color: '#fbbf24' }, textStyle: { color: '#94a3b8', fontSize: 9 } },
        { type: 'inside' as const, xAxisIndex: [0, 1] },
      ] : [],
    };
    return option;
  })();
  }, [data, chartType]);

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-400">{'\u{1F4C8}'} 金价走势</h3>
        <div className="flex gap-0.5 bg-slate-800 rounded-lg p-0.5">
          {tabs.map(t => (
            <button key={t.key} onClick={() => setChartType(t.key)}
              className={`px-3 py-1 text-xs rounded-md transition ${chartType === t.key ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}>
              {t.label}
            </button>
          ))}
        </div>
      </div>
      {loading ? (
        <div className="h-80 flex items-center justify-center text-slate-500">{'加载中...'}</div>
      ) : (
        <ReactECharts option={option} style={{ height: showVol ? 460 : 400 }} theme="dark" notMerge={true} />
      )}
      <div className="flex justify-between mt-1 text-xs text-slate-600">
        {chartType === 'intraday' && <span>蓝色 AU9999 · 黄色虚线 XAU/USD (右轴)</span>}
        {chartType === '5day'   && <span>红涨绿跌 K线 AU9999 · 蓝线收盘 · 黄线 XAU (右轴) │ 下方成交量</span>}
        {chartType === 'daily'  && <span>红涨绿跌 K线 AU9999 · 蓝线收盘 · 黄线 XAU (右轴) │ 中方成交量 · 滑块缩放</span>}
      </div>
    </div>
  );
}
