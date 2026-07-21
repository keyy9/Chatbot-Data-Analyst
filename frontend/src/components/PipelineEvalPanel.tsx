import React, { useEffect, useState } from "react";
import { Grid3x3, RefreshCw, AlertTriangle } from "lucide-react";
import { evaluationApi, ApiError } from "../lib/apiClient";
import type { PipelineEvalRun, PipelineOutcome } from "../types/benchmark";
import { useAuthStore } from "../store/authStore";

const OUTCOME_LABEL: Record<PipelineOutcome, string> = {
  success: "Success",
  clarification: "Clarification",
  blocked: "Blocked"
};

const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

export const PipelineEvalPanel: React.FC = () => {
  const { user } = useAuthStore();
  const [run, setRun] = useState<PipelineEvalRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user?.userId) return;
    setLoading(true);
    evaluationApi
      .getLatestPipelineEval(user.userId)
      .then(setRun)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load evaluation results."))
      .finally(() => setLoading(false));
  }, [user?.userId]);

  if (loading) {
    return (
      <div className="bg-surface border border-border shadow-lg p-5 rounded-xl flex items-center gap-2 text-text-muted text-xs font-sans">
        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
        Loading pipeline routing evaluation...
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

  const { labels, confusion_matrix, per_class, macro_avg } = run.metrics;
  const mismatches = run.results.filter((r) => r.expected_outcome !== r.actual_outcome);

  return (
    <div className="bg-surface border border-border shadow-lg rounded-xl p-5 space-y-5 font-sans">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Grid3x3 className="w-4 h-4 text-accent" />
          <h3 className="text-sm font-bold text-text">Pipeline Routing Evaluation</h3>
        </div>
        <span className="text-[10px] text-text-muted font-mono">
          {run.total_questions} questions &middot; run {new Date(run.run_at).toLocaleString()}
        </span>
      </div>
      <p className="text-[11px] text-text-muted -mt-3">
        Does each test question route to the right outcome (answered / asked for clarification / correctly
        blocked)? Distinct from SQL-correctness accuracy above - this evaluates the pipeline's routing decisions,
        not the quality of a generated SQL statement.
      </p>

      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-surface-2 border border-border rounded-lg p-3">
          <span className="text-[9px] uppercase font-bold text-text-muted block">Accuracy</span>
          <span className="text-lg font-extrabold text-text font-mono">{pct(run.metrics.accuracy)}</span>
        </div>
        <div className="bg-surface-2 border border-border rounded-lg p-3">
          <span className="text-[9px] uppercase font-bold text-text-muted block">Macro Precision</span>
          <span className="text-lg font-extrabold text-text font-mono">{pct(macro_avg.precision)}</span>
        </div>
        <div className="bg-surface-2 border border-border rounded-lg p-3">
          <span className="text-[9px] uppercase font-bold text-text-muted block">Macro Recall</span>
          <span className="text-lg font-extrabold text-text font-mono">{pct(macro_avg.recall)}</span>
        </div>
        <div className="bg-surface-2 border border-border rounded-lg p-3">
          <span className="text-[9px] uppercase font-bold text-text-muted block">Macro F1</span>
          <span className="text-lg font-extrabold text-text font-mono">{pct(macro_avg.f1)}</span>
        </div>
      </div>

      {/* Confusion matrix */}
      <div>
        <span className="text-[10px] uppercase font-bold text-text-muted tracking-wider block mb-2">
          Confusion Matrix (rows = expected, columns = actual)
        </span>
        <div className="overflow-x-auto">
          <table className="text-[11px] border-collapse">
            <thead>
              <tr>
                <th className="p-2 text-left text-text-muted font-mono text-[9px]">expected \ actual</th>
                {labels.map((l) => (
                  <th key={l} className="p-2 text-center text-text-muted font-bold border-b border-border">
                    {OUTCOME_LABEL[l]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {labels.map((expected) => (
                <tr key={expected}>
                  <td className="p-2 text-text-muted font-bold border-r border-border">{OUTCOME_LABEL[expected]}</td>
                  {labels.map((actual) => {
                    const count = confusion_matrix[expected][actual];
                    const isDiagonal = expected === actual;
                    return (
                      <td
                        key={actual}
                        className={`p-2 text-center font-mono font-bold w-20 ${
                          isDiagonal
                            ? "bg-success/15 text-success"
                            : count > 0
                              ? "bg-danger/10 text-danger"
                              : "text-text-faint"
                        }`}
                      >
                        {count}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Per-class precision/recall/F1 */}
      <div>
        <span className="text-[10px] uppercase font-bold text-text-muted tracking-wider block mb-2">
          Per-Class Precision / Recall / F1
        </span>
        <div className="overflow-x-auto">
          <table className="w-full text-[11px] border-collapse">
            <thead>
              <tr className="border-b border-border text-text-muted font-mono text-[9px] uppercase">
                <th className="p-2 text-left">Class</th>
                <th className="p-2 text-right">Precision</th>
                <th className="p-2 text-right">Recall</th>
                <th className="p-2 text-right">F1</th>
                <th className="p-2 text-right">Support</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40">
              {labels.map((l) => (
                <tr key={l}>
                  <td className="p-2 font-bold text-text">{OUTCOME_LABEL[l]}</td>
                  <td className="p-2 text-right font-mono text-text-muted">{pct(per_class[l].precision)}</td>
                  <td className="p-2 text-right font-mono text-text-muted">{pct(per_class[l].recall)}</td>
                  <td className="p-2 text-right font-mono text-text-muted">{pct(per_class[l].f1)}</td>
                  <td className="p-2 text-right font-mono text-text-muted">{per_class[l].support}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mismatches */}
      {mismatches.length > 0 && (
        <div>
          <span className="text-[10px] uppercase font-bold text-text-muted tracking-wider block mb-2">
            Misrouted Questions ({mismatches.length})
          </span>
          <div className="space-y-1.5 max-h-64 overflow-y-auto">
            {mismatches.map((m, idx) => (
              <div key={idx} className="bg-surface-2 border border-border rounded-lg p-2.5 text-[11px]">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-text font-semibold">{m.question}</span>
                  <span className="text-[9px] font-mono whitespace-nowrap">
                    <span className="text-text-muted">{OUTCOME_LABEL[m.expected_outcome]}</span>
                    {" -> "}
                    <span className="text-danger">{OUTCOME_LABEL[m.actual_outcome]}</span>
                  </span>
                </div>
                <span className="text-text-faint text-[10px] font-mono">{m.detail}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
