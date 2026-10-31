import React, { useCallback, useEffect, useRef, useState } from 'react';
import type { BladeRound } from '../api/gamification';
import { PhiKiemEngine } from '../game/phikiem/engine';
import { loadBrushFont } from '../game/phikiem/glyphSprites';
import { GameRunner } from '../game/phikiem/runner';
import type { GameOutcome, GamePrefs, HudState } from '../game/phikiem/types';
import { PhiKiemHud } from './PhiKiemHud';
import { PhiKiemKeyboard } from './PhiKiemKeyboard';

/** Các chữ thư pháp ngoài đề bài cũng cần tải phông trước khi vẽ. */
const FIXED_BRUSH_TEXT = '双斩三连剑舞无双圣万归宗再战开';

const INITIAL_HUD: HudState = { phase: 'intro', score: 0, combo: 0, lives: 0, maxLives: 0, secondsLeft: 0, wave: 1, multiplier: 1, energy: 0, ultimate: false };

const isEditable = (target: EventTarget | null): boolean =>
  target instanceof HTMLElement && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName));

const prefersReducedMotion = (): boolean => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const hasCoarsePointer = (): boolean => window.matchMedia('(pointer: coarse)').matches;

interface StageProps {
  round: BladeRound;
  prefs: GamePrefs;
  onSoundChange: (sound: boolean) => void;
  onEnd: (outcome: GameOutcome) => void;
}

/** Sân chơi toàn màn hình: canvas do engine vẽ, HUD và bàn phím ảo là DOM (F16.01). */
export const PhiKiemStage: React.FC<StageProps> = ({ round, prefs, onSoundChange, onEnd }) => {
  const hostRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const engineRef = useRef<PhiKiemEngine | null>(null);
  const onEndRef = useRef(onEnd);
  const [hud, setHud] = useState<HudState>({ ...INITIAL_HUD, lives: round.lives, maxLives: round.lives, secondsLeft: round.seconds });
  const [ready, setReady] = useState(false);
  const [paused, setPaused] = useState(false);
  const [sound, setSound] = useState(prefs.sound);
  const [touch] = useState(hasCoarsePointer);

  useEffect(() => {
    onEndRef.current = onEnd;
  });

  useEffect(() => {
    const host = hostRef.current;
    const canvas = canvasRef.current;
    if (!host || !canvas) return;
    const engine = new PhiKiemEngine(
      round,
      prefs,
      { onHud: setHud, onEnd: outcome => onEndRef.current(outcome) },
      prefersReducedMotion(),
      Math.min(window.devicePixelRatio || 1, 2)
    );
    const runner = new GameRunner(canvas, host, engine);
    let cancelled = false;
    engineRef.current = engine;
    engine.audio.unlock();
    void loadBrushFont(round.items.map(item => item.text).join('') + FIXED_BRUSH_TEXT).then(() => {
      if (cancelled) return;
      runner.start();
      setReady(true);
    });
    return () => {
      cancelled = true;
      engineRef.current = null;
      runner.dispose();
    };
    // Ván mới luôn dựng lại cả component qua `key`, tùy chọn chỉ đọc một lần lúc bắt đầu.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [round]);

  const setGamePaused = useCallback((value: boolean) => {
    const engine = engineRef.current;
    if (!engine || engine.phase === 'done' || engine.phase === 'outro') return;
    engine.paused = value;
    if (!value) engine.audio.unlock();
    setPaused(value);
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.ctrlKey || event.metaKey || event.altKey || isEditable(event.target)) return;
      const engine = engineRef.current;
      if (!engine) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        setGamePaused(!engine.paused);
      } else if (event.key === 'Backspace') {
        event.preventDefault();
        engine.backspace();
      } else if (/^[a-zA-Z]$/.test(event.key)) {
        event.preventDefault();
        if (!event.repeat) engine.typeKey(event.key.toLowerCase());
      }
    };
    const onVisibility = () => {
      if (document.visibilityState === 'hidden') setGamePaused(true);
    };
    window.addEventListener('keydown', onKeyDown);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [setGamePaused]);

  // Khóa cuộn trang nền trong lúc chơi toàn màn hình.
  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  const toggleSound = useCallback(() => {
    setSound(value => !value);
  }, []);

  // Đồng bộ tiếng trong effect để không có tác dụng phụ trong hàm cập nhật state.
  useEffect(() => {
    engineRef.current?.audio.setMuted(!sound);
    engineRef.current?.audio.unlock();
    onSoundChange(sound);
  }, [sound, onSoundChange]);

  const pause = useCallback(() => setGamePaused(true), [setGamePaused]);
  const typeKey = useCallback((key: string) => engineRef.current?.typeKey(key), []);
  const backspace = useCallback(() => engineRef.current?.backspace(), []);

  return (
    <div className="fixed inset-0 z-[70] flex flex-col bg-[#0d0712] select-none touch-none overscroll-none">
      <div ref={hostRef} className="relative flex-1 min-h-0 overflow-hidden">
        <canvas ref={canvasRef} className="absolute inset-0 w-full h-full block" aria-label="Sân chơi Phi Kiếm Trảm Tự" />
        <PhiKiemHud hud={hud} soundOn={sound} onToggleSound={toggleSound} onPause={pause} />
        {!ready && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#0d0712] text-[#ffd8e7] text-sm font-semibold" role="status">
            Đang mài kiếm...
          </div>
        )}
        {paused && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#0d0712]/75 backdrop-blur-sm px-4">
            <div className="w-full max-w-xs rounded-3xl border border-white/10 bg-[#1b0c26] p-6 flex flex-col items-center gap-3 text-center text-white">
              <span className="font-['Ma_Shan_Zheng'] text-5xl text-[#ffd76a]">暂停</span>
              <p className="text-sm text-white/70">Đồng hồ đã dừng. Nghỉ một chút rồi chém tiếp nhé.</p>
              <button type="button" autoFocus onClick={() => setGamePaused(false)} className="w-full py-2.5 rounded-full bg-[#a43073] hover:bg-[#85145a] text-sm font-bold transition-colors">
                Chơi tiếp
              </button>
              <button
                type="button"
                onClick={() => {
                  setGamePaused(false);
                  engineRef.current?.quit();
                }}
                className="w-full py-2.5 rounded-full bg-white/10 hover:bg-white/20 text-sm font-bold transition-colors"
              >
                Dừng và nộp ván
              </button>
            </div>
          </div>
        )}
      </div>
      {touch && <PhiKiemKeyboard onKey={typeKey} onBackspace={backspace} />}
    </div>
  );
};
