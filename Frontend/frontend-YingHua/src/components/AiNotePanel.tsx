import React, { useCallback, useEffect, useRef, useState } from 'react';
import { errorMessage, isAbortedError } from '../api/client';
import { AiExample, AiNote, getAiNote, isAiRegenerateLimit, regenerateAiNote } from '../api/vocab';
import { useSystemStatus } from '../utils/useSystemStatus';

interface AiNotePanelProps {
  vocabEntryId: number;
  /** Chỉ tải khi true (vd. người học đã lật thẻ); tránh tốn lượt AI cho thẻ chưa xem đáp án. */
  active: boolean;
  onSpeak: (text: string) => void;
}

// Lưu theo mục từ trong phiên làm việc: lật lại thẻ không gọi máy chủ lần nữa.
const noteCache = new Map<number, AiNote>();

const ExampleRow: React.FC<{ item: AiExample; onSpeak: (text: string) => void }> = ({ item, onSpeak }) => (
  <div className="flex items-start justify-between gap-2 rounded-xl bg-white/80 dark:bg-slate-800/80 px-3 py-2">
    <div className="min-w-0">
      <p className="font-['Noto_Serif_SC'] text-sm font-bold text-slate-800 dark:text-slate-100 break-words">{item.zh}</p>
      {item.pinyin && <p className="font-mono text-[11px] text-blue-600 dark:text-blue-300 break-words">{item.pinyin}</p>}
      {item.vi && <p className="text-xs text-slate-600 dark:text-slate-300 break-words">{item.vi}</p>}
    </div>
    <button
      onClick={event => {
        event.stopPropagation();
        onSpeak(item.zh);
      }}
      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-700 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-900/50"
      title="Nghe"
      aria-label={`Nghe ${item.zh}`}
    >
      <span className="material-symbols-outlined text-[16px]">volume_up</span>
    </button>
  </div>
);

