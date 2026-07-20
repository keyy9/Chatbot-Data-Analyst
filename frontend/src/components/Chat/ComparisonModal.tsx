import React from "react";
import { X, AlertCircle, HelpCircle, Loader2, Zap } from "lucide-react";
import type { CompareResponse, RawProviderCompareResult } from "../../lib/apiClient";
import { PROVIDER_LABELS, PROVIDER_COLORS } from "./ModelSelector";
import { SQLToggle } from "./SQLToggle";
import { TableChart } from "../Charts/TableChart";

interface ComparisonModalProps {
  questionText: string;
  isLoading: boolean;
  result: CompareResponse | null;
  error: string | null;
  onClose: () => void;
}

const BAR_FILL: Record<string, string> = {
  groq: "#12403C",
  gemini: "#12403C"
};

function LatencyBars({ results }: { results: RawProviderCompareResult[] }) {
  const maxLatency = Math.max(...results.map((r) => r.latency_ms), 1);

  return (
    <div className="space-y-2 px-5 py-4 border-b border-slate-200 dark:border-border bg-slate-50/60 dark:bg-surface/60">
      <div className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-wider text-text-muted dark:text-text-faint">
        <Zap className="w-3 h-3" />
        Response Latency
      </div>
      {results.map((r) => {
        const widthPct = Math.max((r.latency_ms / maxLatency) * 100, 3);
        return (
          <div key={r.provider} className="flex items-center gap-3 text-[10px] font-mono">
            <span className={`w-20 flex-shrink-0 font-bold ${PROVIDER_COLORS[r.provider].text}`}>
              {PROVIDER_LABELS[r.provider]}
            </span>
            <div className="flex-1 h-2 rounded-full bg-slate-200 dark:bg-surface-hover overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${widthPct}%`, backgroundColor: BAR_FILL[r.provider] }}
              />
            </div>
            <span className="w-16 flex-shrink-0 text-right text-text-faint dark:text-text-muted">
              {Math.round(r.latency_ms)}ms
            </span>
          </div>
        );
      })}
    </div>
  );
}

function ProviderCard({ result }: { result: RawProviderCompareResult }) {
  const colors = PROVIDER_COLORS[result.provider];

  return (
    <div className="flex-1 min-w-0 rounded-xl border border-slate-200 dark:border-border bg-white dark:bg-surface-2 overflow-hidden flex flex-col">
      <div className={`px-4 py-2.5 border-b border-slate-200 dark:border-border flex items-center justify-between ${colors.bg}`}>
        <span className={`text-xs font-extrabold ${colors.text}`}>{PROVIDER_LABELS[result.provider]}</span>
        <span className="text-[9px] font-mono text-text-faint dark:text-text-muted truncate max-w-[60%]" title={result.model_name}>
          {result.model_name}
        </span>
      </div>

      <div className="p-4 space-y-3 text-xs">
        {result.status === "error" && (
          <div className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/25 rounded-lg text-red-600 dark:text-red-400">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span className="text-[11px] leading-relaxed">{result.error || "This model failed to answer."}</span>
          </div>
        )}

        {result.status === "clarification_needed" && (
          <div className="p-3 bg-amber-500/10 border border-amber-500/25 rounded-lg space-y-2">
            <div className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400 font-bold text-[11px]">
              <HelpCircle className="w-3.5 h-3.5" />
              {result.explanation || "This model needs clarification."}
            </div>
            {result.options && result.options.length > 0 && (
              <ul className="text-[10px] text-text-faint dark:text-text-muted list-disc list-inside space-y-0.5">
                {result.options.map((opt) => (
                  <li key={opt}>{opt}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {result.status === "write_preview" && (
          <div className="space-y-2">
            <div className="p-2.5 bg-amber-500/10 border border-amber-500/25 rounded-lg text-[11px] text-amber-700 dark:text-amber-400 leading-relaxed">
              {result.explanation}
            </div>
            {result.generated_sql && <SQLToggle sql={result.generated_sql} />}
          </div>
        )}

        {result.status === "success" && (
          <>
            <p className="text-slate-700 dark:text-text leading-relaxed">{result.explanation}</p>
            {result.generated_sql && <SQLToggle sql={result.generated_sql} />}
            {result.data && result.columns && result.data.length > 0 && (
              <TableChart columns={result.columns} rows={result.data} />
            )}
          </>
        )}
      </div>
    </div>
  );
}

export const ComparisonModal: React.FC<ComparisonModalProps> = ({ questionText, isLoading, result, error, onClose }) => {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white dark:bg-bg-elevated border border-slate-200 dark:border-border shadow-2xl font-sans"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-5 py-4 border-b border-slate-200 dark:border-border flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 className="text-sm font-extrabold text-slate-800 dark:text-slate-100">Model Comparison</h2>
            <p className="text-[11px] text-text-faint dark:text-text-muted mt-0.5 truncate">{questionText}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-text-muted hover:text-slate-700 dark:hover:text-text hover:bg-slate-100 dark:hover:bg-surface-hover transition-colors cursor-pointer flex-shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {isLoading && (
          <div className="flex flex-col items-center justify-center gap-3 py-16 text-text-muted dark:text-text-faint">
            <Loader2 className="w-6 h-6 animate-spin text-accent" />
            <span className="text-[11px] font-bold uppercase tracking-wider">Asking both models...</span>
          </div>
        )}

        {!isLoading && error && (
          <div className="flex items-center gap-2 p-4 m-5 bg-red-500/10 border border-red-500/25 rounded-lg text-red-600 dark:text-red-400 text-xs">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {!isLoading && !error && result && (
          <>
            <LatencyBars results={[result.results.groq, result.results.gemini]} />
            <div className="p-5 flex flex-col md:flex-row gap-4">
              <ProviderCard result={result.results.groq} />
              <ProviderCard result={result.results.gemini} />
            </div>
          </>
        )}
      </div>
    </div>
  );
};
