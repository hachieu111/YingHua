// Tổng hợp âm thanh bằng Web Audio, không dùng tệp ngoài.

const PENTATONIC = [523.25, 587.33, 659.25, 783.99, 880, 1046.5, 1174.66, 1318.51, 1567.98, 1760];

interface ToneOptions {
  freq: number;
  endFreq?: number;
  duration: number;
  type?: OscillatorType;
  volume?: number;
  delay?: number;
}

interface NoiseOptions {
  duration: number;
  from: number;
  to: number;
  volume: number;
  delay?: number;
  q?: number;
}

export class GameAudio {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private noise: AudioBuffer | null = null;
  private muted: boolean;

  constructor(muted: boolean) {
    this.muted = muted;
  }

  /** Phải gọi sau thao tác của người dùng (chính sách tự phát của trình duyệt). */
  unlock(): void {
    if (this.ctx) {
      if (this.ctx.state === 'suspended') void this.ctx.resume();
      return;
    }
    if (typeof AudioContext === 'undefined') return;
    this.ctx = new AudioContext();
    this.master = this.ctx.createGain();
    this.master.gain.value = this.muted ? 0 : 0.5;
    this.master.connect(this.ctx.destination);
    const size = this.ctx.sampleRate;
    this.noise = this.ctx.createBuffer(1, size, size);
    const data = this.noise.getChannelData(0);
    for (let i = 0; i < size; i += 1) data[i] = Math.random() * 2 - 1;
  }

  setMuted(muted: boolean): void {
    this.muted = muted;
    if (this.master) this.master.gain.value = muted ? 0 : 0.5;
  }

  dispose(): void {
    void this.ctx?.close();
    this.ctx = null;
    this.master = null;
  }

  private tone({ freq, endFreq, duration, type = 'sine', volume = 0.2, delay = 0 }: ToneOptions): void {
    if (!this.ctx || !this.master || this.muted) return;
    const start = this.ctx.currentTime + delay;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, start);
    if (endFreq) osc.frequency.exponentialRampToValueAtTime(endFreq, start + duration);
    gain.gain.setValueAtTime(volume, start);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
    osc.connect(gain).connect(this.master);
    osc.start(start);
    osc.stop(start + duration + 0.02);
  }

  private burst({ duration, from, to, volume, delay = 0, q = 2 }: NoiseOptions): void {
    if (!this.ctx || !this.master || !this.noise || this.muted) return;
    const start = this.ctx.currentTime + delay;
    const source = this.ctx.createBufferSource();
    const filter = this.ctx.createBiquadFilter();
    const gain = this.ctx.createGain();
    source.buffer = this.noise;
    filter.type = 'bandpass';
    filter.Q.value = q;
    filter.frequency.setValueAtTime(from, start);
    filter.frequency.exponentialRampToValueAtTime(to, start + duration);
    gain.gain.setValueAtTime(volume, start);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
    source.connect(filter).connect(gain).connect(this.master);
    source.start(start, Math.random() * 0.5, duration + 0.02);
  }

  tick(step: number): void {
    this.tone({ freq: 1500 + step * 70, duration: 0.04, type: 'square', volume: 0.05 });
    this.burst({ duration: 0.03, from: 5000, to: 3000, volume: 0.1, q: 4 });
  }

  typo(): void {
    this.tone({ freq: 190, endFreq: 120, duration: 0.14, type: 'sawtooth', volume: 0.11 });
  }

  whoosh(): void {
    this.burst({ duration: 0.26, from: 900, to: 5200, volume: 0.3, q: 1.2 });
    this.tone({ freq: 1800, endFreq: 3800, duration: 0.2, type: 'triangle', volume: 0.05 });
  }

  slash(): void {
    this.burst({ duration: 0.16, from: 6500, to: 1000, volume: 0.42, q: 0.8 });
    this.tone({ freq: 3200, endFreq: 1500, duration: 0.24, type: 'triangle', volume: 0.09 });
    this.tone({ freq: 130, endFreq: 60, duration: 0.14, volume: 0.25 });
  }

  combo(combo: number): void {
    const note = PENTATONIC[Math.min(combo, 30) % PENTATONIC.length];
    this.tone({ freq: note, duration: 0.24, type: 'triangle', volume: 0.12, delay: 0.04 });
  }

  milestone(): void {
    [0, 2, 4, 5].forEach((step, i) => this.tone({ freq: PENTATONIC[step], duration: 0.34, type: 'triangle', volume: 0.14, delay: i * 0.07 }));
  }

  ultimate(): void {
    this.tone({ freq: 110, endFreq: 660, duration: 0.8, type: 'sawtooth', volume: 0.1 });
    this.burst({ duration: 0.9, from: 400, to: 6000, volume: 0.25, q: 1 });
    this.milestone();
  }

  hurt(): void {
    this.tone({ freq: 160, endFreq: 50, duration: 0.3, type: 'sawtooth', volume: 0.22 });
    this.burst({ duration: 0.2, from: 900, to: 180, volume: 0.35 });
  }

  comboBreak(): void {
    [0, 0.04, 0.09].forEach(delay => this.burst({ duration: 0.09, from: 4200, to: 2400, volume: 0.17, delay, q: 6 }));
  }

  lose(): void {
    [4, 3, 1, 0].forEach((step, i) => this.tone({ freq: PENTATONIC[step] / 2, duration: 0.46, type: 'triangle', volume: 0.14, delay: i * 0.16 }));
  }

  finish(): void {
    [0, 2, 3, 4, 5].forEach((step, i) => this.tone({ freq: PENTATONIC[step], duration: 0.4, type: 'triangle', volume: 0.13, delay: i * 0.09 }));
  }
}
