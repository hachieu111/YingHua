// Kiếm khách chibi vẽ hoàn toàn bằng code, tự chạy tới dưới chữ thấp nhất với quán tính.

const MAX_SPEED_FACTOR = 1.05;
const ACCEL_FACTOR = 7;
const FRICTION = 7;
const ARRIVE_ZONE = 10;
const SLASH_SECONDS = 0.32;
const HURT_SECONDS = 0.55;

const INK = '#1a0a24';
const ROBE = '#a43073';
const ROBE_DARK = '#6d1a4c';
const CAPE = '#3b1250';
const CAPE_INNER = '#ff9fc8';
const SKIN = '#ffe3cf';
const HAIR = '#20102e';
const GOLD = '#ffd76a';

export class Hero {
  x = 0;
  private vx = 0;
  private facing = 1;
  private runPhase = 0;
  private time = 0;
  private slashTimer = 0;
  private hurtTimer = 0;
  private scale = 1;
  private groundY = 0;
  private width = 0;

  resize(width: number, groundY: number, unit: number): void {
    this.x = this.x === 0 ? width / 2 : Math.min(width, this.x);
    this.width = width;
    this.groundY = groundY;
    this.scale = Math.max(0.72, unit / 50);
  }

  slash(targetX: number): void {
    this.slashTimer = SLASH_SECONDS;
    this.facing = targetX >= this.x ? 1 : -1;
  }

  knockback(fromX: number): void {
    const dir = this.x >= fromX ? 1 : -1;
    this.vx = dir * this.topSpeed() * 1.5;
    this.facing = -dir;
    this.hurtTimer = HURT_SECONDS;
  }

  /** Vị trí tay vung kiếm, nơi phi kiếm xuất phát. */
  hand(): { x: number; y: number } {
    return { x: this.x + this.facing * 15 * this.scale, y: this.groundY - 40 * this.scale };
  }

  private topSpeed(): number {
    return this.width * 0.42 * MAX_SPEED_FACTOR + 150;
  }

  update(dt: number, targetX: number | null): void {
    this.time += dt;
    this.slashTimer = Math.max(0, this.slashTimer - dt);
    this.hurtTimer = Math.max(0, this.hurtTimer - dt);
    const gap = targetX === null ? 0 : targetX - this.x;
    if (Math.abs(gap) > ARRIVE_ZONE && this.hurtTimer < HURT_SECONDS * 0.45) {
      // Tốc độ mong muốn giảm dần khi gần đích để dừng êm, không giật qua lại.
      const desired = Math.sign(gap) * Math.min(this.topSpeed(), Math.abs(gap) * 5);
      this.vx += (desired - this.vx) * Math.min(1, ACCEL_FACTOR * dt);
    } else {
      this.vx -= this.vx * Math.min(1, FRICTION * dt);
    }
    this.x = Math.max(24, Math.min(this.width - 24, this.x + this.vx * dt));
    if (Math.abs(this.vx) > 20 && this.hurtTimer <= 0 && this.slashTimer <= 0) this.facing = this.vx > 0 ? 1 : -1;
    this.runPhase += (Math.abs(this.vx) / 46) * dt * 1.6;
  }

