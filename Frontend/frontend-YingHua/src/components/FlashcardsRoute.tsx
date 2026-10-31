import React, { useCallback } from 'react';
import { useSearchParams } from 'react-router';
import { DECK_PARAM, QUIZ_SECTION_PARAM, QUIZ_SECTION_VALUE, parseDeckKey } from '../routes';
import { FlashcardsPage } from './FlashcardsPage';

type FlashcardsPageProps = Omit<
  React.ComponentProps<typeof FlashcardsPage>,
  'focusQuiz' | 'onFocusQuizHandled' | 'initialDeck' | 'onInitialDeckHandled'
>;

/** Trang từ vựng theo URL: /tu-vung, và /tu-vung?muc=kiem-tra để cuộn tới khu kiểm tra. */
export const FlashcardsRoute: React.FC<FlashcardsPageProps> = props => {
  const [searchParams, setSearchParams] = useSearchParams();
  const focusQuiz = searchParams.get(QUIZ_SECTION_PARAM) === QUIZ_SECTION_VALUE;

  const handleFocusHandled = useCallback(() => {
    setSearchParams(
      previous => {
        const next = new URLSearchParams(previous);
        next.delete(QUIZ_SECTION_PARAM);
        return next;
      },
      { replace: true }
    );
  }, [setSearchParams]);

  const initialDeck = parseDeckKey(searchParams.get(DECK_PARAM));

  const handleDeckHandled = useCallback(() => {
    setSearchParams(
      previous => {
        const next = new URLSearchParams(previous);
        next.delete(DECK_PARAM);
        return next;
      },
      { replace: true }
    );
  }, [setSearchParams]);

  return (
    <FlashcardsPage
      {...props}
      focusQuiz={focusQuiz}
      onFocusQuizHandled={handleFocusHandled}
      initialDeck={initialDeck}
      onInitialDeckHandled={handleDeckHandled}
    />
  );
};
