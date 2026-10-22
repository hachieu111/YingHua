export type NavigationTab = 
  | 'reader' 
  | 'catalog' 
  | 'library' 
  | 'flashcards' 
  | 'leaderboard' 
  | 'profile';

export interface VocabularyItem {
  id: string;
  hanzi: string;
  pinyin: string;
  sinoVietnamese: string;
  vietnamese: string;
  hskLevel: number;
  comicSource: string;
  status: 'mastered' | 'reviewing' | 'needs_review';
  isStarred: boolean;
  exampleSentence?: {
    hanzi: string;
    pinyin: string;
    vietnamese: string;
  };
}

export interface SpeechBubble {
  id: string;
  top: string; // e.g. "14.5%"
  left?: string;
  right?: string;
  bottom?: string;
  width: string;
  height: string;
  type: 'dialogue' | 'narration' | 'grammar';
  hanzi: string;
  pinyin: string;
  vietnamese: string;
  locationLabel: string;
  vocabChips: { word: string; meaning: string }[];
}

export interface ComicPage {
  id: string;
  pageNumber: number;
  title: string;
  imageSrc: string;
  bubbles: SpeechBubble[];
  vocabulary: {
    hanzi: string;
    pinyin: string;
    vietnamese: string;
  }[];
  grammarSpotlight?: {
    pattern: string;
    description: string;
    exampleHanzi: string;
    examplePinyin: string;
    exampleVietnamese: string;
  };
}

export interface ComicSeries {
  id: string;
  title: string;
  chineseTitle: string;
  author: string;
  coverImage: string;
  hskLevel: string;
  genre: string;
  description: string;
  progressPercent: number;
  currentPage: number;
  totalPages: number;
  totalChapters: number;
  currentChapterTitle: string;
  savedVocabCount: number;
  rating?: number;
  isFavorite?: boolean;
  status?: 'reading' | 'completed' | 'saved';
  pages?: ComicPage[];
}

export interface LeaderboardUser {
  rank: number;
  name: string;
  avatar: string;
  hskLevel: string;
  pagesRead: number;
  exp: number;
  streakDays: number;
  vocabCount?: number;
  tag?: string;
  isCurrentUser?: boolean;
}

export interface FlashcardDeck {
  id: string;
  title: string;
  comicName: string;
  coverImage?: string;
  badge: string;
  badgeColor: string;
  vocabCount: number;
  reviewedCount: number;
  description: string;
  keyWords?: string;
}

export interface UserProfileData {
  name: string;
  chineseName: string;
  badge: string;
  hskLevel: string;
  id: string;
  vipExpiry: string;
  joinDate: string;
  email: string;
  avatar: string;
  streak: number;
  totalVocab: number;
  pagesRead: number;
  hoursLearned: number;
  weeklyProgress: {
    current: number;
    target: number;
  };
}

