// Kiểu dữ liệu dùng chung của mini-game Phi Kiếm Trảm Tự (F16.01).
import type { BladeEvent, BladeItem } from '../../api/gamification';

export type SpeedOption = 'calm' | 'standard' | 'storm';

export interface GamePrefs {
  sound: boolean;
  hints: boolean;
  speed: SpeedOption;
}

export type EnginePhase = 'intro' | 'playing' | 'outro' | 'done';
export type EndReason = 'time' | 'lives' | 'cleared' | 'quit';

/** Chữ đang rơi. `doomed`: đã gõ đúng, chờ kiếm bay tới nên không thể gây mất mạng nữa. */
export interface Glyph {
  item: BladeItem;
  answers: string[];
  x: number;
  y: number;
  speed: number;
  size: number;
  halfW: number;
  halfH: number;
  swayPhase: number;
  doomed: boolean;
  /** Điểm đã ghi khi gõ xong, hiện lên lúc kiếm chạm chữ. */
  points: number;
  /** Hiệu ứng nảy khi gõ đúng một phím, giảm dần về 0. */
  pulse: number;
  /** Hiệu ứng rung ô pinyin khi gõ sai, giảm dần về 0. */
  shake: number;
}

/** Một nửa sprite sau khi bị chém. */
export interface Slice {
  text: string;
  size: number;
  isBoss: boolean;
  tone: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  rotation: number;
  spin: number;
  life: number;
  maxLife: number;
  /** Góc đường chém. */
  cutAngle: number;
  /** +1 hoặc -1: nửa nào của đường chém. */
  side: number;
}

/** Vệt chém sáng chớp qua chữ. */
export interface SlashFlash {
  x: number;
  y: number;
  angle: number;
  length: number;
  life: number;
  maxLife: number;
}

export interface Banner {
  title: string;
  subtitle: string;
  life: number;
  maxLife: number;
  color: string;
}

export interface HudState {
  phase: EnginePhase;
  score: number;
  combo: number;
  lives: number;
  maxLives: number;
  secondsLeft: number;
  wave: number;
  multiplier: number;
  /** Thanh Kiếm Khí 0..100 (số nguyên để HUD chỉ vẽ lại khi đổi). */
  energy: number;
  ultimate: boolean;
}

export interface GameOutcome {
  reason: EndReason;
  events: BladeEvent[];
  typos: number;
  durationMs: number;
}

export interface EngineCallbacks {
  onHud: (hud: HudState) => void;
  onEnd: (outcome: GameOutcome) => void;
}
