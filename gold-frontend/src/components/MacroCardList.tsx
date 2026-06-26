import type { MacroIndicator } from '../types';

function MacroCard({ name, value, signal, detail }: {
  name: string; value: string; signal?: 'bullish' | 'bearish' | 'neutral' | 'crowded';
  detail?: string;
}) {
  const signalColor = {
    bullish: 'text-green-400',
    bearish: 'text-red-400',
    neutral: 'text-yellow-400',
    crowded: 'text-orange-400',
  };

  return (
    <div className="flex justify-between items-center p-3 bg-slate-800 rounded-lg hover:bg-slate-700 transition">
      <div>
        <div className="text-sm font-medium">{name}</div>
        {detail && <div className="text-xs text-slate-500">{detail}</div>}
      </div>
      <div className="text-right">
        <div className="text-lg font-bold">{value}</div>
        {signal && (
          <div className={`text-xs ${signalColor[signal]}`}>
            {signal === 'bullish' ? '▼ 利好' : signal === 'bearish' ? '▲ 利空' : signal === 'crowded' ? '⚠ 拥挤' : '— 中性'}
          </div>
        )}
      </div>
    </div>
  );
}

export default function MacroCardList({ macro }: { macro: MacroIndicator | null }) {
  if (!macro) return null;

  const cards = [
    { name: '10Y TIPS', value: `${macro.tips_10y?.toFixed(2) ?? '-'}%`, detail: '实际利率' },
    { name: '美元指数 DXY', value: macro.dxy?.toFixed(2) ?? '-', detail: '计价货币' },
    { name: 'SPDR持仓', value: `${macro.spdr_tonnes?.toFixed(1) ?? '-'}t`, detail: '黄金ETF' },
    { name: 'COMEX净多头', value: macro.cot_net_long != null ? `${(macro.cot_net_long / 1000).toFixed(0)}k` : '-', detail: '投机仓位' },
    { name: 'VIX', value: macro.vix?.toFixed(1) ?? '-', detail: '恐慌指数' },
  ];

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold text-slate-400 mb-1">🏦 宏观驱动指标</h3>
      {cards.map(c => (
        <MacroCard key={c.name} {...c} />
      ))}
    </div>
  );
}
