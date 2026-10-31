// Cảnh sơn thủy mực tàu nhiều lớp parallax. Núi và mặt đất dựng sẵn lên canvas phụ, mỗi khung chỉ dán lại.
import { comboTierPalette, drawPetal, makeMist, makeMoon, paintGround, paintRidge } from './backdropArt';

interface Layer {
  canvas: HTMLCanvasElement;
  offset: number;
  speed: number;
  y: number;
}

interface Petal {
  x: number;
  y: number;
  size: number;
  vx: number;
  vy: number;
  spin: number;
  rotation: number;
  flip: number;
}

interface Mist {
  x: number;
  y: number;
  scale: number;
  speed: number;
  alpha: number;
}

const PETAL_COUNT = 34;
const MIST_COUNT = 6;
const TILE_FACTOR = 1.6;
const TINT_SPEED = 1.8;
const SHAKE_BLEED = 24;

const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

export class Backdrop {
  /** Máy không kịp 45 khung/giây thì bỏ lớp sương giữa, lớp phủ tốn nhiều điểm ảnh nhất. */
  lowDetail = false;
  private w = 1;
  private h = 1;
  private groundY = 1;
  private layers: Layer[] = [];
  private ground: HTMLCanvasElement | null = null;
  private moon = makeMoon();
  private mistSprite = makeMist();
  private petals: Petal[] = [];
  private mists: Mist[] = [];
  private tint = 0;
  private tintTarget = 0;

  resize(w: number, h: number, groundY: number): void {
    this.w = w;
    this.h = h;
    this.groundY = groundY;
    const tile = Math.ceil(Math.max(w, 720) * TILE_FACTOR);
    const specs = [
      { peak: 0.2, base: 0.78, color: [88, 44, 110], speed: 5, seed: 1.7, alpha: 0.5 },
      { peak: 0.36, base: 0.86, color: [58, 26, 78], speed: 12, seed: 4.1, alpha: 0.72 },
      { peak: 0.54, base: 0.95, color: [30, 12, 42], speed: 24, seed: 7.9, alpha: 0.92 }
    ];
    this.layers = specs.map(spec => ({
      canvas: paintRidge(tile, Math.ceil(groundY - h * spec.peak) + 4, spec.color, spec.seed, spec.alpha, spec.seed > 7),
      offset: 0,
      speed: spec.speed,
      y: h * spec.peak
    }));
    this.ground = paintGround(tile, Math.ceil(h - groundY) + SHAKE_BLEED);
    this.petals = Array.from({ length: PETAL_COUNT }, () => this.newPetal(true));
    this.mists = Array.from({ length: MIST_COUNT }, (_, i) => ({
      x: Math.random() * w,
      y: groundY - h * (0.08 + 0.09 * (i % 3)),
      scale: 0.8 + Math.random() * 1.3,
      speed: 7 + Math.random() * 16,
      alpha: 0.12 + Math.random() * 0.16
    }));
  }

  private newPetal(anywhere: boolean): Petal {
    return {
      x: Math.random() * this.w * 1.3,
      y: anywhere ? Math.random() * this.h : -12,
      size: 3 + Math.random() * 5,
      vx: -18 - Math.random() * 34,
      vy: 16 + Math.random() * 30,
      spin: (Math.random() - 0.5) * 3,
      rotation: Math.random() * 6,
      flip: Math.random() * 6
    };
  }

  setTier(tier: number): void {
    this.tintTarget = tier;
  }

  update(dt: number): void {
    this.tint += (this.tintTarget - this.tint) * Math.min(1, dt * TINT_SPEED);
    for (const layer of this.layers) layer.offset = (layer.offset + layer.speed * dt) % layer.canvas.width;
    for (const mist of this.mists) {
      mist.x += mist.speed * dt;
      if (mist.x > this.w + 220) mist.x = -220;
    }
    this.petals.forEach((petal, i) => {
      petal.x += petal.vx * dt;
      petal.y += petal.vy * dt;
      petal.rotation += petal.spin * dt;
      petal.flip += dt * 2.4;
      if (petal.y > this.groundY || petal.x < -14) this.petals[i] = this.newPetal(false);
    });
  }

  /** Vẽ phần sau nhân vật: trời, trăng, núi, sương. */
  drawScene(ctx: CanvasRenderingContext2D): void {
    const low = Math.floor(this.tint);
    const high = Math.min(4, low + 1);
    const t = this.tint - low;
    const a = comboTierPalette(low);
    const b = comboTierPalette(high);
    const color = (i: number) => {
      const r = Math.round(lerp(a[i][0], b[i][0], t));
      const g = Math.round(lerp(a[i][1], b[i][1], t));
      const blue = Math.round(lerp(a[i][2], b[i][2], t));
      return `rgb(${r}, ${g}, ${blue})`;
    };
    const sky = ctx.createLinearGradient(0, 0, 0, this.groundY);
    sky.addColorStop(0, color(0));
    sky.addColorStop(0.55, color(1));
    sky.addColorStop(1, color(2));
    ctx.fillStyle = sky;
    // Tràn viền để lúc rung màn không lộ mép đen.
    ctx.fillRect(-SHAKE_BLEED, -SHAKE_BLEED, this.w + SHAKE_BLEED * 2, this.h + SHAKE_BLEED * 2);

    const moonSize = Math.min(this.w, this.h) * 0.5;
    ctx.drawImage(this.moon, this.w * 0.72 - moonSize / 2, this.h * 0.2 - moonSize / 2, moonSize, moonSize);

    this.layers.forEach((layer, i) => {
      this.drawTiled(ctx, layer.canvas, layer.offset, layer.y);
      if (i === 1 && !this.lowDetail) this.drawMist(ctx);
    });
    this.drawMist(ctx);
    this.drawPetals(ctx);
  }

  drawGround(ctx: CanvasRenderingContext2D): void {
    if (this.ground) this.drawTiled(ctx, this.ground, this.layers[2]?.offset ?? 0, this.groundY - 1);
  }

  private drawTiled(ctx: CanvasRenderingContext2D, image: HTMLCanvasElement, offset: number, y: number): void {
    for (let x = -offset; x < this.w; x += image.width) ctx.drawImage(image, Math.floor(x), y);
  }

  private drawMist(ctx: CanvasRenderingContext2D): void {
    for (const mist of this.mists) {
      const width = this.mistSprite.width * mist.scale;
      const height = this.mistSprite.height * mist.scale;
      ctx.globalAlpha = mist.alpha;
      ctx.drawImage(this.mistSprite, mist.x - width / 2, mist.y - height / 2, width, height);
    }
    ctx.globalAlpha = 1;
  }

  private drawPetals(ctx: CanvasRenderingContext2D): void {
    for (const petal of this.petals) drawPetal(ctx, petal.x, petal.y, petal.size, petal.rotation, petal.flip);
  }
}
