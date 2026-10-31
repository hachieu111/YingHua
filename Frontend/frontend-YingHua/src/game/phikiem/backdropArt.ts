// Các nét vẽ tĩnh của nền: dãy núi, thông, mặt đất, trăng, sương, cánh hoa.

type Rgb = readonly [number, number, number];

const TIER_PALETTES: readonly (readonly [Rgb, Rgb, Rgb])[] = [
  [[18, 9, 30], [54, 20, 68], [122, 42, 99]],
  [[24, 10, 36], [74, 20, 80], [164, 48, 115]],
  [[30, 10, 26], [94, 18, 56], [201, 52, 79]],
  [[28, 10, 16], [110, 26, 26], [217, 98, 43]],
  [[20, 10, 6], [96, 44, 12], [232, 169, 58]]
];

export const comboTierPalette = (tier: number): readonly [Rgb, Rgb, Rgb] => TIER_PALETTES[Math.max(0, Math.min(4, tier))];

const makeCanvas = (width: number, height: number): HTMLCanvasElement => {
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, width);
  canvas.height = Math.max(1, height);
  return canvas;
};

/** Độ cao đỉnh núi: tổng các sóng có chu kỳ nguyên lần bề rộng để lớp núi nối liền khi lặp. */
const ridgeHeight = (x: number, width: number, seed: number): number => {
  const p = (x / width) * Math.PI * 2;
  const broad = Math.sin(p * 2 + seed) * 0.34 + Math.sin(p * 3 + seed * 1.7) * 0.26;
  const crag = Math.abs(Math.sin(p * 7 + seed * 2.3)) * 0.22 + Math.abs(Math.sin(p * 17 + seed)) * 0.08;
  return 0.5 + broad + crag - 0.15;
};

const drawPine = (ctx: CanvasRenderingContext2D, x: number, y: number, size: number): void => {
  ctx.strokeStyle = '#0d0512';
  ctx.lineWidth = size * 0.07;
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.quadraticCurveTo(x - size * 0.1, y - size * 0.5, x + size * 0.04, y - size);
  ctx.stroke();
  ctx.fillStyle = '#0d0512';
  [0.45, 0.68, 0.9].forEach((level, i) => {
    const spread = size * (0.46 - i * 0.1);
    const py = y - size * level;
    ctx.beginPath();
    ctx.ellipse(x + (i % 2 ? spread * 0.25 : -spread * 0.2), py, spread, size * 0.1, -0.08, 0, Math.PI * 2);
    ctx.fill();
  });
};

