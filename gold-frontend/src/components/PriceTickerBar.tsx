import type { GoldPrice, ScoreResult } from '../types';

function scoreColor(s: number): string {
  if (s >= 80) return '#ef4444';   // 红 = 极度看多
  if (s >= 60) return '#f97316';   // 橙 = 偏多
  if (s >= 40) return '#eab308';   // 琥珀 = 中性
  if (s >= 20) return '#84cc16';   // 青柠 = 偏空
  return '#22c55e';                // 绿 = 极度看空
}

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
          />
          <div className="w-px h-10 bg-[var(--border-dim)] hidden sm:block" />
          <TickerItem
            label="上海溢价"
            value={`${prices.premium > 0 ? '+' : ''}${prices.premium.toFixed(1)} ¥/g`}
          />
          {score && (
            <>
              <div className="w-px h-10 bg-[var(--border-dim)] hidden sm:block" />
              <div className="text-center px-5 py-3">
                <div className="text-[10px] tracking-[0.16em] uppercase text-[var(--text-muted)] mb-1.5 font-medium">
                  AI 综合评分
                </div>
                <div className="flex items-center justify-center gap-2.5">
                  <span className="text-2xl font-light tracking-tight mono"
                    style={{color: scoreColor(score.total_score)}}>
                    {score.total_score}
                  </span>
                  <span className="px-2.5 py-0.5 rounded text-[10px] tracking-wider font-medium text-white"
                    style={{background: scoreColor(score.total_score)}}>
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
