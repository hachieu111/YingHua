// Lõi game thuần TS: giữ trạng thái trong đối tượng, React chỉ nhận HUD khi giá trị đổi (F16.01).
import type { BladeEvent, BladeItem, BladeRound } from '../../api/gamification';
import { GameAudio } from './audio';
import { Backdrop } from './backdrop';
import { comboBreakFx, cutFx, expire, keystrokeFx, missFx, moveSlices } from './fx';
import { GlyphSpriteCache } from './glyphSprites';
import { toneOf } from './glyphView';
import { Hero } from './hero';
import { Particles } from './particles';
import { COMBO_MILESTONES, DOOMED_FALL_FACTOR, LIFE_BONUS, MIN_KEY_MS, SPEED_FACTOR, ULTIMATE_COMBO, ULTIMATE_FALL_FACTOR, ULTIMATE_SECONDS, comboMultiplier, comboTier, findTarget, pointsFor, waveOf, waveTuning } from './rules';
import { createGlyph, pickLane } from './spawner';
import { SwordSquad } from './swords';
import type { Banner, EndReason, EngineCallbacks, EnginePhase, GamePrefs, Glyph, HudState, SlashFlash, Slice } from './types';

const INTRO_SECONDS = 2.4;
const OUTRO_SECONDS = 1.1;
const WAVE_PAUSE_SECONDS = 1.3;
const EMPTY_FIELD_SPAWN_SECONDS = 0.35;
const SLOWMO_RATE = 0.3;
const SLOWMO_SECONDS = 0.1;
const BOSS_SLOWMO_SECONDS = 0.2;
const COMBO_SHATTER_MIN = 3;

const clamp = (value: number, low: number, high: number): number => Math.max(low, Math.min(high, value));

/** Vị trí bộ đếm combo; engine cần biết để làm vỡ combo đúng chỗ. */
export const comboAnchorY = (h: number): number => Math.max(92, h * 0.16);

export class PhiKiemEngine {
  readonly audio: GameAudio;
  readonly particles = new Particles();
  readonly hero = new Hero();
  readonly backdrop = new Backdrop();
  readonly swords = new SwordSquad();
  readonly sprites: GlyphSpriteCache;
  readonly hints: boolean;

  w = 1;
  h = 1;
  groundY = 1;
  unit = 44;
  time = 0;
  phase: EnginePhase = 'intro';
  paused = false;
  introLeft = INTRO_SECONDS;
  glyphs: Glyph[] = [];
  slices: Slice[] = [];
  flashes: SlashFlash[] = [];
  banners: Banner[] = [];
  buffer = '';
  target: Glyph | null = null;
  combo = 0;
  comboBump = 0;
  redFlash = 0;
  typoFlash = 0;
  shake = 0;

  private readonly speedFactor: number;
  private readonly limitMs: number;
  private elapsedMs = 0;
  private nextIndex = 0;
  private spawnIn = 0.2;
  private wave = 1;
  private score = 0;
  private lives: number;
  private typos = 0;
  private lastMs = 0;
  private lastHitMs = 0;
  private events: BladeEvent[] = [];
  private slowmo = 0;
  private ultimateLeft = 0;
  private outroLeft = 0;
  private endReason: EndReason = 'time';
  private hud: HudState | null = null;

  constructor(
    private readonly round: BladeRound,
    prefs: GamePrefs,
    private readonly callbacks: EngineCallbacks,
    private readonly reducedMotion: boolean,
    dpr: number
  ) {
    this.audio = new GameAudio(!prefs.sound);
    this.sprites = new GlyphSpriteCache(dpr);
    this.hints = prefs.hints;
    this.speedFactor = SPEED_FACTOR[prefs.speed];
    this.limitMs = round.seconds * 1000;
    this.lives = round.lives;
  }

  private sizeFor(item: BladeItem): number {
    return item.is_boss ? Math.round(this.unit * 1.3) : this.unit;
  }

