// Ghép một khung hình từ trạng thái engine, và vẽ phần chữ nổi trên canvas (combo, thông báo, đếm ngược).
import { type PhiKiemEngine, comboAnchorY } from './engine';
import { BRUSH_FONT, UI_FONT } from './glyphSprites';
import { drawGlyph, drawSlash, drawSlice } from './glyphView';
import { comboMultiplier } from './rules';
import type { Banner } from './types';

const SWORD_LENGTH_FACTOR = 1.25;

const drawLaser = (ctx: CanvasRenderingContext2D, engine: PhiKiemEngine): void => {
  const target = engine.target;
  if (!target) return;
  const hand = engine.hero.hand();
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  ctx.setLineDash([9, 7]);
  ctx.lineDashOffset = -engine.time * 90;
  ctx.strokeStyle = 'rgba(255, 215, 130, 0.65)';
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(hand.x, hand.y);
  ctx.lineTo(target.x, target.y + target.halfH);
  ctx.stroke();
  ctx.restore();
};

const drawCombo = (ctx: CanvasRenderingContext2D, engine: PhiKiemEngine): void => {
  if (engine.combo < 2) return;
  const cx = engine.w / 2;
  const cy = comboAnchorY(engine.h);
  const size = Math.min(78, 44 + engine.combo * 0.9);
  const scale = 1 + engine.comboBump * 0.38;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.scale(scale, scale);
  ctx.rotate(Math.sin(engine.comboBump * 8) * engine.comboBump * 0.07);
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineJoin = 'round';
  ctx.font = `800 ${size}px ${UI_FONT}`;
  const fill = ctx.createLinearGradient(0, -size / 2, 0, size / 2);
  fill.addColorStop(0, '#fffbe6');
  fill.addColorStop(0.55, '#ffd76a');
  fill.addColorStop(1, '#ff7a4a');
  ctx.lineWidth = 8;
  ctx.strokeStyle = 'rgba(40, 8, 40, 0.85)';
  ctx.strokeText(String(engine.combo), 0, 0);
  ctx.fillStyle = fill;
  ctx.fillText(String(engine.combo), 0, 0);
  ctx.font = `700 13px ${UI_FONT}`;
  ctx.lineWidth = 3.5;
  const label = `Liên trảm  ×${comboMultiplier(engine.combo).toLocaleString('vi-VN')}`;
  ctx.strokeText(label, 0, size * 0.66);
  ctx.fillStyle = '#ffe3f0';
  ctx.fillText(label, 0, size * 0.66);
  ctx.restore();
};

const drawBanner = (ctx: CanvasRenderingContext2D, banner: Banner, w: number, h: number, slot: number): void => {
  const age = 1 - banner.life / banner.maxLife;
  const pop = age < 0.14 ? 1.7 - (age / 0.14) * 0.7 : 1 + (age - 0.14) * 0.08;
  const size = Math.min(84, w / 7);
  ctx.save();
  ctx.translate(w / 2, h * 0.36 + slot * size * 1.5);
  ctx.scale(pop, pop);
  ctx.globalAlpha = Math.min(1, (banner.life / banner.maxLife) * 3.2);
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineJoin = 'round';
  ctx.font = `${size}px ${BRUSH_FONT}`;
  ctx.lineWidth = 9;
  ctx.strokeStyle = 'rgba(30, 6, 30, 0.82)';
  ctx.strokeText(banner.subtitle, 0, 0);
  ctx.fillStyle = banner.color;
  ctx.fillText(banner.subtitle, 0, 0);
  ctx.font = `800 ${Math.max(17, size * 0.32)}px ${UI_FONT}`;
  ctx.lineWidth = 5;
  ctx.strokeText(banner.title, 0, size * 0.74);
  ctx.fillStyle = '#ffffff';
  ctx.fillText(banner.title, 0, size * 0.74);
  ctx.restore();
};

const drawIntro = (ctx: CanvasRenderingContext2D, engine: PhiKiemEngine): void => {
  const step = engine.introLeft / 0.6;
  const index = Math.ceil(step);
  const local = 1 - (step - Math.floor(step));
  const text = index > 1 ? String(index - 1) : '开剑';
  const size = Math.min(150, engine.w / 4) * (1.35 - Math.min(1, local * 3) * 0.35);
  ctx.save();
  ctx.globalAlpha = Math.min(1, (1 - local) * 5);
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineJoin = 'round';
  ctx.font = `${size}px ${BRUSH_FONT}`;
  ctx.lineWidth = 10;
  ctx.strokeStyle = 'rgba(30, 6, 30, 0.85)';
  ctx.strokeText(text, engine.w / 2, engine.h * 0.42);
  ctx.fillStyle = '#ffd76a';
  ctx.fillText(text, engine.w / 2, engine.h * 0.42);
  ctx.restore();
};

const drawVignettes = (ctx: CanvasRenderingContext2D, engine: PhiKiemEngine): void => {
  if (engine.redFlash > 0) {
    ctx.fillStyle = `rgba(190, 16, 40, ${engine.redFlash * 0.42})`;
    ctx.fillRect(0, 0, engine.w, engine.h);
  }
  if (engine.typoFlash > 0) {
    ctx.strokeStyle = `rgba(255, 70, 90, ${engine.typoFlash * 0.75})`;
    ctx.lineWidth = 10;
    ctx.strokeRect(0, 0, engine.w, engine.h);
  }
};

export const renderFrame = (ctx: CanvasRenderingContext2D, engine: PhiKiemEngine): void => {
  const view = { time: engine.time, buffer: engine.buffer, target: engine.target, hints: engine.hints, sprites: engine.sprites };
  ctx.save();
  if (engine.shake > 0) {
    ctx.translate((Math.random() - 0.5) * engine.shake, (Math.random() - 0.5) * engine.shake);
  }
  engine.backdrop.drawScene(ctx);
  engine.swords.drawRain(ctx);
  engine.backdrop.drawGround(ctx);
  drawLaser(ctx, engine);
  engine.hero.draw(ctx);
  for (const glyph of engine.glyphs) drawGlyph(ctx, glyph, view);
  for (const slice of engine.slices) drawSlice(ctx, slice, engine.sprites);
  for (const flash of engine.flashes) drawSlash(ctx, flash);
  engine.swords.draw(ctx, engine.unit * SWORD_LENGTH_FACTOR);
  engine.particles.draw(ctx);
  engine.particles.drawFloaters(ctx);
  ctx.restore();
  drawVignettes(ctx, engine);
  drawCombo(ctx, engine);
  engine.banners.forEach((banner, i) => drawBanner(ctx, banner, engine.w, engine.h, i));
  if (engine.phase === 'intro') drawIntro(ctx, engine);
};
