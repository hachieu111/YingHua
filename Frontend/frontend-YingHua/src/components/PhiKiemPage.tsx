import React, { useCallback, useRef, useState } from 'react';
import { Link } from 'react-router';
import { ApiError, errorMessage } from '../api/client';
import { BladeRound, BladeRoundRequest, BladeSession, buildBladeRound, getBladeBest, getWeakRadicals, submitBladeSession } from '../api/gamification';
import { loadPrefs, savePrefs } from '../game/phikiem/prefs';
import type { GameOutcome, GamePrefs } from '../game/phikiem/types';
import { TAB_PATHS } from '../routes';
import { useApiResource } from '../utils/useApiResource';
import { notifyActivity } from '../utils/useStreak';
import { PhiKiemLobby } from './PhiKiemLobby';
import { PhiKiemResult } from './PhiKiemResult';
import { PhiKiemStage } from './PhiKiemStage';

type Phase = 'lobby' | 'playing' | 'submitting' | 'result' | 'submit-error';

/** Ván ngắn hơn mức này chưa thực sự chơi nên không nộp. */
const MIN_SUBMIT_MS = 1000;

const ROUND_ERROR_MESSAGE: Record<string, string> = {
  NOT_ENOUGH_WORDS_FOR_GAME: 'Chưa đủ chữ để dựng ván này. Hãy chọn cấp khác hoặc lưu thêm từ vào Sổ tay.',
  MINIGAME_ROUND_NOT_FOUND: 'Không tìm thấy ván chơi này. Hãy bắt đầu ván mới.',
  MINIGAME_ROUND_USED: 'Ván này đã được nộp rồi. Hãy chơi ván mới.',
  MINIGAME_ROUND_EXPIRED: 'Ván chơi đã hết hạn nên không được tính. Hãy chơi lại một ván mới.',
  INVALID_MINIGAME_RESULT: 'Kết quả ván chơi không hợp lệ nên không được tính. Hãy chơi lại một ván mới.'
};

const gameErrorMessage = (err: unknown): string =>
  err instanceof ApiError && ROUND_ERROR_MESSAGE[err.code] ? ROUND_ERROR_MESSAGE[err.code] : errorMessage(err);

/** Lỗi ván đã hỏng thì gửi lại vô ích; chỉ cho gửi lại khi là lỗi mạng hoặc máy chủ. */
const canResubmit = (err: unknown): boolean => !(err instanceof ApiError && ROUND_ERROR_MESSAGE[err.code]);

/** Mini-game Phi Kiếm Trảm Tự: gõ pinyin chém chữ rơi theo band HSK hoặc bộ thủ hay quên (F16.01). */
export const PhiKiemPage: React.FC = () => {
  const best = useApiResource(signal => getBladeBest(signal), []);
  const weak = useApiResource(signal => getWeakRadicals(signal), []);
  const [phase, setPhase] = useState<Phase>('lobby');
  const [prefs, setPrefs] = useState<GamePrefs>(loadPrefs);
  const [round, setRound] = useState<BladeRound | null>(null);
  const [result, setResult] = useState<BladeSession | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryable, setRetryable] = useState(false);
  const lastRequest = useRef<BladeRoundRequest | null>(null);
  const lastOutcome = useRef<GameOutcome | null>(null);

  const updatePrefs = useCallback((next: GamePrefs) => {
    setPrefs(next);
    savePrefs(next);
  }, []);

  const onSoundChange = useCallback((sound: boolean) => {
    setPrefs(current => (current.sound === sound ? current : { ...current, sound }));
  }, []);

  const start = async (request: BladeRoundRequest) => {
    setBusy(true);
    setError(null);
    lastRequest.current = request;
    try {
      const next = await buildBladeRound(request);
      setResult(null);
      setRound(next);
      setPhase('playing');
    } catch (err) {
      setError(gameErrorMessage(err));
      setPhase('lobby');
    } finally {
      setBusy(false);
    }
  };

  const submit = useCallback((target: BladeRound, outcome: GameOutcome) => {
    setPhase('submitting');
    setError(null);
    submitBladeSession({ round_id: target.round_id, events: outcome.events, typos: outcome.typos, duration_ms: outcome.durationMs })
      .then(session => {
        setResult(session);
        setPhase('result');
        notifyActivity();
      })
      .catch(err => {
        setError(gameErrorMessage(err));
        setRetryable(canResubmit(err));
        setPhase('submit-error');
      });
  }, []);

  const finish = useCallback(
    (outcome: GameOutcome) => {
      if (!round) return;
      savePrefs(prefs);
      if (outcome.durationMs < MIN_SUBMIT_MS) {
        setError('Ván kết thúc quá sớm nên không được tính. Hãy chơi lại nhé.');
        setPhase('lobby');
        return;
      }
      lastOutcome.current = outcome;
      submit(round, outcome);
    },
    [round, prefs, submit]
  );

  const toLobby = () => {
    setError(null);
    setPhase('lobby');
    best.reload();
    weak.reload();
  };

  const replay = () => {
    if (lastRequest.current) void start(lastRequest.current);
  };

  return (
    <div className="relative min-h-[calc(100dvh-5rem)] bg-gradient-to-b from-[#120818] via-[#2a0f36] to-[#5a1a4c] text-white">
      <div className="w-full max-w-[860px] mx-auto px-4 md:px-8 py-6 flex flex-col gap-5">
        <Link to={TAB_PATHS.leaderboard} className="text-xs font-bold text-[#ffb7d5] hover:underline w-fit">
          ← Về bảng xếp hạng
        </Link>
        {phase === 'lobby' && <PhiKiemLobby best={best.data} weak={weak} prefs={prefs} busy={busy} error={error} onPrefs={updatePrefs} onStart={request => void start(request)} />}
        {phase === 'submitting' && <p className="py-20 text-center text-sm text-white/70" role="status">Đang chấm điểm...</p>}
        {phase === 'result' && result && <PhiKiemResult result={result} onAgain={replay} onChangeBand={toLobby} />}
        {phase === 'submit-error' && (
          <div className="py-16 flex flex-col items-center gap-4 text-center">
            <span className="material-symbols-outlined text-[44px] text-[#ff9aa8]">error</span>
            <p role="alert" className="text-sm font-semibold text-[#ffd8e7] max-w-md">{error}</p>
            <div className="flex flex-wrap justify-center gap-3">
              {retryable && round && lastOutcome.current && (
                <button type="button" onClick={() => lastOutcome.current && submit(round, lastOutcome.current)} className="px-6 py-2.5 rounded-full bg-[#a43073] hover:bg-[#85145a] text-sm font-bold transition-colors">
                  Gửi lại kết quả
                </button>
              )}
              <button type="button" onClick={replay} className="px-6 py-2.5 rounded-full bg-white/10 hover:bg-white/20 text-sm font-bold transition-colors">
                Chơi lại
              </button>
              <button type="button" onClick={toLobby} className="px-6 py-2.5 rounded-full bg-white/10 hover:bg-white/20 text-sm font-bold transition-colors">
                Đổi cấp độ
              </button>
            </div>
          </div>
        )}
      </div>
      {phase === 'playing' && round && <PhiKiemStage key={round.round_id} round={round} prefs={prefs} onSoundChange={onSoundChange} onEnd={finish} />}
    </div>
  );
};
