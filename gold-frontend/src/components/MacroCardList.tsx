import type { MacroIndicator } from '../types';

function MacroCard({ name, value, detail }: {
  name: string; value: string; detail?: string;
}) {
  return (
    <div className="p-3 rounded-lg transition-all duration-300 hover:border-[#3a3428]"
      style={{background:'var(--surface-2)', border:'1px solid var(--border-dim)'}}>
      <div className="text-[10px] tracking-[0.08em] uppercase mb-1.5" style={{color:'var(--text-muted)'}}>
        {name}
      </div>
      <div className="text-lg font-light tracking-tight mono" style={{color:'var(--text-primary)'}}>
        {value}
      </div>
      {detail && (
        <div className="text-[9px] mt-1 tracking-wide" style={{color:'var(--text-muted)'}}>
          {detail}
        </div>
      )}
    </div>
  );
}

export default function MacroCardList({ macro }: { macro: MacroIndicator | null }) {
  if (!macro) return null;

  const cards = [
    { name: '10Y TIPS 实际利率', value: macro.tips_10y != null ? `${macro.tips_10y}%` : '—', detail: '持有成本' },
    { name: '美元指数 DXY', value: macro.dxy != null ? macro.dxy.toFixed(2) : '—', detail: '计价货币' },
    { name: 'SPDR 黄金持仓', value: macro.spdr_tonnes != null ? `${macro.spdr_tonnes}t` : '—', detail: 'ETF 需求' },
    { name: 'COMEX 净多头', value: macro.cot_net_long != null ? `${(macro.cot_net_long / 1000).toFixed(0)}k` : '—', detail: '投机仓位' },
    { name: 'VIX 恐慌指数', value: macro.vix != null ? macro.vix.toFixed(1) : '—', detail: '市场情绪' },
  ];

  return (
    <div>
      <h3 className="text-[10px] tracking-[0.15em] uppercase mb-3" style={{color:'var(--text-muted)'}}>
        宏观驱动指标
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2.5">
        {cards.map(c => <MacroCard key={c.name} {...c} />)}
      </div>
    </div>
  );
}
