import React, { useCallback, useEffect, useId, useRef, useState } from 'react';

interface StrokeAnimationProps {
  /** Path SVG từng nét (dữ liệu makemeahanzi, trục Y lật). */
  strokes: string[];
  /** Đường trung tuyến từng nét: danh sách điểm [x, y]. */
  medians: number[][][];
  /** Cạnh khung vuông, px. */
  size?: number;
  autoPlay?: boolean;
}

const STROKE_MS = { normal: 600, slow: 1200 } as const;
const GAP_MS = 120;

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

const medianToPath = (points: number[][] | undefined) =>
  points && points.length > 0 ? 'M' + points.map((p) => p.join(' ')).join(' L') : '';

const StrokeAnimation: React.FC<StrokeAnimationProps> = ({ strokes, medians, size = 160, autoPlay = false }) => {
  const uid = useId().replace(/:/g, '');
  const groupRefs = useRef<(SVGGElement | null)[]>([]);
  const lineRefs = useRef<(SVGPathElement | null)[]>([]);
  const runRef = useRef(0);
  const animsRef = useRef<Animation[]>([]);
  const [slow, setSlow] = useState(false);
  const slowRef = useRef(false);
  const [current, setCurrent] = useState(strokes.length);

  const total = strokes.length;

  const cancelAll = useCallback(() => {
    runRef.current += 1;
    animsRef.current.forEach((a) => a.cancel());
    animsRef.current = [];
  }, []);

  const showAll = useCallback(() => {
    groupRefs.current.forEach((g) => {
      if (g) g.style.visibility = 'visible';
    });
    lineRefs.current.forEach((l) => {
      if (l) l.style.strokeDasharray = '';
    });
    setCurrent(total);
  }, [total]);

  const play = useCallback(async () => {
    cancelAll();
    const my = runRef.current;
    groupRefs.current.forEach((g) => {
      if (g) g.style.visibility = 'hidden';
    });
    setCurrent(0);
    for (let i = 0; i < total; i += 1) {
      if (my !== runRef.current) return;
      const line = lineRefs.current[i];
      const group = groupRefs.current[i];
      if (!line || !group) continue;
      let len = 0;
      try {
        len = line.getTotalLength();
      } catch {
        len = 0;
      }
      group.style.visibility = 'visible';
      setCurrent(i + 1);
      const duration = slowRef.current ? STROKE_MS.slow : STROKE_MS.normal;
      if (len > 0 && typeof line.animate === 'function') {
        line.style.strokeDasharray = String(len);
        const anim = line.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], {
          duration,
          easing: 'ease-in-out',
          fill: 'forwards'
        });
        animsRef.current.push(anim);
        await anim.finished.catch(() => undefined);
      } else {
        await sleep(duration);
      }
      await sleep(GAP_MS);
    }
  }, [cancelAll, total]);

  useEffect(() => {
    if (autoPlay && !prefersReducedMotion()) {
      void play();
    } else {
      showAll();
    }
    return cancelAll;
  }, [autoPlay, play, showAll, cancelAll, strokes, medians]);

  if (strokes.length === 0) return null;

  const toggleSpeed = () => {
    slowRef.current = !slowRef.current;
    setSlow(slowRef.current);
  };

  return (
    <div className="flex flex-col items-center gap-1.5 shrink-0">
      <svg
        viewBox="0 0 1024 1024"
        width={size}
        height={size}
        className="bg-white border border-slate-200 rounded-xl"
        role="img"
        aria-label="Hoạt ảnh thứ tự nét viết"
      >
        <rect x={0} y={0} width={1024} height={1024} fill="none" stroke="#ccc" strokeWidth={6} />
        <line x1={0} y1={0} x2={1024} y2={1024} stroke="#eee" strokeWidth={4} />
        <line x1={1024} y1={0} x2={0} y2={1024} stroke="#eee" strokeWidth={4} />
        <g transform="scale(1,-1) translate(0,-900)">
          <defs>
            {strokes.map((d, i) => (
              <clipPath key={i} id={`clip${uid}-${i}`}>
                <path d={d} />
              </clipPath>
            ))}
          </defs>
          {strokes.map((d, i) => (
            <path key={`outline-${i}`} d={d} fill="#e6e6e6" />
          ))}
          {strokes.map((_, i) => (
            <g
              key={`stroke-${i}`}
              ref={(el) => {
                groupRefs.current[i] = el;
              }}
              clipPath={`url(#clip${uid}-${i})`}
            >
              <path
                ref={(el) => {
                  lineRefs.current[i] = el;
                }}
                d={medianToPath(medians[i])}
                fill="none"
                stroke="#111"
                strokeWidth={180}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </g>
          ))}
        </g>
      </svg>
      <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
        <span className="font-mono">
          Nét {current}/{total}
        </span>
        <button
          type="button"
          onClick={() => void play()}
          className="flex items-center gap-0.5 px-2 py-0.5 rounded-full bg-[#a43073]/10 text-[#a43073] font-bold hover:bg-[#a43073]/20 transition-colors"
          aria-label="Phát lại hoạt ảnh nét viết"
        >
          <span className="material-symbols-outlined text-[14px]">replay</span>
          <span>Phát lại</span>
        </button>
        <button
          type="button"
          onClick={toggleSpeed}
          className="px-2 py-0.5 rounded-full border border-slate-200 hover:bg-slate-100 transition-colors"
          aria-pressed={slow}
        >
          {slow ? 'Chậm' : 'Thường'}
        </button>
      </div>
    </div>
  );
};

export default StrokeAnimation;
