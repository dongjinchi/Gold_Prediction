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
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="text-yellow-400 text-4xl mb-4">🥇</div>
          <div className="text-slate-400">加载黄金投资数据...</div>
          <div className="text-xs text-slate-600 mt-2">首次启动可能需要等待数据抓取</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-400 text-lg mb-2">加载失败</div>
          <div className="text-slate-500 text-sm mb-4">{error}</div>
          <button onClick={refresh} className="px-4 py-2 bg-blue-600 rounded-lg text-sm hover:bg-blue-500">
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950">
      <PriceTickerBar prices={data?.prices ?? null} score={data?.score ?? null} />

      <main className="max-w-7xl mx-auto p-4 space-y-4">
        {/* Row 1: Chart (full width, K-line + volume) */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
          <PriceChart />
        </div>

        {/* Row 2: Macro cards (horizontal strip) */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
          <MacroCardList macro={data?.macro ?? null} />
        </div>

        {/* Accuracy Chart */}
        <AccuracyChart accuracy={accuracy} />

        {/* Row 3: AI + Risk */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-lg p-4">
            <AIAnalysisPanel score={data?.score ?? null} />
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <RiskPanel macro={data?.macro ?? null} cbEvents={data?.cb_events ?? []} />
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-xs text-slate-600 py-4 border-t border-slate-800">
          <p>⚠️ 以上AI分析不构成投资建议，仅供研究参考</p>
          <p className="mt-1">数据来源: akshare | yfinance | FRED | CFTC | 新浪财经</p>
        </div>
      </main>
    </div>
  );
}
