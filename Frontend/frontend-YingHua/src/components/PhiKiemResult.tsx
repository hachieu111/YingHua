import React, { useEffect, useRef, useState } from 'react';
import type { BladeSession } from '../api/gamification';
import { speakChinese } from '../utils/speech';

const COUNT_MS = 900;

const RANK_NOTE: Record<BladeSession['rank'], string> = {
  S: 'Kiếm pháp thông thần!',
  A: 'Đường kiếm sắc bén!',
  B: 'Kiếm thế vững vàng.',
  C: 'Mài kiếm thêm nhé.'
};

const prefersReducedMotion = (): boolean => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Điểm chạy từ 0 lên đích, tắt khi người dùng không muốn chuyển động. */
const useCountUp = (target: number): number => {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (prefersReducedMotion()) {
      setValue(target);
      return;
    }
    let raf = 0;
    const started = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - started) / COUNT_MS);
      setValue(Math.round(target * (1 - (1 - t) ** 3)));
      if (t < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target]);
  return value;
};

const Stat: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="rounded-2xl bg-white/5 border border-white/10 p-3 text-center">
    <div className="text-lg font-extrabold text-white tabular-nums">{value}</div>
    <div className="text-[11px] text-white/55">{label}</div>
  </div>
);

interface ResultProps {
  result: BladeSession;
  onAgain: () => void;
  onChangeBand: () => void;
}

/** Màn kết quả: con dấu triện theo hạng, điểm đếm tăng, danh sách chữ bị rơi (F16.01). */
export const PhiKiemResult: React.FC<ResultProps> = ({ result, onAgain, onChangeBand }) => {
  const score = useCountUp(result.score);
  const sealRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (prefersReducedMotion()) return;
    const animation = sealRef.current?.animate(
      [
        { transform: 'scale(2.6) rotate(-16deg)', opacity: 0 },
        { transform: 'scale(0.92) rotate(-7deg)', opacity: 1, offset: 0.7 },
        { transform: 'scale(1) rotate(-7deg)', opacity: 1 }
      ],
      { duration: 420, easing: 'cubic-bezier(0.3, 0, 0.3, 1)', delay: 250, fill: 'backwards' }
    );
    return () => animation?.cancel();
  }, []);

  return (
    <div className="flex flex-col items-center gap-5">
      <div
        ref={sealRef}
        role="img"
        aria-label={`Hạng ${result.rank}`}
        className="w-28 h-28 sm:w-32 sm:h-32 rounded-2xl bg-[#b3202e] border-4 border-[#ffb3a0]/40 shadow-[0_0_0_4px_#b3202e,0_10px_30px_rgba(179,32,46,0.5)] flex items-center justify-center rotate-[-7deg]"
      >
        <span className="font-['Noto_Serif_SC'] text-7xl sm:text-8xl font-bold text-[#ffe9dc] leading-none">{result.rank}</span>
      </div>
      <div className="text-center">
        <p className="text-sm font-bold text-[#ffd8e7]">{RANK_NOTE[result.rank]}</p>
        <p className="text-5xl sm:text-6xl font-extrabold text-[#ffd76a] tabular-nums font-['Plus_Jakarta_Sans']">{score.toLocaleString('vi-VN')}</p>
        {result.is_best && (
          <p className="mt-1 inline-flex items-center gap-1 px-3 py-1 rounded-full bg-[#a43073] text-white text-xs font-bold">
            <span className="material-symbols-outlined text-[16px]">military_tech</span>
            Kỷ lục mới
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 w-full">
        <Stat label="Độ chính xác" value={`${(result.accuracy * 100).toLocaleString('vi-VN', { maximumFractionDigits: 1 })}%`} />
        <Stat label="Chuỗi lớn nhất" value={String(result.max_combo)} />
        <Stat label="Chém / rơi" value={`${result.correct} / ${result.wrong}`} />
        <Stat label="XP nhận được" value={`+${result.xp_awarded}`} />
      </div>
      {result.xp_awarded === 0 && <p className="text-[11px] text-white/50 text-center">Lần này không cộng XP (đã chạm trần XP mini-game trong ngày hoặc chưa có điểm).</p>}

      {result.missed.length > 0 && (
        <section className="w-full flex flex-col gap-2" aria-label="Chữ bị rơi">
          <h2 className="text-sm font-bold text-white">Chữ bị rơi, ôn lại nhé</h2>
          <ul className="grid sm:grid-cols-2 gap-2 max-h-56 overflow-y-auto pr-1">
            {result.missed.map((item, position) => (
              // Một ván có thể lặp chữ và danh sách không đổi thứ tự nên ghép thêm vị trí làm khóa.
              <li key={`${item.text}-${position}`} className="flex items-center gap-3 rounded-2xl bg-white/5 border border-white/10 px-3 py-2">
                <span className="font-['Ma_Shan_Zheng','Noto_Serif_SC'] text-2xl text-[#ffd76a]">{item.text}</span>
                <span className="flex-1 min-w-0 text-xs">
                  <span className="block font-bold text-white truncate">{item.pinyin}</span>
                  {item.han_viet && <span className="block text-white/55 truncate">{item.han_viet}</span>}
                </span>
                <button type="button" aria-label={`Đọc ${item.text}`} onClick={() => void speakChinese(item.text)} className="w-8 h-8 rounded-full bg-white/10 hover:bg-[#a43073] text-white flex items-center justify-center transition-colors">
                  <span className="material-symbols-outlined text-[18px]">volume_up</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="flex flex-wrap justify-center gap-3">
        <button type="button" onClick={onAgain} className="px-6 py-2.5 rounded-full bg-[#a43073] hover:bg-[#85145a] text-white text-sm font-bold transition-colors">
          Chơi lại
        </button>
        <button type="button" onClick={onChangeBand} className="px-6 py-2.5 rounded-full bg-white/10 hover:bg-white/20 text-white text-sm font-bold transition-colors">
          Đổi cấp độ
        </button>
      </div>
    </div>
  );
};
