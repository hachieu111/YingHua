import React, { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { TourCard, TourCardActions } from './TourCard';
import { TourDefinition, TourStep, resolveTourText } from './types';
import { TargetBox, ViewportSize, useTargetRect } from './useTargetRect';

const SPOT_PADDING_PX = 6;
const CARD_GAP_PX = 14;
const EDGE_MARGIN_PX = 12;
/** Bằng breakpoint `sm`: dưới mức này thẻ thành bottom sheet. */
const MOBILE_MAX_WIDTH_PX = 640;
const FOCUSABLE = 'button:not([disabled]), input:not([disabled])';

interface TourOverlayProps extends TourCardActions {
  tour: TourDefinition;
  step: TourStep;
  stepNumber: number;
  stepTotal: number;
  isLoggedIn: boolean;
  neverAgain: boolean;
}

interface Size {
  width: number;
  height: number;
}

const clamp = (value: number, min: number, max: number): number => Math.min(Math.max(value, min), Math.max(min, max));

/** Vùng sáng thu vào trong màn hình, vùng lớn hơn màn hình vẫn thấy đủ viền. */
const spotlightOf = (box: TargetBox | null, viewport: ViewportSize): TargetBox => {
  if (!box) return { top: viewport.height / 2, left: viewport.width / 2, width: 0, height: 0 };
  const left = Math.max(EDGE_MARGIN_PX / 2, box.left - SPOT_PADDING_PX);
  const top = Math.max(EDGE_MARGIN_PX / 2, box.top - SPOT_PADDING_PX);
  const right = Math.min(viewport.width - EDGE_MARGIN_PX / 2, box.left + box.width + SPOT_PADDING_PX);
  const bottom = Math.min(viewport.height - EDGE_MARGIN_PX / 2, box.top + box.height + SPOT_PADDING_PX);
  return { top, left, width: Math.max(0, right - left), height: Math.max(0, bottom - top) };
};

/** Chọn phía còn đủ chỗ: dưới, trên, phải, trái; không phía nào đủ thì nép góc dưới phải. */
const placeCard = (spot: TargetBox, hasTarget: boolean, card: Size, viewport: ViewportSize): { x: number; y: number } => {
  const maxX = viewport.width - card.width - EDGE_MARGIN_PX;
  const maxY = viewport.height - card.height - EDGE_MARGIN_PX;
  if (!hasTarget) return { x: (viewport.width - card.width) / 2, y: (viewport.height - card.height) / 2 };
  const centeredX = clamp(spot.left + spot.width / 2 - card.width / 2, EDGE_MARGIN_PX, maxX);
  const centeredY = clamp(spot.top + spot.height / 2 - card.height / 2, EDGE_MARGIN_PX, maxY);
  const below = spot.top + spot.height + CARD_GAP_PX;
  if (below <= maxY) return { x: centeredX, y: below };
  const above = spot.top - CARD_GAP_PX - card.height;
  if (above >= EDGE_MARGIN_PX) return { x: centeredX, y: above };
  const right = spot.left + spot.width + CARD_GAP_PX;
  if (right <= maxX) return { x: right, y: centeredY };
  const left = spot.left - CARD_GAP_PX - card.width;
  if (left >= EDGE_MARGIN_PX) return { x: left, y: centeredY };
  return { x: maxX, y: maxY };
};

/** Lớp phủ tour: chặn bấm vào trang, tô sáng vùng đang giới thiệu, đặt thẻ cạnh vùng đó. */
export const TourOverlay: React.FC<TourOverlayProps> = ({ tour, step, stepNumber, stepTotal, isLoggedIn, neverAgain, ...actions }) => {
  const { box, target, viewport, settled } = useTargetRect(step.targets, tour.insideModal === true);
  const cardRef = useRef<HTMLDivElement>(null);
  const [cardSize, setCardSize] = useState<Size | null>(null);
  const titleId = useId();
  const bodyId = useId();

  const context = { isLoggedIn, target };
  const title = resolveTourText(step.title, context);
  const body = resolveTourText(step.body, context);
  const isMobile = viewport.width < MOBILE_MAX_WIDTH_PX;
  const spot = spotlightOf(box, viewport);
  const hasTarget = box !== null;

  useLayoutEffect(() => {
    const element = cardRef.current;
    if (!element) return;
    const width = element.offsetWidth;
    const height = element.offsetHeight;
    setCardSize(previous => (previous?.width === width && previous.height === height ? previous : { width, height }));
  }, [title, body, viewport, isMobile, step.welcome]);

  const visible = settled && cardSize !== null;

  useEffect(() => {
    if (visible) cardRef.current?.focus({ preventScroll: true });
  }, [visible, step.id]);

  const actionsRef = useRef(actions);
  useEffect(() => {
    actionsRef.current = actions;
  });

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const handlers: Record<string, (() => void) | undefined> = {
        Escape: actionsRef.current.onSkip,
        ArrowLeft: actionsRef.current.onBack,
        ArrowRight: actionsRef.current.onNext
      };
      const handler = handlers[event.key];
      if (handler) {
        event.preventDefault();
        event.stopPropagation();
        handler();
        return;
      }
      if (event.key !== 'Tab' || !cardRef.current) return;
      const focusable = Array.from(cardRef.current.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      const leavingStart = event.shiftKey && (active === first || active === cardRef.current);
      const leavingEnd = !event.shiftKey && active === last;
      const outside = !cardRef.current.contains(active);
      if (!leavingStart && !leavingEnd && !outside) return;
      event.preventDefault();
      (event.shiftKey ? last : first).focus();
    };
    // capture: trang phía dưới không được nhận phím trong lúc tour chạy.
    window.addEventListener('keydown', onKeyDown, true);
    return () => window.removeEventListener('keydown', onKeyDown, true);
  }, []);

  // Bottom sheet che mất vùng đang giới thiệu (vd. thanh nổi cuối trang) thì chuyển lên mép trên.
  const sheetOnTop = isMobile && hasTarget && cardSize !== null && spot.top + spot.height > viewport.height - cardSize.height - EDGE_MARGIN_PX;
  const position = !isMobile && cardSize ? placeCard(spot, hasTarget, cardSize, viewport) : null;
  const welcomeOnMobile = isMobile && !hasTarget;

  const cardClass = isMobile
    ? welcomeOnMobile
      ? 'fixed inset-x-3 top-1/2 -translate-y-1/2 rounded-3xl'
      : `fixed inset-x-0 ${sheetOnTop ? 'top-0 rounded-b-3xl' : 'bottom-0 rounded-t-3xl'}`
    : 'tour-card fixed left-0 top-0 w-[340px] rounded-3xl';
  const swallow = (event: React.SyntheticEvent) => event.stopPropagation();

  return createPortal(
    <div className="fixed inset-0 z-[120]" onClick={swallow} onMouseDown={swallow} onTouchStart={swallow}>
      <div
        aria-hidden="true"
        className="tour-spot pointer-events-none absolute left-0 top-0"
        style={{ transform: `translate(${spot.left}px, ${spot.top}px)`, width: spot.width, height: spot.height }}
      ></div>
      <div
        ref={cardRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={bodyId}
        tabIndex={-1}
        className={`${cardClass} max-h-[70vh] overflow-y-auto border border-pink-200 bg-white shadow-floating outline-none dark:border-slate-700 dark:bg-[#0f172a] ${visible ? 'opacity-100' : 'opacity-0'}`}
        style={position ? { transform: `translate(${position.x}px, ${position.y}px)` } : undefined}
      >
        <TourCard
          {...actions}
          title={title}
          body={body}
          welcome={step.welcome === true}
          stepNumber={stepNumber}
          stepTotal={stepTotal}
          finishLabel={tour.finishLabel}
          neverAgain={neverAgain}
          titleId={titleId}
          bodyId={bodyId}
        />
      </div>
    </div>,
    document.body
  );
};
