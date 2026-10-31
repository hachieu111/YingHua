// Vẽ chữ đang rơi, khung ngắm, ô pinyin, khung lửa boss và hai nửa chữ sau cú chém.
import { GlyphSpriteCache, UI_FONT } from './glyphSprites';
import type { Glyph, SlashFlash, Slice } from './types';

export interface GlyphViewContext {
  time: number;
  buffer: string;
  target: Glyph | null;
  hints: boolean;
  sprites: GlyphSpriteCache;
}

export const toneOf = (index: number): number => index % 2;

const FLAME_POINTS = 56;
const FLAME_STROKES = [
  { color: 'rgba(255, 92, 28, 0.75)', width: 5 },
  { color: 'rgba(255, 214, 110, 0.85)', width: 1.8 }
];

const roundedPill = (ctx: CanvasRenderingContext2D, x: number, y: number, width: number, height: number): void => {
  ctx.beginPath();
  ctx.roundRect(x, y, width, height, height / 2);
};

const drawFlameFrame = (ctx: CanvasRenderingContext2D, glyph: Glyph, time: number): void => {
  const halfW = glyph.halfW + 12;
  const halfH = glyph.halfH + 10;
  const perimeter = 4 * (halfW + halfH);
  const pointAt = (i: number): [number, number] => {
    let d = (i / FLAME_POINTS) * perimeter;
    let x: number;
    let y: number;
    if (d < 2 * halfW) [x, y] = [-halfW + d, -halfH];
    else if ((d -= 2 * halfW) < 2 * halfH) [x, y] = [halfW, -halfH + d];
    else if ((d -= 2 * halfH) < 2 * halfW) [x, y] = [halfW - d, halfH];
    else [x, y] = [-halfW, halfH - (d - 2 * halfW)];
    const lick = (Math.sin(i * 1.9 + time * 9) + Math.sin(i * 0.7 - time * 6)) * 3.2;
    const length = Math.hypot(x, y) || 1;
    return [x + (x / length) * lick, y + (y / length) * lick - Math.abs(lick) * 0.6];
  };
  ctx.globalCompositeOperation = 'lighter';
  FLAME_STROKES.forEach(({ color, width }) => {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.beginPath();
    for (let i = 0; i <= FLAME_POINTS; i += 1) {
      const [x, y] = pointAt(i % FLAME_POINTS);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  });
  ctx.globalCompositeOperation = 'source-over';
};

const drawReticle = (ctx: CanvasRenderingContext2D, glyph: Glyph, time: number): void => {
  const inset = Math.sin(time * 8) * 2.5;
  const halfW = glyph.halfW + 12 + inset;
  const halfH = glyph.halfH + 8 + inset;
  const arm = Math.min(halfW, halfH) * 0.42;
  ctx.strokeStyle = '#ffd76a';
  ctx.lineWidth = 2.4;
  ctx.lineCap = 'round';
  [[-1, -1], [1, -1], [1, 1], [-1, 1]].forEach(([sx, sy]) => {
    ctx.beginPath();
    ctx.moveTo(sx * halfW, sy * (halfH - arm));
    ctx.lineTo(sx * halfW, sy * halfH);
    ctx.lineTo(sx * (halfW - arm), sy * halfH);
    ctx.stroke();
  });
};

const drawPill = (ctx: CanvasRenderingContext2D, glyph: Glyph, view: GlyphViewContext): void => {
  const isTarget = view.target === glyph;
  if (glyph.doomed || (!isTarget && !view.hints)) return;
  const typed = isTarget ? view.buffer : '';
  const answer = glyph.answers.find(item => item.startsWith(typed)) ?? typed;
  const rest = isTarget && view.hints ? answer.slice(typed.length) : '';
  const label = isTarget ? '' : glyph.item.pinyin;

  ctx.font = `700 ${isTarget ? 16 : 13}px ${UI_FONT}`;
  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  const typedWidth = ctx.measureText(typed).width;
  const restWidth = ctx.measureText(rest).width;
  const labelWidth = ctx.measureText(label).width;
  const width = Math.max(30, typedWidth + restWidth + labelWidth + 22);
  const height = isTarget ? 28 : 22;
  const shakeX = Math.sin(view.time * 62) * glyph.shake * 7;
  const x = glyph.x - width / 2 + shakeX;
  const y = glyph.y + glyph.halfH + 7;

  roundedPill(ctx, x, y, width, height);
  ctx.fillStyle = glyph.shake > 0.05 ? 'rgba(120, 12, 36, 0.92)' : 'rgba(20, 8, 30, 0.8)';
  ctx.fill();
  ctx.lineWidth = isTarget ? 1.6 : 1;
  ctx.strokeStyle = glyph.shake > 0.05 ? '#ff5c6c' : isTarget ? '#ffd76a' : 'rgba(255, 255, 255, 0.2)';
  ctx.stroke();

  const baseline = y + height / 2 + 1;
  const textX = x + 11;
  if (label) {
    ctx.fillStyle = 'rgba(255, 236, 246, 0.85)';
    ctx.fillText(label, textX, baseline);
  }
  if (typed) {
    ctx.fillStyle = '#ffd76a';
    ctx.fillText(typed, textX, baseline - glyph.pulse * 5);
  }
  if (rest) {
    ctx.fillStyle = 'rgba(255, 255, 255, 0.34)';
    ctx.fillText(rest, textX + typedWidth, baseline);
  } else if (isTarget && Math.sin(view.time * 9) > 0) {
    ctx.fillStyle = '#ffd76a';
    ctx.fillRect(textX + typedWidth + 2, y + 7, 2, height - 14);
  }
  if (isTarget && view.hints) {
    ctx.font = `600 12px ${UI_FONT}`;
    ctx.textAlign = 'center';
    ctx.fillStyle = 'rgba(255, 236, 246, 0.8)';
    ctx.fillText(glyph.item.pinyin, glyph.x, y + height + 10);
  }
};

export const drawGlyph = (ctx: CanvasRenderingContext2D, glyph: Glyph, view: GlyphViewContext): void => {
  const sprite = view.sprites.get(glyph.item.text, glyph.size, glyph.item.is_boss, toneOf(glyph.item.index));
  const sway = Math.sin(view.time * 1.5 + glyph.swayPhase);
  const scale = 1 + glyph.pulse * 0.1;
  ctx.save();
  ctx.translate(glyph.x + sway * 5, glyph.y);
  ctx.rotate(sway * 0.05);
  if (sprite.aura) {
    const flicker = 1.06 + Math.sin(view.time * 13 + glyph.swayPhase) * 0.04;
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = 0.72 + Math.sin(view.time * 7) * 0.2;
    ctx.drawImage(sprite.aura, (-sprite.width * flicker) / 2, (-sprite.height * flicker) / 2, sprite.width * flicker, sprite.height * flicker);
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
    drawFlameFrame(ctx, glyph, view.time);
  }
  if (view.target === glyph) drawReticle(ctx, glyph, view.time);
  ctx.scale(scale, scale);
  ctx.globalAlpha = glyph.doomed ? 0.86 : 1;
  ctx.drawImage(sprite.canvas, -sprite.width / 2, -sprite.height / 2, sprite.width, sprite.height);
  ctx.restore();
  drawPill(ctx, glyph, view);
};

export const drawSlice = (ctx: CanvasRenderingContext2D, slice: Slice, sprites: GlyphSpriteCache): void => {
  const sprite = sprites.get(slice.text, slice.size, slice.isBoss, slice.tone);
  const reach = Math.max(sprite.width, sprite.height);
  ctx.save();
  ctx.globalAlpha = Math.min(1, (slice.life / slice.maxLife) * 1.7);
  ctx.translate(slice.x, slice.y);
  ctx.rotate(slice.rotation);
  ctx.save();
  ctx.rotate(slice.cutAngle);
  ctx.beginPath();
  ctx.rect(-reach, slice.side > 0 ? 0 : -reach, reach * 2, reach);
  ctx.restore();
  ctx.clip();
  ctx.drawImage(sprite.canvas, -sprite.width / 2, -sprite.height / 2, sprite.width, sprite.height);
  ctx.restore();
};

export const drawSlash = (ctx: CanvasRenderingContext2D, flash: SlashFlash): void => {
  const t = flash.life / flash.maxLife;
  const half = (flash.length * (1.25 - t * 0.6)) / 2;
  ctx.save();
  ctx.translate(flash.x, flash.y);
  ctx.rotate(flash.angle);
  ctx.globalCompositeOperation = 'lighter';
  ctx.globalAlpha = t;
  const beam = ctx.createLinearGradient(-half, 0, half, 0);
  beam.addColorStop(0, 'rgba(255, 255, 255, 0)');
  beam.addColorStop(0.5, 'rgba(255, 255, 255, 1)');
  beam.addColorStop(1, 'rgba(255, 255, 255, 0)');
  ctx.fillStyle = beam;
  ctx.beginPath();
  ctx.moveTo(-half, 0);
  ctx.quadraticCurveTo(0, -7 * t, half, 0);
  ctx.quadraticCurveTo(0, 7 * t, -half, 0);
  ctx.fill();
  ctx.restore();
};
