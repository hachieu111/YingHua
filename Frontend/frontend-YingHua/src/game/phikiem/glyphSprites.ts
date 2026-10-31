// Dựng chữ thư pháp khối 3D lên canvas phụ rồi cache theo chữ: vẽ lại mỗi khung sẽ quá nặng.

export const BRUSH_FONT = '"Ma Shan Zheng", "Zhi Mang Xing", "Noto Serif SC", serif';
export const UI_FONT = '"Plus Jakarta Sans", "Inter", sans-serif';

const FONT_TIMEOUT_MS = 3500;
const MAX_DEPTH_LAYERS = 20;

export interface GlyphSprite {
  canvas: HTMLCanvasElement;
  aura: HTMLCanvasElement | null;
  /** Kích thước hiển thị theo px CSS. */
  width: number;
  height: number;
  /** Bề rộng thân chữ theo px CSS. */
  bodyWidth: number;
}

interface Palette {
  face: [string, string, string];
  sideFar: [number, number, number];
  sideNear: [number, number, number];
  outline: string;
  glow: string;
}

const PALETTES: Palette[] = [
  { face: ['#fff6cf', '#ffd76a', '#c9862a'], sideFar: [34, 10, 40], sideNear: [130, 40, 96], outline: '#2a0a24', glow: 'rgba(164, 48, 115, 0.85)' },
  { face: ['#eafff5', '#83e6c6', '#1f8f7a'], sideFar: [8, 26, 34], sideNear: [18, 94, 92], outline: '#06252a', glow: 'rgba(40, 180, 160, 0.75)' }
];
const BOSS_PALETTE: Palette = { face: ['#ffffff', '#ffd25a', '#ff5a2a'], sideFar: [48, 8, 4], sideNear: [176, 58, 20], outline: '#3a0a02', glow: 'rgba(255, 96, 32, 0.95)' };

const mix = (a: number, b: number, t: number): number => Math.round(a + (b - a) * t);

const makeCanvas = (width: number, height: number): HTMLCanvasElement => {
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, Math.ceil(width));
  canvas.height = Math.max(1, Math.ceil(height));
  return canvas;
};

/** Phông Google chia theo bảng mã nên phải yêu cầu đúng các chữ sắp vẽ; quá hạn thì dùng phông dự phòng. */
export const loadBrushFont = async (text: string): Promise<void> => {
  const fonts = document.fonts;
  if (!fonts) return;
  const unique = [...new Set(text)].join('');
  const load = Promise.allSettled([fonts.load('64px "Ma Shan Zheng"', unique), fonts.load('64px "Zhi Mang Xing"', unique)]);
  await Promise.race([load, new Promise(resolve => window.setTimeout(resolve, FONT_TIMEOUT_MS))]);
};

const paintFace = (canvas: HTMLCanvasElement, text: string, font: string, palette: Palette, cx: number, cy: number): void => {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  const top = cy - canvas.height * 0.26;
  const bottom = cy + canvas.height * 0.26;
  ctx.font = font;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  const gradient = ctx.createLinearGradient(0, top, 0, bottom);
  gradient.addColorStop(0, palette.face[0]);
  gradient.addColorStop(0.5, palette.face[1]);
  gradient.addColorStop(1, palette.face[2]);
  ctx.fillStyle = gradient;
  ctx.fillText(text, cx, cy);
  // Dải phản quang chéo chỉ phủ lên phần đã có chữ.
  ctx.globalCompositeOperation = 'source-atop';
  const sheen = ctx.createLinearGradient(0, top, canvas.width, bottom);
  sheen.addColorStop(0.32, 'rgba(255,255,255,0)');
  sheen.addColorStop(0.46, 'rgba(255,255,255,0.75)');
  sheen.addColorStop(0.6, 'rgba(255,255,255,0)');
  ctx.fillStyle = sheen;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.globalCompositeOperation = 'source-over';
};

