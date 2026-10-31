import React from 'react';
import type { HudState } from '../game/phikiem/types';

const formatClock = (seconds: number): string => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;

const GLASS = 'bg-[#14081e]/60 backdrop-blur-sm border border-white/10 rounded-2xl';

const IconButton: React.FC<{ icon: string; label: string; onClick: () => void }> = ({ icon, label, onClick }) => (
  <button
    type="button"
    aria-label={label}
    title={label}
    onClick={onClick}
    className={`${GLASS} w-10 h-10 flex items-center justify-center text-white/90 hover:text-[#ffd76a] transition-colors`}
  >
    <span className="material-symbols-outlined text-[20px]">{icon}</span>
  </button>
);

interface HudProps {
  hud: HudState;
  soundOn: boolean;
  onToggleSound: () => void;
  onPause: () => void;
}

/** Chỉ số đặt trên canvas; chỉ vẽ lại khi engine báo giá trị đổi. */
export const PhiKiemHud: React.FC<HudProps> = React.memo(({ hud, soundOn, onToggleSound, onPause }) => (
  <div className="absolute inset-x-0 top-0 p-3 sm:p-4 flex items-start justify-between gap-3 pointer-events-none text-white">
    <div className="flex flex-col gap-2 min-w-0">
      <div className={`${GLASS} px-3 py-1.5 flex items-center gap-3`}>
        <span className="flex items-center" role="img" aria-label={`Còn ${hud.lives} mạng`}>
          {Array.from({ length: hud.maxLives }, (_, i) => (
            <span
              key={i}
              className={`material-symbols-outlined text-[20px] transition-all duration-300 ${i < hud.lives ? 'text-[#ff5c8a] scale-100' : 'text-white/20 scale-75'}`}
              style={{ fontVariationSettings: `'FILL' ${i < hud.lives ? 1 : 0}` }}
            >
              favorite
            </span>
          ))}
        </span>
        <span className="text-[11px] font-bold text-white/60">Đợt {hud.wave}</span>
      </div>
      <div className={`${GLASS} px-3 py-1 w-fit`}>
        <div className="text-[10px] font-semibold text-white/60 leading-tight">Điểm</div>
        <div className="text-xl font-extrabold leading-tight tabular-nums text-[#ffd76a]">{hud.score.toLocaleString('vi-VN')}</div>
      </div>
    </div>

    <div className="flex flex-col items-end gap-2">
      <div className="flex items-center gap-2 pointer-events-auto">
        <div className={`${GLASS} h-10 px-3 flex items-center gap-1 font-extrabold tabular-nums ${hud.secondsLeft <= 10 ? 'text-[#ff5c6c]' : ''}`}>
          <span className="material-symbols-outlined text-[18px]">timer</span>
          {formatClock(hud.secondsLeft)}
        </div>
        <IconButton icon={soundOn ? 'volume_up' : 'volume_off'} label={soundOn ? 'Tắt âm thanh' : 'Bật âm thanh'} onClick={onToggleSound} />
        <IconButton icon="pause" label="Tạm dừng" onClick={onPause} />
      </div>
      <div className={`${GLASS} px-3 py-1.5 w-[150px] sm:w-[190px]`}>
        <div className="flex justify-between text-[10px] font-bold">
          <span className={hud.ultimate ? 'text-[#ffd76a]' : 'text-white/70'}>{hud.ultimate ? 'Vạn Kiếm Quy Tông' : 'Kiếm Khí'}</span>
          <span className="text-white/60">×{hud.multiplier.toLocaleString('vi-VN')}</span>
        </div>
        <div className="mt-1 h-1.5 rounded-full bg-white/10 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#a43073] via-[#ff7ab0] to-[#ffd76a] transition-[width] duration-200"
            style={{ width: `${hud.energy}%` }}
          />
        </div>
      </div>
    </div>
  </div>
));
PhiKiemHud.displayName = 'PhiKiemHud';
