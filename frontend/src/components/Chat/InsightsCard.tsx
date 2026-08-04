import React, { useState } from "react";
import { Sparkles, TrendingUp, TrendingDown, Award, Zap, ChevronDown, ChevronUp, Copy, Check } from "lucide-react";
import type { DataInsight } from "../../types";

interface InsightsCardProps {
  insights?: DataInsight[];
  resultPreview?: {
    columns: string[];
    rows: Record<string, any>[];
  };
}

export const InsightsCard: React.FC<InsightsCardProps> = ({ insights = [], resultPreview }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [copied, setCopied] = useState(false);

  // Derive smart insights if backend insights are empty but result rows exist
  const effectiveInsights: DataInsight[] = React.useMemo(() => {
    if (insights && insights.length > 0) {
      return insights;
    }

    if (!resultPreview || !resultPreview.rows || resultPreview.rows.length === 0) {
      return [];
    }

    const { columns, rows } = resultPreview;
    const derived: DataInsight[] = [];

    // 1. Total row count insight
    derived.push({
      type: "AGGREGATION",
      title: "Data Scope",
      description: `Analyzed ${rows.length} total record${rows.length > 1 ? "s" : ""} across ${columns.length} field(s).`,
      value: rows.length,
      confidence: 1.0
    });

    // Find numeric columns for min/max/sum
    const numericCols = columns.filter((col) =>
      rows.every((r) => r[col] !== null && r[col] !== undefined && !isNaN(Number(r[col])))
    );

    const nonNumericCols = columns.filter((col) => !numericCols.includes(col));
    const primaryLabelCol = nonNumericCols[0] || columns[0];

    if (numericCols.length > 0) {
      const targetCol = numericCols[0];
      const numbers = rows.map((r) => Number(r[targetCol]));
      const maxVal = Math.max(...numbers);
      const maxRow = rows.find((r) => Number(r[targetCol]) === maxVal);
      const labelVal = maxRow && primaryLabelCol ? String(maxRow[primaryLabelCol]) : "Top Result";

      // 2. Highest performing item insight
      derived.push({
        type: "MAXIMUM",
        title: `Top ${targetCol.replace(/_/g, " ")}`,
        description: `Highest value recorded is ${labelVal} with ${maxVal.toLocaleString()}.`,
        value: maxVal,
        confidence: 0.95
      });

      // 3. Average insight if multi-row
      if (rows.length > 1) {
        const sum = numbers.reduce((a, b) => a + b, 0);
        const avg = sum / numbers.length;
        derived.push({
          type: "AVERAGE",
          title: `Average ${targetCol.replace(/_/g, " ")}`,
          description: `Mean average across all rows is ${avg.toLocaleString(undefined, { maximumFractionDigits: 2 })}.`,
          value: avg,
          confidence: 0.9
        });
      }
    }

    return derived;
  }, [insights, resultPreview]);

  if (effectiveInsights.length === 0) {
    return null;
  }

  const getInsightBadgeStyle = (type: string) => {
    const t = type.toUpperCase();
    if (t.includes("MAX") || t.includes("TOP") || t.includes("HIGH")) {
      return {
        icon: <Award className="w-3.5 h-3.5 text-amber-500" />,
        badgeBg: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20"
      };
    }
    if (t.includes("TREND") || t.includes("GROWTH")) {
      return {
        icon: <TrendingUp className="w-3.5 h-3.5 text-teal" />,
        badgeBg: "bg-teal/10 text-teal border-teal/20"
      };
    }
    if (t.includes("MIN") || t.includes("DROP") || t.includes("LOW")) {
      return {
        icon: <TrendingDown className="w-3.5 h-3.5 text-rose-500" />,
        badgeBg: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20"
      };
    }
    if (t.includes("RANK") || t.includes("SCORE")) {
      return {
        icon: <Zap className="w-3.5 h-3.5 text-accent" />,
        badgeBg: "bg-accent/10 text-accent border-accent/20"
      };
    }
    return {
      icon: <Sparkles className="w-3.5 h-3.5 text-cyan-500" />,
      badgeBg: "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20"
    };
  };

  const handleCopyInsights = () => {
    const textToCopy = effectiveInsights
      .map((i) => `• ${i.title}: ${i.description}`)
      .join("\n");
    navigator.clipboard.writeText(`AI Executive Insights:\n${textToCopy}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-3 rounded-xl border border-teal/25 bg-gradient-to-br from-surface-2/90 via-surface/70 to-teal/5 p-3.5 shadow-sm backdrop-blur-sm font-sans space-y-2.5 transition-all">
      {/* Header Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-teal/15 text-teal border border-teal/30 shadow-xs">
            <Sparkles className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <h4 className="text-xs font-extrabold uppercase tracking-wide bg-gradient-to-r from-teal to-accent bg-clip-text text-transparent flex items-center gap-1.5">
              AI Executive Summary &amp; Trend Insights
            </h4>
            <span className="text-[10px] text-text-muted font-medium">
              {effectiveInsights.length} key takeaway{effectiveInsights.length > 1 ? "s" : ""} generated
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={handleCopyInsights}
            title="Copy insights to clipboard"
            className="p-1.5 rounded-lg hover:bg-surface-hover text-text-muted hover:text-accent transition-colors cursor-pointer text-xs"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-teal" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 rounded-lg hover:bg-surface-hover text-text-muted hover:text-text transition-colors cursor-pointer text-xs"
          >
            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Insights Content List */}
      {isExpanded && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1 animate-fade-in">
          {effectiveInsights.map((insight, idx) => {
            const { icon, badgeBg } = getInsightBadgeStyle(insight.type);
            return (
              <div
                key={idx}
                className="p-2.5 rounded-lg bg-surface/80 border border-border/60 hover:border-teal/40 transition-all flex items-start gap-2.5 shadow-2xs group hover:scale-[1.01]"
              >
                <div className="p-1.5 rounded-md bg-surface-hover group-hover:bg-teal/10 transition-colors flex-shrink-0 mt-0.5">
                  {icon}
                </div>
                <div className="flex-1 min-w-0 space-y-0.5">
                  <div className="flex items-center justify-between gap-1">
                    <h5 className="text-xs font-bold text-text group-hover:text-teal transition-colors truncate">
                      {insight.title}
                    </h5>
                    <span
                      className={`px-1.5 py-0.5 text-[9px] font-extrabold uppercase rounded border tracking-wider flex-shrink-0 ${badgeBg}`}
                    >
                      {insight.type.replace(/_/g, " ")}
                    </span>
                  </div>
                  <p className="text-[11px] text-text-muted leading-relaxed font-medium">
                    {insight.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
