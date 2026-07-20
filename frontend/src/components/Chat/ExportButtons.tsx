import React, { useState } from "react";
import { Download, FileText, Loader2 } from "lucide-react";
import { exportResultAsCsv, exportResultAsPdf } from "../../lib/exportUtils";

interface ExportButtonsProps {
  questionText: string;
  explanationText: string;
  sql?: string;
  columns: string[];
  rows: Record<string, unknown>[];
  /**
   * Ref to the already-rendered chart DOM node, read at click time (not
   * render time) - refs attach after the render that creates them, so a
   * snapshot value captured during render can still be null the first
   * time this answer is ever interacted with.
   */
  chartElementRef?: React.RefObject<HTMLElement | null>;
}

const buttonClass =
  "flex items-center gap-1 text-[9px] font-bold uppercase tracking-wide px-2 py-1 rounded-lg border " +
  "border-slate-200 dark:border-border bg-slate-50 dark:bg-surface-hover text-text-faint dark:text-text-muted " +
  "hover:text-accent hover:border-accent/40 transition-colors cursor-pointer " +
  "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:text-text-faint";

/**
 * Per-answer export controls, entirely client-side: both buttons build
 * their file from data already held in the message's state (no network
 * request, no re-query), so the export always matches exactly what's on
 * screen.
 */
export const ExportButtons: React.FC<ExportButtonsProps> = ({
  questionText,
  explanationText,
  sql,
  columns,
  rows,
  chartElementRef
}) => {
  const [isExportingPdf, setIsExportingPdf] = useState(false);

  const handleCsvExport = () => {
    exportResultAsCsv(columns, rows, questionText);
  };

  const handlePdfExport = async () => {
    setIsExportingPdf(true);
    try {
      await exportResultAsPdf({
        questionText,
        explanationText,
        sql,
        columns,
        rows,
        chartElement: chartElementRef?.current
      });
    } finally {
      setIsExportingPdf(false);
    }
  };

  return (
    <div className="flex items-center gap-1.5 pt-1 font-sans">
      <button type="button" onClick={handleCsvExport} className={buttonClass}>
        <Download className="w-3 h-3" />
        Export CSV
      </button>
      <button type="button" onClick={handlePdfExport} disabled={isExportingPdf} className={buttonClass}>
        {isExportingPdf ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileText className="w-3 h-3" />}
        {isExportingPdf ? "Generating..." : "Export PDF"}
      </button>
    </div>
  );
};
