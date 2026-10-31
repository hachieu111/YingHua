import React from 'react';

const ROWS = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm'];

interface KeyboardProps {
  onKey: (key: string) => void;
  onBackspace: () => void;
}

const KEY_CLASS =
  'flex-1 max-w-[42px] h-11 rounded-lg bg-white/10 active:bg-[#a43073] text-white text-base font-bold uppercase flex items-center justify-center transition-colors';

/** Bàn phím ảo cho điện thoại: nút DOM thay cho ô nhập nên không bật bàn phím hệ thống. */
export const PhiKiemKeyboard: React.FC<KeyboardProps> = React.memo(({ onKey, onBackspace }) => {
  // Bắt pointerdown thay cho click để không trễ và không mất phím khi gõ nhanh.
  const press = (event: React.PointerEvent, action: () => void) => {
    event.preventDefault();
    action();
  };
  return (
    <div className="shrink-0 bg-[#100616] border-t border-white/10 px-1 pt-1.5 pb-[max(0.5rem,env(safe-area-inset-bottom))] flex flex-col gap-1.5 touch-none select-none">
      {ROWS.map((row, rowIndex) => (
        <div key={row} className="flex justify-center gap-1">
          {[...row].map(key => (
            <button key={key} type="button" tabIndex={-1} aria-label={key} className={KEY_CLASS} onPointerDown={event => press(event, () => onKey(key))}>
              {key}
            </button>
          ))}
          {rowIndex === ROWS.length - 1 && (
            <button type="button" tabIndex={-1} aria-label="Xóa" className={`${KEY_CLASS} max-w-[58px]`} onPointerDown={event => press(event, onBackspace)}>
              <span className="material-symbols-outlined text-[20px]">backspace</span>
            </button>
          )}
        </div>
      ))}
    </div>
  );
});
PhiKiemKeyboard.displayName = 'PhiKiemKeyboard';
