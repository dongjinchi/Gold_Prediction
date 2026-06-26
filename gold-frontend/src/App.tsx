import { useDashboard } from './hooks/useDashboard';
import PriceTickerBar from './components/PriceTickerBar';
import PriceChart from './components/PriceChart';
import MacroCardList from './components/MacroCardList';
import AIAnalysisPanel from './components/AIAnalysisPanel';
import AccuracyChart from './components/AccuracyChart';
import RiskPanel from './components/RiskPanel';

export default function App() {
  const { data, accuracy, loading, error, refresh } = useDashboard();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{background:'var(--obsidian)'}}>
        <div className="text-center animate-in">
          <div className="text-5xl mb-6 font-serif italic text-[var(--gold-400)] opacity-80">Au</div>
          <div className="text-sm tracking-[0.2em] text-[var(--text-secondary)] uppercase">Loading Market Data</div>
          <div className="mt-4 flex justify-center gap-1">
            {[0,1,2].map(i => (
              <div key={i} className="w-1 h-1 rounded-full bg-[var(--gold-400)]/60"
                style={{animation: `pulse 1.2s ${i*0.2}s infinite`}} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{background:'var(--obsidian)'}}>
        <div className="text-center animate-in">
          <div className="text-rose-400/80 text-sm tracking-wider mb-3">数据加载失败</div>
          <div className="text-[var(--text-muted)] text-xs mb-6">{error}</div>
          <button onClick={refresh}
            className="px-6 py-2 border border-[var(--gold-400)]/30 text-[var(--gold-300)] text-xs tracking-wider
                       hover:bg-[var(--gold-400)]/10 transition rounded">
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{background:'var(--obsidian)'}}>
      <PriceTickerBar prices={data?.prices ?? null} score={data?.score ?? null} />

      <main className="max-w-7xl mx-auto p-5 space-y-4">
        {/* 走势图 */}
        <div className="gold-card p-5 animate-in" style={{animationDelay:'0.1s'}}>
          <PriceChart />
        </div>

        {/* 宏观指标 */}
        <div className="gold-card p-5 animate-in" style={{animationDelay:'0.2s'}}>
          <MacroCardList macro={data?.macro ?? null} />
        </div>

        {/* 准确率 */}
        <div className="animate-in" style={{animationDelay:'0.3s'}}>
          <AccuracyChart accuracy={accuracy} />
        </div>

        {/* AI + 风险 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 animate-in" style={{animationDelay:'0.35s'}}>
          <div className="lg:col-span-2 gold-card p-5">
            <AIAnalysisPanel score={data?.score ?? null} />
          </div>
          <div className="gold-card p-5">
            <RiskPanel macro={data?.macro ?? null} cbEvents={data?.cb_events ?? []} />
          </div>
        </div>

        {/* Footer */}
        <div className="text-center py-6">
          <hr className="gold-divider mb-4" />
          <p className="text-[10px] tracking-[0.12em] text-[var(--text-muted)] uppercase">
            Au Vision · 数据来源 akshare / yfinance / FRED / CFTC · AI 分析不构成投资建议
          </p>
        </div>
      </main>
    </div>
  );
}
