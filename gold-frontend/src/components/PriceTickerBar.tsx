import type { GoldPrice, ScoreResult } from '../types';

function TickerItem({ label, value, change, color = 'text-yellow-400' }: {
  label: string; value: string; change?: string; color?: string;
}) {
  return (
    <div className="text-center px-3">
      <div className="text-xs text-slate-400 whitespace-nowrap">{label}</div>
      <div className={`text-lg font-bold ${color}`}>{value}</div>
      {change && <div className="text-xs text-green-400">{change}</div>}
    </div>
  );
}

export default function PriceTickerBar({ prices, score }: {
  prices: GoldPrice | null;
  score: ScoreResult | null;
}) {
  if (!prices) return null;

  const signalColors: Record<string, string> = {
    '极度看多': 'text-green-400',
    '偏多': 'text-green-300',
    '中性': 'text-yellow-400',
    '偏空': 'text-orange-400',
    '极度看空': 'text-red-400',
  };

  return (
    <div className="bg-slate-900 border-b border-slate-700 py-3">
      <div className="max-w-7xl mx-auto flex justify-around items-center flex-wrap gap-y-2">
        <TickerItem label="国际金价 XAU/USD" value={`$${prices.xau_usd.toFixed(2)}`} />
        <TickerItem label="国内金价 AU9999" value={`¥${prices.au9999.toFixed(2)}/g`} />
        <TickerItem label="USD/CNY" value={prices.usd_cny.toFixed(4)} color="text-slate-200" />
        <TickerItem
          label="上海溢价"
          value={`¥${prices.premium.toFixed(1)}/g`}
          color={prices.premium > 0 ? 'text-green-400' : 'text-red-400'}
        />
        {score && (
          <div className="text-center px-3">
            <div className="text-xs text-slate-400">AI综合评分</div>
            <div className="text-2xl font-extrabold text-yellow-400">{score.total_score}</div>
            <div className={`text-xs ${signalColors[score.signal] || 'text-slate-400'}`}>
              {score.signal}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
