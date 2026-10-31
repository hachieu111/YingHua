// Tạo chữ mới và chọn vị trí rơi.
import type { BladeItem } from '../../api/gamification';
import { normalizeAnswer } from './rules';
import type { Glyph } from './types';

const SECONDS_PER_LETTER = 0.22;
const BOSS_SPEED_FACTOR = 0.8;
const LANE_TRIES = 7;

interface Field {
  w: number;
  h: number;
  groundY: number;
  unit: number;
}

export const createGlyph = (item: BladeItem, field: Field, fallSeconds: number, speedFactor: number): Glyph => {
  const answers = item.answers.map(normalizeAnswer).filter(Boolean);
  const longest = answers.reduce((max, answer) => Math.max(max, answer.length), 0);
  // Từ dài cần nhiều phím hơn nên được rơi lâu hơn một chút.
  const seconds = fallSeconds + longest * SECONDS_PER_LETTER;
  return {
    item,
    answers,
    x: 0,
    y: 0,
    speed: ((field.groundY + field.unit) / seconds) * speedFactor * (item.is_boss ? BOSS_SPEED_FACTOR : 1),
    size: field.unit,
    halfW: 0,
    halfH: 0,
    swayPhase: Math.random() * Math.PI * 2,
    doomed: false,
    points: 0,
    pulse: 0,
    shake: 0
  };
};

/** Thử vài vị trí, lấy chỗ xa các chữ trên cao nhất để chữ không chồng lên nhau. */
export const pickLane = (glyphs: Glyph[], field: Field, margin: number): number => {
  const low = margin;
  const high = Math.max(low + 1, field.w - margin);
  const near = glyphs.filter(glyph => glyph.y < field.h * 0.4);
  let bestX = low;
  let bestGap = -1;
  for (let i = 0; i < LANE_TRIES; i += 1) {
    const x = low + Math.random() * (high - low);
    const gap = near.reduce((min, glyph) => Math.min(min, Math.abs(glyph.x - x)), field.w);
    if (gap > bestGap) {
      bestX = x;
      bestGap = gap;
    }
  }
  return bestX;
};
