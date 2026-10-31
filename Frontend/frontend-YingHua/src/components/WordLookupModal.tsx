import React, { useEffect, useState } from 'react';
import { ApiError, errorMessage } from '../api/client';
import { ApiCharacter, ApiExample, WordLookup, hskLabel, lookupWord } from '../api/dictionary';
import { isAlreadySaved, saveResultMessage, saveWord } from '../api/vocab';
import { useInNotebook } from '../utils/useInNotebook';
import { useSystemStatus } from '../utils/useSystemStatus';
import { speakChinese } from '../utils/speech';
import StrokeAnimation from './StrokeAnimation';

interface WordLookupModalProps {
  /** Từ cần tra; null = đóng. */
  term: string | null;
  onClose: () => void;
  isLoggedIn: boolean;
  onRequireLogin: () => void;
  showToast: (message: string) => void;
}

const etymologyText = (e: ApiCharacter['etymology']): string => {
  if (!e) return '';
  const parts = [e.type, e.hint, e.phonetic ? `âm: ${e.phonetic}` : null, e.semantic ? `nghĩa: ${e.semantic}` : null];
  return parts.filter((x): x is string => Boolean(x)).join(' · ');
};

const ExampleLine: React.FC<{ example: ApiExample }> = ({ example }) => (
  <div className="text-xs bg-slate-50 border border-slate-100 rounded-xl p-2.5 leading-relaxed dark:bg-slate-800 dark:border-slate-700">
    <div className="font-['Noto_Serif_SC'] font-medium text-slate-800 dark:text-slate-100">{example.zh}</div>
    {example.pinyin && <div className="font-mono text-[11px] text-blue-600 dark:text-blue-300">{example.pinyin}</div>}
    {example.vi && <div className="text-slate-600 dark:text-slate-300">{example.vi}</div>}
    {example.source === 'tatoeba' && <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">Tatoeba</div>}
  </div>
);

export const WordLookupModal: React.FC<WordLookupModalProps> = ({ term, onClose, isLoggedIn, onRequireLogin, showToast }) => {
  const { tts_enabled } = useSystemStatus();
  const [data, setData] = useState<WordLookup | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [inNotebook, markSaved] = useInNotebook(data?.term ?? term, isLoggedIn);

  useEffect(() => {
    if (!term) return;
    let cancelled = false;
    setData(null);
    setError(null);
    setLoading(true);
    lookupWord(term)
      .then(result => {
        if (!cancelled) setData(result);
      })
      .catch(err => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : 'Không thể tra từ, vui lòng thử lại.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [term]);

  useEffect(() => {
    if (!term) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [term, onClose]);

  if (!term) return null;

  // Lưu vào Sổ tay từ khung tra từ: không gắn bong bóng nên không có ảnh ngữ cảnh (F07.01).
  const handleSave = async () => {
    if (!isLoggedIn) {
      onClose();
      onRequireLogin();
      return;
    }
    const word = data?.term ?? term;
    setSaving(true);
    try {
      showToast(saveResultMessage(word, await saveWord({ term: word, source: 'lookup' })));
      markSaved();
    } catch (err) {
      if (isAlreadySaved(err)) markSaved();
      showToast(isAlreadySaved(err) ? 'Từ này đã có với ngữ cảnh này' : errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const usesCvdict = data?.readings.some(r => r.definitions.some(d => d.source === 'cvdict')) ?? false;

  return (
    <div
      className="fixed inset-0 z-[60] bg-slate-900/50 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-[#0f172a] dark:border dark:border-slate-700 dark:shadow-none rounded-3xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6 flex flex-col gap-4"
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Tra từ"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex flex-col gap-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-4xl font-extrabold text-slate-800 dark:text-white font-['Noto_Serif_SC'] break-all">
                {data?.term ?? term}
              </span>
              <button
                onClick={() => void speakChinese(data?.term ?? term, 0.9)}
                disabled={!tts_enabled}
                className="w-8 h-8 shrink-0 rounded-full bg-blue-50 hover:bg-blue-100 text-blue-600 dark:bg-blue-900/20 dark:hover:bg-blue-900/30 dark:text-blue-300 flex items-center justify-center transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                title={tts_enabled ? 'Nghe phát âm' : 'Tính năng nghe đang tạm tắt'}
              >
                <span className="material-symbols-outlined text-[18px]">volume_up</span>
              </button>
            </div>
            {data?.pinyin && <span className="text-sm font-mono font-semibold text-blue-600 dark:text-blue-300">{data.pinyin}</span>}
            {data?.han_viet && <span className="text-xs font-semibold text-[#a43073] dark:text-pink-400">Hán Việt:{data.han_viet}</span>}
            {data && (
              <span className="self-start mt-1 px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-300 font-bold text-xs">
                {hskLabel(data.hsk.level)}
                {data.hsk.source === 'derived' && (
                  <span className="font-normal"> (ước lượng từ chữ cấu thành)</span>
                )}
              </span>
            )}
          </div>
          <button onClick={onClose} className="p-1.5 rounded-full text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700" title="Đóng">
            <span className="material-symbols-outlined text-[22px]">close</span>
          </button>
        </div>

        {loading && <div className="text-sm text-slate-500 dark:text-slate-400 py-6 text-center">Đang tra từ...</div>}
        {error && <div className="text-sm text-rose-600 bg-rose-50 dark:text-rose-300 dark:bg-rose-900/30 rounded-xl p-3">{error}</div>}

        {data && !data.found && !loading && (
          <div className="text-sm text-slate-600 bg-slate-50 dark:text-slate-300 dark:bg-slate-800 rounded-xl p-3">Chưa có nghĩa trong từ điển</div>
        )}

        {data?.found && (
          <>
            {data.readings.map((reading, idx) => (
              <section key={`${reading.pinyin}-${idx}`} className="flex flex-col gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-mono font-bold text-blue-600 dark:text-blue-300">{reading.pinyin}</span>
                  {reading.han_viet && <span className="text-xs text-slate-500 dark:text-slate-400">({reading.han_viet})</span>}
                  {reading.part_of_speech.map(pos => (
                    <span key={pos} className="px-2 py-0.5 rounded-full bg-pink-50 text-[#a43073] dark:bg-pink-900/20 dark:text-pink-400 text-[11px] font-semibold">
                      {pos}
                    </span>
                  ))}
                </div>
                {reading.definitions.length > 0 ? (
                  <ol className="list-decimal pl-5 text-sm text-slate-700 dark:text-slate-200 space-y-1">
                    {reading.definitions.map((def, i) => (
                      <li key={i}>{def.gloss}</li>
                    ))}
                  </ol>
                ) : (
                  reading.english.length > 0 && (
                    <ol className="list-decimal pl-5 text-sm text-slate-700 dark:text-slate-200 space-y-1">
                      {reading.english.map((gloss, i) => (
                        <li key={i}>{gloss}</li>
                      ))}
                    </ol>
                  )
                )}
                {reading.examples.map((ex, i) => (
                  <ExampleLine key={i} example={ex} />
                ))}
              </section>
            ))}

            {data.specialized.length > 0 && (
              <section className="flex flex-col gap-1.5">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Từ điển tu tiên</h4>
                {data.specialized.map(item => (
                  <div key={item.kind} className="text-sm text-slate-700 bg-amber-50 dark:text-slate-200 dark:bg-amber-900/20 rounded-xl p-2.5">
                    <span className="font-semibold text-amber-900 dark:text-amber-300">{item.label}: </span>
                    {item.meanings.join('; ')}
                  </div>
                ))}
              </section>
            )}

            {data.limited ? (
              <div className="rounded-2xl bg-pink-50 border border-pink-100 dark:bg-pink-900/20 dark:border-pink-900/40 p-4 flex flex-col gap-2 text-center">
                <p className="text-sm text-slate-700 dark:text-slate-200">Đăng nhập để xem đầy đủ nghĩa, ví dụ và phân rã chữ Hán.</p>
                <button
                  onClick={() => {
                    onClose();
                    onRequireLogin();
                  }}
                  className="self-center px-5 py-2 rounded-full bg-[#a43073] hover:bg-[#85145a] text-white text-xs font-bold transition-colors"
                >
                  Đăng nhập / Đăng ký
                </button>
              </div>
            ) : (
              data.characters.length > 0 && (
                <section className="flex flex-col gap-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Phân rã chữ Hán</h4>
                  {data.characters.map((c, i) => (
                    <div key={`${c.ch}-${i}`} className="flex flex-wrap items-start gap-3 bg-slate-50 dark:bg-slate-800 rounded-xl p-2.5">
                      <span className="text-3xl font-['Noto_Serif_SC'] font-bold text-slate-800 dark:text-slate-100">{c.ch}</span>
                      {c.found ? (
                        <div className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed flex-1 min-w-[160px]">
                          <div>
                            {c.pinyin && <span className="font-mono text-blue-600 dark:text-blue-300">{c.pinyin}</span>}
                            {c.han_viet && <span> · Hán Việt: {c.han_viet}</span>}
                          </div>
                          <div>
                            {c.radical && (
                              <span>
                                Bộ thủ: <span className="font-['Noto_Serif_SC']">{c.radical}</span>
                              </span>
                            )}
                            {c.stroke_count !== null && <span> · {c.stroke_count} nét</span>}
                          </div>
                          {(c.decomposition || c.components.length > 0) && (
                            <div>
                              Cấu tạo: <span className="font-['Noto_Serif_SC']">{c.decomposition ?? ''}</span>
                              {c.components.length > 0 && (
                                <span className="font-['Noto_Serif_SC']"> ({c.components.join(' + ')})</span>
                              )}
                            </div>
                          )}
                          {etymologyText(c.etymology) && <div>Nguồn gốc: {etymologyText(c.etymology)}</div>}
                          {(c.strokes ?? []).length === 0 && (
                            <div className="text-slate-400 dark:text-slate-500">Chưa có dữ liệu nét viết</div>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-slate-500 dark:text-slate-400 self-center">Chưa có dữ liệu phân rã</span>
                      )}
                      {(c.strokes ?? []).length > 0 && (
                        <div className="w-full flex justify-center">
                          <StrokeAnimation strokes={c.strokes ?? []} medians={c.medians ?? []} autoPlay />
                        </div>
                      )}
                    </div>
                  ))}
                </section>
              )
            )}
          </>
        )}

        <button
          onClick={() => void handleSave()}
          disabled={saving || inNotebook}
          className="w-full py-2.5 rounded-full text-xs font-bold text-white bg-gradient-to-r from-pink-500 to-rose-400 hover:from-pink-600 hover:to-rose-500 flex items-center justify-center gap-1.5 transition-all disabled:opacity-60"
        >
          <span className="material-symbols-outlined text-[16px]">{inNotebook ? 'check' : 'bookmark_add'}</span>
          <span>{saving ? 'Đang lưu...' : inNotebook ? 'Đã có trong Sổ tay' : 'Lưu vào Sổ tay'}</span>
        </button>

        {usesCvdict && <p className="text-[10px] text-slate-400 dark:text-slate-500 text-center">Nghĩa: CVDICT (CC BY-SA 4.0)</p>}
      </div>
    </div>
  );
};
