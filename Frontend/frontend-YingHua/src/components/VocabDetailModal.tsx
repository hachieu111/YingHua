import React, { useCallback, useEffect, useState } from 'react';
import { errorMessage, isAbortedError } from '../api/client';
import { hskLabel } from '../api/dictionary';
import {
  ApiReviewLog,
  CARD_STATE_LABEL,
  CARD_TYPE_LABEL,
  RATING_LABEL,
  getCardHistory,
  resetCard,
  resumeCard,
  suspendCard
} from '../api/review';
import {
  ApiCardBrief,
  ApiVocabDetail,
  VocabStatus,
  deleteVocab,
  deleteVocabContext,
  getVocab,
  updateVocab
} from '../api/vocab';
import { ReaderTarget } from '../types';
import { formatDateTime } from '../utils/format';
import { speakChinese } from '../utils/speech';
import { AuthImage } from './AuthImage';
import { AiNotePanel } from './AiNotePanel';
import { ConfirmDialog } from './ConfirmDialog';

interface VocabDetailModalProps {
  entryId: number | null;
  onClose: () => void;
  /** Dữ liệu Sổ tay đổi (sao, trạng thái, ghi chú, thẻ...): danh sách và số liệu cần tải lại. */
  onChanged: () => void;
  onDeleted: () => void;
  onOpenReader: (target: ReaderTarget) => void;
  showToast: (message: string) => void;
}

const NOTE_MAX = 1000;
const MEANING_MAX = 500;
const HISTORY_SIZE = 5;

const STATUS_OPTIONS: { value: VocabStatus; label: string }[] = [
  { value: 'learning', label: 'Đang học' },
  { value: 'known', label: 'Đã thuộc' },
  { value: 'ignored', label: 'Tạm bỏ qua' }
];

type Pending =
  | { kind: 'delete-word' }
  | { kind: 'delete-context'; contextId: number }
  | { kind: 'reset-card'; cardId: number };