  /** Dựng sẵn sprite của cả ván để lúc chơi không khựng khi chữ mới xuất hiện. */
  prebuild(): void {
    for (const item of this.round.items) this.sprites.get(item.text, this.sizeFor(item), item.is_boss, toneOf(item.index));
  }

  resize(w: number, h: number, dpr: number): void {
    const ratioX = w / this.w;
    const ratioY = h / this.h;
    const first = this.w === 1;
    this.w = w;
    this.h = h;
    this.groundY = Math.round(h * (h < 560 ? 0.85 : 0.88));
    this.unit = Math.round(clamp(Math.min(w, h * 1.15) / 13, 34, 68));
    this.sprites.reset(dpr);
    this.backdrop.resize(w, h, this.groundY);
    this.hero.resize(w, this.groundY, this.unit);
    if (first) return;
    for (const glyph of this.glyphs) {
      glyph.x *= ratioX;
      glyph.y *= ratioY;
      glyph.speed *= ratioY;
      this.measure(glyph);
    }
  }

  private measure(glyph: Glyph): void {
    glyph.size = this.sizeFor(glyph.item);
    const sprite = this.sprites.get(glyph.item.text, glyph.size, glyph.item.is_boss, toneOf(glyph.item.index));
    glyph.halfW = sprite.bodyWidth / 2;
    glyph.halfH = glyph.size * 0.56;
  }

  update(dtReal: number): void {
    if (this.phase === 'done') return;
    const dt = dtReal * (this.slowmo > 0 ? SLOWMO_RATE : 1);
    this.slowmo = Math.max(0, this.slowmo - dtReal);
    this.time += dt;

    if (this.phase === 'intro') {
      this.introLeft -= dtReal;
      if (this.introLeft <= 0) this.phase = 'playing';
    } else if (this.phase === 'playing') {
      this.elapsedMs = Math.min(this.limitMs, this.elapsedMs + dtReal * 1000);
      this.ultimateLeft = Math.max(0, this.ultimateLeft - dtReal);
      this.spawn(dtReal);
      this.fall(dt);
      this.checkEnd();
    } else if (this.phase === 'outro') {
      this.outroLeft -= dtReal;
      if (this.outroLeft <= 0) this.complete();
    }

    this.animate(dt, dtReal);
    this.emitHud();
  }

  private checkEnd(): void {
    if (this.phase !== 'playing') return;
    if (this.elapsedMs >= this.limitMs) this.end('time');
    else if (this.nextIndex >= this.round.items.length && this.glyphs.length === 0) this.end('cleared');
  }

  private spawn(dt: number): void {
    // Người gõ nhanh không phải chờ trên màn trống.
    if (this.glyphs.length === 0) this.spawnIn = Math.min(this.spawnIn, EMPTY_FIELD_SPAWN_SECONDS);
    this.spawnIn -= dt;
    if (this.spawnIn > 0 || this.nextIndex >= this.round.items.length) return;
    const tuning = waveTuning(this.wave);
    if (this.glyphs.length >= tuning.maxActive) return;
    const item = this.round.items[this.nextIndex];
    this.nextIndex += 1;
    this.spawnIn = tuning.spawnGap;
    const glyph = createGlyph(item, this, tuning.fallSeconds, this.speedFactor);
    this.measure(glyph);
    glyph.x = pickLane(this.glyphs, this, glyph.halfW + 22);
    glyph.y = -glyph.halfH - 10;
    this.glyphs.push(glyph);
    const wave = waveOf(this.nextIndex);
    if (wave !== this.wave) {
      this.wave = wave;
      this.spawnIn += WAVE_PAUSE_SECONDS;
      this.banners.push({ title: `Đợt ${wave}`, subtitle: '再战', life: 1.4, maxLife: 1.4, color: '#ffe3f0' });
    }
  }

