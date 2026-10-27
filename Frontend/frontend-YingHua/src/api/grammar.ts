// Gọi API phân tích ngữ pháp (M05, F05.09): chỉ gọi khi người học bấm nút vì tốn hạn mức AI.
import { apiRequest } from './client';

export type GrammarStatus = 'ok' | 'unavailable' | 'limit_reached' | 'unanalyzable';

export interface SyntaxNode {
  label: string;
  label_vi: string;
  text: string;
  note: string | null;
  children: SyntaxNode[];
}

export interface GrammarPoint {
  pattern: string;
  name: string;
  explanation: string;
  example_zh: string;
  example_vi: string;
}

export interface GrammarResult {
  status: GrammarStatus;
  bubble_id: number;
  sentence: string;
  cached: boolean;
  message: string | null;
  ai_label: string | null;
  tree: SyntaxNode[];
  points: GrammarPoint[];
}

export function analyzeBubbleGrammar(bubbleId: number, signal?: AbortSignal): Promise<GrammarResult> {
  return apiRequest<GrammarResult>(`/bubbles/${bubbleId}/grammar`, { method: 'POST', signal });
}