export const VocabDetailModal: React.FC<VocabDetailModalProps> = ({ entryId, onClose, onChanged, onDeleted, onOpenReader, showToast }) => {
  const [detail, setDetail] = useState<ApiVocabDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<Pending | null>(null);
  const [historyFor, setHistoryFor] = useState<number | null>(null);
  const [history, setHistory] = useState<ApiReviewLog[] | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [editingMeaning, setEditingMeaning] = useState(false);
  const [meaningDraft, setMeaningDraft] = useState('');
  // Chỉ gọi AI khi người học chủ động mở, để không tốn lượt cho mỗi lần xem chi tiết.
  const [aiOpenFor, setAiOpenFor] = useState<number | null>(null);

  const load = useCallback(
    async (id: number, signal?: AbortSignal) => {
      try {
        const data = await getVocab(id, signal);
        setDetail(data);
        setNote(data.note ?? '');
        setError(null);
      } catch (err) {
        if (!isAbortedError(err)) setError(errorMessage(err));
      }
    },
    []
  );

  useEffect(() => {
    if (entryId === null) return;
    const controller = new AbortController();
    setDetail(null);
    setError(null);
    setHistoryFor(null);
    setHistory(null);
    setPending(null);
    setEditingMeaning(false);
    setLoading(true);
    load(entryId, controller.signal).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [entryId, load]);

  useEffect(() => {
    if (entryId === null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !pending) onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [entryId, onClose, pending]);

  if (entryId === null) return null;

  // Chạy một thao tác ghi, rồi tải lại chi tiết để hiển thị đúng trạng thái máy chủ.
  const run = async (action: () => Promise<unknown>, successMessage?: string) => {
    setBusy(true);
    try {
      await action();
      await load(entryId);
      onChanged();
      if (successMessage) showToast(successMessage);
    } catch (err) {
      showToast(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const confirmPending = async () => {
    if (!pending) return;
    const action = pending;
    setBusy(true);
    try {
      if (action.kind === 'delete-word') {
        await deleteVocab(entryId);
        showToast('Đã xóa từ khỏi Sổ tay');
        setPending(null);
        onDeleted();
        return;
      }
      if (action.kind === 'delete-context') {
        await deleteVocabContext(entryId, action.contextId);
        showToast('Đã xóa ngữ cảnh');
      } else {
        await resetCard(action.cardId);
        showToast('Đã đặt lại thẻ như thẻ mới');
      }
      await load(entryId);
      onChanged();
      setPending(null);
    } catch (err) {
      showToast(errorMessage(err));
      setPending(null);
    } finally {
      setBusy(false);
    }
  };

  const toggleHistory = async (card: ApiCardBrief) => {
    if (historyFor === card.id) {
      setHistoryFor(null);
      return;
    }
    setHistoryFor(card.id);
    setHistory(null);
    setHistoryLoading(true);
    try {
      setHistory((await getCardHistory(card.id, 1, HISTORY_SIZE)).items);
    } catch (err) {
      showToast(errorMessage(err));
      setHistoryFor(null);
    } finally {
      setHistoryLoading(false);
    }
  };

  const saveMeaning = async (current: ApiVocabDetail) => {
    const value = meaningDraft.trim();
    if (!value) {
      showToast('Vui lòng nhập nghĩa tiếng Việt.');
      return;
    }
    if (value === (current.meaning_vi ?? '')) {
      setEditingMeaning(false);
      return;
    }
    await run(() => updateVocab(current.id, { meaning_vi: value }), 'Đã lưu nghĩa của bạn');
    setEditingMeaning(false);
  };

  const noteChanged = detail !== null && note.trim() !== (detail.note ?? '');

  const pendingText: Record<Pending['kind'], { title: string; message: string; confirm: string }> = {
    'delete-word': {
      title: 'Xóa từ khỏi Sổ tay?',
      message: 'Từ cùng mọi ngữ cảnh, thẻ ôn và lịch sử ôn của nó sẽ bị xóa và không thể khôi phục.',
      confirm: 'Xóa từ'
    },
    'delete-context': {
      title: 'Xóa ngữ cảnh này?',
      message: 'Chỉ ngữ cảnh (ảnh và câu) bị xóa; từ và các thẻ ôn vẫn được giữ.',
      confirm: 'Xóa ngữ cảnh'
    },
    'reset-card': {
      title: 'Đặt lại thẻ này?',
      message: 'Thẻ quay về như thẻ mới và đến hạn ngay; lịch sử ôn vẫn được giữ.',
      confirm: 'Đặt lại'
    }
  };

  return (
    <div className="fixed inset-0 z-[60] bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white rounded-3xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 flex flex-col gap-5"
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Chi tiết từ vựng"
      >
        {loading && <div className="py-10 text-center text-sm text-slate-500">Đang tải chi tiết từ...</div>}
        {error && !detail && (
          <div className="flex flex-col items-center gap-3 py-8 text-center">
            <p className="text-sm text-rose-600">{error}</p>
            <button onClick={() => void load(entryId)} className="px-4 py-2 rounded-full bg-[#a43073] text-white text-xs font-bold">Thử lại</button>
          </div>
        )}

        {detail && (
          <>
            <div className="flex items-start justify-between gap-3">
              <div className="flex flex-col gap-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-4xl font-extrabold text-slate-800 font-['Noto_Serif_SC'] break-all">{detail.term}</span>
                  <button
                    onClick={() => void speakChinese(detail.term, 0.85)}
                    className="w-8 h-8 shrink-0 rounded-full bg-blue-50 hover:bg-blue-100 text-blue-600 flex items-center justify-center"
                    title="Nghe phát âm"
                  >
                    <span className="material-symbols-outlined text-[18px]">volume_up</span>
                  </button>
                  <button
                    disabled={busy}
                    onClick={() => void run(() => updateVocab(detail.id, { is_starred: !detail.is_starred }))}
                    className={`w-8 h-8 shrink-0 rounded-full flex items-center justify-center ${detail.is_starred ? 'bg-amber-100 text-amber-500' : 'bg-slate-100 text-slate-400 hover:text-amber-500'}`}
                    title="Đánh dấu sao"
                  >
                    <span className="material-symbols-outlined text-[18px]">{detail.is_starred ? 'star' : 'star_border'}</span>
                  </button>
                </div>
                {detail.pinyin && <span className="text-sm font-mono font-semibold text-blue-600">{detail.pinyin}</span>}
                {detail.sino_vietnamese && <span className="text-xs font-semibold text-[#a43073]">Hán Việt: {detail.sino_vietnamese}</span>}
                <span className="self-start mt-1 px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-900 font-bold text-xs">
                  {hskLabel(detail.hsk_level)}
                  {detail.hsk_source === 'derived' && <span className="font-normal"> (ước lượng)</span>}
                </span>
              </div>
              <button onClick={onClose} className="p-1.5 rounded-full text-slate-500 hover:bg-slate-100" title="Đóng">
                <span className="material-symbols-outlined text-[22px]">close</span>
              </button>
            </div>

            <div className="p-4 rounded-2xl bg-[#eff4ff] border border-blue-100">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Nghĩa tiếng Việt</span>
                {!editingMeaning && (
                  <button
                    disabled={busy}
                    onClick={() => {
                      setMeaningDraft(detail.meaning_vi ?? '');
                      setEditingMeaning(true);
                    }}
                    className="inline-flex items-center gap-1 text-[11px] font-bold text-[#a43073] hover:underline disabled:opacity-50"
                  >
                    <span className="material-symbols-outlined text-[14px]">edit</span>
                    {detail.meaning_vi ? 'Sửa nghĩa' : 'Nhập nghĩa'}
                  </button>
                )}
              </div>
              {editingMeaning ? (
                <div className="flex flex-col gap-2">
                  <textarea
                    value={meaningDraft}
                    maxLength={MEANING_MAX}
                    onChange={e => setMeaningDraft(e.target.value)}
                    rows={2}
                    autoFocus
                    placeholder="Nhập nghĩa tiếng Việt của bạn..."
                    className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-sm text-slate-800 outline-none focus:ring-2 focus:ring-[#f472b6] resize-y"
                  />
                  <div className="flex justify-end gap-2">
                    <button disabled={busy} onClick={() => setEditingMeaning(false)} className="px-3 py-1 rounded-full text-xs font-bold text-slate-600 hover:bg-white">Hủy</button>
                    <button
                      disabled={busy || !meaningDraft.trim()}
                      onClick={() => void saveMeaning(detail)}
                      className="px-4 py-1 rounded-full bg-[#a43073] hover:bg-[#85145a] text-white text-xs font-bold disabled:opacity-50"
                    >
                      Lưu nghĩa
                    </button>
                  </div>
                </div>
              ) : (
                <span className={`text-sm font-semibold ${detail.meaning_vi ? 'text-slate-800' : 'text-slate-500'}`}>
                  {detail.meaning_vi || 'Chưa có nghĩa trong từ điển, bạn có thể tự nhập nghĩa.'}
                </span>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Trạng thái học</span>
              <div className="flex flex-wrap gap-2">
                {STATUS_OPTIONS.map(option => (
                  <button
                    key={option.value}
                    disabled={busy || detail.status === option.value}
                    onClick={() => void run(() => updateVocab(detail.id, { status: option.value }), `Đã chuyển sang “${option.label}”`)}
                    className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all ${
                      detail.status === option.value ? 'bg-[#a43073] text-white' : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Ghi chú của bạn</span>
                <span className="text-[10px] text-slate-400">{note.length}/{NOTE_MAX}</span>
              </div>
              <textarea
                value={note}
                maxLength={NOTE_MAX}
                onChange={e => setNote(e.target.value)}
                rows={3}
                placeholder="Mẹo nhớ, cách dùng, ví dụ riêng..."
                className="w-full rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800 outline-none focus:ring-2 focus:ring-[#f472b6] resize-y"
              />
              <button
                disabled={busy || !noteChanged}
                onClick={() => void run(() => updateVocab(detail.id, { note: note.trim() }), note.trim() ? 'Đã lưu ghi chú' : 'Đã xóa ghi chú')}
                className="self-end px-4 py-1.5 rounded-full bg-[#a43073] hover:bg-[#85145a] text-white text-xs font-bold disabled:opacity-50"
              >
                Lưu ghi chú
              </button>
            </div>

            {aiOpenFor === detail.id ? (
              <AiNotePanel key={detail.id} vocabEntryId={detail.id} active onSpeak={text => void speakChinese(text, 0.85)} />
            ) : (
              <button
                onClick={() => setAiOpenFor(detail.id)}
                className="inline-flex items-center justify-center gap-1.5 rounded-2xl border border-violet-200 bg-violet-50 px-4 py-2.5 text-xs font-bold text-[#a43073] hover:bg-pink-50"
              >
                <span className="material-symbols-outlined text-[16px]">auto_awesome</span>
                Xem thẻ mở rộng AI (mẹo nhớ, ví dụ, cụm từ)
              </button>
            )}

            <div className="flex flex-col gap-2">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Ngữ cảnh ({detail.contexts.length})</span>
              {detail.contexts.length === 0 && <p className="text-xs text-slate-500">Từ này chưa có ngữ cảnh (lưu từ khung tra từ).</p>}
              {detail.contexts.map(context => (
                <div key={context.id} className="rounded-2xl border border-pink-100 bg-[#ffd8e7]/20 p-3 flex flex-col gap-2">
                  {context.snippet_url && (
                    <AuthImage src={context.snippet_url} alt={`Ngữ cảnh của ${detail.term}`} className="w-full max-h-48 object-contain rounded-xl bg-white" />
                  )}
                  <p className="text-sm font-['Noto_Serif_SC'] font-bold text-slate-800">{context.sentence_zh}</p>
                  {context.sentence_vi && <p className="text-xs text-slate-600 italic">{context.sentence_vi}</p>}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-[11px] text-slate-500">{context.source_label ?? 'Không rõ nguồn'}</span>
                    <div className="flex items-center gap-1">
                      {context.source && context.source.chapter_id !== null && (
                        <button
                          onClick={() => {
                            const source = context.source;
                            if (!source) return;
                            onClose();
                            onOpenReader({ chapterId: source.chapter_id, pageNo: source.page_no, pageId: source.page_id });
                          }}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold text-[#0060ac] hover:bg-blue-50"
                        >
                          <span className="material-symbols-outlined text-[14px]">open_in_new</span>
                          Mở trang truyện
                        </button>
                      )}
                      <button
                        disabled={busy}
                        onClick={() => setPending({ kind: 'delete-context', contextId: context.id })}
                        className="p-1 rounded-full text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                        title="Xóa ngữ cảnh"
                      >
                        <span className="material-symbols-outlined text-[18px]">delete</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex flex-col gap-2">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Thẻ ôn ({detail.cards.length})</span>
              {detail.cards.map(card => (
                <div key={card.id} className="rounded-2xl border border-slate-200 p-3 flex flex-col gap-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-col">
                      <span className="text-sm font-bold text-slate-800">
                        {CARD_TYPE_LABEL[card.card_type]}
                        {card.is_suspended && (
                          <span className="ml-2 px-2 py-0.5 rounded-full bg-slate-200 text-slate-600 text-[10px] font-bold">Đang tạm ngưng</span>
                        )}
                      </span>
                      <span className="text-[11px] text-slate-500">
                        {CARD_STATE_LABEL[card.state] ?? card.state} · ôn {card.reps} lần · quên {card.lapses} lần · hạn {formatDateTime(card.due_at)}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        disabled={busy}
                        onClick={() =>
                          void run(
                            () => (card.is_suspended ? resumeCard(card.id) : suspendCard(card.id)),
                            card.is_suspended ? 'Đã tiếp tục thẻ' : 'Đã tạm ngưng thẻ'
                          )
                        }
                        className="px-2.5 py-1 rounded-full text-[11px] font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 disabled:opacity-50"
                      >
                        {card.is_suspended ? 'Tiếp tục' : 'Tạm ngưng'}
                      </button>
                      <button
                        disabled={busy}
                        onClick={() => setPending({ kind: 'reset-card', cardId: card.id })}
                        className="px-2.5 py-1 rounded-full text-[11px] font-bold text-amber-800 bg-amber-100 hover:bg-amber-200 disabled:opacity-50"
                      >
                        Đặt lại
                      </button>
                      <button
                        onClick={() => void toggleHistory(card)}
                        className="px-2.5 py-1 rounded-full text-[11px] font-bold text-[#0060ac] bg-blue-50 hover:bg-blue-100"
                      >
                        Lịch sử
                      </button>
                    </div>
                  </div>
                  {historyFor === card.id && (
                    <div className="text-[11px] text-slate-600 bg-slate-50 rounded-xl p-2.5">
                      {historyLoading && <span>Đang tải lịch sử...</span>}
                      {history && history.length === 0 && <span>Thẻ chưa được ôn lần nào.</span>}
                      {history?.map(log => (
                        <div key={log.id} className="flex justify-between gap-2 py-0.5">
                          <span>{formatDateTime(log.reviewed_at)} · <strong>{RATING_LABEL[log.rating] ?? log.rating}</strong></span>
                          <span>hạn kế tiếp {formatDateTime(log.due_after)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-100">
              <button
                disabled={busy}
                onClick={() => setPending({ kind: 'delete-word' })}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-bold text-rose-700 bg-rose-50 hover:bg-rose-100 disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-[16px]">delete</span>
                Xóa từ khỏi Sổ tay
              </button>
              <button onClick={onClose} className="px-5 py-2 rounded-full text-xs font-bold text-slate-600 hover:bg-slate-100">Đóng</button>
            </div>
          </>
        )}
      </div>

      {pending && (
        <ConfirmDialog
          title={pendingText[pending.kind].title}
          message={pendingText[pending.kind].message}
          confirmLabel={pendingText[pending.kind].confirm}
          busy={busy}
          onConfirm={() => void confirmPending()}
          onCancel={() => setPending(null)}
        />
      )}
    </div>
  );
};
