import React from 'react';
import type { BladeBest, BladeRoundRequest, WeakRadicals } from '../api/gamification';
import { SPEED_LABEL } from '../game/phikiem/rules';
import type { GamePrefs, SpeedOption } from '../game/phikiem/types';
import { useTourPage } from '../tour/TourProvider';

const BANDS: { band: number; label: string; hanzi: string }[] = [
  { band: 1, label: 'HSK 1', hanzi: '一' },
  { band: 2, label: 'HSK 2', hanzi: '二' },
  { band: 3, label: 'HSK 3', hanzi: '三' },
  { band: 4, label: 'HSK 4', hanzi: '四' },
  { band: 5, label: 'HSK 5', hanzi: '五' },
  { band: 6, label: 'HSK 6', hanzi: '六' },
  { band: 7, label: 'HSK 7–9', hanzi: '高' }
];

const STEPS = [
  { icon: 'keyboard', text: 'Gõ pinyin không dấu, không cần chọn chữ: kiếm tự khóa chữ thấp nhất khớp phần đã gõ. Chữ ü gõ là u.' },
  { icon: 'swords', text: 'Gõ đúng hết, phi kiếm bay tới chém đứt đôi chữ. Chuỗi càng dài, điểm càng cao, tối đa ×3.' },
  { icon: 'favorite', text: 'Chữ chạm đáy mất một mạng và đứt chuỗi. Backspace xóa, Esc tạm dừng.' }
];

const SPEEDS: SpeedOption[] = ['calm', 'standard', 'storm'];