export const paintRidge = (
  width: number,
  height: number,
  color: readonly number[],
  seed: number,
  alpha: number,
  withPines: boolean
): HTMLCanvasElement => {
  const canvas = makeCanvas(width, height);
  const ctx = canvas.getContext('2d');
  if (!ctx) return canvas;
  const [r, g, b] = color;
  const wash = ctx.createLinearGradient(0, 0, 0, height);
  wash.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${alpha})`);
  wash.addColorStop(0.65, `rgba(${r}, ${g}, ${b}, ${alpha * 0.82})`);
  wash.addColorStop(1, `rgba(${r}, ${g}, ${b}, ${alpha * 0.22})`);
  ctx.fillStyle = wash;
  ctx.beginPath();
  ctx.moveTo(0, height);
  for (let x = 0; x <= width; x += 6) ctx.lineTo(x, height * (1 - ridgeHeight(x, width, seed) * 0.9));
  ctx.lineTo(width, height);
  ctx.closePath();
  ctx.fill();

  // Vệt mực loang dọc sườn núi, chỉ phủ lên phần đã có núi.
  ctx.globalCompositeOperation = 'source-atop';
  ctx.fillStyle = `rgba(${Math.min(255, r + 70)}, ${Math.min(255, g + 40)}, ${Math.min(255, b + 70)}, 0.1)`;
  for (let x = 0; x < width; x += 26) {
    const top = height * (1 - ridgeHeight(x, width, seed) * 0.9);
    ctx.beginPath();
    ctx.ellipse(x, top + height * 0.13, 9, height * 0.15, 0.25, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalCompositeOperation = 'source-over';

  if (withPines) {
    for (let x = 60; x < width - 40; x += 170 + (x % 90)) {
      drawPine(ctx, x, height * (1 - ridgeHeight(x, width, seed) * 0.9) + 8, 42 + (x % 34));
    }
  }
  return canvas;
};

export const paintGround = (width: number, height: number): HTMLCanvasElement => {
  const canvas = makeCanvas(width, height);
  const ctx = canvas.getContext('2d');
  if (!ctx) return canvas;
  const soil = ctx.createLinearGradient(0, 0, 0, height);
  soil.addColorStop(0, '#2a1036');
  soil.addColorStop(0.2, '#190a22');
  soil.addColorStop(1, '#0a040e');
  ctx.fillStyle = soil;
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = 'rgba(255, 170, 214, 0.4)';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(0, 1);
  ctx.lineTo(width, 1);
  ctx.stroke();
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
  ctx.lineWidth = 2;
  for (let x = 0; x < width; x += 62) {
    const y = 10 + (x % 5) * (height / 7);
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + 34, y + 1);
    ctx.stroke();
  }
  return canvas;
};

export const makeMoon = (): HTMLCanvasElement => {
  const size = 420;
  const canvas = makeCanvas(size, size);
  const ctx = canvas.getContext('2d');
  if (!ctx) return canvas;
  const c = size / 2;
  const halo = ctx.createRadialGradient(c, c, size * 0.15, c, c, c);
  halo.addColorStop(0, 'rgba(255, 226, 238, 0.36)');
  halo.addColorStop(1, 'rgba(255, 200, 226, 0)');
  ctx.fillStyle = halo;
  ctx.fillRect(0, 0, size, size);
  const disc = ctx.createRadialGradient(c - 22, c - 26, 8, c, c, size * 0.2);
  disc.addColorStop(0, '#fff7ef');
  disc.addColorStop(0.8, '#ffdfe8');
  disc.addColorStop(1, '#f5bcd2');
  ctx.fillStyle = disc;
  ctx.beginPath();
  ctx.arc(c, c, size * 0.19, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = 'rgba(214, 150, 184, 0.28)';
  [[-22, -8, 18], [30, 18, 13], [-4, 34, 10], [18, -32, 8]].forEach(([dx, dy, r]) => {
    ctx.beginPath();
    ctx.arc(c + dx, c + dy, r, 0, Math.PI * 2);
    ctx.fill();
  });
  return canvas;
};

export const makeMist = (): HTMLCanvasElement => {
  const width = 460;
  const height = 150;
  const canvas = makeCanvas(width, height);
  const ctx = canvas.getContext('2d');
  if (!ctx) return canvas;
  for (let i = 0; i < 7; i += 1) {
    const x = width * (0.18 + i * 0.11);
    const y = height * (0.42 + (i % 3) * 0.08);
    const r = 64 + (i % 3) * 16;
    const puff = ctx.createRadialGradient(x, y, 0, x, y, r);
    puff.addColorStop(0, 'rgba(244, 224, 240, 0.55)');
    puff.addColorStop(1, 'rgba(244, 224, 240, 0)');
    ctx.fillStyle = puff;
    ctx.fillRect(0, 0, width, height);
  }
  return canvas;
};

export const drawPetal = (ctx: CanvasRenderingContext2D, x: number, y: number, size: number, rotation: number, flip: number): void => {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rotation);
  ctx.scale(1, Math.abs(Math.cos(flip)) * 0.8 + 0.2);
  ctx.fillStyle = 'rgba(255, 183, 213, 0.75)';
  ctx.beginPath();
  ctx.moveTo(0, -size);
  ctx.quadraticCurveTo(size, -size * 0.2, 0, size);
  ctx.quadraticCurveTo(-size, -size * 0.2, 0, -size);
  ctx.fill();
  ctx.restore();
};
