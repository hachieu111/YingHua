// Luật hiển thị trên màn: phải giống máy chủ (máy chủ mới là nơi chấm thật). Hằng số độ khó gom ở đây.
import type { Glyph, SpeedOption } from './types';

const BASE_POINTS = 10;
const BOSS_FACTOR = 3;
const COMBO_STEP = 5;
const COMBO_RATE = 0.5;
const MAX_MULTIPLIER = 3;
const WAVE_SIZE = 7;

/** Máy chủ loại ván có hai lần chém sát nhau hơn mức này trên mỗi phím (giống `MIN_KEY_MS` ở blade_rules). */
export const MIN_KEY_MS = 35;
/** Thưởng mỗi mạng còn lại khi chém hết bộ chữ. */
export const LIFE_BONUS = 5;

export const ULTIMATE_COMBO = 20;
export const ULTIMATE_SECONDS = 3;
export const ULTIMATE_FALL_FACTOR = 0.4;
export const DOOMED_FALL_FACTOR = 0.2;

export const SPEED_FACTOR: Record<SpeedOption, number> = { calm: 0.72, standard: 1, storm: 1.4 };

export const SPEED_LABEL: Record<SpeedOption, string> = { calm: 'Thong dong', standard: 'Tiêu chuẩn', storm: 'Cuồng phong' };

export interface Milestone {
  title: string;
  hanzi: string;
  color: string;
}

export const COMBO_MILESTONES: Record<number, Milestone> = {
  5: { title: 'Song Trảm', hanzi: '双斩', color: '#ffd86b' },
  10: { title: 'Tam Liên', hanzi: '三连', color: '#ffb35c' },
  20: { title: 'Kiếm Vũ', hanzi: '剑舞', color: '#ff8a5c' },
  30: { title: 'Vô Song', hanzi: '无双', color: '#ff5c8a' },
  50: { title: 'Kiếm Thánh', hanzi: '剑圣', color: '#fff3c4' }
};

export const comboMultiplier = (combo: number): number =>
  Math.min(MAX_MULTIPLIER, 1 + COMBO_RATE * Math.floor(combo / COMBO_STEP));

export const pointsFor = (isBoss: boolean, combo: number): number =>
  Math.round(BASE_POINTS * (isBoss ? BOSS_FACTOR : 1) * comboMultiplier(combo));

export const waveOf = (spawned: number): number => Math.floor(spawned / WAVE_SIZE) + 1;

export interface WaveTuning {
  maxActive: number;
  spawnGap: number;
  fallSeconds: number;
}

export const waveTuning = (wave: number): WaveTuning => ({
  maxActive: Math.min(7, wave + 1),
  spawnGap: Math.max(0.75, 2.3 - 0.24 * (wave - 1)),
  fallSeconds: Math.max(5.5, 12.5 - 0.9 * (wave - 1))
});

/** Bậc màu nền theo combo: 0 (thường) tới 4 (rực vàng). */
export const comboTier = (combo: number): number => {
  if (combo >= 30) return 4;
  if (combo >= 20) return 3;
  if (combo >= 10) return 2;
  return combo >= 5 ? 1 : 0;
};

/** Đưa cách gõ về a-z, `ü` thành `u`. */
export const normalizeAnswer = (answer: string): string =>
  answer
    .toLowerCase()
    .replace(/ü|u:/g, 'u')
    .replace(/[^a-z]/g, '');

export const matchesPrefix = (glyph: Glyph, prefix: string): boolean => glyph.answers.some(answer => answer.startsWith(prefix));

/** Chữ thấp nhất khớp tiền tố đã gõ; chữ đang chờ kiếm không tính. */
export const findTarget = (glyphs: Glyph[], prefix: string): Glyph | null => {
  let best: Glyph | null = null;
  for (const glyph of glyphs) {
    if (glyph.doomed || !matchesPrefix(glyph, prefix)) continue;
    if (!best || glyph.y > best.y) best = glyph;
  }
  return best;
};
