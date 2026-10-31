// Nhớ tùy chọn người chơi; localStorage có thể bị chặn nên luôn bọc try/catch.
import type { GamePrefs, SpeedOption } from './types';

const STORAGE_KEY = 'yinghua:phikiem:prefs';
const SPEEDS: SpeedOption[] = ['calm', 'standard', 'storm'];

export const DEFAULT_PREFS: GamePrefs = { sound: true, hints: true, speed: 'standard' };

export const loadPrefs = (): GamePrefs => {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PREFS;
    const parsed = JSON.parse(raw) as Partial<GamePrefs> | null;
    return {
      sound: typeof parsed?.sound === 'boolean' ? parsed.sound : DEFAULT_PREFS.sound,
      hints: typeof parsed?.hints === 'boolean' ? parsed.hints : DEFAULT_PREFS.hints,
      speed: parsed?.speed && SPEEDS.includes(parsed.speed) ? parsed.speed : DEFAULT_PREFS.speed
    };
  } catch {
    return DEFAULT_PREFS;
  }
};

export const savePrefs = (prefs: GamePrefs): void => {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // Không ghi được (chế độ riêng tư, hết hạn mức) thì tùy chọn chỉ có tác dụng trong phiên này.
  }
};