  private fall(dt: number): void {
    const slow = this.ultimateLeft > 0 ? ULTIMATE_FALL_FACTOR : 1;
    for (const glyph of [...this.glyphs]) {
      glyph.y += glyph.speed * dt * slow * (glyph.doomed ? DOOMED_FALL_FACTOR : 1);
      const floor = this.groundY - glyph.halfH;
      if (glyph.y < floor) continue;
      if (glyph.doomed) glyph.y = floor;
      else this.miss(glyph);
      if (this.phase !== 'playing') return;
    }
  }

  private animate(dt: number, dtReal: number): void {
    const lowest = findTarget(this.glyphs, '');
    this.hero.update(dt, lowest ? lowest.x : null);
    this.swords.update(dt, glyph => this.cut(glyph));
    this.swords.updateRain(dt, this.ultimateLeft > 0, this.w, this.h);
    this.backdrop.setTier(comboTier(this.combo));
    this.backdrop.update(dt);
    this.particles.update(dt);
    for (const glyph of this.glyphs) {
      glyph.pulse = Math.max(0, glyph.pulse - dtReal * 6);
      glyph.shake = Math.max(0, glyph.shake - dtReal * 4);
      if (glyph.item.is_boss && Math.random() < 0.5) {
        this.particles.ember(glyph.x + (Math.random() - 0.5) * glyph.halfW * 2, glyph.y + glyph.halfH, Math.random() < 0.5 ? '#ff7a2a' : '#ffd76a');
      }
    }
    moveSlices(this.slices, dt);
    this.slices = expire(this.slices, dt);
    this.flashes = expire(this.flashes, dtReal);
    this.banners = expire(this.banners, dtReal);
    this.comboBump = Math.max(0, this.comboBump - dtReal * 5);
    this.redFlash = Math.max(0, this.redFlash - dtReal * 2.2);
    this.typoFlash = Math.max(0, this.typoFlash - dtReal * 6);
    this.shake = Math.max(0, this.shake - dtReal * 26);
  }

  /** `elapsedMs` chỉ tăng khi đang chơi nên mốc này đã không tính lúc tạm dừng. */
  private record(index: number, result: BladeEvent['result'], minGapMs = 0): void {
    this.lastMs = Math.max(this.lastMs, Math.floor(this.elapsedMs));
    // Đồng hồ chỉ tăng theo khung hình: khi máy khựng, hai lần chém thật có thể mang cùng một mốc và bị máy chủ coi là gõ quá nhanh.
    if (minGapMs > 0) this.lastMs = Math.max(this.lastMs, this.lastHitMs + minGapMs);
    if (result === 'hit') this.lastHitMs = this.lastMs;
    this.events.push({ index, result, ms: this.lastMs });
  }

  typeKey(key: string): void {
    if (this.phase !== 'playing' || this.paused) return;
    this.audio.unlock();
    const candidate = this.buffer + key;
    const next = findTarget(this.glyphs, candidate);
    if (!next) {
      if (!findTarget(this.glyphs, '')) return;
      this.typos += 1;
      this.typoFlash = 1;
      if (this.target) this.target.shake = 1;
      this.audio.typo();
      return;
    }
    this.buffer = candidate;
    this.target = next;
    next.pulse = 1;
    keystrokeFx(this.particles, next);
    this.audio.tick(candidate.length);
    if (next.answers.includes(candidate)) this.strike(next);
  }

  backspace(): void {
    if (this.phase !== 'playing' || this.paused || !this.buffer) return;
    this.buffer = this.buffer.slice(0, -1);
    this.target = this.buffer ? findTarget(this.glyphs, this.buffer) : null;
  }

  /** Gõ xong đáp án: ghi nhận ngay, kiếm chỉ là phần trình diễn nên chữ không còn gây mất mạng. */
  private strike(glyph: Glyph): void {
    glyph.doomed = true;
    this.combo += 1;
    this.comboBump = 1;
    glyph.points = pointsFor(glyph.item.is_boss, this.combo);
    this.score += glyph.points;
    this.record(glyph.item.index, 'hit', Math.min(...glyph.answers.map(answer => answer.length)) * MIN_KEY_MS);
    this.buffer = '';
    this.target = null;
    this.hero.slash(glyph.x);
    this.swords.launch(this.hero.hand(), glyph, glyph.item.is_boss ? Math.min(4, [...glyph.item.text].length + 1) : 0);
    this.audio.whoosh();
    this.audio.combo(this.combo);
    this.celebrate();
  }

