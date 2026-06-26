import type { MacroIndicator, CBEvent } from '../types';

function RiskChip({ label, value, status }: {
  label: string; value: string; status: 'low' | 'normal' | 'high' | 'active';
}) {
  const bg = {
    low: 'bg-emerald-900/30 text-emerald-400 border-emerald-800',
    normal: 'bg-slate-800 text-slate-300 border-slate-700',
    high: 'bg-orange-900/30 text-orange-400 border-orange-800',
    active: 'bg-blue-900/30 text-blue-400 border-blue-800',
  };

  return (
    <div className={`flex justify-between items-center p-3 rounded-lg border ${bg[status]}`}>
      <span className="text-sm">{label}</span>
      <span className="font-semibold">{value}</span>
    </div>
  );
}

export default function RiskPanel({ macro, cbEvents }: {
  macro: MacroIndicator | null;
  cbEvents: CBEvent[];
}) {
  if (!macro) return null;

  const hasActiveCB = cbEvents.length > 0 &&
    (new Date().getTime() - new Date(cbEvents[0].event_date).getTime()) < 3 * 86400000;

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold text-slate-400 mb-1">⚠️ 风险信号</h3>
      <RiskChip
        label="VIX 恐慌指数"
        value={macro.vix != null ? `${macro.vix.toFixed(1)}` : '-'}
        status={(macro.vix ?? 0) > 25 ? 'high' : 'low'}
      />
      <RiskChip
        label="COMEX投机拥挤"
        value={macro.cot_net_long != null ? `${(macro.cot_net_long / 1000).toFixed(0)}k` : '-'}
        status="normal"
      />
      <RiskChip
        label="央行购金事件"
        value={hasActiveCB ? '🟢 活跃' : '⚪ 静默'}
        status={hasActiveCB ? 'active' : 'normal'}
      />
      <RiskChip
        label="上海溢价"
        value="--"
        status="normal"
      />
    </div>
  );
}
