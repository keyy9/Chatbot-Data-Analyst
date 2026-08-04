/**
 * The backend's chart recommendation only reliably supplies a `type`
 * string (`configuration` comes back empty in practice) - axis/series
 * keys have to be derived client-side from the actual result columns.
 */

/** Chart types the shared ChatBubble can render. Both user and admin chat use this same list. */
export const SUPPORTED_CHART_TYPES = ["bar", "line", "pie", "area"] as const;

/** Backend recommends a wider set of chart types than the UI renders; map the
 * renderable ones onto our supported set instead of silently dropping the chart. */
const CHART_TYPE_ALIASES: Record<string, string> = {
  column: "bar",
  bar_chart: "bar",
  histogram: "bar",
  funnel: "bar",
  donut: "pie",
  doughnut: "pie",
  pie_chart: "pie",
  line_chart: "line",
  spline: "line",
  area_chart: "area",
};

const TIME_HINTS = ["date", "month", "year", "quarter", "week", "day", "time", "period"];

function looksLikeTime(key: string): boolean {
  const k = key.toLowerCase();
  return TIME_HINTS.some((h) => k.includes(h));
}

function deriveAxisFields(data: Record<string, unknown>[], columns: string[]) {
  if (data.length === 0 || columns.length === 0) return null;

  const firstRow = data[0];
  const numericCols = columns.filter((c) => typeof firstRow[c] === "number");
  const nonNumericCols = columns.filter((c) => typeof firstRow[c] !== "number");

  if (numericCols.length === 0) return null;

  const xAxisKey = nonNumericCols[0] || columns[0];
  const dataKeys = numericCols.filter((c) => c !== xAxisKey);

  if (dataKeys.length === 0) return null;

  return { xAxisKey, dataKeys };
}

/** When the backend picks a type the UI can't render (scatter, gauge, ...) or
 * none at all, pick a sensible default from the shape of the data so a chart
 * still appears whenever the data is genuinely chartable. */
function pickDefaultChart(
  xAxisKey: string,
  data: Record<string, unknown>[],
  supportedTypes: readonly string[]
): string {
  // A time-like x-axis with several points reads best as a trend line.
  if (looksLikeTime(xAxisKey) && data.length >= 3 && supportedTypes.includes("line")) {
    return "line";
  }
  // A small set of categories with a single measure reads well as a pie.
  if (data.length >= 2 && data.length <= 6 && supportedTypes.includes("pie")) {
    return "pie";
  }
  return supportedTypes.includes("bar") ? "bar" : (supportedTypes[0] as string);
}

export function mapChartRecommendation<T extends string>(
  chartType: string | undefined,
  data: Record<string, unknown>[],
  columns: string[],
  supportedTypes: readonly T[]
): { type: T; xAxisKey: string; dataKeys: string[]; data: Record<string, unknown>[] } | undefined {
  // No chartable shape (single value, all-text, empty) -> no chart at all.
  const axisFields = deriveAxisFields(data, columns);
  if (!axisFields) return undefined;

  const raw = (chartType || "").toLowerCase().trim();
  const normalized = CHART_TYPE_ALIASES[raw] || raw;

  // Types that intentionally shouldn't render as one of our series charts
  // (a single KPI number, a raw table) -> leave the answer chart-less.
  const NO_CHART = new Set(["metric", "gauge", "card", "kpi", "table", "none"]);
  if (NO_CHART.has(normalized)) return undefined;

  const type = (supportedTypes as readonly string[]).includes(normalized)
    ? normalized
    : pickDefaultChart(axisFields.xAxisKey, data, supportedTypes as readonly string[]);

  return {
    type: type as T,
    xAxisKey: axisFields.xAxisKey,
    dataKeys: axisFields.dataKeys,
    data
  };
}