  draw(ctx: CanvasRenderingContext2D): void {
    const speedRatio = Math.min(1, Math.abs(this.vx) / this.topSpeed());
    const running = speedRatio > 0.04;
    const breath = Math.sin(this.time * 2.6) * 0.8;
    const bob = running ? Math.abs(Math.sin(this.runPhase)) * 2.6 : breath * 0.5;
    const flash = this.hurtTimer > 0 && Math.floor(this.hurtTimer * 18) % 2 === 0;
    const lean = running ? 0.12 + speedRatio * 0.12 : 0;

    ctx.save();
    ctx.fillStyle = 'rgba(0, 0, 0, 0.42)';
    ctx.beginPath();
    ctx.ellipse(this.x, this.groundY + 3, 20 * this.scale, 5 * this.scale, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.translate(this.x, this.groundY);
    ctx.scale(this.facing * this.scale, this.scale);
    if (flash) ctx.globalAlpha = 0.55;

    this.drawLegs(ctx, running);
    ctx.translate(0, -bob);
    ctx.rotate(lean);
    this.drawCape(ctx, speedRatio);
    this.drawBackSword(ctx);
    this.drawTorso(ctx, breath);
    this.drawHead(ctx, speedRatio, breath);
    this.drawArm(ctx, running);
    ctx.restore();
  }

  private drawLegs(ctx: CanvasRenderingContext2D, running: boolean): void {
    const swing = running ? Math.sin(this.runPhase) : 0;
    const limb = (angle: number, shade: string) => {
      const footX = Math.sin(angle) * 11;
      const lift = Math.max(0, Math.cos(angle)) * (running ? 5 : 0);
      ctx.strokeStyle = shade;
      ctx.lineWidth = 6;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(0, -17);
      ctx.quadraticCurveTo(footX * 0.6 + 2, -9, footX, -3 - lift);
      ctx.stroke();
      ctx.fillStyle = INK;
      ctx.beginPath();
      ctx.ellipse(footX + 2, -2.5 - lift, 5, 2.8, 0, 0, Math.PI * 2);
      ctx.fill();
    };
    limb(running ? swing * 1.1 + Math.PI : -0.22, ROBE_DARK);
    limb(running ? -swing * 1.1 : 0.22, '#3a1a4a');
  }

  private drawCape(ctx: CanvasRenderingContext2D, speedRatio: number): void {
    const t = this.time * (5 + speedRatio * 8);
    const reach = 15 + speedRatio * 19;
    const tail = (offset: number) => Math.sin(t + offset) * (3 + speedRatio * 4);
    ctx.fillStyle = CAPE;
    ctx.beginPath();
    ctx.moveTo(4, -33);
    ctx.quadraticCurveTo(-reach * 0.7, -30 + tail(0), -reach, -16 + tail(1));
    ctx.quadraticCurveTo(-reach * 0.9, -6 + tail(2), -reach * 0.5, -9 + tail(2.5));
    ctx.quadraticCurveTo(-8, -3, 2, -16);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = CAPE_INNER;
    ctx.lineWidth = 1.1;
    ctx.beginPath();
    ctx.moveTo(-reach, -16 + tail(1));
    ctx.quadraticCurveTo(-reach * 0.9, -6 + tail(2), -reach * 0.5, -9 + tail(2.5));
    ctx.stroke();
  }

  private drawBackSword(ctx: CanvasRenderingContext2D): void {
    ctx.save();
    ctx.translate(-4, -29);
    ctx.rotate(-0.72);
    ctx.fillStyle = '#d6e2f0';
    ctx.fillRect(-1.3, -21, 2.6, 34);
    ctx.fillStyle = GOLD;
    ctx.fillRect(-4, 12, 8, 2);
    ctx.fillStyle = ROBE_DARK;
    ctx.fillRect(-1.6, 14, 3.2, 8);
    ctx.restore();
  }

  private drawTorso(ctx: CanvasRenderingContext2D, breath: number): void {
    ctx.fillStyle = ROBE;
    ctx.beginPath();
    ctx.moveTo(-8, -34 - breath * 0.4);
    ctx.quadraticCurveTo(0, -37 - breath * 0.4, 8, -34 - breath * 0.4);
    ctx.lineTo(11, -13);
    ctx.quadraticCurveTo(0, -9, -11, -13);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = '#ffd8e7';
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.moveTo(-4, -34);
    ctx.lineTo(3, -24);
    ctx.lineTo(7, -33);
    ctx.stroke();
    ctx.fillStyle = GOLD;
    ctx.fillRect(-10, -22, 20, 3);
  }

  private drawHead(ctx: CanvasRenderingContext2D, speedRatio: number, breath: number): void {
    const y = -46 + breath * 0.3;
    const sway = Math.sin(this.time * (4 + speedRatio * 8)) * (2 + speedRatio * 4);
    ctx.strokeStyle = HAIR;
    ctx.lineWidth = 4.2;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(-7, y - 8);
    ctx.quadraticCurveTo(-16 - speedRatio * 6, y - 6 + sway, -19 - speedRatio * 11, y + 9 + sway);
    ctx.stroke();
    ctx.fillStyle = SKIN;
    ctx.beginPath();
    ctx.arc(0, y, 12.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = HAIR;
    ctx.beginPath();
    ctx.moveTo(-13, y + 3);
    ctx.quadraticCurveTo(-14, y - 15, 1, y - 14);
    ctx.quadraticCurveTo(14, y - 14, 13, y - 3);
    ctx.lineTo(8, y - 7);
    ctx.lineTo(5, y - 3);
    ctx.lineTo(1, y - 8);
    ctx.lineTo(-3, y - 3);
    ctx.lineTo(-7, y - 6);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = ROBE;
    ctx.fillRect(-13, y - 8, 7, 2.4);
    ctx.fillStyle = INK;
    const blink = Math.sin(this.time * 0.9) > 0.985;
    if (this.hurtTimer > 0 || blink) {
      ctx.fillRect(4, y + 1, 5, 1.3);
    } else {
      ctx.beginPath();
      ctx.ellipse(6.5, y + 1.5, 1.9, 2.7, 0, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.fillStyle = 'rgba(255, 130, 170, 0.5)';
    ctx.beginPath();
    ctx.ellipse(3.5, y + 6, 2.6, 1.4, 0, 0, Math.PI * 2);
    ctx.fill();
  }

  private drawArm(ctx: CanvasRenderingContext2D, running: boolean): void {
    const slashing = this.slashTimer > 0;
    const progress = 1 - this.slashTimer / SLASH_SECONDS;
    let angle = running ? 0.35 + Math.sin(this.runPhase + Math.PI) * 0.9 : 0.25;
    if (slashing) angle = -2.4 + progress * 3.2;
    const handX = Math.sin(angle + 0.5) * 15;
    const handY = -30 + Math.cos(angle + 0.5) * 15;
    ctx.strokeStyle = ROBE_DARK;
    ctx.lineWidth = 5.2;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(4, -32);
    ctx.lineTo(handX, handY);
    ctx.stroke();
    ctx.fillStyle = SKIN;
    ctx.beginPath();
    ctx.arc(handX, handY, 3, 0, Math.PI * 2);
    ctx.fill();
    if (slashing) {
      ctx.strokeStyle = `rgba(255, 228, 160, ${0.85 * (1 - progress)})`;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(4, -32, 24, -1.8, -1.8 + progress * 3);
      ctx.stroke();
    }
  }
}
