// Hạt hiệu ứng và chữ bay. Giữ mảng có trần để khung hình không tụt khi chém liên tục.

export type ParticleKind = 'spark' | 'ink' | 'ring' | 'shard' | 'ember';

interface Particle {
  kind: ParticleKind;
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  size: number;
  color: string;
  rotation: number;
  spin: number;
  gravity: number;
}

interface Floater {
  text: string;
  x: number;
  y: number;
  vy: number;
  life: number;
  maxLife: number;
  font: string;
  color: string;
}

const MAX_PARTICLES = 520;
const FLOATER_STROKE = 'rgba(20, 6, 26, 0.85)';

export class Particles {
  private items: Particle[] = [];
  private floaters: Floater[] = [];

  private add(particle: Omit<Particle, 'rotation' | 'spin' | 'gravity'> & Partial<Pick<Particle, 'rotation' | 'spin' | 'gravity'>>): void {
    if (this.items.length >= MAX_PARTICLES) this.items.shift();
    this.items.push({ rotation: 0, spin: 0, gravity: 0, ...particle });
  }

  sparks(x: number, y: number, count: number, color: string, power = 220): void {
    for (let i = 0; i < count; i += 1) {
      const angle = Math.random() * Math.PI * 2;
      const speed = power * (0.35 + Math.random());
      const life = 0.22 + Math.random() * 0.3;
      this.add({ kind: 'spark', x, y, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed, life, maxLife: life, size: 1.2 + Math.random() * 2, color, gravity: 360 });
    }
  }

  ink(x: number, y: number, count: number, spread = 240): void {
    for (let i = 0; i < count; i += 1) {
      const angle = Math.random() * Math.PI * 2;
      const speed = spread * Math.random();
      const life = 0.4 + Math.random() * 0.5;
      this.add({ kind: 'ink', x, y, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed - 40, life, maxLife: life, size: 1.5 + Math.random() * 5, color: '#14061a', gravity: 620 });
    }
  }

  ring(x: number, y: number, size: number, color: string): void {
    this.add({ kind: 'ring', x, y, vx: 0, vy: 0, life: 0.34, maxLife: 0.34, size, color });
  }

  shards(x: number, y: number, count: number, color: string): void {
    for (let i = 0; i < count; i += 1) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 90 + Math.random() * 260;
      const life = 0.5 + Math.random() * 0.4;
      this.add({ kind: 'shard', x, y, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed, life, maxLife: life, size: 5 + Math.random() * 9, color, rotation: Math.random() * 6, spin: (Math.random() - 0.5) * 16, gravity: 560 });
    }
  }

  ember(x: number, y: number, color: string): void {
    const life = 0.35 + Math.random() * 0.4;
    this.add({ kind: 'ember', x, y, vx: (Math.random() - 0.5) * 34, vy: -60 - Math.random() * 80, life, maxLife: life, size: 1.5 + Math.random() * 3, color });
  }

  floatText(text: string, x: number, y: number, font: string, color: string, life = 1): void {
    this.floaters.push({ text, x, y, vy: -58, life, maxLife: life, font, color });
  }

  update(dt: number): void {
    for (let i = this.items.length - 1; i >= 0; i -= 1) {
      const p = this.items[i];
      p.life -= dt;
      if (p.life <= 0) {
        this.items.splice(i, 1);
        continue;
      }
      p.vy += p.gravity * dt;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.rotation += p.spin * dt;
    }
    for (let i = this.floaters.length - 1; i >= 0; i -= 1) {
      const f = this.floaters[i];
      f.life -= dt;
      f.y += f.vy * dt;
      f.vy *= 1 - 1.6 * dt;
      if (f.life <= 0) this.floaters.splice(i, 1);
    }
  }

  draw(ctx: CanvasRenderingContext2D): void {
    for (const p of this.items) {
      const t = p.life / p.maxLife;
      ctx.globalAlpha = Math.min(1, t * 1.6);
      if (p.kind === 'ink') this.drawDot(ctx, p, p.size);
    }
    ctx.globalCompositeOperation = 'lighter';
    for (const p of this.items) {
      const t = p.life / p.maxLife;
      ctx.globalAlpha = Math.min(1, t * 1.6);
      if (p.kind === 'spark') this.drawStreak(ctx, p);
      else if (p.kind === 'ember') this.drawDot(ctx, p, p.size * t);
      else if (p.kind === 'ring') this.drawRing(ctx, p, 1 - t);
    }
    ctx.globalCompositeOperation = 'source-over';
    for (const p of this.items) {
      if (p.kind !== 'shard') continue;
      ctx.globalAlpha = Math.min(1, (p.life / p.maxLife) * 1.6);
      this.drawShard(ctx, p);
    }
    ctx.globalAlpha = 1;
  }

  drawFloaters(ctx: CanvasRenderingContext2D): void {
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.lineJoin = 'round';
    ctx.lineWidth = 4;
    ctx.strokeStyle = FLOATER_STROKE;
    for (const f of this.floaters) {
      const age = 1 - f.life / f.maxLife;
      ctx.globalAlpha = Math.min(1, (f.life / f.maxLife) * 2.5);
      const pop = age < 0.12 ? 0.7 + (age / 0.12) * 0.45 : 1.15 - Math.min(0.15, (age - 0.12) * 0.8);
      ctx.save();
      ctx.translate(f.x, f.y);
      ctx.scale(pop, pop);
      ctx.font = f.font;
      ctx.strokeText(f.text, 0, 0);
      ctx.fillStyle = f.color;
      ctx.fillText(f.text, 0, 0);
      ctx.restore();
    }
    ctx.globalAlpha = 1;
  }

  private drawDot(ctx: CanvasRenderingContext2D, p: Particle, size: number): void {
    ctx.fillStyle = p.color;
    ctx.beginPath();
    ctx.arc(p.x, p.y, Math.max(0.3, size), 0, Math.PI * 2);
    ctx.fill();
  }

  private drawStreak(ctx: CanvasRenderingContext2D, p: Particle): void {
    ctx.strokeStyle = p.color;
    ctx.lineWidth = p.size;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
    ctx.lineTo(p.x - p.vx * 0.03, p.y - p.vy * 0.03);
    ctx.stroke();
  }

  private drawRing(ctx: CanvasRenderingContext2D, p: Particle, progress: number): void {
    ctx.strokeStyle = p.color;
    ctx.lineWidth = 3 * (1 - progress) + 0.5;
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.size * (0.3 + progress), 0, Math.PI * 2);
    ctx.stroke();
  }

  private drawShard(ctx: CanvasRenderingContext2D, p: Particle): void {
    ctx.save();
    ctx.translate(p.x, p.y);
    ctx.rotate(p.rotation);
    ctx.fillStyle = p.color;
    ctx.beginPath();
    ctx.moveTo(-p.size * 0.6, -p.size * 0.3);
    ctx.lineTo(p.size * 0.7, -p.size * 0.1);
    ctx.lineTo(-p.size * 0.1, p.size * 0.6);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }
}
