import { useEffect, useState } from 'react';

const SETTLE_TIMEOUT_MS = 900;
const SETTLE_STABLE_FRAMES = 5;
/** Chiều cao thanh điều hướng cố định: phần tử nằm dưới nó coi như chưa thấy. */
const NAVBAR_HEIGHT_PX = 88;
const TALL_TARGET_RATIO = 0.7;

export interface ViewportSize {
  width: number;
  height: number;
}

export interface TargetBox {
  top: number;
  left: number;
  width: number;
  height: number;
}

const toBox = (rect: DOMRect): TargetBox => ({ top: rect.top, left: rect.left, width: rect.width, height: rect.height });

const sameBox = (a: TargetBox | null, b: TargetBox | null): boolean => {
  if (a === null || b === null) return a === b;
  return (
    Math.abs(a.top - b.top) < 0.5 &&
    Math.abs(a.left - b.left) < 0.5 &&
    Math.abs(a.width - b.width) < 0.5 &&
    Math.abs(a.height - b.height) < 0.5
  );
};

const isVisible = (element: Element): boolean => {
  const rect = element.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0 && window.getComputedStyle(element).visibility !== 'hidden';
};

/** Phần tử đầu tiên đang thật sự hiển thị; phần tử ẩn theo màn hình (`hidden md:flex`) có kích thước 0. */
export const findTarget = (keys: readonly string[]): { element: Element; key: string } | null => {
  for (const key of keys) {
    const element = document.querySelector(`[data-tour="${key}"]`);
    if (element && isVisible(element)) return { element, key };
  }
  return null;
};

const prefersReducedMotion = (): boolean => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

const bringIntoView = (element: Element, alwaysScroll: boolean): void => {
  const rect = element.getBoundingClientRect();
  const inView = rect.top >= NAVBAR_HEIGHT_PX && rect.bottom <= window.innerHeight;
  // Trong hộp thoại có thanh cuộn riêng: nằm trong màn hình chưa chắc đã thấy nên luôn cuộn.
  if (inView && !alwaysScroll) return;
  const isTall = rect.height > window.innerHeight * TALL_TARGET_RATIO;
  element.scrollIntoView({ block: isTall ? 'start' : 'center', behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
};

export interface TargetTracking {
  box: TargetBox | null;
  /** Điểm neo thực sự được dùng; null khi thẻ nằm giữa màn hình. */
  target: string | null;
  viewport: ViewportSize;
  /** false trong lúc đang cuộn tới vùng, thẻ chưa nên hiện. */
  settled: boolean;
}

/** Cuộn vùng vào tầm nhìn, chờ cuộn xong rồi đo và bám theo vùng khi cuộn, đổi cỡ. */
export const useTargetRect = (keys: readonly string[], alwaysScroll: boolean): TargetTracking => {
  const [box, setBox] = useState<TargetBox | null>(null);
  const [target, setTarget] = useState<string | null>(null);
  const [settled, setSettled] = useState(false);
  const [viewport, setViewport] = useState<ViewportSize>(() => ({ width: window.innerWidth, height: window.innerHeight }));
  const keyList = keys.join('|');

  useEffect(() => {
    const found = keyList ? findTarget(keyList.split('|')) : null;
    setSettled(false);
    setTarget(found?.key ?? null);
    if (!found) {
      setBox(null);
      setSettled(true);
      return;
    }

    let element = found.element;
    let frame = 0;
    let settleFrame = 0;
    let observer: ResizeObserver | null = null;
    let tracking = false;

    const measure = () => {
      frame = 0;
      if (!element.isConnected) {
        const again = findTarget(keyList.split('|'));
        if (!again) {
          setBox(null);
          return;
        }
        element = again.element;
        observer?.disconnect();
        observer?.observe(element);
      }
      const next = toBox(element.getBoundingClientRect());
      setBox(previous => (sameBox(previous, next) ? previous : next));
    };

    // Gộp theo khung hình: cuộn nhanh không tạo setState thừa.
    const schedule = () => {
      if (tracking && frame === 0) frame = window.requestAnimationFrame(measure);
    };

    bringIntoView(element, alwaysScroll);
    const startedAt = performance.now();
    let last = toBox(element.getBoundingClientRect());
    let stableFrames = 0;
    const waitForSettle = () => {
      const current = toBox(element.getBoundingClientRect());
      stableFrames = sameBox(last, current) ? stableFrames + 1 : 0;
      last = current;
      if (stableFrames < SETTLE_STABLE_FRAMES && performance.now() - startedAt < SETTLE_TIMEOUT_MS) {
        settleFrame = window.requestAnimationFrame(waitForSettle);
        return;
      }
      tracking = true;
      measure();
      setSettled(true);
    };
    settleFrame = window.requestAnimationFrame(waitForSettle);

    if (typeof ResizeObserver !== 'undefined') {
      observer = new ResizeObserver(schedule);
      observer.observe(element);
    }
    window.addEventListener('resize', schedule);
    // capture: sự kiện cuộn của khung có thanh cuộn riêng (hộp thoại) không nổi bọt lên window.
    window.addEventListener('scroll', schedule, true);

    return () => {
      window.cancelAnimationFrame(frame);
      window.cancelAnimationFrame(settleFrame);
      observer?.disconnect();
      window.removeEventListener('resize', schedule);
      window.removeEventListener('scroll', schedule, true);
    };
  }, [keyList, alwaysScroll]);

  // Bước giữa màn hình không có vùng để theo dõi nhưng vẫn cần cỡ màn mới nhất khi xoay máy.
  useEffect(() => {
    const onResize = () =>
      setViewport(previous =>
        previous.width === window.innerWidth && previous.height === window.innerHeight
          ? previous
          : { width: window.innerWidth, height: window.innerHeight }
      );
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  return { box, target, viewport, settled };
};
