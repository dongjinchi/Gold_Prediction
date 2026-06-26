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

  return (
    <div className="flex items-center gap-4 p-4 bg-slate-800 rounded-lg">
      <div className="relative w-16 h-16 flex items-center justify-center">
        <svg className="w-16 h-16 -rotate-90" viewBox="0 0 36 36">
          <circle cx="18" cy="18" r="15.5" fill="none" stroke="#334155" strokeWidth="3" />
          <circle cx="18" cy="18" r="15.5" fill="none" stroke="#fbbf24"
            strokeWidth="3" strokeDasharray={`${score.total_score} 100`}
            strokeLinecap="round" />
        </svg>
        <span className="absolute text-lg font-bold text-yellow-400">{score.total_score}</span>
      </div>
      <div>
        <span className={`px-2 py-0.5 rounded text-xs font-semibold text-white ${colors[score.signal] || 'bg-slate-500'}`}>
          {score.signal}
        </span>
        <div className="text-xs text-slate-400 mt-1">
          置信度: {(score.confidence * 100).toFixed(0)}%
        </div>
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
          <div className="text-xs text-emerald-400 mb-1">📋 最终结论</div>
          <div className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
            {result.consensus}
          </div>
          {result.direction && (
            <div className="mt-2 flex gap-2 text-xs">
              <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                方向: {{ up: '涨↑', down: '跌↓', flat: '平→' }[result.direction]}
              </span>
              <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                置信度: {((result.confidence ?? 0) * 100).toFixed(0)}%
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
