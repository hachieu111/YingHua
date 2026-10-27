import React, { useCallback } from 'react';
import { useSearchParams } from 'react-router';
import { QUIZ_SECTION_PARAM, QUIZ_SECTION_VALUE } from '../routes';
import { FlashcardsPage } from './FlashcardsPage';

type FlashcardsPageProps = Omit<React.ComponentProps<typeof FlashcardsPage>, 'focusQuiz' | 'onFocusQuizHandled'>;

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

  return <FlashcardsPage {...props} focusQuiz={focusQuiz} onFocusQuizHandled={handleFocusHandled} />;
};
