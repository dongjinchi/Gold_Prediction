import type { ScoreResult } from '../types';
import { useSSE } from '../hooks/useSSE';
import DebateStreamView from './DebateStreamView';

const signalMap: Record<string, string> = {
  '极度看多': 'bg-emerald-600/80', '偏多': 'bg-emerald-500/60',
  '中性': 'bg-amber-600/60', '偏空': 'bg-orange-500/60', '极度看空': 'bg-red-600/70',
};

function scoreColor(s: number): string {
  if (s >= 80) return '#22c55e';
  if (s >= 60) return '#84cc16';
  if (s >= 40) return '#eab308';
  if (s >= 20) return '#f97316';
  return '#ef4444';
}

function ScoreBadge({ score, llm }: {
  score: ScoreResult;
  llm?: { direction?: string; position?: string; confidence?: number } | null;
}) {
  const hasLlm = !!(llm?.direction || llm?.position);
  const displayScore = score.total_score;
  const displaySignal = score.signal;
  const arcColor = scoreColor(displayScore);

  const scores = score.indicator_scores || {};
  const entries = Object.entries(scores) as [string, number][];
  const topBull = entries.filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
  const topBear = entries.filter(([, v]) => v < 0).sort((a, b) => a[1] - b[1]);

  const keyDrivers = topBull.length > 0
    ? topBull.slice(0, 2).map(([k]) =>
        ({tips_10y:'TIPS下行',dxy:'美元走弱',spdr:'ETF增持',cot:'持仓安全',premium:'国内溢价',cb_event:'央行购金'}[k]||k)).join(' · ')
    : topBear.length > 0
    ? topBear.slice(0, 2).map(([k]) =>
        ({tips_10y:'TIPS上行',dxy:'美元走强',spdr:'ETF减持',cot:'持仓拥挤',premium:'溢价收窄',cb_event:'央行售金'}[k]||k)).join(' · ')
    : null;

  const llmVerdict = hasLlm
    ? `— AI 研判：${llm!.direction === 'up' ? '看涨 ↑' : llm!.direction === 'down' ? '看跌 ↓' : '看平 →'}，建议${{buy:'买入',sell:'清仓',reduce:'减仓',hold:'持有'}[llm!.position||'hold']}`
    : '';

  return (
    <div className="flex items-center gap-5 p-5 rounded-lg" style={{background:'var(--surface-2)', border:'1px solid var(--border-dim)'}}>
      {/* 评分圆环 — 奢华表盘风格 */}
      <div className="relative w-[72px] h-[72px] flex-shrink-0 flex items-center justify-center">
        {/* 外圈暗纹 */}
        <svg className="absolute w-[72px] h-[72px] -rotate-90" viewBox="0 0 40 40">
          <circle cx="20" cy="20" r="17" fill="none" stroke="var(--border-dim)" strokeWidth="2.5" />
          <circle cx="20" cy="20" r="17" fill="none"
            stroke={arcColor}
            strokeWidth="2.5"
            strokeDasharray={`${displayScore * 1.07} 107`}
            strokeLinecap="round"
            style={{transition:'stroke-dasharray 0.8s ease-out'}}
          />
        </svg>
        {/* 内刻度点 */}
        {[0, 72, 144, 216, 288].map(deg => (
          <div key={deg} className="absolute w-[58px] h-[58px]"
            style={{transform:`rotate(${deg}deg)`}}>
            <div className="w-0.5 h-1.5 rounded-full mx-auto"
              style={{background:deg===0?arcColor:'var(--text-muted)', opacity:deg===0?1:0.3}} />
          </div>
        ))}
        <span className="relative text-xl font-light tracking-tight mono"
          style={{color: arcColor}}>
          {displayScore}
        </span>
        {hasLlm && (
          <span className="absolute -bottom-1.5 text-[9px] tracking-[0.15em] uppercase font-medium"
            style={{color: arcColor}}>AI</span>
        )}
      </div>

      {/* 文字总结 */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-2">
          <span className={`px-2 py-0.5 rounded text-[10px] tracking-wider font-medium text-white/90 ${signalMap[displaySignal] || 'bg-slate-600'}`}>
            {displaySignal}
          </span>
          {hasLlm && (
            <span className="text-[10px] tracking-[0.12em] uppercase" style={{color:'var(--gold-400)'}}>
              ✦ 已研判
            </span>
          )}
        </div>
        {keyDrivers && (
          <div className="text-xs leading-relaxed" style={{color:'var(--text-secondary)'}}>
            {keyDrivers}{llmVerdict && <span style={{color:'var(--text-primary)'}}> {llmVerdict}</span>}
          </div>
        )}
        {!keyDrivers && (
          <div className="text-xs leading-relaxed" style={{color:'var(--text-muted)'}}>
            多空力量均衡，方向待明朗。点击下方按钮获取 AI 深度研判。
          </div>
        )}
      </div>
    </div>
  );
}

export default function AIAnalysisPanel({ score }: { score: ScoreResult | null }) {
  const { events, status, result, loading, error, start, stop } = useSSE();

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-sm tracking-[0.1em] uppercase" style={{color:'var(--text-muted)'}}>
        AI 投资研判
      </h3>

      {score && <ScoreBadge score={score} llm={result} />}

      <button
        onClick={loading ? stop : start}
        className={`py-2.5 px-5 rounded text-xs tracking-[0.1em] font-medium transition-all duration-300 ${
          loading
            ? 'border border-rose-700/30 text-rose-400/80 cursor-pointer hover:bg-rose-900/20'
            : 'text-[var(--obsidian)] font-semibold hover:opacity-90'
        }`}
        style={loading ? {background:'transparent'} : {background:'var(--gold-400)'}}
      >
        {loading ? '停止分析' : '生成 AI 研判'}
      </button>

      {error && (
        <div className="text-xs text-rose-400/70 bg-rose-900/10 border border-rose-800/20 rounded p-3">
          {error}
        </div>
      )}

      {events.length > 0 && <DebateStreamView events={events} status={status} />}

      {result && (
        <div className="rounded-lg p-4" style={{background:'rgba(200,164,92,0.04)', border:'1px solid rgba(200,164,92,0.12)'}}>
          <div className="text-[10px] tracking-[0.15em] uppercase mb-2" style={{color:'var(--gold-400)'}}>
            最终结论
          </div>
          <div className="text-sm leading-relaxed whitespace-pre-wrap" style={{color:'var(--text-primary)'}}>
            {result.consensus}
          </div>
          {(result.direction || result.position) && (
            <div className="mt-4 flex flex-wrap gap-2 text-[11px]">
              {result.direction && (
                <span className="px-3 py-1.5 rounded font-medium tracking-wide"
                  style={{background:'var(--surface)', border:'1px solid var(--border-dim)'}}>
                  {'\u{25B2}'} 明日: {{up:'看涨',down:'看跌',flat:'看平'}[result.direction]}
                </span>
              )}
              {result.position && (
                <span className="px-3 py-1.5 rounded font-medium tracking-wide"
                  style={{
                    background: result.position === 'buy' ? 'rgba(52,211,153,0.1)' :
                                result.position === 'sell' ? 'rgba(248,113,113,0.1)' :
                                result.position === 'reduce' ? 'rgba(251,146,60,0.1)' :
                                'rgba(96,165,250,0.1)',
                    border: `1px solid ${
                      result.position === 'buy' ? 'rgba(52,211,153,0.3)' :
                      result.position === 'sell' ? 'rgba(248,113,113,0.3)' :
                      result.position === 'reduce' ? 'rgba(251,146,60,0.3)' :
                      'rgba(96,165,250,0.3)'}`,
                    color: result.position === 'buy' ? '#6ee7b7' :
                           result.position === 'sell' ? '#fca5a5' :
                           result.position === 'reduce' ? '#fdba74' : '#93c5fd'
                  }}>
                  {'\u{25C6}'} 持仓: {{buy:'买入/加仓',sell:'卖出/清仓',reduce:'轻仓/减仓',hold:'持有/观望'}[result.position]}
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
