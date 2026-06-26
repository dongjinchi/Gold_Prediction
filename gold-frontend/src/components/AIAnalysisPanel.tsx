import type { ScoreResult } from '../types';
import { useSSE } from '../hooks/useSSE';
import DebateStreamView from './DebateStreamView';

function ScoreBadge({ score }: { score: ScoreResult }) {
  const colors: Record<string, string> = {
    '极度看多': 'bg-green-600',
    '偏多': 'bg-green-500',
    '中性': 'bg-yellow-500',
    '偏空': 'bg-orange-500',
    '极度看空': 'bg-red-600',
  };

  // 根据指标得分生成简短总结
  const scores = score.indicator_scores || {};
  const entries = Object.entries(scores) as [string, number][];
  const topBull = entries.filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
  const topBear = entries.filter(([, v]) => v < 0).sort((a, b) => a[1] - b[1]);
  const signalText = score.signal === '偏多' ? '多数指标温和看多' :
    score.signal === '极度看多' ? '多项指标共振，强烈看多' :
    score.signal === '偏空' ? '多数指标倾向看空' :
    score.signal === '极度看空' ? '多项指标共振，强烈看空' :
    '多空力量均衡，方向待明朗';
  const detail = topBull.length > 0
    ? `主要利多：${topBull.slice(0, 2).map(([k]) => ({tips_10y:'TIPS下行',dxy:'美元走弱',spdr:'ETF增持',cot:'持仓安全',premium:'国内溢价',cb_event:'央行购金'}[k] || k)).join('、')}`
    : topBear.length > 0
    ? `主要利空：${topBear.slice(0, 2).map(([k]) => ({tips_10y:'TIPS上行',dxy:'美元走强',spdr:'ETF减持',cot:'持仓拥挤',premium:'溢价收窄',cb_event:'央行售金'}[k] || k)).join('、')}`
    : '暂无显著方向性信号';

  return (
    <div className="flex items-center gap-4 p-4 bg-slate-800 rounded-lg">
      <div className="relative w-16 h-16 flex-shrink-0 flex items-center justify-center">
        <svg className="w-16 h-16 -rotate-90" viewBox="0 0 36 36">
          <circle cx="18" cy="18" r="15.5" fill="none" stroke="#334155" strokeWidth="3" />
          <circle cx="18" cy="18" r="15.5" fill="none" stroke="#fbbf24"
            strokeWidth="3" strokeDasharray={`${score.total_score} 100`}
            strokeLinecap="round" />
        </svg>
        <span className="absolute text-lg font-bold text-yellow-400">{score.total_score}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded text-xs font-semibold text-white ${colors[score.signal] || 'bg-slate-500'}`}>
            {score.signal}
          </span>
          <span className="text-xs text-slate-500">信心 {(score.confidence * 100).toFixed(0)}%</span>
        </div>
        <div className="text-xs text-slate-300 mt-1.5 leading-relaxed">{signalText}。{detail}。</div>
      </div>
    </div>
  );
}

export default function AIAnalysisPanel({ score }: { score: ScoreResult | null }) {
  const { events, status, result, loading, start, stop } = useSSE();

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-slate-400">🧠 AI投资研判</h3>

      {score && <ScoreBadge score={score} />}

      <button
        onClick={loading ? stop : start}
        disabled={loading}
        className={`py-2 px-4 rounded-lg font-medium text-sm transition ${
          loading
            ? 'bg-red-600/20 text-red-400 border border-red-800'
            : 'bg-blue-600 hover:bg-blue-500 text-white'
        }`}
      >
        {loading ? '⏹ 停止' : '🚀 生成AI研判'}
      </button>

      {events.length > 0 && <DebateStreamView events={events} status={status} />}

      {result && (
        <div className="bg-emerald-900/20 border border-emerald-800 rounded-lg p-4">
          <div className="text-xs text-emerald-400 mb-1">{'\u{1F4CB}'} 最终结论</div>
          <div className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
            {result.consensus}
          </div>
          {(result.direction || result.position) && (
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              {result.direction && (
                <span className="px-2.5 py-1 rounded bg-slate-800 text-slate-200 font-semibold">
                  {'\u{1F4C8}'} 明日: {{ up: '涨 ↑', down: '跌 ↓', flat: '平 →' }[result.direction]}
                </span>
              )}
              {result.position && (
                <span className={`px-2.5 py-1 rounded font-semibold ${
                  result.position === 'buy' ? 'bg-green-700 text-green-200' :
                  result.position === 'sell' ? 'bg-red-700 text-red-200' :
                  result.position === 'reduce' ? 'bg-orange-700 text-orange-200' :
                  'bg-blue-700 text-blue-200'
                }`}>
                  {'\u{1F4B0}'} 持仓: {{ buy: '买入/加仓', sell: '卖出/清仓', reduce: '轻仓/减仓', hold: '持有/观望' }[result.position]}
                </span>
              )}
              <span className="px-2.5 py-1 rounded bg-slate-800 text-slate-300">
                信心: {((result.confidence ?? 0) * 100).toFixed(0)}%
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
