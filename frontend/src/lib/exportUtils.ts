import Papa from "papaparse";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import html2canvas from "html2canvas-pro";

// Above this many rows, the PDF table is capped with a note pointing at
// the CSV export (which always has the complete set) rather than
// hand-rolling multi-page table continuation logic.
const MAX_PDF_TABLE_ROWS = 200;

/**
 * Turns free text into a short, filesystem-safe slug for filenames
 * (lowercase, non-alphanumeric runs collapsed to a single "-", capped
 * length so a long question doesn't produce an unwieldy filename).
 */
function slugify(text: string, maxLength: number = 40): string {
  const slug = text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug.slice(0, maxLength).replace(/-+$/g, "") || "export";
}

function buildTimestamp(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}` +
    `-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
  );
}

export function buildExportFilename(questionText: string, extension: string): string {
  return `lapis_export_${slugify(questionText)}_${buildTimestamp()}.${extension}`;
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export a result table as CSV - the full row set already held in state,
 * never re-queried. Uses Papaparse for proper quoting/escaping (values
 * containing commas, quotes, or newlines) rather than hand-joining
 * strings, and prepends a UTF-8 BOM so non-ASCII text (names, currency
 * symbols, etc.) opens correctly in Excel instead of as mojibake.
 */
export function exportResultAsCsv(
  columns: string[],
  rows: Record<string, unknown>[],
  questionText: string
): void {
  const csvBody = Papa.unparse({ fields: columns, data: rows });
  const utf8Bom = "﻿";
  const blob = new Blob([utf8Bom + csvBody], { type: "text/csv;charset=utf-8;" });
  triggerDownload(blob, buildExportFilename(questionText, "csv"));
}

export interface PdfExportParams {
  questionText: string;
  explanationText: string;
  sql?: string;
  columns: string[];
  rows: Record<string, unknown>[];
  /** The already-rendered chart DOM node to rasterize, if this answer has one. */
  chartElement?: HTMLElement | null;
}

/**
 * Export a single answer as a full PDF report: question, explanation,
 * the chart exactly as rendered (captured from the live DOM via
 * html2canvas-pro - the app renders charts with `recharts`/SVG, not Plotly,
 * so there's no server-side or toImage()-based regeneration path), the
 * result table (jspdf-autotable, capped at MAX_PDF_TABLE_ROWS with a
 * note for larger sets), and the generated SQL, with a generated-at
 * timestamp in the footer of every page.
 *
 * Entirely client-side: no network request, no re-query - every value
 * written to the PDF comes from `params`, which the caller already has
 * in state.
 */
export async function exportResultAsPdf(params: PdfExportParams): Promise<void> {
  const { questionText, explanationText, sql, columns, rows, chartElement } = params;

  const pdf = new jsPDF({ unit: "pt", format: "a4" });
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const margin = 40;
  const footerHeight = 30;
  let y = margin;

  const ensureSpace = (needed: number) => {
    if (y + needed > pageHeight - footerHeight) {
      pdf.addPage();
      y = margin;
    }
  };

  const writeSectionHeading = (label: string) => {
    ensureSpace(24);
    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(12);
    pdf.setTextColor(0);
    pdf.text(label, margin, y);
    y += 16;
  };

  const writeWrappedText = (text: string, font: "helvetica" | "courier", fontSize: number) => {
    pdf.setFont(font, "normal");
    pdf.setFontSize(fontSize);
    const lines: string[] = pdf.splitTextToSize(text, pageWidth - margin * 2);
    for (const line of lines) {
      ensureSpace(fontSize + 4);
      pdf.text(line, margin, y);
      y += fontSize + 4;
    }
  };

  // ============ Title ============
  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(16);
  pdf.setTextColor(0);
  pdf.text("Lapis AI - Query Report", margin, y);
  y += 26;

  // ============ Question ============
  writeSectionHeading("Question");
  writeWrappedText(questionText, "helvetica", 10);
  y += 8;

  // ============ Explanation ============
  writeSectionHeading("Explanation");
  writeWrappedText(explanationText || "(no explanation available)", "helvetica", 10);
  y += 8;

  // ============ Chart (captured from the live DOM) ============
  if (chartElement) {
    const canvas = await html2canvas(chartElement, { backgroundColor: "#ffffff", scale: 2 });
    const imgData = canvas.toDataURL("image/png");
    const imgWidth = pageWidth - margin * 2;
    const imgHeight = (canvas.height / canvas.width) * imgWidth;

    writeSectionHeading("Chart");
    ensureSpace(imgHeight);
    pdf.addImage(imgData, "PNG", margin, y, imgWidth, imgHeight);
    y += imgHeight + 16;
  }

  // ============ Result table ============
  if (columns.length > 0 && rows.length > 0) {
    writeSectionHeading("Result Data");

    const cappedRows = rows.slice(0, MAX_PDF_TABLE_ROWS);
    autoTable(pdf, {
      startY: y,
      head: [columns],
      body: cappedRows.map((row) => columns.map((col) => String(row[col] ?? ""))),
      margin: { left: margin, right: margin, bottom: footerHeight },
      styles: { fontSize: 8 },
      headStyles: { fillColor: [192, 78, 1] } // matches the app's accent orange (#C04E01)
    });

    y = (pdf as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 16;

    if (rows.length > MAX_PDF_TABLE_ROWS) {
      ensureSpace(14);
      pdf.setFont("helvetica", "italic");
      pdf.setFontSize(9);
      pdf.setTextColor(120);
      pdf.text(
        `Showing first ${MAX_PDF_TABLE_ROWS} of ${rows.length} rows - see the CSV export for the complete data.`,
        margin,
        y
      );
      y += 16;
      pdf.setTextColor(0);
    }
  }

  // ============ Generated SQL ============
  if (sql) {
    writeSectionHeading("Generated SQL");
    writeWrappedText(sql, "courier", 8);
  }

  // ============ Footer (generated-at timestamp, every page) ============
  const generatedAt = new Date().toLocaleString();
  const pageCount = pdf.getNumberOfPages();
  for (let page = 1; page <= pageCount; page++) {
    pdf.setPage(page);
    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(8);
    pdf.setTextColor(140);
    pdf.text(`Generated at ${generatedAt}`, margin, pageHeight - 16);
    pdf.text(`Page ${page} of ${pageCount}`, pageWidth - margin - 60, pageHeight - 16);
  }

  pdf.save(buildExportFilename(questionText, "pdf"));
}
