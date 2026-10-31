import React, { useEffect, useRef, useState } from 'react';
import { ApiError, errorMessage, isAbortedError } from '../api/client';
import { GrammarResult, SyntaxNode, analyzeBubbleGrammar } from '../api/grammar';
import { ReadingBubble } from '../api/reader';
import { speakChinese } from '../utils/speech';

interface GrammarPanelProps {
  /** Các bong bóng của trang đang đọc. */
  bubbles: ReadingBubble[];
  /** Bong bóng người học vừa tra từ (nếu có) được chọn sẵn. */
  preferredBubbleId: number | null;
  /** Đổi trang thì xóa kết quả cũ. */
  pageId: number | null;
  isLoggedIn: boolean;
  onRequireLogin: (message: string) => void;
}

const HAN = /[㐀-鿿]/;

// Màu theo thành phần câu; nhãn lạ dùng màu trung tính.
const LABEL_STYLES: Record<string, string> = {
  subject: 'bg-pink-100 text-pink-900 border-pink-200 dark:bg-pink-900/30 dark:text-pink-300 dark:border-pink-900/50',
  predicate: 'bg-blue-100 text-blue-900 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-900/50',
  object: 'bg-emerald-100 text-emerald-900 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-900/50',
  complement: 'bg-amber-100 text-amber-900 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-900/50',
  adverbial: 'bg-violet-100 text-violet-900 border-violet-200 dark:bg-violet-900/30 dark:text-violet-300 dark:border-violet-900/50'
};
const DEFAULT_LABEL_STYLE = 'bg-slate-100 text-slate-800 border-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:border-slate-700';

