export interface BenchmarkQuestion {
  id: string;
  question: string;
  expectedSql: string;
  generatedSql?: string;
  result?: 'Correct' | 'Incorrect' | 'Pending';
  responseTimeMs?: number;
  errorDetail?: string;
  expectedAnswer?: string;
  tablesUsed?: string[];
  timestamp?: string;
  resultPreview?: {
    columns: string[];
    rows: Record<string, any>[];
  };
}

export interface DailyQueryVolume {
  date: string;
  queries: number;
  successRate: number;
}

export interface BenchmarkRunHistory {
  runId: string;
  timestamp: string;
  totalQuestions: number;
  accuracy: number;
  avgResponseTimeMs: number;
}

/**
 * One provider's newest benchmark run.
 *
 * Every run scores the same questions against the same gold SQL, so accuracy
 * is comparable across providers. Cost and latency travel with it because a
 * model that is more accurate but far more expensive is a different decision.
 */
export interface ProviderBenchmark {
  model_provider: string;
  model_name: string;
  run_at: string;
  total_questions: number;
  correct: number;
  partial: number;
  wrong: number;
  accuracy_score: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_cost: number;
  avg_latency_ms: number;
}

export type PipelineOutcome = "success" | "clarification" | "blocked";

export interface PipelineEvalClassMetric {
  precision: number;
  recall: number;
  f1: number;
  support: number;
}

export interface PipelineEvalMetrics {
  labels: PipelineOutcome[];
  confusion_matrix: Record<PipelineOutcome, Record<PipelineOutcome, number>>;
  per_class: Record<PipelineOutcome, PipelineEvalClassMetric>;
  macro_avg: { precision: number; recall: number; f1: number };
  accuracy: number;
  total: number;
}

export interface PipelineEvalResultRow {
  question: string;
  expected_outcome: PipelineOutcome;
  actual_outcome: PipelineOutcome;
  detail: string;
}

export interface PipelineEvalRun {
  eval_run_id: string;
  run_at: string;
  total_questions: number;
  accuracy: number;
  metrics: PipelineEvalMetrics;
  results: PipelineEvalResultRow[];
}

export interface BenchmarkEvalResultRow {
  question: string;
  sql_generated: string;
  actual_answer: string;
  status: "correct" | "partial" | "wrong";
}

export interface BenchmarkEvalRun {
  eval_run_id: string;
  run_at: string;
  total_questions: number;
  correct: number;
  partial: number;
  wrong: number;
  accuracy_score: number;
  results: BenchmarkEvalResultRow[];
}
