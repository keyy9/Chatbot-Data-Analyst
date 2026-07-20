"""
Explanation Prompt Module.

Converts database query results into natural language explanations.
Handles formatting, aggregation, and user-friendly presentation of data.
"""

from typing import Any, List, Dict, Optional, Union
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
import json


class ResultType(Enum):
    """
    Enumeration of query result types.
    """
    SINGLE_METRIC = "single_metric"  # Single value (COUNT, SUM, AVG, etc.)
    TIME_SERIES = "time_series"  # Data over time periods
    RANKING = "ranking"  # Sorted list (TOP N)
    COMPARISON = "comparison"  # Comparing two or more periods/categories
    AGGREGATION = "aggregation"  # Grouped data
    TABLE = "table"  # Raw table data
    PIVOT = "pivot"  # Pivot table / cross-tab


@dataclass
class QueryResult:
    """
    Represents a database query result.
    
    Attributes:
        data: The actual query result data
        row_count: Number of rows returned
        columns: List of column names
        execution_time: Query execution time in milliseconds
        result_type: Type of result (detected or specified)
    """
    data: Union[List[Dict], Dict, Any]
    row_count: int
    columns: List[str]
    execution_time: float
    result_type: ResultType = ResultType.TABLE


class ExplanationPromptManager:
    """
    Manages explanation generation for query results.
    
    Responsible for:
    - Converting query results to natural language
    - Formatting numbers, dates, and currencies
    - Creating user-friendly summaries
    - Detecting key insights from data
    """

    # ============ Explanation Generation System Prompt ============
    SYSTEM_PROMPT = """You are an expert data analyst who explains database query results in clear, natural language.

Your task is to convert raw database query results into friendly, understandable explanations that a non-technical user can comprehend.

## RULES:

1. **Language**: Reply in the same language as the user's question. Use conversational, easy-to-understand language and avoid technical jargon.
2. **No JSON**: Never expose raw JSON or database structures. Format all data naturally.
3. **Number Formatting**: 
   - Format large numbers with dot as thousand separator (e.g. 1.000 not 1000)
   - Use Rp as the currency symbol (e.g., Rp 150.000)
   - Do NOT show decimals or cents for IDR currency (e.g., Rp 150.000, not Rp 150.000,00)
   - Round percentages to 1 decimal place
4. **Date Formatting**: Use readable date formats (e.g., "January 15, 2024" not "2024-01-15")
5. **Context**: Explain what the numbers mean in business context
6. **Highlights**: Highlight the most important insights or trends
7. **Conciseness**: Start with a direct answer. Then provide at most 2-4 short sentences or bullets with the most useful supporting detail.
8. **Grammar**: Use proper grammar and punctuation
9. **Specificity**: Use the actual data values, not placeholders
10. **Faithfulness**: State only facts supported by the result. Do not invent comparisons, causes, targets, or trends that were not queried.
11. **Empty results**: Clearly say that no matching records were found and, if useful, mention the applied scope from the question.

## EXPLANATION PATTERNS:

### Single Metric (COUNT, SUM, AVG, etc.):
"The [metric] is [value]. [Optional context about significance]."
Example: "The total revenue for this month is Rp 125.430.000. This is 12% higher than last month."

### Top/Bottom N:
"The top [N] [items] are: [list]. [Details about rankings]."
Example: "The top 3 products by revenue are: Product A (Rp 50.000.000), Product B (Rp 35.000.000), and Product C (Rp 28.000.000)."

### Time Series:
"[Metric] shows [trend description]. [Peak/trough details]."
Example: "Sales increased steadily throughout Q1, peaking in March with Rp 98.500.000."

### Comparison:
"[Period 1] had [value1], while [Period 2] had [value2]. This represents a [change]% [increase/decrease]."
Example: "January had Rp 45.200.000 in sales, while February had Rp 52.100.000. This is a 15% increase."

### Aggregation/Breakdown:
"[Category 1] accounts for [percentage/value], [Category 2] for [percentage/value], and so on."
Example: "Online sales make up 65% of total revenue, while in-store sales account for 35%."

## KEY INSIGHTS TO HIGHLIGHT:

- Largest/smallest values
- Significant increases/decreases
- Trends or patterns
- Anomalies or unusual data
- Business implications"""

    # ============ Format Templates ============
    FORMAT_TEMPLATES = {
        ResultType.SINGLE_METRIC: "The {metric_name} is {value}{unit}.",
        ResultType.TIME_SERIES: "{metric_name} shows {trend_description} over {period}.",
        ResultType.RANKING: "The top {count} {items} are {list_items}.",
        ResultType.COMPARISON: "{period_1} had {value_1}, while {period_2} had {value_2}. "
                               "This is a {change_percent}% {direction}.",
        ResultType.AGGREGATION: "{breakdown_items}",
        ResultType.TABLE: "Here are the results: {item_count} records found.",
        ResultType.PIVOT: "{pivot_summary}"
    }

    def __init__(self):
        """Initialize the Explanation Prompt Manager."""
        pass

    def detect_result_type(self, data: Union[List[Dict], Dict], columns: List[str]) -> ResultType:
        """
        Auto-detect the type of query result.
        
        Args:
            data: The query result data.
            columns: List of column names.
        
        Returns:
            ResultType: The detected result type.
        """
        # Single metric: single row with one column
        if isinstance(data, dict) and len(data) == 1:
            return ResultType.SINGLE_METRIC
        
        # Single value result (e.g., COUNT(*))
        if isinstance(data, list) and len(data) == 1 and len(data[0]) == 1:
            return ResultType.SINGLE_METRIC
        
        # Check for time-based columns (indicates time series)
        date_keywords = ["date", "month", "year", "quarter", "week", "day", "time"]
        has_date_column = any(keyword in col.lower() for col in columns for keyword in date_keywords)
        
        if has_date_column and isinstance(data, list) and len(data) > 1:
            return ResultType.TIME_SERIES
        
        # Check for ranking (single non-key column sorted)
        if isinstance(data, list) and len(columns) == 2:
            if any(keyword in columns[0].lower() for keyword in ["rank", "top", "position"]):
                return ResultType.RANKING
        
        # Aggregated data (has GROUP BY indicators)
        if len(columns) >= 2 and isinstance(data, list) and len(data) > 1:
            agg_keywords = ["count", "sum", "avg", "max", "min", "total"]
            has_aggregation = any(keyword in col.lower() for col in columns for keyword in agg_keywords)
            if has_aggregation:
                return ResultType.AGGREGATION
        
        # Default to table
        return ResultType.TABLE

    def format_value(
        self,
        value: Any,
        column_name: str,
        value_type: Optional[str] = None
    ) -> str:
        """
        Format a single value for natural language display.
        
        Args:
            value: The value to format.
            column_name: The name of the column (used for type inference).
            value_type: Optional explicit type hint (currency, percentage, date, etc.).
        
        Returns:
            str: The formatted value as a string.
            
        Example:
        formatted = manager.format_value(1234567.89, "revenue", "currency")
        # Returns: "$1,234,567.89"
        """
        if value is None:
            return "N/A"
        
        # Explicit type handling
        if value_type:
            if value_type == "currency":
                return self._format_currency(value)
            elif value_type == "percentage":
                return self._format_percentage(value)
            elif value_type == "date":
                return self._format_date(value)
            elif value_type == "number":
                return self._format_number(value)
        
        # Infer from column name
        column_lower = column_name.lower()
        
        if any(word in column_lower for word in ["price", "cost", "revenue", "sales", "amount", "total", "fee", "payment"]):
            return self._format_currency(value)
        
        if any(word in column_lower for word in ["percent", "percentage", "rate", "%"]):
            return self._format_percentage(value)
        
        if any(word in column_lower for word in ["date", "timestamp", "created_at", "updated_at"]):
            return self._format_date(value)
        
        if isinstance(value, (int, float, Decimal)):
            return self._format_number(value)
        
        return str(value)

    def _format_currency(self, value: Union[int, float, Decimal]) -> str:
        """Format value as currency."""
        try:
            numeric_value = float(value)
            formatted = f"{numeric_value:,.0f}"
            return f"Rp {formatted.replace(',', '.')}"
        except (ValueError, TypeError):
            return str(value)

    def _format_percentage(self, value: Union[int, float, Decimal]) -> str:
        """Format value as percentage."""
        try:
            numeric_value = float(value)
            # If value is already a decimal (0.5 = 50%), multiply by 100
            if numeric_value <= 1:
                numeric_value *= 100
            return f"{numeric_value:.1f}%"
        except (ValueError, TypeError):
            return str(value)

    def _format_date(self, value: Union[str, date, datetime]) -> str:
        """Format value as readable date."""
        try:
            if isinstance(value, str):
                # Try to parse common date formats
                for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y", "%d/%m/%Y"]:
                    try:
                        dt = datetime.strptime(value, fmt)
                        return dt.strftime("%B %d, %Y")
                    except ValueError:
                        continue
                return value
            
            if isinstance(value, datetime):
                return value.strftime("%B %d, %Y")
            
            if isinstance(value, date):
                return value.strftime("%B %d, %Y")
            
            return str(value)
        except Exception:
            return str(value)

    def _format_number(self, value: Union[int, float, Decimal]) -> str:
        """Format number with thousand separators."""
        try:
            numeric_value = float(value)
            
            # For large numbers, use dot separators
            if abs(numeric_value) >= 1000:
                if numeric_value == int(numeric_value):
                    return f"{int(numeric_value):,}".replace(",", ".")
                else:
                    formatted = f"{numeric_value:,.2f}"
                    return formatted.replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
            else:
                if numeric_value == int(numeric_value):
                    return str(int(numeric_value))
                else:
                    return f"{numeric_value:.2f}".replace(".", ",")
        except Exception:
            return str(value)

    def extract_single_metric(self, data: Union[List[Dict], Dict]) -> tuple:
        """
        Extract a single metric from query result.
        
        Args:
            data: The query result.
        
        Returns:
            tuple: (metric_name, metric_value)
        """
        if isinstance(data, dict):
            items = list(data.items())
            if len(items) == 1:
                return items[0]
            return (list(data.keys())[0], list(data.values())[0])
        
        if isinstance(data, list) and len(data) > 0:
            row = data[0]
            if isinstance(row, dict):
                items = list(row.items())
                if len(items) == 1:
                    return items[0]
                return (list(row.keys())[0], list(row.values())[0])
        
        return ("result", data)

    def build_explanation_prompt(
        self,
        user_question: str,
        generated_sql: str,
        query_result: QueryResult
    ) -> Dict[str, str]:
        """
        Build a complete explanation prompt.
        
        Args:
            user_question (str): The user's original question.
            generated_sql (str): The SQL that was executed.
            query_result (QueryResult): The database query result.
        
        Returns:
            Dict[str, str]: Dictionary with 'system' and 'user' keys.
        """
        system_prompt = self.SYSTEM_PROMPT
        
        # Format the result data for the prompt
        if query_result.result_type == ResultType.SINGLE_METRIC:
            metric_name, metric_value = self.extract_single_metric(query_result.data)
            formatted_result = f"Metric: {metric_name}, Value: {metric_value}"
        else:
            formatted_result = json.dumps(query_result.data, indent=2, default=str)
        
        user_prompt = f"""User's Question: {user_question}

Database Result:
{formatted_result}

Columns: {', '.join(query_result.columns)}
Total Rows: {query_result.row_count}
Execution Time: {query_result.execution_time}ms

Please provide a clear, natural language explanation of this result."""
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }

    def format_result_for_explanation(
        self,
        data: Union[List[Dict], Dict],
        max_rows: int = 10
    ) -> str:
        """
        Format query result for readability in explanation.
        
        Args:
            data: The query result data.
            max_rows: Maximum rows to include in formatted output.
        
        Returns:
            str: Formatted result string.
        """
        if isinstance(data, dict):
            # Single row result
            items = []
            for key, value in data.items():
                formatted_value = self.format_value(value, key)
                items.append(f"{key}: {formatted_value}")
            return "\n".join(items)
        
        if isinstance(data, list):
            if len(data) == 0:
                return "No results found."
            
            if len(data) == 1 and isinstance(data[0], dict):
                # Single row
                return self.format_result_for_explanation(data[0])
            
            # Multiple rows - format as table-like structure
            formatted_rows = []
            for i, row in enumerate(data[:max_rows], 1):
                if isinstance(row, dict):
                    row_str = " | ".join(
                        f"{k}: {self.format_value(v, k)}"
                        for k, v in row.items()
                    )
                    formatted_rows.append(f"{i}. {row_str}")
                else:
                    formatted_rows.append(f"{i}. {row}")
            
            result = "\n".join(formatted_rows)
            
            if len(data) > max_rows:
                result += f"\n... and {len(data) - max_rows} more rows"
            
            return result
        
        return str(data)

    def generate_simple_explanation(
        self,
        user_question: str,
        query_result: QueryResult
    ) -> str:
        """
        Generate a simple explanation without LLM.
        
        Useful for quick explanations without API calls.
        
        Args:
            user_question (str): The user's question.
            query_result (QueryResult): The query result.
        
        Returns:
            str: Simple explanation text.
        """
        result_type = query_result.result_type
        data = query_result.data
        
        if result_type == ResultType.SINGLE_METRIC:
            metric_name, metric_value = self.extract_single_metric(data)
            formatted_value = self.format_value(metric_value, metric_name)
            return f"The {metric_name} is {formatted_value}."
        
        elif result_type == ResultType.RANKING and isinstance(data, list):
            items = [f"{i+1}. {row}" for i, row in enumerate(data[:5])]
            return f"Here are the top results:\n" + "\n".join(items)
        
        elif result_type == ResultType.TABLE:
            return f"Found {query_result.row_count} records matching your query."
        
        else:
            formatted = self.format_result_for_explanation(data)
            return f"Query results:\n{formatted}"

    def add_context_to_explanation(
        self,
        explanation: str,
        previous_context: Optional[Dict] = None
    ) -> str:
        """
        Add business context to an explanation.
        
        Args:
            explanation (str): The base explanation.
            previous_context (Optional[Dict]): Context from previous queries.
        
        Returns:
            str: Enhanced explanation with context.
        """
        if previous_context is None:
            return explanation
        
        # Add comparison context if available
        if "previous_value" in previous_context:
            prev_val = previous_context["previous_value"]
            change = previous_context.get("change_percent", 0)
            direction = "increase" if change > 0 else "decrease"
            explanation += f" This is a {abs(change):.1f}% {direction} from the previous period."
        
        return explanation

    def sanitize_explanation(self, explanation: str) -> str:
        """
        Sanitize explanation for safety.
        
        Removes any SQL, code, or potentially sensitive information.
        
        Args:
            explanation (str): Raw explanation text.
        
        Returns:
            str: Sanitized explanation.
        """
        # Remove any SQL keywords in uppercase (suspicious)
        sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER"]
        for keyword in sql_keywords:
            if keyword in explanation:
                explanation = explanation.replace(keyword, "")
        
        # Remove any code blocks
        explanation = explanation.replace("```", "")
        
        # Clean up extra whitespace
        explanation = " ".join(explanation.split())
        
        return explanation.strip()


# ============ Singleton Instance ============
explanation_prompt_manager = ExplanationPromptManager()


def get_explanation_prompt_manager() -> ExplanationPromptManager:
    """
    Get the global Explanation Prompt Manager instance.
    
    Returns:
        ExplanationPromptManager: The prompt manager instance.
    """
    return explanation_prompt_manager