const NodeView: React.FC<{ node: SyntaxNode; depth: number }> = ({ node, depth }) => {
  const [open, setOpen] = useState(false);
  const expandable = Boolean(node.note) || node.children.length > 0;
  const style = LABEL_STYLES[node.label] ?? DEFAULT_LABEL_STYLE;
  return (
    <div className={depth > 0 ? 'ml-3 border-l-2 border-white/80 dark:border-slate-700 pl-2' : ''}>
      <button
        type="button"
        onClick={() => expandable && setOpen(value => !value)}
        aria-expanded={expandable ? open : undefined}
        className={`flex w-full items-center justify-between gap-2 rounded-xl border px-2.5 py-1.5 text-left ${style} ${expandable ? 'cursor-pointer' : 'cursor-default'}`}
      >
        <span className="font-['Noto_Serif_SC'] text-sm font-bold">{node.text}</span>
        <span className="shrink-0 text-[10px] font-bold uppercase tracking-wide opacity-80">{node.label_vi}</span>
      </button>
      {open && (
        <div className="mt-1 flex flex-col gap-1">
          {node.note && <p className="px-1 text-[11px] leading-relaxed text-slate-600 dark:text-slate-300">{node.note}</p>}
          {node.children.map((child, index) => (
            <NodeView key={`${child.label}-${index}`} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
};

const errorText = (err: unknown): string => {
  if (err instanceof ApiError) {
    if (err.code === 'BUBBLE_HAS_NO_HAN') return 'Bong bóng này không có chữ Hán để phân tích.';
    if (err.code === 'SENTENCE_TOO_LONG') return 'Câu quá dài để phân tích. Hãy chọn câu ngắn hơn.';
    if (err.status === 404) return 'Không tìm thấy bong bóng này.';
  }
  return errorMessage(err);
};

export const GrammarPanel: React.FC<GrammarPanelProps> = ({ bubbles, preferredBubbleId, pageId, isLoggedIn, onRequireLogin }) => {
  const candidates = bubbles.filter(bubble => HAN.test(bubble.text_zh));
  const [chosenId, setChosenId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GrammarResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  // Đổi trang: bỏ yêu cầu đang chờ và kết quả cũ.
  useEffect(() => {
    controllerRef.current?.abort();
    setChosenId(null);
    setResult(null);
    setError(null);
    setLoading(false);
  }, [pageId]);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const selected =
    candidates.find(bubble => bubble.id === chosenId) ??
    candidates.find(bubble => bubble.id === preferredBubbleId) ??
    candidates[0] ??
    null;

  const choose = (id: number) => {
    controllerRef.current?.abort();
    setChosenId(id);
    setResult(null);
    setError(null);
    setLoading(false);
  };

  const analyze = async () => {
    if (!selected || loading) return;
    if (!isLoggedIn) {
      onRequireLogin('Vui lòng đăng nhập để phân tích ngữ pháp!');
      return;
    }
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await analyzeBubbleGrammar(selected.id, controller.signal);
      if (!controller.signal.aborted) setResult(data);
    } catch (err) {
      if (isAbortedError(err) || controller.signal.aborted) return;
      setError(errorText(err));
    } finally {
      if (controllerRef.current === controller) setLoading(false);
    }
  };

  return (
    <div className="bg-gradient-to-br from-blue-50/80 via-white to-pink-50/50 dark:from-[#0f172a] dark:via-[#0f172a] dark:to-[#0f172a] rounded-3xl p-5 shadow-soft dark:shadow-none border border-blue-100/70 dark:border-slate-700 transition-colors duration-300">
      <div className="flex items-center gap-2 mb-2">
        <span className="w-2 h-2 rounded-full bg-blue-400"></span>
        <span className="text-xs font-bold text-blue-600 dark:text-blue-300 uppercase tracking-wide">Cấu trúc trọng điểm</span>
      </div>

      {candidates.length === 0 ? (
        <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">Trang này chưa có câu chữ Hán để phân tích ngữ pháp.</p>
      ) : (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap gap-1.5" role="group" aria-label="Chọn câu thoại">
            {candidates.map((bubble, index) => (
              <button
                key={bubble.id}
                type="button"
                onClick={() => choose(bubble.id)}
                aria-pressed={selected?.id === bubble.id}
                title={bubble.text_zh}
                className={`max-w-full truncate rounded-full border px-2.5 py-1 font-['Noto_Serif_SC'] text-[11px] font-bold transition-colors ${
                  selected?.id === bubble.id ? 'border-[#a43073] bg-[#a43073] text-white' : 'border-pink-200 bg-white text-slate-700 hover:bg-pink-50 dark:border-slate-700 dark:bg-[#1e293b] dark:text-slate-200 dark:hover:bg-slate-700'
                }`}
              >
                {index + 1}. {bubble.text_zh.length > 10 ? `${bubble.text_zh.slice(0, 10)}…` : bubble.text_zh}
              </button>
            ))}
          </div>

          {selected && <p className="font-['Noto_Serif_SC'] text-sm leading-relaxed text-slate-800 dark:text-slate-100">{selected.text_zh}</p>}

          <button
            type="button"
            onClick={() => void analyze()}
            disabled={loading || !selected}
            className="flex items-center justify-center gap-1.5 rounded-2xl border border-pink-200 bg-pink-50 py-2 text-xs font-bold text-[#a43073] transition-colors hover:bg-pink-100 dark:border-pink-900/40 dark:bg-pink-900/20 dark:text-pink-400 dark:hover:bg-pink-900/30 disabled:opacity-60"
          >
            <span className="material-symbols-outlined text-[16px]">account_tree</span>
            {loading ? 'Đang phân tích...' : result ? 'Phân tích lại câu này' : 'Phân tích ngữ pháp'}
          </button>
          {!isLoggedIn && <p className="text-[11px] text-slate-500 dark:text-slate-400">Đăng nhập để dùng tính năng này.</p>}

          {error && <p role="alert" className="rounded-xl bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:bg-rose-900/30 dark:text-rose-300">{error}</p>}

          {result && result.status !== 'ok' && (
            <p className="rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">{result.message ?? 'Chưa phân tích được câu này.'}</p>
          )}

          {result && result.status === 'ok' && (
            <div className="flex flex-col gap-3">
              {result.ai_label && <p className="text-[11px] italic text-slate-500 dark:text-slate-400">{result.ai_label}</p>}

              {result.tree.length > 0 && (
                <div className="flex flex-col gap-1.5">
                  <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400">Thành phần câu (bấm để xem chi tiết)</span>
                  {result.tree.map((node, index) => (
                    <NodeView key={`${node.label}-${index}`} node={node} depth={0} />
                  ))}
                </div>
              )}

              {result.points.length > 0 && (
                <div className="flex flex-col gap-2">
                  <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400">Điểm ngữ pháp</span>
                  {result.points.map((point, index) => (
                    <div key={`${point.pattern}-${index}`} className="rounded-2xl border border-blue-100 bg-white p-3 dark:border-slate-700 dark:bg-slate-800">
                      <div className="flex flex-wrap items-baseline gap-2">
                        <span className="font-['Noto_Serif_SC'] text-sm font-bold text-[#a43073] dark:text-pink-400">{point.pattern}</span>
                        <span className="text-xs font-bold text-slate-700 dark:text-slate-200">{point.name}</span>
                      </div>
                      <p className="mt-1 text-[11px] leading-relaxed text-slate-600 dark:text-slate-300">{point.explanation}</p>
                      <div className="mt-2 flex items-start justify-between gap-2 rounded-xl bg-slate-50 p-2 dark:bg-[#1e293b]">
                        <div className="min-w-0">
                          <p className="font-['Noto_Serif_SC'] text-xs text-slate-800 dark:text-slate-100">{point.example_zh}</p>
                          <p className="text-[11px] text-slate-500 dark:text-slate-400">{point.example_vi}</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => void speakChinese(point.example_zh)}
                          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white text-slate-400 hover:bg-pink-100 hover:text-pink-600 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-pink-900/30 dark:hover:text-pink-300"
                          title="Nghe câu ví dụ"
                          aria-label="Nghe câu ví dụ"
                        >
                          <span className="material-symbols-outlined text-[16px]">volume_up</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {result.tree.length === 0 && result.points.length === 0 && (
                <p className="text-xs text-slate-600 dark:text-slate-300">Câu này không có cấu trúc đáng chú ý.</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