interface WeakState {
  data: WeakRadicals | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

interface LobbyProps {
  best: BladeBest[] | null;
  weak: WeakState;
  prefs: GamePrefs;
  busy: boolean;
  error: string | null;
  onPrefs: (prefs: GamePrefs) => void;
  onStart: (request: BladeRoundRequest) => void;
}

const Toggle: React.FC<{ label: string; icon: string; on: boolean; onChange: (value: boolean) => void }> = ({ label, icon, on, onChange }) => (
  <button
    type="button"
    aria-pressed={on}
    onClick={() => onChange(!on)}
    className={`px-3 py-2 rounded-full text-xs font-bold flex items-center gap-1.5 border transition-colors ${on ? 'bg-[#a43073] border-[#a43073] text-white' : 'bg-white/5 border-white/15 text-white/60 hover:text-white'}`}
  >
    <span className="material-symbols-outlined text-[16px]">{icon}</span>
    {label}
  </button>
);

/** Sảnh chọn band HSK, chế độ bộ thủ hay quên và tùy chọn chơi (F16.01). */
export const PhiKiemLobby: React.FC<LobbyProps> = ({ best, weak, prefs, busy, error, onPrefs, onStart }) => {
  useTourPage('game');
  const bandBest = (band: number) => best?.find(item => item.mode === 'hsk' && item.hsk_band === band);
  const radicalBest = best?.find(item => item.mode === 'weak_radical');
  return (
    <div className="flex flex-col gap-7">
      <header className="text-center flex flex-col items-center gap-1">
        <h1 className="font-['Ma_Shan_Zheng','Noto_Serif_SC'] text-5xl sm:text-7xl bg-gradient-to-b from-[#fff6cf] via-[#ffd76a] to-[#c9862a] bg-clip-text text-transparent drop-shadow-[0_4px_0_rgba(164,48,115,0.7)]">
          飞剑斩字
        </h1>
        <p className="text-lg sm:text-xl font-extrabold text-white tracking-tight font-['Plus_Jakarta_Sans']">Phi Kiếm Trảm Tự</p>
        <p className="text-xs sm:text-sm text-white/60 max-w-md">Gõ pinyin thật nhanh, ngự kiếm chém đôi những chữ Hán đang rơi. Điểm do máy chủ chấm, mỗi ván nhận XP.</p>
      </header>

      {error && <p role="alert" className="text-sm text-center font-semibold text-[#ffb3c0] bg-[#7a1030]/40 border border-[#ff5c6c]/30 rounded-2xl px-4 py-2.5">{error}</p>}

      <section data-tour="game-bands" className="flex flex-col gap-3" aria-label="Chọn cấp HSK">
        <h2 className="text-sm font-bold text-white">Chọn cấp HSK</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {BANDS.map(({ band, label, hanzi }) => {
            const stats = bandBest(band);
            return (
              <button
                key={band}
                type="button"
                disabled={busy}
                onClick={() => onStart({ mode: 'hsk', hsk_band: band, radical: null })}
                className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 hover:border-[#ffd76a]/70 hover:-translate-y-0.5 p-4 text-left transition-all disabled:opacity-50"
              >
                <span aria-hidden className="absolute -right-1 -bottom-4 font-['Ma_Shan_Zheng','Noto_Serif_SC'] text-7xl text-white/10 group-hover:text-[#ffd76a]/25 transition-colors">{hanzi}</span>
                <span className="block text-base font-extrabold text-white">{label}</span>
                <span className="block mt-2 text-[11px] text-white/60">{stats ? `Kỷ lục ${stats.best_score.toLocaleString('vi-VN')}` : 'Chưa có kỷ lục'}</span>
                <span className="block text-[11px] text-white/40">{stats ? `${stats.plays} ván · chuỗi ${stats.best_combo}` : 'Khai kiếm ván đầu'}</span>
              </button>
            );
          })}
        </div>
      </section>

      <section data-tour="game-radicals" className="flex flex-col gap-3" aria-label="Bộ thủ hay quên">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3">
          <h2 className="text-sm font-bold text-white">Chế độ bộ thủ hay quên</h2>
          {radicalBest && <span className="text-[11px] text-white/50">Kỷ lục {radicalBest.best_score.toLocaleString('vi-VN')} · {radicalBest.plays} ván</span>}
        </div>
        {weak.loading && <p className="text-xs text-white/50" role="status">Đang tải bộ thủ gợi ý...</p>}
        {weak.error && !weak.data && (
          <p role="alert" className="text-xs text-[#ffb3c0]">
            {weak.error}{' '}
            <button type="button" onClick={weak.reload} className="font-bold underline">Thử lại</button>
          </p>
        )}
        {weak.data && (
          <>
            {weak.data.message && <p className="text-xs text-white/50">{weak.data.message}</p>}
            {weak.data.radicals.length === 0 ? (
              <p className="text-xs text-white/50">Chưa có bộ thủ nào để gợi ý. Hãy lưu thêm từ vào Sổ tay rồi quay lại nhé.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {weak.data.radicals.map(item => (
                  <button
                    key={item.radical}
                    type="button"
                    disabled={busy}
                    onClick={() => onStart({ mode: 'weak_radical', hsk_band: null, radical: item.radical })}
                    className="w-16 h-20 rounded-2xl border border-white/10 bg-white/5 hover:border-[#ffd76a]/70 flex flex-col items-center justify-center transition-colors disabled:opacity-50"
                  >
                    <span className="font-['Ma_Shan_Zheng','Noto_Serif_SC'] text-3xl text-[#ffd76a]">{item.radical}</span>
                    {!weak.data?.fallback && <span className="text-[10px] text-white/50 mt-0.5">Quên {item.count}</span>}
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </section>

      <section data-tour="game-options" className="flex flex-wrap items-center gap-2" aria-label="Tùy chọn">
        <Toggle label="Âm thanh" icon="volume_up" on={prefs.sound} onChange={sound => onPrefs({ ...prefs, sound })} />
        <Toggle label="Gợi ý pinyin" icon="lightbulb" on={prefs.hints} onChange={hints => onPrefs({ ...prefs, hints })} />
        <div className="flex rounded-full bg-white/5 border border-white/15 p-0.5" role="group" aria-label="Tốc độ rơi">
          {SPEEDS.map(speed => (
            <button
              key={speed}
              type="button"
              aria-pressed={prefs.speed === speed}
              onClick={() => onPrefs({ ...prefs, speed })}
              className={`px-3 py-1.5 rounded-full text-xs font-bold transition-colors ${prefs.speed === speed ? 'bg-[#ffd76a] text-[#2a0a24]' : 'text-white/60 hover:text-white'}`}
            >
              {SPEED_LABEL[speed]}
            </button>
          ))}
        </div>
      </section>

      <ol className="grid sm:grid-cols-3 gap-3">
        {STEPS.map(step => (
          <li key={step.icon} className="rounded-2xl bg-white/5 border border-white/10 p-3 flex gap-2.5 text-xs text-white/70">
            <span className="material-symbols-outlined text-[20px] text-[#ff9fc8]">{step.icon}</span>
            <span>{step.text}</span>
          </li>
        ))}
      </ol>
    </div>
  );
};