const paintExtrusion = (ctx: CanvasRenderingContext2D, text: string, cx: number, cy: number, fontPx: number, palette: Palette): void => {
  const layers = Math.min(MAX_DEPTH_LAYERS, Math.ceil(fontPx * 0.16));
  ctx.shadowColor = 'rgba(0, 0, 0, 0.6)';
  ctx.shadowBlur = fontPx * 0.09;
  ctx.shadowOffsetX = fontPx * 0.05;
  ctx.shadowOffsetY = fontPx * 0.09;
  for (let i = layers; i >= 1; i -= 1) {
    const t = 1 - i / layers;
    ctx.fillStyle = `rgb(${mix(palette.sideFar[0], palette.sideNear[0], t)}, ${mix(palette.sideFar[1], palette.sideNear[1], t)}, ${mix(palette.sideFar[2], palette.sideNear[2], t)})`;
    // Thu nhỏ dần theo chiều sâu để có điểm tụ phối cảnh, không chỉ là bóng lệch.
    const scale = 1 - i * 0.0042;
    ctx.save();
    ctx.translate(cx + i * 0.55, cy + i * 0.8);
    ctx.scale(scale, scale);
    ctx.fillText(text, 0, 0);
    ctx.restore();
    if (i === layers) {
      ctx.shadowColor = 'transparent';
      ctx.shadowBlur = 0;
      ctx.shadowOffsetX = 0;
      ctx.shadowOffsetY = 0;
    }
  }
};

const buildAura = (text: string, font: string, width: number, height: number, fontPx: number): HTMLCanvasElement => {
  const canvas = makeCanvas(width, height);
  const ctx = canvas.getContext('2d');
  if (!ctx) return canvas;
  ctx.font = font;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = '#ff7a2a';
  ctx.shadowColor = '#ff5a1a';
  ctx.shadowBlur = fontPx * 0.5;
  // Vẽ lệch ra ngoài khung để chỉ giữ quầng sáng, không giữ thân chữ.
  ctx.shadowOffsetX = width * 2;
  for (let i = 0; i < 3; i += 1) ctx.fillText(text, width / 2 - width * 2, height / 2);
  return canvas;
};

const buildSprite = (text: string, cssSize: number, isBoss: boolean, tone: number, dpr: number): GlyphSprite => {
  const fontPx = Math.round(cssSize * dpr);
  const font = `${fontPx}px ${BRUSH_FONT}`;
  const palette = isBoss ? BOSS_PALETTE : PALETTES[tone % PALETTES.length];
  const probe = makeCanvas(1, 1).getContext('2d');
  if (probe) probe.font = font;
  const bodyPx = probe ? probe.measureText(text).width : fontPx * text.length;
  const pad = fontPx * 0.5;
  const width = bodyPx + pad * 2;
  const height = fontPx * 1.3 + pad * 2;
  const canvas = makeCanvas(width, height);
  const ctx = canvas.getContext('2d');
  const cx = canvas.width / 2 - fontPx * 0.05;
  const cy = canvas.height / 2 - fontPx * 0.06;
  if (ctx) {
    // Nghiêng phối cảnh nhẹ, như khối chữ ngả về phía sau.
    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.transform(1, 0, -0.08, 0.96, 0, 0);
    ctx.translate(-canvas.width / 2, -canvas.height / 2);
    ctx.font = font;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.lineJoin = 'round';
    paintExtrusion(ctx, text, cx, cy, fontPx, palette);
    ctx.shadowColor = palette.glow;
    ctx.shadowBlur = fontPx * 0.12;
    ctx.strokeStyle = palette.outline;
    ctx.lineWidth = Math.max(1.5, fontPx * 0.045);
    ctx.strokeText(text, cx, cy);
    ctx.shadowColor = 'transparent';
    ctx.shadowBlur = 0;
    const face = makeCanvas(canvas.width, canvas.height);
    paintFace(face, text, font, palette, cx, cy);
    ctx.drawImage(face, 0, 0);
  }
  return {
    canvas,
    aura: isBoss ? buildAura(text, font, canvas.width, canvas.height, fontPx) : null,
    width: canvas.width / dpr,
    height: canvas.height / dpr,
    bodyWidth: bodyPx / dpr
  };
};

export class GlyphSpriteCache {
  private sprites = new Map<string, GlyphSprite>();
  private dpr: number;

  constructor(dpr: number) {
    this.dpr = dpr;
  }

  get(text: string, size: number, isBoss: boolean, tone: number): GlyphSprite {
    const key = `${text}|${size}|${isBoss ? 1 : 0}|${tone}`;
    let sprite = this.sprites.get(key);
    if (!sprite) {
      sprite = buildSprite(text, size, isBoss, tone, this.dpr);
      this.sprites.set(key, sprite);
    }
    return sprite;
  }

  /** Đổi kích thước khung hoặc mật độ điểm ảnh thì bỏ cache cũ. */
  reset(dpr: number): void {
    this.dpr = dpr;
    this.sprites.clear();
  }
}
