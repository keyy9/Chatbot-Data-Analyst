"""
Explainer Module.

Advanced explanation utilities and insight extraction.
Builds on top of ExplanationPromptManager to provide rich explanations.
"""

import logging
from typing import Any, List, Dict, Optional, Union, Tuple
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, date
from collections import Counter, defaultdict
import statistics

from backend.ai.utils.sql_introspection import extract_tables, extract_columns

# ============ Setup Logging ============
logger = logging.getLogger(__name__)


@dataclass
class DataInsight:
    """
    Represents a data insight extracted from query results.
    
    Attributes:
        insight_type: Type of insight (max, min, average, trend, etc.)
        title: Human-readable title
        description: Description of the insight
        value: The actual value or metric
        context: Additional context (e.g., "highest", "increased by")
        confidence: Confidence level (0-1)
    """
    insight_type: str
    title: str
    description: str
    value: Any
    context: str
    confidence: float = 0.9


class InsightExtractor:
    """
    Extracts actionable insights from query results.
    
    Detects:
    - Maximum/minimum values
    - Trends and patterns
    - Anomalies
    - Aggregations
    - Comparisons
    """
    
    def __init__(self):
        """Initialize insight extractor."""
        pass
    
    def extract_insights(
        self,
        data: Union[List[Dict], Dict],
        columns: List[str]
    ) -> List[DataInsight]:
        """
        Extract insights from query result.
        
        Args:
            data: The query result data.
            columns: List of column names.
        
        Returns:
            List[DataInsight]: List of extracted insights.
        """
        insights = []

        if isinstance(data, dict):
            data = [data]

        if not data or len(data) == 0:
            return insights

        # Id columns (e.g. "product_id") are identifiers, not a metric -
        # max/min/average/ranking over them is meaningless to a business
        # user even though their values are numeric.
        columns = [c for c in columns if not c.lower().endswith("_id") and c.lower() != "id"]

        if not columns:
            return insights
        
        # ============ Extract numeric insights ============
        numeric_insights = self._extract_numeric_insights(data, columns)
        insights.extend(numeric_insights)
        
        # ============ Extract aggregation insights ============
        aggregation_insights = self._extract_aggregation_insights(data, columns)
        insights.extend(aggregation_insights)
        
        # ============ Extract trend insights ============
        trend_insights = self._extract_trend_insights(data, columns)
        insights.extend(trend_insights)
        
        # ============ Extract ranking insights ============
        ranking_insights = self._extract_ranking_insights(data, columns)
        insights.extend(ranking_insights)
        
        return insights
    
    def _extract_numeric_insights(
        self,
        data: List[Dict],
        columns: List[str]
    ) -> List[DataInsight]:
        """
        Extract numeric insights (max, min, average).
        
        Args:
            data: The query result data.
            columns: Column names.
        
        Returns:
            List[DataInsight]: Numeric insights.
        """
        insights = []
        
        for col in columns:
            values = self._extract_numeric_values(data, col)
            
            if not values:
                continue
            
            try:
                max_val = max(values)
                min_val = min(values)
                avg_val = statistics.mean(values)
                
                # Max insight
                insights.append(DataInsight(
                    insight_type="maximum",
                    title=f"Highest {col}",
                    description=f"The highest {col} is {self._format_value(max_val)}",
                    value=max_val,
                    context="highest",
                    confidence=0.95
                ))
                
                # Min insight
                insights.append(DataInsight(
                    insight_type="minimum",
                    title=f"Lowest {col}",
                    description=f"The lowest {col} is {self._format_value(min_val)}",
                    value=min_val,
                    context="lowest",
                    confidence=0.95
                ))
                
                # Average insight
                insights.append(DataInsight(
                    insight_type="average",
                    title=f"Average {col}",
                    description=f"The average {col} is {self._format_value(avg_val)}",
                    value=avg_val,
                    context="average",
                    confidence=0.90
                ))
            
            except (ValueError, statistics.StatisticsError):
                continue
        
        return insights
    
    def _extract_aggregation_insights(
        self,
        data: List[Dict],
        columns: List[str]
    ) -> List[DataInsight]:
        """
        Extract aggregation insights (sum, count).
        
        Args:
            data: The query result data.
            columns: Column names.
        
        Returns:
            List[DataInsight]: Aggregation insights.
        """
        insights = []
        
        # Check if this looks like aggregated data
        agg_keywords = ["count", "sum", "total", "avg", "average", "max", "min"]
        has_aggregation = any(
            keyword in col.lower() 
            for col in columns 
            for keyword in agg_keywords
        )
        
        if not has_aggregation:
            return insights
        
        # Extract sum from numeric columns
        for col in columns:
            if any(keyword in col.lower() for keyword in ["sum", "total", "amount", "revenue"]):
                values = self._extract_numeric_values(data, col)
                
                if values:
                    total = sum(values)
                    
                    insights.append(DataInsight(
                        insight_type="total",
                        title=f"Total {col}",
                        description=f"Total {col} is {self._format_value(total)}",
                        value=total,
                        context="total",
                        confidence=0.95
                    ))
        
        return insights
    
    def _extract_trend_insights(
        self,
        data: List[Dict],
        columns: List[str]
    ) -> List[DataInsight]:
        """
        Extract trend insights from time series data.
        
        Args:
            data: The query result data.
            columns: Column names.
        
        Returns:
            List[DataInsight]: Trend insights.
        """
        insights = []
        
        # Check if this is time series data
        date_keywords = ["date", "month", "year", "quarter", "week", "day", "time"]
        has_time = any(keyword in col.lower() for col in columns for keyword in date_keywords)
        
        numeric_cols = [
            col for col in columns 
            if col not in [c for c in columns if any(k in c.lower() for k in date_keywords)]
        ]
        
        if not has_time or not numeric_cols:
            return insights
        
        # Get first numeric column values
        if numeric_cols:
            col = numeric_cols[0]
            values = self._extract_numeric_values(data, col)
            
            if len(values) >= 2:
                # Check if increasing or decreasing
                first_half = values[:len(values)//2]
                second_half = values[len(values)//2:]
                
                first_avg = statistics.mean(first_half) if first_half else 0
                second_avg = statistics.mean(second_half) if second_half else 0
                
                if first_avg > 0:
                    change_percent = ((second_avg - first_avg) / first_avg) * 100
                    
                    if change_percent > 5:
                        direction = "increasing"
                        context = f"up by {change_percent:.1f}%"
                    elif change_percent < -5:
                        direction = "decreasing"
                        context = f"down by {abs(change_percent):.1f}%"
                    else:
                        direction = "stable"
                        context = "relatively stable"
                    
                    insights.append(DataInsight(
                        insight_type="trend",
                        title=f"{col} Trend",
                        description=f"{col} is {direction} over time, {context}",
                        value=change_percent,
                        context=direction,
                        confidence=0.85
                    ))
        
        return insights
    
    def _extract_ranking_insights(
        self,
        data: List[Dict],
        columns: List[str]
    ) -> List[DataInsight]:
        """
        Extract ranking insights (top items).
        
        Args:
            data: The query result data.
            columns: Column names.
        
        Returns:
            List[DataInsight]: Ranking insights.
        """
        insights = []
        
        if len(data) <= 1:
            return insights
        
        # Look for numeric columns to rank by
        for col in columns:
            values = self._extract_numeric_values(data, col)
            
            if len(values) >= 2:
                # Find max row
                max_idx = values.index(max(values))
                max_row = data[max_idx]
                
                # Create ranking insight
                top_item_desc = " / ".join(
                    f"{k}: {v}" for k, v in list(max_row.items())[:2]
                )
                
                insights.append(DataInsight(
                    insight_type="ranking",
                    title=f"Top by {col}",
                    description=f"Top item: {top_item_desc}",
                    value=max(values),
                    context="highest",
                    confidence=0.90
                ))
                break
        
        return insights
    
    def _extract_numeric_values(
        self,
        data: List[Dict],
        column: str
    ) -> List[float]:
        """
        Extract numeric values from a column.
        
        Args:
            data: The data rows.
            column: Column name.
        
        Returns:
            List[float]: Numeric values.
        """
        values = []
        
        for row in data:
            if isinstance(row, dict) and column in row:
                val = row[column]
                
                if isinstance(val, (int, float, Decimal)):
                    values.append(float(val))
        
        return values
    
    def _format_value(self, value: Any) -> str:
        """
        Format a value for display.
        
        Args:
            value: The value to format.
        
        Returns:
            str: Formatted value.
        """
        if isinstance(value, float):
            if value >= 1_000_000:
                return f"{value/1_000_000:.2f}M"
            elif value >= 1_000:
                return f"{value/1_000:.2f}K"
            else:
                return f"{value:.2f}"
        
        return str(value)


class SourceAttributor:
    """
    Builds a "where did this come from" citation for an answer.

    Given the executed SQL and the rows it returned, reports which
    tables/columns were actually read from, plus (when an identifying
    column like `id` or `<table>_id` is present in the result) the
    concrete row identifiers behind the numbers - so an answer like
    "$125,430 in revenue" can be traced back to specific orders.
    """

    #: Column names treated as row identifiers when found in a result set.
    _ID_COLUMN_HINTS = ("id",)

    def __init__(self):
        """Initialize source attributor."""
        pass

    def build_sources(
        self,
        sql: str,
        data: Union[List[Dict], Dict],
        columns: List[str]
    ) -> Dict[str, Any]:
        """
        Build source attribution for a query result.

        Args:
            sql: The SQL query that was executed.
            data: The query result data.
            columns: List of column names in the result.

        Returns:
            Dict: {
                "tables": [...],
                "columns": {table: [columns, ...]},
                "row_references": [{"table", "id_column", "ids"}, ...]
            }
        """
        tables = extract_tables(sql)
        table_columns = extract_columns(sql)

        rows = data if isinstance(data, list) else ([data] if data else [])

        row_references = []
        for table in tables:
            id_column = self._find_id_column(table, columns)
            if not id_column:
                continue

            ids = []
            for row in rows:
                if isinstance(row, dict) and id_column in row and row[id_column] is not None:
                    if row[id_column] not in ids:
                        ids.append(row[id_column])

            if ids:
                row_references.append({
                    "table": table,
                    "id_column": id_column,
                    "ids": ids[:20]
                })

        return {
            "tables": tables,
            "columns": table_columns,
            "row_references": row_references
        }

    def _find_id_column(self, table: str, columns: List[str]) -> Optional[str]:
        """
        Find the most likely row-identifying column for a table among the
        result columns (e.g. "product_id" for table "products").
        """
        singular = table[:-1] if table.endswith("s") else table
        candidates = [f"{table}_id", f"{singular}_id", "id"]

        columns_lower = {c.lower(): c for c in columns}

        for candidate in candidates:
            if candidate in columns_lower:
                return columns_lower[candidate]

        return None


class ResultFormatter:
    """
    Formats query results for different display types.
    """
    
    @staticmethod
    def format_as_summary(
        data: Union[List[Dict], Dict],
        columns: List[str],
        max_items: int = 5
    ) -> str:
        """
        Format result as a summary.
        
        Args:
            data: Query result.
            columns: Column names.
            max_items: Maximum items to show.
        
        Returns:
            str: Formatted summary.
        """
        if isinstance(data, dict):
            data = [data]
        
        if not data:
            return "No results"
        
        summary_lines = []
        
        # If single row, show as key-value pairs
        if len(data) == 1:
            row = data[0]
            for key, value in row.items():
                summary_lines.append(f"• {key}: {value}")
        else:
            # Multiple rows, show as bullet list
            for i, row in enumerate(data[:max_items], 1):
                row_str = " | ".join(str(v) for v in row.values())
                summary_lines.append(f"{i}. {row_str}")
            
            if len(data) > max_items:
                summary_lines.append(f"... and {len(data) - max_items} more")
        
        return "\n".join(summary_lines)
    
    @staticmethod
    def format_as_table(
        data: Union[List[Dict], Dict],
        columns: List[str],
        max_rows: int = 10
    ) -> str:
        """
        Format result as a table.
        
        Args:
            data: Query result.
            columns: Column names.
            max_rows: Maximum rows to show.
        
        Returns:
            str: Formatted table.
        """
        if isinstance(data, dict):
            data = [data]
        
        if not data:
            return "No results"
        
        # Calculate column widths
        col_widths = {col: len(str(col)) for col in columns}
        
        for row in data[:max_rows]:
            for col in columns:
                if col in row:
                    col_widths[col] = max(col_widths[col], len(str(row[col])))
        
        # Build table
        lines = []
        
        # Header
        header_parts = [str(col).ljust(col_widths[col]) for col in columns]
        lines.append(" | ".join(header_parts))
        lines.append("-" * len(lines[0]))
        
        # Rows
        for row in data[:max_rows]:
            row_parts = [
                str(row.get(col, "")).ljust(col_widths[col])
                for col in columns
            ]
            lines.append(" | ".join(row_parts))
        
        if len(data) > max_rows:
            lines.append(f"... and {len(data) - max_rows} more rows")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_as_statistics(
        data: Union[List[Dict], Dict],
        columns: List[str]
    ) -> str:
        """
        Format result as statistics.
        
        Args:
            data: Query result.
            columns: Column names.
        
        Returns:
            str: Formatted statistics.
        """
        if isinstance(data, dict):
            data = [data]
        
        if not data:
            return "No results"
        
        stats_lines = [f"Total records: {len(data)}"]
        
        # Calculate statistics for numeric columns
        for col in columns:
            values = []
            for row in data:
                if isinstance(row, dict) and col in row:
                    val = row[col]
                    if isinstance(val, (int, float, Decimal)):
                        values.append(float(val))
            
            if values:
                stats_lines.append(f"\n{col}:")
                stats_lines.append(f"  • Count: {len(values)}")
                stats_lines.append(f"  • Min: {min(values):.2f}")
                stats_lines.append(f"  • Max: {max(values):.2f}")
                stats_lines.append(f"  • Average: {statistics.mean(values):.2f}")
                
                if len(values) > 1:
                    std_dev = statistics.stdev(values)
                    stats_lines.append(f"  • Std Dev: {std_dev:.2f}")
        
        return "\n".join(stats_lines)


class ExplanationBuilder:
    """
    Builds comprehensive explanations combining insights and formatting.
    """
    
    def __init__(self):
        """Initialize explanation builder."""
        self.insight_extractor = InsightExtractor()
        self.result_formatter = ResultFormatter()
        logger.info("ExplanationBuilder initialized")
    
    def build_comprehensive_explanation(
        self,
        user_question: str,
        data: Union[List[Dict], Dict],
        columns: List[str],
        include_insights: bool = True,
        include_summary: bool = True,
        include_statistics: bool = False
    ) -> Dict:
        """
        Build a comprehensive explanation.
        
        Args:
            user_question: The user's original question.
            data: Query result data.
            columns: Column names.
            include_insights: Whether to extract insights.
            include_summary: Whether to include summary.
            include_statistics: Whether to include statistics.
        
        Returns:
            Dict: Comprehensive explanation with multiple components.
            
        Example:
            explanation = builder.build_comprehensive_explanation(
            user_question="What are the top products?",
            data=[{"name": "Widget", "sales": 1500}, ...],
            columns=["name", "sales"],
            include_insights=True
        )
        """
        result = {
            "user_question": user_question,
            "row_count": len(data) if isinstance(data, list) else 1
        }
        
        # ============ Extract insights ============
        if include_insights:
            insights = self.insight_extractor.extract_insights(data, columns)
            result["insights"] = [
                {
                    "type": i.insight_type,
                    "title": i.title,
                    "description": i.description,
                    "value": i.value,
                    "confidence": i.confidence
                }
                for i in insights
            ]
        
        # ============ Format summary ============
        if include_summary:
            summary = self.result_formatter.format_as_summary(data, columns)
            result["summary"] = summary
        
        # ============ Format statistics ============
        if include_statistics:
            stats = self.result_formatter.format_as_statistics(data, columns)
            result["statistics"] = stats
        
        # ============ Format table ============
        table = self.result_formatter.format_as_table(data, columns)
        result["table"] = table
        
        return result
    
    def build_narrative_explanation(
        self,
        user_question: str,
        data: Union[List[Dict], Dict],
        columns: List[str]
    ) -> str:
        """
        Build a narrative explanation combining all elements.
        
        Creates a flowing, readable explanation from the data.
        
        Args:
            user_question: The user's question.
            data: Query result.
            columns: Column names.
        
        Returns:
            str: Narrative explanation.
        """
        narrative_parts = []
        
        # Extract insights
        insights = self.insight_extractor.extract_insights(data, columns)
        
        if not insights:
            insights = []
        
        # Build narrative
        if isinstance(data, dict):
            data_list = [data]
        else:
            data_list = data
        
        row_count = len(data_list)
        
        # Opening statement
        if row_count == 0:
            narrative_parts.append("No results found for your query.")
        elif row_count == 1:
            narrative_parts.append("Found 1 result:")
        else:
            narrative_parts.append(f"Found {row_count} results.")
        
        # Add insights as statements
        if insights:
            narrative_parts.append("")
            narrative_parts.append("Key insights:")
            
            for insight in insights[:3]:  # Top 3 insights
                narrative_parts.append(f"• {insight.description}")
        
        # Add summary
        if row_count <= 5:
            summary = self.result_formatter.format_as_summary(data, columns)
            narrative_parts.append("")
            narrative_parts.append("Details:")
            narrative_parts.append(summary)
        
        return "\n".join(narrative_parts)
    
    def build_contextual_explanation(
        self,
        user_question: str,
        data: Union[List[Dict], Dict],
        columns: List[str],
        context: Optional[Dict] = None
    ) -> str:
        """
        Build explanation with contextual information.
        
        Args:
            user_question: The user's question.
            data: Query result.
            columns: Column names.
            context: Optional context (previous queries, comparisons, etc.).
        
        Returns:
            str: Contextual explanation.
        """
        narrative = self.build_narrative_explanation(user_question, data, columns)
        
        # Add context if provided
        if context:
            if "comparison" in context:
                narrative += f"\n\nComparison: {context['comparison']}"
            
            if "previous_value" in context:
                change = context.get("change_percent", 0)
                direction = "increased" if change > 0 else "decreased"
                narrative += f"\nThis is a {abs(change):.1f}% {direction} from the previous period."
        
        return narrative


# ============ Singleton Instances ============
_explanation_builder: Optional[ExplanationBuilder] = None
_source_attributor: Optional[SourceAttributor] = None


def get_explanation_builder() -> ExplanationBuilder:
    """
    Get or create the global explanation builder instance.

    Returns:
        ExplanationBuilder: The builder instance.
    """
    global _explanation_builder
    if _explanation_builder is None:
        _explanation_builder = ExplanationBuilder()
    return _explanation_builder


def get_source_attributor() -> SourceAttributor:
    """
    Get or create the global source attributor instance.

    Returns:
        SourceAttributor: The source attributor instance.
    """
    global _source_attributor
    if _source_attributor is None:
        _source_attributor = SourceAttributor()
    return _source_attributor