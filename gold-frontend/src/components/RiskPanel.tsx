import type { MacroIndicator, CBEvent } from '../types';

function RiskChip({ label, value, status }: {
  label: string; value: string;
  status: 'safe' | 'neutral' | 'warning' | 'active' | 'danger';
}) {
  const palette = {
    safe:    { bg:'rgba(52,211,153,0.06)', border:'rgba(52,211,153,0.2)', dot:'#34d399' },
    neutral: { bg:'var(--surface-2)', border:'var(--border-dim)', dot:'var(--text-muted)' },
    warning: { bg:'rgba(251,191,36,0.06)', border:'rgba(251,191,36,0.2)', dot:'#fbbf24' },
    active:  { bg:'rgba(96,165,250,0.06)', border:'rgba(96,165,250,0.2)', dot:'#60a5fa' },
    danger:  { bg:'rgba(248,113,113,0.06)', border:'rgba(248,113,113,0.2)', dot:'#f87171' },
  };
  const p = palette[status];

  return (
    <div className="flex justify-between items-center p-3 rounded-lg transition-all duration-300"
      style={{background:p.bg, border:`1px solid ${p.border}`}}>
      <div className="flex items-center gap-2">
        <div className="w-1.5 h-1.5 rounded-full" style={{background:p.dot}} />
        <span className="text-xs tracking-wide" style={{color:'var(--text-secondary)'}}>{label}</span>
      </div>
      <span className="text-xs font-medium mono" style={{color:'var(--text-primary)'}}>{value}</span>
    </div>
  );
}

export default function RiskPanel({ macro, cbEvents }: {
  macro: MacroIndicator | null;
  cbEvents: CBEvent[];
}) {
  if (!macro) return null;

  const hasActiveCB = cbEvents.length > 0 &&
    (Date.now() - new Date(cbEvents[0].event_date).getTime()) < 3 * 86400000;

  return (
    <div className="flex flex-col gap-2.5">
      <h3 className="text-[10px] tracking-[0.15em] uppercase mb-1" style={{color:'var(--text-muted)'}}>
        风险信号
      </h3>
      <RiskChip label="VIX 恐慌指数"
        value={macro.vix != null ? macro.vix.toFixed(1) : '—'}
        status={(macro.vix ?? 0) > 28 ? 'danger' : (macro.vix ?? 0) > 20 ? 'warning' : 'safe'} />
      <RiskChip label="COMEX 投机拥挤度"
        value={macro.cot_net_long != null ? `${(macro.cot_net_long / 1000).toFixed(0)}k` : '—'}
        status="neutral" />
      <RiskChip label="央行购金事件"
        value={hasActiveCB ? '活跃' : '静默'}
        status={hasActiveCB ? 'active' : 'neutral'} />
    </div>
  );
}
