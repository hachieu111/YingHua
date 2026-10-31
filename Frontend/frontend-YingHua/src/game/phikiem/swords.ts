// Phi kiếm bay theo đường cong tới chữ, kèm vệt sáng, và mưa kiếm nền của Vạn Kiếm Quy Tông.
import type { Glyph } from './types';

const FLIGHT_SECONDS = 0.26;
const TRAIL_POINTS = 12;
const RAIN_COUNT = 26;

interface Point {
  x: number;
  y: number;
}

interface FlyingSword {
  from: Point;
  bend: Point;
  target: Glyph;
  /** Chỉ thanh chính kích hoạt cú chém; các thanh phụ để tăng độ hoành tráng khi chém boss. */
  primary: boolean;
  t: number;
  delay: number;
  angle: number;
  pos: Point;
  trail: Point[];
}

interface RainSword {
  x: number;
  y: number;
  speed: number;
  length: number;
  alpha: number;
}

/** Vẽ một thanh kiếm hướng theo `angle`, mũi ở phía trước gốc tọa độ. */
export const drawBlade = (ctx: CanvasRenderingContext2D, x: number, y: number, angle: number, length: number): void => {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(angle);
  const edge = ctx.createLinearGradient(0, -length * 0.05, 0, length * 0.05);
  edge.addColorStop(0, '#ffffff');
  edge.addColorStop(0.5, '#cfe4ff');
  edge.addColorStop(1, '#7f9cc4');
  ctx.fillStyle = edge;
  ctx.beginPath();
  ctx.moveTo(length * 0.5, 0);
  ctx.lineTo(length * 0.38, -length * 0.045);
  ctx.lineTo(-length * 0.2, -length * 0.035);
  ctx.lineTo(-length * 0.2, length * 0.035);
  ctx.lineTo(length * 0.38, length * 0.045);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = 'rgba(70, 90, 130, 0.8)';
  ctx.lineWidth = Math.max(0.6, length * 0.008);
  ctx.beginPath();
  ctx.moveTo(-length * 0.2, 0);
  ctx.lineTo(length * 0.42, 0);
  ctx.stroke();
  ctx.fillStyle = '#ffd76a';
  ctx.fillRect(-length * 0.235, -length * 0.1, length * 0.04, length * 0.2);
  ctx.fillStyle = '#6d1a4c';
  ctx.fillRect(-length * 0.42, -length * 0.03, length * 0.19, length * 0.06);
  ctx.fillStyle = '#ffd76a';
  ctx.beginPath();
  ctx.arc(-length * 0.44, 0, length * 0.04, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
};

export class SwordSquad {
  private swords: FlyingSword[] = [];
  private rain: RainSword[] = [];
  private rainAlpha = 0;

  launch(from: Point, target: Glyph, extras: number): void {
    for (let i = 0; i <= extras; i += 1) {
      const side = i % 2 === 0 ? -1 : 1;
      const lift = 60 + i * 34;
      this.swords.push({
        from: { ...from },
        bend: { x: (from.x + target.x) / 2 + side * (70 + i * 52), y: Math.min(from.y, target.y) - lift },
        target,
        primary: i === 0,
        t: 0,
        delay: i * 0.04,
        angle: -Math.PI / 2,
        pos: { ...from },
        trail: []
      });
    }
  }

  /** Gọi `onHit` khi thanh chính chạm chữ. */
  update(dt: number, onHit: (target: Glyph) => void): void {
    for (let i = this.swords.length - 1; i >= 0; i -= 1) {
      const sword = this.swords[i];
      if (sword.delay > 0) {
        sword.delay -= dt;
        continue;
      }
      sword.t = Math.min(1, sword.t + dt / FLIGHT_SECONDS);
      const u = sword.t * sword.t;
      const v = 1 - u;
      const x = v * v * sword.from.x + 2 * v * u * sword.bend.x + u * u * sword.target.x;
      const y = v * v * sword.from.y + 2 * v * u * sword.bend.y + u * u * sword.target.y;
      if (x !== sword.pos.x || y !== sword.pos.y) sword.angle = Math.atan2(y - sword.pos.y, x - sword.pos.x);
      sword.pos = { x, y };
      sword.trail.push(sword.pos);
      if (sword.trail.length > TRAIL_POINTS) sword.trail.shift();
      if (sword.t >= 1) {
        this.swords.splice(i, 1);
        if (sword.primary) onHit(sword.target);
      }
    }
  }

  updateRain(dt: number, active: boolean, w: number, h: number): void {
    this.rainAlpha += ((active ? 1 : 0) - this.rainAlpha) * Math.min(1, dt * 5);
    if (active && this.rain.length === 0) {
      this.rain = Array.from({ length: RAIN_COUNT }, () => ({
        x: Math.random() * (w + 300),
        y: Math.random() * h - h,
        speed: 620 + Math.random() * 520,
        length: 46 + Math.random() * 56,
        alpha: 0.25 + Math.random() * 0.5
      }));
    }
    if (this.rainAlpha < 0.01) {
      this.rain = [];
      return;
    }
    for (const sword of this.rain) {
      sword.y += sword.speed * dt;
      sword.x -= sword.speed * dt * 0.42;
      if (sword.y > h + 60) {
        sword.y = -60;
        sword.x = Math.random() * (w + 300);
      }
    }
  }

  drawRain(ctx: CanvasRenderingContext2D): void {
    const angle = Math.atan2(1, -0.42);
    for (const sword of this.rain) {
      ctx.globalAlpha = sword.alpha * this.rainAlpha;
      drawBlade(ctx, sword.x, sword.y, angle, sword.length);
    }
    ctx.globalAlpha = 1;
  }

  draw(ctx: CanvasRenderingContext2D, length: number): void {
    ctx.globalCompositeOperation = 'lighter';
    ctx.lineCap = 'round';
    for (const sword of this.swords) {
      for (let i = 1; i < sword.trail.length; i += 1) {
        const a = sword.trail[i - 1];
        const b = sword.trail[i];
        const t = i / sword.trail.length;
        ctx.strokeStyle = `rgba(255, 214, 150, ${t * 0.75})`;
        ctx.lineWidth = t * 7;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
    }
    ctx.globalCompositeOperation = 'source-over';
    for (const sword of this.swords) {
      if (sword.delay <= 0) drawBlade(ctx, sword.pos.x, sword.pos.y, sword.angle, length);
    }
  }
}
