import { useState } from 'react';
import ReactECharts from 'echarts-for-react';
import type { AccuracyStats } from '../types';

export default function AccuracyChart({ accuracy }: { accuracy: AccuracyStats | null }) {
  const [expanded, setExpanded] = useState(false);

  if (!accuracy || accuracy.total_count === 0) {
    return (
      <div className="p-3 bg-slate-800/50 rounded-lg text-center text-xs text-slate-500">
        暂无预测记录 — 生成AI研判并等待T+1验证后显示
      </div>
    );
  }

  const dailyData: { date: string; correct: number }[] = [];
  const records = accuracy.records || [];
  let runningCorrect = 0;
  let runningTotal = 0;

  [...records].reverse().forEach(r => {
    runningTotal++;
    if (r.is_correct === 1) runningCorrect++;
    dailyData.push({
      date: r.pred_date,
      correct: runningTotal > 0 ? runningCorrect / runningTotal : 0,
    });
  });

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 10, right: 20, bottom: 25, left: 45 },
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: 'rgba(30,41,59,0.95)',
      borderColor: '#475569',
      textStyle: { color: '#f8fafc', fontSize: 11 },
      formatter: (params: any) => {
        const val = params[0]?.value;
        return `累计准确率: ${(val * 100).toFixed(0)}%`;
      },
    },
    xAxis: {
      type: 'category' as const,
      data: dailyData.map(d => d.date?.slice(5) || ''),
      axisLabel: { color: '#64748b', fontSize: 9 },
      axisLine: { lineStyle: { color: '#334155' } },
    },
    yAxis: {
      type: 'value' as const,
      min: 0,
      max: 1,
      axisLabel: { color: '#64748b', fontSize: 10, formatter: (v: number) => `${(v * 100).toFixed(0)}%` },
      splitLine: { lineStyle: { color: '#1e293b' } },
    },
    series: [{
      name: '累计准确率',
      type: 'line',
      data: dailyData.map(d => d.correct),
      smooth: false,
      symbol: 'none',
      lineStyle: { color: '#22c55e', width: 1.5 },
      markLine: {
            silent: true,
            data: [{ yAxis: 0.5, label: { formatter: '50%', color: '#64748b', fontSize: 10 }, lineStyle: { color: '#475569', type: 'dashed' } }],
      },
    }],
  };

  return (
    <div className="border border-slate-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 bg-slate-800 hover:bg-slate-700 transition text-left"
      >
        <div>
          <span className="text-sm font-semibold text-slate-300">📊 历史预测准确率</span>
          <span className="ml-2 text-xs text-slate-500">
            {accuracy.total_count}次预测
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="text-green-400">
            累计 {(accuracy.total_accuracy * 100).toFixed(0)}%
          </span>
          <span className="text-blue-400">
            30日 {(accuracy.rolling_30d_accuracy * 100).toFixed(0)}%
          </span>
          <span className="text-slate-500">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {expanded && (
        <div className="p-3 bg-slate-900">
          <div className="flex gap-4 mb-3 text-xs">
            <div className="px-3 py-1.5 bg-slate-800 rounded">
              <span className="text-slate-400">总次数 </span>
              <span className="text-white font-semibold">{accuracy.total_count}</span>
            </div>
            <div className="px-3 py-1.5 bg-slate-800 rounded">
              <span className="text-slate-400">正确 </span>
              <span className="text-green-400 font-semibold">{accuracy.correct_count}</span>
            </div>
            <div className="px-3 py-1.5 bg-slate-800 rounded">
              <span className="text-slate-400">错误 </span>
              <span className="text-red-400 font-semibold">{accuracy.total_count - accuracy.correct_count}</span>
            </div>
          </div>
          <ReactECharts option={option} style={{ height: 180 }} theme="dark" />
        </div>
      )}
    </div>
  );
}
