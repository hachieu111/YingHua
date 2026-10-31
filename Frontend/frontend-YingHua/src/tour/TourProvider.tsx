import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { TAB_PATHS } from '../routes';
import { useSystemStatus } from '../utils/useSystemStatus';
import { HOME_TOUR } from './homeSteps';
import {
  ADMIN_TOUR,
  FLASHCARDS_TOUR,
  GAME_TOUR,
  LEADERBOARD_TOUR,
  LIBRARY_TOUR,
  PROFILE_TOUR,
  SAMPLE_TOUR,
  SHOP_TOUR
} from './pageSteps';
import { READER_TOUR } from './readerSteps';
import { TourOverlay } from './TourOverlay';
import { TourDefinition, TourId, TourStep } from './types';
import { UPLOAD_TOUR } from './uploadSteps';
import { findTarget } from './useTargetRect';
import { useTourState } from './useTourState';

const TOURS: Record<TourId, TourDefinition> = {
  home: HOME_TOUR,
  reader: READER_TOUR,
  upload: UPLOAD_TOUR,
  library: LIBRARY_TOUR,
  flashcards: FLASHCARDS_TOUR,
  leaderboard: LEADERBOARD_TOUR,
  profile: PROFILE_TOUR,
  shop: SHOP_TOUR,
  game: GAME_TOUR,
  sample: SAMPLE_TOUR,
  admin: ADMIN_TOUR
};

/** Chờ trang ổn định rồi mới mở, để tour không chen vào lúc người dùng vừa thao tác. */
const START_DELAY_MS = 800;
const REPLAY_DELAY_MS = 300;
const MODAL_RETRY_MS = 800;
// Mọi hộp thoại trong app dùng lớp nền `fixed inset-0`, kể cả hộp nằm riêng trong từng trang.
const MODAL_SELECTOR = '.fixed.inset-0:not(.pointer-events-none), [aria-modal="true"]';

interface ActiveTour {
  tour: TourDefinition;
  steps: TourStep[];
  index: number;
  neverAgain: boolean;
}

interface TourContextValue {
  /** Chạy lại tour của màn hình đang đứng; không có thì về trang chủ rồi chạy. */
  replay: () => void;
  setPageTour: (id: TourId | null) => void;
  setModalTour: (id: TourId | null) => void;
}

const TourContext = createContext<TourContextValue | null>(null);

export const useTour = (): TourContextValue => {
  const value = useContext(TourContext);
  if (!value) throw new Error('useTour phải nằm trong TourProvider');
  return value;
};

/** Báo trang đang có tour nào; truyền null khi dữ liệu trang chưa tải xong. */
export const useTourPage = (id: TourId | null): void => {
  const { setPageTour } = useTour();
  useEffect(() => {
    setPageTour(id);
    return () => setPageTour(null);
  }, [id, setPageTour]);
};

/** Báo hộp thoại có tour riêng đang mở; đóng hộp thì tour của hộp cũng đóng. */
export const useTourModal = (id: TourId, open: boolean): void => {
  const { setModalTour } = useTour();
  useEffect(() => {
    if (!open) return;
    setModalTour(id);
    return () => setModalTour(null);
  }, [id, open, setModalTour]);
};

const resolveSteps = (tour: TourDefinition, isLoggedIn: boolean, isReplay: boolean): TourStep[] => {
  const available = tour.steps.filter(step => {
    if (step.audience === 'guest' && isLoggedIn) return false;
    if (step.audience === 'user' && !isLoggedIn) return false;
    if (step.welcome) return !isReplay;
    return step.targets.length === 0 || findTarget(step.targets) !== null;
  });
  return available.some(step => !step.welcome) ? available : [];
};

interface TourProviderProps {
  isLoggedIn: boolean;
  children: React.ReactNode;
}

