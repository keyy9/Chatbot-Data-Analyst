import React, { useEffect, useState } from "react";
import { Award, RefreshCw, AlertTriangle } from "lucide-react";
import { evaluationApi, ApiError } from "../lib/apiClient";
import type { BenchmarkEvalRun } from "../types/benchmark";
import { useAuthStore } from "../store/authStore";

const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

const STATUS_STYLE: Record<string, string> = {
  correct: "bg-success/10 text-success border border-success/20",
  partial: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  wrong: "bg-danger/10 text-danger border border-danger/20"
};

export const BenchmarkEvalPanel: React.FC<{ refreshKey?: number }> = ({ refreshKey = 0 }) => {
  const { user } = useAuthStore();
  const [run, setRun] = useState<BenchmarkEvalRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user?.userId) return;
    setLoading(true);
    setError(null);
    evaluationApi
      .getLatestBenchmarkEval(user.userId)
      .then(setRun)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load evaluation results."))
      .finally(() => setLoading(false));
  }, [user?.userId, refreshKey]);

  if (loading) {
    return (
      <div className="bg-surface border border-border shadow-lg p-5 rounded-xl flex items-center gap-2 text-text-muted text-xs font-sans">
        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
        Loading SQL-correctness benchmark results...
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-surface border border-border shadow-lg p-5 rounded-xl flex items-center gap-2 text-amber-400 text-xs font-sans">
        <AlertTriangle className="w-3.5 h-3.5" />
        {error}
      </div>
    );
  }

  if (!run) return null;

  const mistakes = run.results.filter((r) => r.status !== "correct");

  return (
    <div className="bg-surface border border-border shadow-lg rounded-xl p-5 space-y-5 font-sans">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Award className="w-4 h-4 text-accent" />
          <h3 className="text-sm font-bold text-white">Real SQL-Correctness Benchmark Results</h3>
        </div>
        <span className="text-[10px] text-text-muted font-mono">
          {run.total_questions} questions &middot; run {new Date(run.run_at).toLocaleString()}
        </span>
      </div>
      <p className="text-[11px] text-text-muted -mt-3">
        Live results from <code className="text-text-muted">run_benchmark.py</code>, scoring generated SQL against a
        known-good gold answer for each question - distinct from the "Benchmark Performance Simulator" above, which
        is a local demo simulation.
      </p>

      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-surface-2 border border-border rounded-lg p-3">
          <span className="text-[9px] uppercase font-bold text-text-muted block">Accuracy Score</span>
          <span className="text-lg font-extrabold text-white font-mono">{pct(run.accuracy_score)}</span>
        </div>
        <div className="bg-surface-2 border border-border rounded-lg p-3">
          <span className="text-[9px] uppercase font-bold text-success block">Correct</span>
          <span className="text-lg font-extrabold text-white font-mono">{run.correct}</span>
        </div>
        <div className="bg-surface-2 border border-border rounded-lg p-3">
          <span className="text-[9px] uppercase font-bold text-amber-400 block">Partial</span>
          <span className="text-lg font-extrabold text-white font-mono">{run.partial}</span>
        </div>
        <div className="bg-surface-2 border border-border rounded-lg p-3">
          <span className="text-[9px] uppercase font-bold text-danger block">Wrong</span>
          <span className="text-lg font-extrabold text-white font-mono">{run.wrong}</span>
        </div>
      </div>

      {/* Non-correct results detail */}
      {mistakes.length > 0 && (
        <div>
          <span className="text-[10px] uppercase font-bold text-text-muted tracking-wider block mb-2">
            Partial / Wrong Answers ({mistakes.length})
          </span>
          <div className="space-y-1.5 max-h-64 overflow-y-auto">
            {mistakes.map((r, idx) => (
              <div key={idx} className="bg-surface-2 border border-border rounded-lg p-2.5 text-[11px] space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-text font-semibold">{r.question}</span>
                  <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase ${STATUS_STYLE[r.status]}`}>
                    {r.status}
                  </span>
                </div>
                <span className="text-text-faint text-[10px] font-mono block truncate">{r.sql_generated}</span>
                <span className="text-text-faint text-[10px] font-mono block truncate">{r.actual_answer}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