  private celebrate(): void {
    const milestone = COMBO_MILESTONES[this.combo];
    if (milestone) {
      this.banners.push({ title: milestone.title, subtitle: milestone.hanzi, life: 1.5, maxLife: 1.5, color: milestone.color });
      this.audio.milestone();
    }
    if (this.combo % ULTIMATE_COMBO === 0) {
      this.ultimateLeft = ULTIMATE_SECONDS;
      this.banners.push({ title: 'Vạn Kiếm Quy Tông', subtitle: '万剑归宗', life: 2.2, maxLife: 2.2, color: '#fff3c4' });
      this.audio.ultimate();
    }
  }

  private cut(glyph: Glyph): void {
    this.glyphs = this.glyphs.filter(item => item !== glyph);
    const { slices, flash } = cutFx(this.particles, glyph);
    this.slices.push(...slices);
    this.flashes.push(flash);
    this.audio.slash();
    if (this.reducedMotion) return;
    this.slowmo = glyph.item.is_boss ? BOSS_SLOWMO_SECONDS : SLOWMO_SECONDS;
    this.shake = glyph.item.is_boss ? 11 : 5;
  }

  private miss(glyph: Glyph): void {
    this.glyphs = this.glyphs.filter(item => item !== glyph);
    this.record(glyph.item.index, 'miss');
    if (this.target === glyph) {
      this.buffer = '';
      this.target = null;
    }
    this.lives -= 1;
    this.redFlash = 1;
    if (!this.reducedMotion) this.shake = 15;
    this.hero.knockback(glyph.x);
    missFx(this.particles, glyph, this.groundY);
    this.audio.hurt();
    if (this.combo >= COMBO_SHATTER_MIN) {
      comboBreakFx(this.particles, this.w / 2, comboAnchorY(this.h));
      this.audio.comboBreak();
    }
    this.combo = 0;
    this.ultimateLeft = 0;
    if (this.lives <= 0) this.end('lives');
  }

  /** Người chơi bấm dừng: nộp ngay phần đã chơi. */
  quit(): void {
    if (this.phase !== 'playing' && this.phase !== 'intro') return;
    this.end('quit');
    this.complete();
  }

  private end(reason: EndReason): void {
    this.endReason = reason;
    this.phase = 'outro';
    this.outroLeft = OUTRO_SECONDS;
    this.buffer = '';
    this.target = null;
    if (reason === 'cleared') this.score += LIFE_BONUS * this.lives;
    if (reason === 'lives') this.audio.lose();
    else if (reason !== 'quit') this.audio.finish();
  }

  private complete(): void {
    if (this.phase === 'done') return;
    this.phase = 'done';
    this.emitHud();
    this.callbacks.onEnd({ reason: this.endReason, events: this.events, typos: this.typos, durationMs: Math.max(this.lastMs, Math.floor(this.elapsedMs)) });
  }

  private emitHud(): void {
    const energy = this.ultimateLeft > 0 ? this.ultimateLeft / ULTIMATE_SECONDS : (this.combo % ULTIMATE_COMBO) / ULTIMATE_COMBO;
    const next: HudState = {
      phase: this.phase,
      score: this.score,
      combo: this.combo,
      lives: this.lives,
      maxLives: this.round.lives,
      secondsLeft: Math.ceil((this.limitMs - this.elapsedMs) / 1000),
      wave: this.wave,
      multiplier: comboMultiplier(this.combo),
      energy: Math.round(energy * 100),
      ultimate: this.ultimateLeft > 0
    };
    const prev = this.hud;
    if (prev && (Object.keys(next) as (keyof HudState)[]).every(key => prev[key] === next[key])) return;
    this.hud = next;
    this.callbacks.onHud(next);
  }
}
