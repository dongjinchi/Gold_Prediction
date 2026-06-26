import type { GoldPrice, ScoreResult } from '../types';

function TickerItem({ label, value, sub }: {
  label: string; value: string; sub?: string;
}) {
  return (
    <div className="text-center px-5 py-3">
      <div className="text-[10px] tracking-[0.16em] uppercase text-[var(--text-muted)] mb-1.5 font-medium">
        {label}
      </div>
      <div className="text-xl tracking-tight text-[var(--text-primary)] font-light">
        {value}
      </div>
      {sub && (
        <div className={`text-[10px] mt-1 tracking-wide ${
          sub.startsWith('+') ? 'text-emerald-400/80' :
          sub.startsWith('-') ? 'text-rose-400/70' :
          'text-[var(--text-secondary)]'
        }`}>{sub}</div>
      )}
    </div>
  );
}

export default function PriceTickerBar({ prices, score }: {
  prices: GoldPrice | null;
  score: ScoreResult | null;
}) {
  if (!prices) return null;

  const signalColors: Record<string, string> = {
    '极度看多': 'bg-emerald-600/80',
    '偏多': 'bg-emerald-500/60',
    '中性': 'bg-amber-600/60',
    '偏空': 'bg-orange-500/60',
    '极度看空': 'bg-red-600/70',
  };

  return (
    <div>
      <div className="h-px bg-gradient-to-r from-transparent via-[var(--gold-400)]/30 to-transparent" />
      <div className="bg-[var(--surface)] border-b border-[var(--border-dim)]">
        <div className="max-w-7xl mx-auto flex justify-around items-center flex-wrap">
          <TickerItem
            label="国际金价 XAU/USD"
            value={`$ ${prices.xau_usd.toFixed(1)}`}
          />
          <div className="w-px h-10 bg-[var(--border-dim)] hidden sm:block" />
          <TickerItem
            label="国内金价 AU9999"
            value={`¥ ${prices.au9999.toFixed(1)}`}
          />
          <div className="w-px h-10 bg-[var(--border-dim)] hidden sm:block" />
          <TickerItem
            label="美元 / 人民币"
            value={prices.usd_cny.toFixed(4)}
            sub={`溢价 ${prices.premium > 0 ? '+' : ''}${prices.premium.toFixed(1)} ¥/g`}
          />
          {score && (
            <>
              <div className="w-px h-10 bg-[var(--border-dim)] hidden sm:block" />
              <div className="text-center px-5 py-3">
                <div className="text-[10px] tracking-[0.16em] uppercase text-[var(--text-muted)] mb-1.5 font-medium">
                  AI 综合评分
                </div>
                <div className="flex items-center justify-center gap-2.5">
                  <span className="text-2xl font-light text-[var(--gold-300)] tracking-tight mono">
                    {score.total_score}
                  </span>
                  <span className={`px-2.5 py-0.5 rounded text-[10px] tracking-wider font-medium text-white/90 ${signalColors[score.signal] || 'bg-slate-600'}`}>
                    {score.signal}
                  </span>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
      <div className="h-px bg-gradient-to-r from-transparent via-[var(--gold-400)]/20 to-transparent" />
    </div>
  );
}