/** Điều phối tour: quyết định khi nào mở, giữ bước hiện tại, ghi nhận đã xem. */
export const TourProvider: React.FC<TourProviderProps> = ({ isLoggedIn, children }) => {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { maintenance_mode: maintenance } = useSystemStatus();
  const { dismissed, markSeen } = useTourState(isLoggedIn);
  const [pageTour, setPageTour] = useState<TourId | null>(null);
  const [modalTour, setModalTour] = useState<TourId | null>(null);
  const [pending, setPending] = useState<TourId | null>(null);
  const [active, setActive] = useState<ActiveTour | null>(null);
  // Tour đã đóng trong phiên này không tự mở lại, kể cả khi chưa lưu được lên máy chủ.
  const handledRef = useRef<Set<TourId>>(new Set());
  const returnFocusRef = useRef<HTMLElement | null>(null);

  const closeTour = useCallback(
    (seen: boolean) => {
      if (active) {
        handledRef.current.add(active.tour.id);
        if (seen || active.neverAgain) markSeen(active.tour.id);
      }
      setActive(null);
      const focusTarget = returnFocusRef.current;
      returnFocusRef.current = null;
      if (focusTarget?.isConnected) focusTarget.focus({ preventScroll: true });
    },
    [active, markSeen]
  );
  const closeTourRef = useRef(closeTour);
  useEffect(() => {
    closeTourRef.current = closeTour;
  });

  // Điều hướng hoặc phiên đổi giữa tour (Back, hết hạn phiên): các điểm neo không còn đúng nên đóng.
  useEffect(() => {
    return () => closeTourRef.current(false);
  }, [pathname, isLoggedIn]);

  useEffect(() => {
    if (pathname !== TAB_PATHS.catalog) setPending(current => (current === 'home' ? null : current));
  }, [pathname]);

  // Hộp thoại đóng giữa tour của nó: đóng tour, hủy luôn yêu cầu xem lại đang chờ.
  useEffect(() => {
    if (modalTour) return;
    setPending(current => (current && TOURS[current].insideModal ? null : current));
    if (active?.tour.insideModal) closeTourRef.current(false);
  }, [modalTour, active]);

  useEffect(() => {
    if (active || maintenance) return;
    const isNew = (id: TourId) => dismissed !== null && !dismissed.includes(id) && !handledRef.current.has(id);
    // Hộp thoại đang mở thì chỉ xét tour của hộp đó.
    const current = modalTour ?? pageTour;
    if (!current || (pending !== current && !isNew(current))) return;
    const tour = TOURS[current];
    const isReplay = pending === current;

    let timer: ReturnType<typeof setTimeout>;
    const attempt = () => {
      if (!tour.insideModal && document.querySelector(MODAL_SELECTOR)) {
        timer = setTimeout(attempt, MODAL_RETRY_MS);
        return;
      }
      setPending(null);
      const steps = resolveSteps(tour, isLoggedIn, isReplay);
      if (steps.length === 0) return;
      returnFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      setActive({ tour, steps, index: 0, neverAgain: false });
    };
    timer = setTimeout(attempt, isReplay ? REPLAY_DELAY_MS : START_DELAY_MS);
    return () => clearTimeout(timer);
  }, [active, maintenance, dismissed, modalTour, pageTour, pending, isLoggedIn]);

  const replay = useCallback(() => {
    const current = modalTour ?? pageTour;
    setPending(current ?? 'home');
    if (!current && pathname !== TAB_PATHS.catalog) navigate(TAB_PATHS.catalog);
  }, [modalTour, pageTour, pathname, navigate]);

  const contextValue = useMemo(() => ({ replay, setPageTour, setModalTour }), [replay]);

  const goNext = () => {
    if (!active) return;
    if (active.index >= active.steps.length - 1) {
      closeTour(true);
      return;
    }
    setActive({ ...active, index: active.index + 1 });
  };

  const goBack = () => {
    if (!active) return;
    const firstIndex = active.steps[0].welcome ? 1 : 0;
    if (active.index > firstIndex) setActive({ ...active, index: active.index - 1 });
  };

  const welcomeCount = active?.steps[0].welcome ? 1 : 0;

  return (
    <TourContext.Provider value={contextValue}>
      {children}
      {active && (
        <TourOverlay
          tour={active.tour}
          step={active.steps[active.index]}
          stepNumber={active.index + 1 - welcomeCount}
          stepTotal={active.steps.length - welcomeCount}
          isLoggedIn={isLoggedIn}
          neverAgain={active.neverAgain}
          onBack={goBack}
          onNext={goNext}
          onSkip={() => closeTour(false)}
          onNeverAgain={() => closeTour(true)}
          onToggleNeverAgain={checked => setActive({ ...active, neverAgain: checked })}
        />
      )}
    </TourContext.Provider>
  );
};
