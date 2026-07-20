import React from "react";
import { X, Sparkles } from "lucide-react";
import type { BenchmarkQuestion } from "../../types/benchmark";

interface BenchmarkInspectModalProps {
  selectedBenchmark: BenchmarkQuestion | null;
  setSelectedBenchmark: (bq: BenchmarkQuestion | null) => void;
}

export const BenchmarkInspectModal: React.FC<BenchmarkInspectModalProps> = ({
  selectedBenchmark,
  setSelectedBenchmark,
}) => {
  if (!selectedBenchmark) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div
        onClick={() => setSelectedBenchmark(null)}
        className="absolute inset-0 bg-slate-950/70 backdrop-blur-xs transition-opacity cursor-pointer"
      ></div>

      <div className="relative w-full max-w-md bg-surface border-l border-border h-full shadow-2xl flex flex-col justify-between animate-slide-in text-text z-10 font-sans">
        <div className="px-6 py-4 border-b border-border bg-surface-2/50 flex items-center justify-between">
          <h3 className="text-sm font-bold text-text uppercase tracking-wider">
            Benchmark Question Details
          </h3>
          <button
            type="button"
            onClick={() => setSelectedBenchmark(null)}
            className="p-1.5 hover:bg-surface-hover rounded-lg text-text-muted hover:text-text transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Question Info */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span
                className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                  selectedBenchmark.result === "Correct"
                    ? "bg-success/10 text-success border border-success/20"
                    : selectedBenchmark.result === "Incorrect"
                      ? "bg-danger/10 text-danger border border-danger/20"
                      : "bg-surface-hover text-text-muted border border-border"
                }`}
              >
                {selectedBenchmark.result || "Pending"}
              </span>
              <span className="text-[10px] text-text-faint font-mono">
                ID: #{selectedBenchmark.id}
              </span>
            </div>
            <h2 className="text-sm font-bold text-text leading-snug">
              {selectedBenchmark.question}
            </h2>
          </div>

          {/* SQL Comparison */}
          <div className="grid grid-cols-1 gap-4">
            <div className="space-y-1.5">
              <h4 className="text-[10px] font-bold text-text-muted uppercase tracking-wider">
                Expected Gold SQL
              </h4>
              <pre className="bg-surface-2 border border-border p-3.5 rounded-lg font-mono text-[10px] text-text-muted overflow-x-auto whitespace-pre-wrap">
                {selectedBenchmark.expectedSql}
              </pre>
            </div>

            <div className="space-y-1.5">
              <h4 className="text-[10px] font-bold text-text-muted uppercase tracking-wider">
                Generated SQL
              </h4>
              <pre
                className={`p-3.5 rounded-lg font-mono text-[10px] overflow-x-auto whitespace-pre-wrap border ${
                  selectedBenchmark.result === "Correct"
                    ? "bg-success/5 border-success/20 text-text-muted"
                    : selectedBenchmark.result === "Incorrect"
                      ? "bg-danger/5 border-danger/20 text-text-muted"
                      : "bg-surface-hover/45 border-border text-text-muted"
                }`}
              >
                {selectedBenchmark.generatedSql || "-- No SQL generated yet"}
              </pre>
            </div>
          </div>

          {/* Accuracy & Performance Metrics */}
          <div className="grid grid-cols-3 gap-4">
            <div className="border border-border p-3 rounded-lg bg-surface-2/40">
              <span className="text-[10px] font-bold text-text-faint uppercase tracking-wider block">
                Latency
              </span>
              <span className="text-sm font-extrabold text-text block mt-1 font-mono">
                {selectedBenchmark.responseTimeMs
                  ? `${selectedBenchmark.responseTimeMs}ms`
                  : "N/A"}
              </span>
            </div>
            <div className="border border-border p-3 rounded-lg bg-surface-2/40">
              <span className="text-[10px] font-bold text-text-faint uppercase tracking-wider block">
                Tables Used
              </span>
              <span className="text-xs font-bold text-text block mt-1 truncate">
                {selectedBenchmark.tablesUsed?.join(", ") || "products, orders"}
              </span>
            </div>
            <div className="border border-border p-3 rounded-lg bg-surface-2/40">
              <span className="text-[10px] font-bold text-text-faint uppercase tracking-wider block">
                Complexity
              </span>
              <span className="text-xs font-bold text-text block mt-1 uppercase">
                {selectedBenchmark.expectedSql.includes("JOIN")
                  ? "Medium (JOIN)"
                  : "Simple"}
              </span>
            </div>
          </div>

          {/* Result Preview Comparison */}
          <div className="space-y-2">
            <h4 className="text-[10px] font-bold text-text-faint uppercase tracking-wider">
              Query Result Preview
            </h4>
            {selectedBenchmark.expectedAnswer ? (
              <div className="border border-border rounded-lg overflow-hidden bg-surface shadow-md">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-surface-2 border-b border-border font-bold text-text-faint text-[10px] uppercase">
                      <th className="py-2 px-4">Metric / Field</th>
                      <th className="py-2 px-4 font-sans">Expected Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40 text-text-muted font-mono">
                    {/* Render standard result info */}
                    <tr className="hover:bg-surface-hover/40">
                      <td className="py-2 px-4 font-bold text-text font-sans">
                        Details
                      </td>
                      <td className="py-2 px-4">
                        {selectedBenchmark.expectedAnswer}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="bg-surface-2 border border-dashed border-border text-text-muted p-6 rounded-lg text-center text-xs">
                Run the benchmark test to see generated query output.
              </div>
            )}
          </div>

          {/* AI Explanation */}
          <div className="space-y-2">
            <h4 className="text-[10px] font-bold text-text-faint uppercase tracking-wider flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5 text-accent" />
              AI Natural Language Explanation
            </h4>
            <p className="text-xs text-text-muted bg-surface-2/50 border border-border p-4 rounded-lg leading-relaxed font-medium">
              {selectedBenchmark.result === "Correct"
                ? "The AI successfully translated the natural language intent into an optimized SQL query. The generated query correctly filters and groups the database records, producing the exact matching results expected."
                : "The AI model requires review. The generated SQL query did not match the expected structure or filters, which may result in incorrect records or data aggregation discrepancies."}
            </p>
          </div>
        </div>

        {/* Close footer drawer */}
        <div className="p-4 border-t border-border bg-surface-2/45 flex justify-end">
          <button
            type="button"
            onClick={() => setSelectedBenchmark(null)}
            className="bg-surface-hover hover:bg-[#1D3F3A] border border-border text-text-muted font-bold px-4 py-2 rounded-lg text-xs shadow-md transition-all cursor-pointer"
          >
            Close Panel
          </button>
        </div>
      </div>
    </div>
  );
};
