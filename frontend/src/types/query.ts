export interface QueryLog {
  id: string;
  /** Display name of the author, resolved from the `users` table. */
  user: string;
  userEmail?: string | null;
  /** True when the author's account no longer exists or was soft-deleted. */
  userDeleted?: boolean;
  question: string;
  generatedSql: string;
  executionTimeMs: number;
  status: 'Success' | 'Failed';
  timestamp: string;
  errorDetail?: string;
  aiExplanation?: string;
  resultPreview?: {
    columns: string[];
    rows: Record<string, any>[];
  };
  clarificationHistory?: {
    originalPrompt: string;
    clarificationQuestion: string;
    userResponse: string;
    finalPrompt: string;
  };
  guardrailStatus?: 'Allowed' | 'Blocked';
  guardrailReason?: string;
}
