// Vòng lặp requestAnimationFrame, co giãn canvas theo khung và mật độ điểm ảnh; dọn sạch khi trang rời đi.
import type { PhiKiemEngine } from './engine';
import { renderFrame } from './renderer';

const MAX_DPR = 2;
/** Khung bị trễ quá dài (đổi tab, máy khựng) không được làm chữ nhảy cóc. */
const MAX_FRAME_SECONDS = 0.05;
/** Trung bình trên chừng này khung chậm hơn ~45 khung/giây thì hạ một bậc chất lượng. */
const SAMPLE_FRAMES = 45;
const SLOW_FRAME_SECONDS = 1 / 45;
// Màn hình hoặc khung nhúng có thể khóa 30 khung/giây dù máy thừa sức, nên chỉ hạ nhẹ để chữ không bị mờ oan.
const RENDER_SCALES = [1, 0.8];

export class GameRunner {
  private raf = 0;
  private last = 0;
  private frameSum = 0;
  private frameCount = 0;
  private scaleIndex = 0;
  private readonly observer: ResizeObserver;
  private readonly ctx: CanvasRenderingContext2D | null;

  constructor(
    private readonly canvas: HTMLCanvasElement,
    private readonly host: HTMLElement,
    private readonly engine: PhiKiemEngine
  ) {
    // Nền vẽ kín khung nên bỏ kênh alpha để trình duyệt ghép lớp nhanh hơn.
    this.ctx = canvas.getContext('2d', { alpha: false });
    this.observer = new ResizeObserver(() => this.resize());
  }

  start(): void {
    this.resize();
    this.engine.prebuild();
    this.observer.observe(this.host);
    this.last = performance.now();
    this.raf = requestAnimationFrame(this.frame);
  }

  dispose(): void {
    cancelAnimationFrame(this.raf);
    this.observer.disconnect();
    this.engine.audio.dispose();
  }

  private resize(): void {
    const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR);
    const width = this.host.clientWidth;
    const height = this.host.clientHeight;
    if (!width || !height) return;
    const pixelW = Math.round(width * dpr);
    const pixelH = Math.round(height * dpr);
    if (this.engine.w === width && this.engine.h === height && this.canvas.width === pixelW) return;
    this.engine.resize(width, height, dpr);
    this.applyScale();
    if (this.ctx) renderFrame(this.ctx, this.engine);
  }

  /** Chỉ đổi độ phân giải canvas, giữ nguyên sprite và cảnh nền nên không gây khựng khi hạ chất lượng. */
  private applyScale(): void {
    const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR) * RENDER_SCALES[this.scaleIndex];
    this.canvas.width = Math.round(this.host.clientWidth * dpr);
    this.canvas.height = Math.round(this.host.clientHeight * dpr);
    this.ctx?.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  private adaptQuality(seconds: number): void {
    this.frameSum += seconds;
    this.frameCount += 1;
    if (this.frameCount < SAMPLE_FRAMES) return;
    const slow = this.frameSum / this.frameCount > SLOW_FRAME_SECONDS;
    this.frameSum = 0;
    this.frameCount = 0;
    if (!slow) return;
    if (this.engine.backdrop.lowDetail && this.scaleIndex < RENDER_SCALES.length - 1) {
      this.scaleIndex += 1;
      this.applyScale();
    }
    this.engine.backdrop.lowDetail = true;
  }

  private frame = (now: number): void => {
    const elapsed = (now - this.last) / 1000;
    const dt = Math.min(MAX_FRAME_SECONDS, elapsed);
    this.last = now;
    if (this.engine.phase === 'done') return;
    this.raf = requestAnimationFrame(this.frame);
    if (this.engine.paused || !this.ctx) return;
    // Bỏ khung trễ do đổi tab hay tạm dừng, chúng không phản ánh tốc độ vẽ.
    if (elapsed < MAX_FRAME_SECONDS * 2) this.adaptQuality(elapsed);
    this.engine.update(dt);
    renderFrame(this.ctx, this.engine);
  };
}
