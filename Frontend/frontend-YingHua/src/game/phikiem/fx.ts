// Gói hiệu ứng cho từng sự kiện: gõ phím, chém đứt đôi, chữ chạm đáy.
import { UI_FONT } from './glyphSprites';
import { toneOf } from './glyphView';
import type { Particles } from './particles';
import type { Glyph, SlashFlash, Slice } from './types';

const SLICE_SECONDS = 0.95;
const SLASH_SECONDS = 0.24;
const SLICE_GRAVITY = 900;

/** Giảm tuổi thọ và bỏ các phần tử đã hết. */
export const expire = <T extends { life: number }>(items: T[], dt: number): T[] => {
  for (const item of items) item.life -= dt;
  return items.filter(item => item.life > 0);
};

export const moveSlices = (slices: Slice[], dt: number): void => {
  for (const slice of slices) {
    slice.vy += SLICE_GRAVITY * dt;
    slice.x += slice.vx * dt;
    slice.y += slice.vy * dt;
    slice.rotation += slice.spin * dt;
  }
};

export const keystrokeFx = (particles: Particles, glyph: Glyph): void => {
  particles.sparks(glyph.x, glyph.y, 7, '#ffd76a', 170);
  particles.ring(glyph.x, glyph.y, glyph.size * 0.85, '#ffd8e7');
  particles.ink(glyph.x, glyph.y + glyph.halfH, 3, 90);
};

/** Đường chém chéo: hai nửa văng theo pháp tuyến của đường chém, kèm vệt sáng và mực. */
export const cutFx = (particles: Particles, glyph: Glyph): { slices: Slice[]; flash: SlashFlash } => {
  const { item, x, y, size } = glyph;
  const angle = (Math.random() < 0.5 ? -1 : 1) * (0.5 + Math.random() * 0.55);
  const normalX = -Math.sin(angle);
  const normalY = Math.cos(angle);
  const slices = [1, -1].map(
    (side): Slice => ({
      text: item.text,
      size,
      isBoss: item.is_boss,
      tone: toneOf(item.index),
      x,
      y,
      vx: (normalX * 150 + Math.cos(angle) * 40) * side,
      vy: normalY * side * 150 - 230,
      rotation: 0,
      spin: side * (1.6 + Math.random() * 2.2),
      life: SLICE_SECONDS,
      maxLife: SLICE_SECONDS,
      cutAngle: angle,
      side
    })
  );
  particles.ink(x, y, item.is_boss ? 30 : 16);
  particles.sparks(x, y, item.is_boss ? 34 : 16, '#fff0c4', 340);
  particles.ring(x, y, size * 1.6, '#ffffff');
  const reading = item.han_viet ? `${item.pinyin} · ${item.han_viet}` : item.pinyin;
  particles.floatText(reading, x, y - size * 0.9, `600 15px ${UI_FONT}`, '#ffe3f0', 1.25);
  particles.floatText(`+${glyph.points}`, x, y - size * 0.4, `800 24px ${UI_FONT}`, '#ffd76a', 1);
  return { slices, flash: { x, y, angle, length: Math.max(glyph.halfW * 2, size) * 2.4, life: SLASH_SECONDS, maxLife: SLASH_SECONDS } };
};

export const missFx = (particles: Particles, glyph: Glyph, groundY: number): void => {
  particles.ink(glyph.x, groundY, 22, 320);
  particles.sparks(glyph.x, groundY, 14, '#ff5c6c', 300);
  particles.floatText(glyph.item.pinyin, glyph.x, groundY - 40, `700 16px ${UI_FONT}`, '#ff9aa8', 1.3);
};

export const comboBreakFx = (particles: Particles, x: number, y: number): void => {
  particles.shards(x, y, 26, '#ffd76a');
  particles.floatText('Đứt chuỗi', x, y, `700 22px ${UI_FONT}`, '#ff9aa8', 1);
};