/** Khối "Thẻ mở rộng AI" của một mục từ (F08.11): mẹo chiết tự, ví dụ, cụm từ đi kèm. */
export const AiNotePanel: React.FC<AiNotePanelProps> = ({ vocabEntryId, active, onSpeak }) => {
  const { llm_enabled } = useSystemStatus();
  const [note, setNote] = useState<AiNote | null>(() => noteCache.get(vocabEntryId) ?? null);
  const [loading, setLoading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const requested = useRef(false);

  const load = useCallback(
    (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      getAiNote(vocabEntryId, signal)
        .then(result => {
          noteCache.set(vocabEntryId, result);
          setNote(result);
        })
        .catch(err => {
          if (!isAbortedError(err)) setError(errorMessage(err));
        })
        .finally(() => {
          if (!signal?.aborted) setLoading(false);
        });
    },
    [vocabEntryId]
  );

  useEffect(() => {
    if (!llm_enabled || !active || requested.current || noteCache.has(vocabEntryId)) return;
    requested.current = true;
    const controller = new AbortController();
    load(controller.signal);
    return () => {
      controller.abort();
      requested.current = false;
    };
  }, [active, vocabEntryId, load, llm_enabled]);

  const handleRegenerate = async () => {
    if (regenerating) return;
    setRegenerating(true);
    setNotice(null);
    setError(null);
    try {
      const result = await regenerateAiNote(vocabEntryId);
      noteCache.set(vocabEntryId, result);
      setNote(result);
    } catch (err) {
      if (isAiRegenerateLimit(err)) {
        setNotice('Bạn đã hết lượt tạo lại cho từ này.');
        setNote(current => {
          if (!current) return current;
          const updated = { ...current, regenerate_remaining: 0 };
          noteCache.set(vocabEntryId, updated);
          return updated;
        });
      } else {
        setNotice(errorMessage(err));
      }
    } finally {
      setRegenerating(false);
    }
  };

  // Quản trị viên đã tắt tính năng AI (F13.05): ẩn khối này, phần còn lại của thẻ vẫn dùng bình thường.
  if (!llm_enabled || (!active && !note)) return null;

  const busy = loading || regenerating;
  const hasContent = note !== null && (note.mnemonic || note.examples.length > 0 || note.phrases.length > 0);

  return (
    <div className="flex flex-col gap-2 rounded-2xl border border-violet-200 bg-gradient-to-br from-violet-50 to-pink-50 p-4 dark:border-violet-900/50 dark:from-violet-900/20 dark:to-pink-900/20" onClick={event => event.stopPropagation()}>
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1 text-[11px] font-bold uppercase tracking-wider text-[#a43073] dark:text-pink-400">
          <span className="material-symbols-outlined text-[16px]">auto_awesome</span>
          Thẻ mở rộng AI
        </span>
        {note && (
          <span className="rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-bold text-slate-500 dark:bg-slate-800/80 dark:text-slate-400">{note.source_label}</span>
        )}
      </div>

      {busy && (
        <div className="flex flex-col gap-2" aria-busy="true" aria-label="Đang tạo thẻ mở rộng">
          <div className="h-4 w-3/4 animate-pulse rounded bg-white/80 dark:bg-slate-700/60"></div>
          <div className="h-10 animate-pulse rounded-xl bg-white/80 dark:bg-slate-700/60"></div>
          <div className="h-10 animate-pulse rounded-xl bg-white/80 dark:bg-slate-700/60"></div>
          <p className="text-[10px] text-slate-500 dark:text-slate-400">{regenerating ? 'AI đang tạo lại nội dung...' : 'AI đang chuẩn bị nội dung, vài giây nữa...'}</p>
        </div>
      )}

      {!busy && error && (
        <div className="flex items-center justify-between gap-2 rounded-xl bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:bg-rose-900/30 dark:text-rose-300" role="alert">
          <span>{error}</span>
          <button
            onClick={event => {
              event.stopPropagation();
              load();
            }}
            className="font-bold text-[#a43073] dark:text-pink-400 hover:underline"
          >
            Thử lại
          </button>
        </div>
      )}

      {!busy && note && !hasContent && <p className="text-xs text-slate-500 dark:text-slate-400">Chưa có nội dung mở rộng cho từ này.</p>}

      {!busy && note && (
        <>
          {note.mnemonic && (
            <div className="rounded-xl bg-white/80 dark:bg-slate-800/80 px-3 py-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">Mẹo nhớ chiết tự</span>
              <p className="text-xs leading-relaxed text-slate-700 dark:text-slate-200 break-words whitespace-pre-line">{note.mnemonic}</p>
            </div>
          )}
          {note.examples.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">Câu ví dụ</span>
              {note.examples.map((item, index) => (
                <ExampleRow key={`${index}-${item.zh}`} item={item} onSpeak={onSpeak} />
              ))}
            </div>
          )}
          {note.phrases.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">Cụm từ đi kèm</span>
              {note.phrases.map((item, index) => (
                <ExampleRow key={`${index}-${item.zh}`} item={item} onSpeak={onSpeak} />
              ))}
            </div>
          )}
        </>
      )}

      {notice && <p className="text-[11px] font-semibold text-amber-800 dark:text-amber-300">{notice}</p>}

      {note && (
        <div className="flex items-center justify-end">
          <button
            onClick={event => {
              event.stopPropagation();
              void handleRegenerate();
            }}
            disabled={busy || note.regenerate_remaining <= 0}
            className="inline-flex items-center gap-1 rounded-full bg-white px-3 py-1 text-[11px] font-bold text-[#a43073] shadow-xs hover:bg-pink-50 dark:bg-slate-800 dark:text-pink-400 dark:shadow-none dark:hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            title={note.regenerate_remaining > 0 ? 'Nhờ AI tạo lại nội dung' : 'Đã hết lượt tạo lại'}
          >
            <span className="material-symbols-outlined text-[14px]">refresh</span>
            Tạo lại ({note.regenerate_remaining} lượt)
          </button>
        </div>
      )}
    </div>
  );
};
