"""
Plotly Figure Generator.

Renders an actual Plotly figure from a query result, given the chart
type/axes already picked by `ChartPromptManager` (chart_prompt.py) -
this module only does rendering, not chart-type selection or shape
detection, both of which are already handled upstream. Returns a
JSON-serializable Plotly figure spec (`fig.to_dict()`), not an image
file, so it can be embedded directly in an API response and rendered
client-side (e.g. via `react-plotly.js` or `Plotly.newPlot`) without a
round-trip through a static image.
"""

import logging
from typing import Any, Dict, List, Optional, Union

import plotly.graph_objects as go

from backend.ai.prompts.chart_prompt import ChartRecommendation, ChartType, get_chart_prompt_manager

logger = logging.getLogger(__name__)

# Chart types this generator can actually render. Anything else (METRIC,
# GAUGE, HEATMAP, FUNNEL, WATERFALL, TABLE) falls back to no figure - the
# frontend already renders a plain result table for those.
SUPPORTED_TYPES = {
    ChartType.BAR, ChartType.COLUMN, ChartType.LINE,
    ChartType.AREA, ChartType.PIE, ChartType.SCATTER, ChartType.HISTOGRAM
}


def _pick_axes(data: List[Dict], columns: List[str]) -> Optional[Dict[str, Any]]:
    """
    Pick a category/x axis and one or more numeric series, reusing the
    same column analysis `ChartPromptManager` already does for chart-type
    selection rather than re-deriving it independently.
    """
    if not data or not columns:
        return None

    manager = get_chart_prompt_manager()
    characteristics = manager.analyze_data_characteristics(data, columns)

    numeric_cols = characteristics["numeric_columns"] or [
        c for c in columns if isinstance(data[0].get(c), (int, float))
    ]
    category_cols = characteristics["time_columns"] or characteristics["categorical_columns"] or columns

    if not numeric_cols:
        return None

    # Prefer a human-readable label (e.g. "product_name") over an id
    # column (e.g. "product_id") when both are candidates for the x-axis.
    candidates = [c for c in category_cols if c not in numeric_cols]
    x_col = next(
        (c for c in candidates if not c.lower().endswith("_id") and c.lower() != "id"),
        candidates[0] if candidates else columns[0]
    )
    y_cols = [c for c in numeric_cols if c != x_col] or numeric_cols

    return {"x_col": x_col, "y_cols": y_cols}


def generate_plotly_figure(
    recommendation: Union[ChartRecommendation, Dict],
    data: List[Dict],
    columns: List[str]
) -> Dict:
    """
    Build a Plotly figure for a query result, using the chart type
    already recommended for it.

    Args:
        recommendation: A ChartRecommendation (or its formatted dict form
            with a "chart_type"/"type" key) from `ChartRecommender.recommend()`.
        data: The query result rows.
        columns: The result's column names.

    Returns:
        Dict: `fig.to_dict()` (JSON-serializable Plotly figure spec), or
            `{}` if the data/chart type isn't renderable (e.g. empty
            result, or a chart type without a Plotly mapping like "table").
    """
    chart_type_value = (
        recommendation.chart_type.value if isinstance(recommendation, ChartRecommendation)
        else recommendation.get("chart_type") or recommendation.get("type")
    )

    try:
        chart_type = ChartType(chart_type_value)
    except ValueError:
        return {}

    if chart_type not in SUPPORTED_TYPES:
        return {}

    axes = _pick_axes(data, columns)
    if not axes:
        return {}

    x_col, y_cols = axes["x_col"], axes["y_cols"]
    x_values = [row.get(x_col) for row in data]

    try:
        if chart_type in (ChartType.BAR, ChartType.COLUMN):
            fig = go.Figure([go.Bar(name=y, x=x_values, y=[row.get(y) for row in data]) for y in y_cols])
        elif chart_type == ChartType.LINE:
            fig = go.Figure([go.Scatter(name=y, x=x_values, y=[row.get(y) for row in data], mode="lines+markers") for y in y_cols])
        elif chart_type == ChartType.AREA:
            fig = go.Figure([go.Scatter(name=y, x=x_values, y=[row.get(y) for row in data], mode="lines", fill="tozeroy") for y in y_cols])
        elif chart_type == ChartType.SCATTER:
            y = y_cols[0]
            fig = go.Figure(go.Scatter(x=x_values, y=[row.get(y) for row in data], mode="markers", name=y))
        elif chart_type == ChartType.PIE:
            y = y_cols[0]
            fig = go.Figure(go.Pie(labels=x_values, values=[row.get(y) for row in data]))
        elif chart_type == ChartType.HISTOGRAM:
            # Bins the distribution of one numeric column - no category
            # axis involved, unlike the other chart types above.
            y = y_cols[0]
            fig = go.Figure(go.Histogram(x=[row.get(y) for row in data], name=y))
        else:
            return {}
    except Exception as e:
        logger.warning(f"Plotly figure generation failed for chart_type={chart_type_value}: {str(e)}")
        return {}

    fig.update_layout(
        margin=dict(l=40, r=20, t=20, b=40),
        legend=dict(orientation="h"),
        template="plotly_dark"
    )

    return fig.to_dict()
