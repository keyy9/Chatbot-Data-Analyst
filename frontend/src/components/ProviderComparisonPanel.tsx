import React, { useEffect, useState } from "react";
import { AlertTriangle, GitCompare, RefreshCw, Trophy, Play } from "lucide-react";
import { evaluationApi, ApiError } from "../lib/apiClient";
import type { ProviderBenchmark } from "../types/benchmark";
import { useAuthStore } from "../store/authStore";

const pct = (n: number) => `${(n * 100).toFixed(1)}%`;
const money = (n: number) => (n > 0 ? `$${n.toFixed(6)}` : "—");
const ms = (n: number) => (n > 0 ? `${Math.round(n).toLocaleString()} ms` : "—");
const num = (n: number) => (n > 0 ? n.toLocaleString() : "—");

/**
 * Side-by-side benchmark results for each LLM provider.
 *
 * Deliberately shows cost and latency next to accuracy: the same questions and
 * the same gold SQL are used for every provider, so the accuracies compare
 * directly - but a model two points better at four times the cost is a
 * different call, and a table showing only accuracy would hide that.
 */
export const ProviderComparisonPanel: React.FC<{
  refreshKey?: number;
  onRun?: (mode: "compare") => void;
  isRunning?: boolean;
}> = ({ refreshKey = 0, onRun, isRunning = false }) => {
  const { user } = useAuthStore();
  const [providers, setProviders] = useState<ProviderBenchmark[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user?.userId) return;
    let cancelled = false;
    setError(null);
    evaluationApi
      .compareBenchmarkProviders(user.userId)
      .then((res) => { if (!cancelled) setProviders(res.providers); })
      .catch((e) => {
        if (!cancelled) setError(e instanceof ApiError ? e.message : "Failed to load provider comparison.");
      });
    return () => { cancelled = true; };
  }, [user?.userId, refreshKey]);

  if (error) {
    return (
      <div className="bg-surface border border-border shadow-lg p-5 rounded-xl flex items-center gap-2 text-amber-400 text-xs font-sans">
        <AlertTriangle className="w-3.5 h-3.5" />
        {error}
      </div>
    );
  }

  if (providers === null) {
    return (
      <div className="bg-surface border border-border shadow-lg p-5 rounded-xl flex items-center gap-2 text-text-muted text-xs font-sans">
        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
        Loading model comparison...
      </div>
    );
  }

  // Best accuracy is highlighted, but only when there is something to compare
  // against - marking a "winner" among one entry would be meaningless.
  const bestAccuracy = providers.length > 1
    ? Math.max(...providers.map((p) => p.accuracy_score))
    : -1;

  return (
    <div className="bg-surface border border-border shadow-lg rounded-xl p-5 space-y-4 font-sans">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <GitCompare className="w-4 h-4 text-accent" />
          <h3 className="text-sm font-bold text-text">Model Comparison — Groq vs Gemini</h3>
        </div>
        {onRun && (
          <button
            type="button"
            onClick={() => onRun("compare")}
            disabled={isRunning}
            className="px-3 py-1.5 text-xs font-bold rounded-lg bg-accent hover:bg-accent-hover text-white flex gap-1.5 items-center disabled:opacity-50 cursor-pointer transition-colors shadow-sm self-start sm:self-auto"
          >
            <Play className="w-3 h-3" /> {isRunning ? "Running..." : "Run Provider Comparison"}
          </button>
        )}
      </div>
      <p className="text-[11px] text-text-muted -mt-2">
        Latest run per provider. Same questions, same gold SQL, same comparator — only the model writing the SQL
        differs, so accuracy is directly comparable. Cost and latency are shown alongside because the cheapest
        adequate model is often the right choice, not the most accurate one.
      </p>

      {providers.length === 0 ? (
        <p className="text-xs text-text-muted bg-surface-2 border border-border rounded-lg p-3">
          No per-provider runs recorded yet. Run{" "}
          <code className="font-mono text-text">python -m backend.ai.evaluation.run_benchmark --compare</code>{" "}
          to benchmark every provider in turn.
        </p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-2 text-text-muted">
                <tr>
                  <th className="p-3 font-bold">Provider</th>
                  <th className="p-3 font-bold">Model</th>
                  <th className="p-3 font-bold text-right">Accuracy</th>
                  <th className="p-3 font-bold text-right">Correct</th>
                  <th className="p-3 font-bold text-right">Tokens</th>
                  <th className="p-3 font-bold text-right">Est. cost</th>
                  <th className="p-3 font-bold text-right">Avg latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {providers.map((p) => {
                  const isBest = p.accuracy_score === bestAccuracy;
                  return (
                    <tr key={p.model_provider} className={isBest ? "bg-success/5" : undefined}>
                      <td className="p-3 font-bold text-text capitalize">
                        <span className="flex items-center gap-1.5">
                          {isBest && <Trophy className="w-3 h-3 text-success" />}
                          {p.model_provider}
                        </span>
                      </td>
                      <td className="p-3 font-mono text-text-muted">{p.model_name || "—"}</td>
                      <td className={`p-3 text-right font-mono font-extrabold ${isBest ? "text-success" : "text-text"}`}>
                        {pct(p.accuracy_score)}
                      </td>
                      <td className="p-3 text-right font-mono text-text-muted">
                        {p.correct}/{p.total_questions}
                      </td>
                      <td className="p-3 text-right font-mono text-text-muted">{num(p.total_tokens)}</td>
                      <td className="p-3 text-right font-mono text-text-muted">{money(p.estimated_cost)}</td>
                      <td className="p-3 text-right font-mono text-text-muted">{ms(p.avg_latency_ms)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-text-faint font-mono">
            {providers.map((p) => (
              <span key={p.model_provider}>
                {p.model_provider}: run {new Date(p.run_at).toLocaleString()}
              </span>
            ))}
          </div>

          {providers.length === 1 && (
            <p className="text-[11px] text-amber-400">
              Only one provider has been benchmarked. Run the comparison to score the others on the same questions.
            </p>
          )}

          {providers.some((p) => p.estimated_cost === 0) && (
            <p className="text-[11px] text-amber-400">
              A provider reports $0.00 — its model is missing from the pricing table, so its cost is unknown rather
              than free.
            </p>
          )}
        </>
      )}
    </div>
  );
};
