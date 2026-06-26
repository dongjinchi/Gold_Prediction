import { useEffect, useRef } from 'react';
import type { SSEEvent } from '../types';

export default function DebateStreamView({ events, status }: {
  events: SSEEvent[];
  status: string;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  return (
    <div className="bg-slate-900 rounded-lg p-3 max-h-80 overflow-y-auto text-sm">
      <div className="text-blue-400 mb-2">🔄 {status}</div>
      {events
        .filter(e => e.type === 'partial' || e.type === 'status')
        .map((e, i) => (
          <div key={i} className={`mb-2 pb-2 border-b border-slate-800 ${
            e.model === 'deepseek' ? 'text-emerald-400' : 'text-violet-400'
          }`}>
            {e.type === 'status' && (
              <div className="text-slate-500 text-xs">--- {e.message} ---</div>
            )}
            {e.model && (
              <div className="text-xs font-semibold mb-1">
                {e.model === 'deepseek' ? '🤖 DeepSeek' : '🧠 OpenAI'}
              </div>
            )}
            {e.content && <div className="text-slate-300 text-xs leading-relaxed">{e.content}</div>}
          </div>
        ))}
      <div ref={bottomRef} />
    </div>
  );
}
