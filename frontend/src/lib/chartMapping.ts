/**
 * The backend's chart recommendation only reliably supplies a `type`
 * string (`configuration` comes back empty in practice) - axis/series
 * keys have to be derived client-side from the actual result columns.
 */

/** Chart types the shared ChatBubble can render. Both user and admin chat use this same list. */
export const SUPPORTED_CHART_TYPES = ["bar", "line", "pie", "area"] as const;

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

export function mapChartRecommendation<T extends string>(
  chartType: string | undefined,
  data: Record<string, unknown>[],
  columns: string[],
  supportedTypes: readonly T[]
): { type: T; xAxisKey: string; dataKeys: string[]; data: Record<string, unknown>[] } | undefined {
  if (!chartType) return undefined;

  const normalized = chartType === "column" ? "bar" : chartType;
  if (!(supportedTypes as readonly string[]).includes(normalized)) return undefined;

  const axisFields = deriveAxisFields(data, columns);
  if (!axisFields) return undefined;

  return {
    type: normalized as T,
    xAxisKey: axisFields.xAxisKey,
    dataKeys: axisFields.dataKeys,
    data
  };
}
