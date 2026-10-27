import React, { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { errorMessage, isAbortedError } from '../api/client';
import { hskLabel, WordLookup } from '../api/dictionary';
import { lookupBubbleWord } from '../api/reader';
import { SampleBubble, SamplePage as SamplePageData, getSamplePage, isSampleMissing } from '../api/sample';
import { TAB_PATHS } from '../routes';
import { speakChinese } from '../utils/speech';
import { useSystemStatus } from '../utils/useSystemStatus';
import { AuthImage } from './AuthImage';

type Variant = 'original' | 'inpainted' | 'rendered';

const VARIANT_LABELS: Record<Variant, string> = {
  original: 'Ảnh gốc',
  inpainted: 'Đã xóa chữ',
  rendered: 'Đã dịch'
};

const HAS_CJK = /[㐀-鿿]/;

type LookupState =
  | { status: 'idle' }
  | { status: 'loading'; word: string }
  | { status: 'ok'; word: string; data: WordLookup }
  | { status: 'error'; word: string; message: string };

interface SamplePageProps {
  onLookupWord: (term: string) => void;
}

/** Trang mẫu đã xử lý thật để người mới thử Hover & Dịch trước khi tải truyện của mình (F04.16). */
export const SamplePage: React.FC<SamplePageProps> = ({ onLookupWord }) => {
  const { tts_enabled } = useSystemStatus();
  const [sample, setSample] = useState<SamplePageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [missing, setMissing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [variant, setVariant] = useState<Variant>('original');
  const [activeBubbleId, setActiveBubbleId] = useState<number | null>(null);
  const [lookup, setLookup] = useState<LookupState>({ status: 'idle' });
  const [retryTick, setRetryTick] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    getSamplePage(controller.signal)
      .then(result => {
        setSample(result);
        setMissing(false);
        setVariant(current => (result.variants[current] ? current : 'original'));
      })
      .catch(err => {
        if (isAbortedError(err)) return;
        if (isSampleMissing(err)) setMissing(true);
        else setError(errorMessage(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [retryTick]);

  const activeBubble = sample?.bubbles.find(bubble => bubble.id === activeBubbleId) ?? null;

  const pickBubble = (bubble: SampleBubble) => {
    setActiveBubbleId(bubble.id);
    setLookup({ status: 'idle' });
    if (tts_enabled) void speakChinese(bubble.text_zh, 0.85);
  };

  const lookupToken = async (bubbleId: number, word: string) => {
    setLookup({ status: 'loading', word });
    try {
      const result = await lookupBubbleWord(bubbleId, word, false);
      setLookup({ status: 'ok', word, data: result.lookup });
    } catch (err) {
      setLookup({ status: 'error', word, message: errorMessage(err) });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-sm text-slate-500">
        <span className="w-5 h-5 border-2 border-pink-300 border-t-transparent rounded-full animate-spin"></span>
        Đang tải trang mẫu...
      </div>
    );
  }

  if (missing || error || !sample) {
    return (
      <div className="w-full max-w-[600px] mx-auto px-4 py-20 flex flex-col items-center text-center gap-4">
        <span className="material-symbols-outlined text-[48px] text-pink-300">image_search</span>
        <h2 className="text-xl font-extrabold text-slate-800 font-['Plus_Jakarta_Sans']">
          {missing ? 'Chưa có trang mẫu' : 'Không tải được trang mẫu'}
        </h2>
        <p className="text-sm text-slate-600">
          {missing ? 'Quản trị viên chưa chọn trang mẫu. Bạn có thể thử ngay với truyện trong Thư viện.' : error}
        </p>
        <div className="flex gap-2">
          {!missing && (
            <button onClick={() => setRetryTick(value => value + 1)} className="px-5 py-2.5 rounded-full bg-[#a43073] hover:bg-[#85145a] text-white text-xs font-bold">
              Thử lại
            </button>
          )}
          <Link to={TAB_PATHS.library} className="px-5 py-2.5 rounded-full bg-white border border-pink-200 text-[#a43073] text-xs font-bold hover:bg-pink-50">
            Mở Thư viện
          </Link>
        </div>
      </div>
    );
  }

  const variantKeys = (Object.keys(VARIANT_LABELS) as Variant[]).filter(key => sample.variants[key]);
  const imageUrl = sample.variants[variant];
  const aspect = sample.width && sample.height ? `${sample.width} / ${sample.height}` : undefined;

  return (
    <div className="w-full max-w-[1100px] mx-auto px-4 sm:px-6 py-8 flex flex-col gap-5">
      <div className="flex flex-col gap-1">
        <span className="text-xs font-bold uppercase tracking-wider text-[#a43073]">Dành cho người mới</span>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-800 font-['Plus_Jakarta_Sans']">Thử Hover & Dịch với trang mẫu</h1>
        <p className="text-sm text-slate-500">Chạm vào khung thoại để xem Pinyin và bản dịch, rồi bấm từng từ để tra nghĩa như khi đọc truyện thật.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_340px] gap-5 items-start">
        <section className="rounded-3xl bg-white border border-pink-100 shadow-soft p-3 sm:p-4 flex flex-col gap-3">
          {variantKeys.length > 1 && (
            <div className="flex flex-wrap gap-2">
              {variantKeys.map(key => (
                <button
                  key={key}
                  onClick={() => setVariant(key)}
                  aria-pressed={variant === key}
                  className={`px-3 py-1.5 rounded-full text-xs font-semibold ${variant === key ? 'bg-[#a43073] text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                >
                  {VARIANT_LABELS[key]}
                </button>
              ))}
            </div>
          )}
          <div className="relative w-full overflow-hidden rounded-2xl bg-slate-50" style={{ aspectRatio: aspect }}>
            <AuthImage src={imageUrl} alt="Trang truyện mẫu" className="w-full h-full object-contain" />
            {sample.bubbles.map((bubble, index) => {
              if (bubble.x_pct === null || bubble.y_pct === null || bubble.w_pct === null || bubble.h_pct === null) return null;
              const active = bubble.id === activeBubbleId;
              return (
                <button
                  key={bubble.id}
                  type="button"
                  onClick={() => pickBubble(bubble)}
                  aria-label={`Lời thoại ${index + 1}`}
                  aria-pressed={active}
                  style={{ top: `${bubble.y_pct}%`, left: `${bubble.x_pct}%`, width: `${bubble.w_pct}%`, height: `${bubble.h_pct}%` }}
                  className={`absolute rounded-xl border-2 transition-colors ${active ? 'border-[#a43073] bg-pink-400/25' : 'border-pink-400/70 bg-pink-400/10 hover:bg-pink-400/25'}`}
                >
                  <span className="absolute -top-2 -left-2 w-5 h-5 rounded-full bg-pink-500 text-white text-[10px] font-bold flex items-center justify-center shadow-xs">{index + 1}</span>
                </button>
              );
            })}
          </div>
        </section>

        <aside className="rounded-3xl bg-white border border-pink-100 shadow-soft p-5 flex flex-col gap-3 lg:sticky lg:top-24">
          {!activeBubble ? (
            <div className="text-sm text-slate-500 flex flex-col items-center text-center gap-2 py-6">
              <span className="material-symbols-outlined text-[36px] text-pink-300">touch_app</span>
              Chọn một khung thoại trên trang để bắt đầu.
            </div>
          ) : (
            <>
              <div>
                {activeBubble.pinyin && <div className="text-xs font-mono text-slate-500">{activeBubble.pinyin}</div>}
                <div className="text-lg font-['Noto_Serif_SC'] font-bold text-slate-800 mt-0.5">{activeBubble.text_zh}</div>
              </div>
              <div className="p-3 rounded-xl bg-pink-50/80 border border-pink-200 text-pink-900 text-xs font-semibold leading-relaxed">
                {activeBubble.text_vi ? activeBubble.text_vi : 'Chưa có bản dịch'}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {activeBubble.tokens.filter(token => HAS_CJK.test(token.word)).map((token, index) => (
                  <button
                    key={`${token.word}-${index}`}
                    onClick={() => void lookupToken(activeBubble.id, token.word)}
                    className="bg-slate-100 hover:bg-pink-100 hover:text-pink-600 px-2 py-1 rounded-md text-xs text-slate-600 font-medium transition-colors"
                    title="Bấm để tra nghĩa"
                  >
                    {token.word}{token.pinyin ? ` (${token.pinyin})` : ''}
                  </button>
                ))}
              </div>
              {lookup.status === 'loading' && <p className="text-xs text-slate-500">Đang tra từ...</p>}
              {lookup.status === 'error' && <p role="alert" className="text-xs text-red-600">{lookup.message}</p>}
              {lookup.status === 'ok' && (
                <div className="text-xs text-slate-600 space-y-1.5 border-t border-slate-100 pt-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-base font-bold text-slate-800 font-['Noto_Serif_SC']">{lookup.word}</span>
                    {lookup.data.pinyin && <span className="font-mono text-blue-600">{lookup.data.pinyin}</span>}
                    {lookup.data.han_viet && <span className="text-slate-500">· {lookup.data.han_viet}</span>}
                    <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 text-[10px] font-bold">{hskLabel(lookup.data.hsk.level)}</span>
                  </div>
                  {!lookup.data.found && <p>Chưa có trong từ điển.</p>}
                  {lookup.data.readings.slice(0, 1).flatMap(reading => reading.definitions.slice(0, 3)).map((definition, index) => (
                    <p key={index}>• {definition.gloss}</p>
                  ))}
                  <button onClick={() => onLookupWord(lookup.word)} className="text-[11px] font-bold text-[#a43073] hover:underline">Xem chi tiết đầy đủ</button>
                </div>
              )}
            </>
          )}
        </aside>
      </div>
    </div>
  );
};
