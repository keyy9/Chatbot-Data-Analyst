"""
Chart Recommendation Prompt Module.

Analyzes query results and recommends appropriate visualization types.
Provides chart type selection logic based on data characteristics.
"""

from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import json


class ChartType(Enum):
    """
    Enumeration of supported chart types.
    """
    LINE = "line"  # Time series, trends
    BAR = "bar"  # Rankings, comparisons, categories
    PIE = "pie"  # Proportions, percentages, parts of whole
    AREA = "area"  # Time series with emphasis on magnitude
    SCATTER = "scatter"  # Correlation, distribution
    METRIC = "metric"  # Single KPI, big number display
    TABLE = "table"  # Raw data, detailed results
    COLUMN = "column"  # Similar to bar but vertical
    GAUGE = "gauge"  # Progress toward goal
    HEATMAP = "heatmap"  # Two-dimensional data
    FUNNEL = "funnel"  # Sequential process steps
    WATERFALL = "waterfall"  # Cumulative impact over time
    HISTOGRAM = "histogram"  # Distribution of a single numeric column


@dataclass
class ChartRecommendation:
    """
    Represents a chart recommendation.
    
    Attributes:
        chart_type: The recommended chart type
        confidence_score: Confidence in recommendation (0-1)
        reason: Explanation for the recommendation
        alternative_charts: List of alternative chart types
        configuration: Optional chart-specific configuration
        data_transformation_needed: Whether data needs transformation
    """
    chart_type: ChartType
    confidence_score: float
    reason: str
    alternative_charts: List[ChartType] = None
    configuration: Optional[Dict] = None
    data_transformation_needed: bool = False

    def __post_init__(self):
        if self.alternative_charts is None:
            self.alternative_charts = []


class ChartPromptManager:
    """
    Manages chart recommendation logic.
    
    Responsible for:
    - Analyzing query result characteristics
    - Recommending appropriate chart types
    - Providing configuration suggestions
    - Handling data transformation requirements
    """

    # ============ Chart Selection Rules ============
    CHART_RULES = {
        ChartType.METRIC: {
            "description": "Single KPI or metric display",
            "characteristics": ["single_value", "single_row", "single_column"],
            "min_rows": 1,
            "max_rows": 1,
            "confidence_multiplier": 0.95
        },
        ChartType.TABLE: {
            "description": "Raw data table",
            "characteristics": ["multiple_rows", "multiple_columns", "no_aggregation"],
            "min_rows": 2,
            "max_rows": float('inf'),
            "confidence_multiplier": 0.8
        },
        ChartType.LINE: {
            "description": "Time series trend",
            "characteristics": ["time_series", "trending", "multiple_values"],
            "min_rows": 3,
            "max_rows": float('inf'),
            "confidence_multiplier": 0.9
        },
        ChartType.AREA: {
            "description": "Time series with emphasis on magnitude",
            "characteristics": ["time_series", "cumulative", "stacked"],
            "min_rows": 3,
            "max_rows": float('inf'),
            "confidence_multiplier": 0.85
        },
        ChartType.BAR: {
            "description": "Ranking or category comparison",
            "characteristics": ["ranking", "categories", "aggregated"],
            "min_rows": 2,
            "max_rows": 50,
            "confidence_multiplier": 0.88
        },
        ChartType.COLUMN: {
            "description": "Vertical bar chart for categories",
            "characteristics": ["categories", "comparison", "grouped"],
            "min_rows": 2,
            "max_rows": 50,
            "confidence_multiplier": 0.85
        },
        ChartType.PIE: {
            "description": "Proportions and percentages",
            "characteristics": ["percentage", "proportion", "parts_of_whole"],
            "min_rows": 2,
            "max_rows": 10,
            "confidence_multiplier": 0.85
        },
        ChartType.SCATTER: {
            "description": "Correlation and distribution",
            "characteristics": ["correlation", "distribution", "two_dimensions"],
            "min_rows": 10,
            "max_rows": float('inf'),
            "confidence_multiplier": 0.75
        },
        ChartType.HEATMAP: {
            "description": "Two-dimensional data matrix",
            "characteristics": ["matrix", "two_dimensions", "numeric_values"],
            "min_rows": 3,
            "max_rows": 100,
            "confidence_multiplier": 0.8
        },
        ChartType.GAUGE: {
            "description": "Progress toward goal",
            "characteristics": ["single_value", "target", "percentage"],
            "min_rows": 1,
            "max_rows": 1,
            "confidence_multiplier": 0.85
        },
        ChartType.FUNNEL: {
            "description": "Sequential process steps",
            "characteristics": ["sequential", "funnel", "decreasing"],
            "min_rows": 2,
            "max_rows": 10,
            "confidence_multiplier": 0.8
        },
        ChartType.WATERFALL: {
            "description": "Cumulative impact over categories",
            "characteristics": ["cumulative", "waterfall", "categories"],
            "min_rows": 2,
            "max_rows": 50,
            "confidence_multiplier": 0.8
        }
    }

    def __init__(self):
        """Initialize the Chart Prompt Manager."""
        pass

    def analyze_data_characteristics(
        self,
        data: Union[List[Dict], Dict],
        columns: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze characteristics of query result data.
        
        Args:
            data: The query result data.
            columns: List of column names.
        
        Returns:
            Dict: Data characteristics analysis.
        """
        characteristics = {
            "row_count": 0,
            "column_count": len(columns),
            "has_time_column": False,
            "has_numeric_column": False,
            "has_categorical_column": False,
            "has_percentage": False,
            "has_null_values": False,
            "numeric_columns": [],
            "categorical_columns": [],
            "time_columns": [],
            "percentage_columns": [],
            "data_type": "unknown"
        }
        
        # ============ Determine data type ============
        if isinstance(data, dict):
            characteristics["row_count"] = 1
            characteristics["data_type"] = "single_row"
            data_to_analyze = [data]
        elif isinstance(data, list):
            characteristics["row_count"] = len(data)
            characteristics["data_type"] = "multiple_rows"
            data_to_analyze = data
        else:
            characteristics["data_type"] = "unknown"
            return characteristics
        
        # ============ Analyze columns ============
        time_keywords = ["date", "month", "year", "quarter", "week", "day", "time", "timestamp"]
        numeric_keywords = ["count", "sum", "avg", "average", "total", "amount", "price", "cost", "revenue", "sales", "value"]
        percentage_keywords = ["percent", "percentage", "rate", "%", "ratio"]
        
        for col in columns:
            col_lower = col.lower()
            
            if any(keyword in col_lower for keyword in time_keywords):
                characteristics["has_time_column"] = True
                characteristics["time_columns"].append(col)
            
            if any(keyword in col_lower for keyword in percentage_keywords):
                characteristics["has_percentage"] = True
                characteristics["percentage_columns"].append(col)
            
            if any(keyword in col_lower for keyword in numeric_keywords):
                characteristics["has_numeric_column"] = True
                characteristics["numeric_columns"].append(col)
            else:
                characteristics["has_categorical_column"] = True
                characteristics["categorical_columns"].append(col)
        
        # ============ Check for null values ============
        for row in data_to_analyze:
            if isinstance(row, dict):
                if any(v is None for v in row.values()):
                    characteristics["has_null_values"] = True
                    break
        
        return characteristics

    def detect_data_patterns(
        self,
        data: Union[List[Dict], Dict],
        columns: List[str],
        characteristics: Dict
    ) -> List[str]:
        """
        Detect data patterns that influence chart selection.
        
        Args:
            data: The query result data.
            columns: List of column names.
            characteristics: Data characteristics from analyze_data_characteristics.
        
        Returns:
            List[str]: List of detected patterns.
        """
        patterns = []
        
        # Single value pattern
        if characteristics["row_count"] == 1 and characteristics["column_count"] == 1:
            patterns.append("single_value")
        
        # Time series pattern
        if characteristics["has_time_column"] and characteristics["row_count"] >= 3:
            patterns.append("time_series")
            patterns.append("trending")
        
        # Ranking pattern (sorted data)
        if characteristics["row_count"] >= 2 and characteristics["row_count"] <= 20:
            if characteristics["has_numeric_column"] and characteristics["has_categorical_column"]:
                patterns.append("ranking")
        
        # Categories pattern
        if characteristics["has_categorical_column"] and characteristics["row_count"] <= 50:
            patterns.append("categories")
        
        # Aggregated data pattern
        numeric_keywords = ["count", "sum", "avg", "average", "total"]
        if any(keyword in col.lower() for col in columns for keyword in numeric_keywords):
            patterns.append("aggregated")
        
        # Proportion/percentage pattern
        if characteristics["has_percentage"] or characteristics["percentage_columns"]:
            patterns.append("proportion")
            patterns.append("percentage")
        
        # Multiple numeric columns (multivariate)
        if len(characteristics["numeric_columns"]) > 1:
            patterns.append("multivariate")
        
        # Correlation pattern (many rows with 2-3 numeric columns)
        if characteristics["row_count"] >= 10 and len(characteristics["numeric_columns"]) >= 2:
            patterns.append("correlation")
            patterns.append("distribution")

        # Single-numeric-column distribution pattern (histogram candidate):
        # many individual values with no second numeric column to plot
        # against - too many rows for a readable per-row bar chart.
        if len(characteristics["numeric_columns"]) == 1 and characteristics["row_count"] > 20:
            patterns.append("single_value_distribution")
        
        # Sequential/decreasing pattern (for funnel)
        if isinstance(data, list) and len(data) >= 2:
            numeric_vals = []
            for row in data[:5]:
                if isinstance(row, dict) and characteristics["numeric_columns"]:
                    val = row.get(characteristics["numeric_columns"][0])
                    if isinstance(val, (int, float)):
                        numeric_vals.append(val)
            
            if len(numeric_vals) >= 3:
                is_decreasing = all(numeric_vals[i] >= numeric_vals[i+1] for i in range(len(numeric_vals)-1))
                if is_decreasing:
                    patterns.append("funnel")
                    patterns.append("sequential")
        
        return patterns

    def recommend_chart(
        self,
        data: Union[List[Dict], Dict],
        columns: List[str],
        query_type: Optional[str] = None
    ) -> ChartRecommendation:
        """
        Recommend the best chart type for the given data.
        
        Main method for chart selection logic.
        
        Args:
            data: The query result data.
            columns: List of column names.
            query_type: Optional hint about query type (e.g., "ranking", "time_series").
        
        Returns:
            ChartRecommendation: The recommended chart with confidence score.
            
        Example:
            recommendation = manager.recommend_chart(
            data=query_result,
            columns=["date", "revenue"],
            query_type="time_series"
        )
        # Returns ChartRecommendation with chart_type=ChartType.LINE
        """
        # Analyze data
        characteristics = self.analyze_data_characteristics(data, columns)
        patterns = self.detect_data_patterns(data, columns, characteristics)
        
        # ============ Rule-based selection ============
        
        # Single metric
        if characteristics["row_count"] == 1 and characteristics["column_count"] == 1:
            return ChartRecommendation(
                chart_type=ChartType.METRIC,
                confidence_score=0.98,
                reason="Single metric value - best displayed as a KPI card",
                alternative_charts=[ChartType.GAUGE],
                data_transformation_needed=False
            )
        
        # Time series
        if "time_series" in patterns:
            return ChartRecommendation(
                chart_type=ChartType.LINE,
                confidence_score=0.92,
                reason="Time-based data detected - line chart shows trends clearly",
                alternative_charts=[ChartType.AREA, ChartType.COLUMN],
                configuration={"x_axis": characteristics["time_columns"][0] if characteristics["time_columns"] else None},
                data_transformation_needed=False
            )
        
        # Ranking/Bar chart
        if "ranking" in patterns and characteristics["row_count"] <= 20:
            return ChartRecommendation(
                chart_type=ChartType.BAR,
                confidence_score=0.90,
                reason="Ranked data - horizontal bar chart ideal for comparisons",
                alternative_charts=[ChartType.COLUMN, ChartType.TABLE],
                data_transformation_needed=False
            )
        
        # Histogram for a single numeric column across many rows
        if "single_value_distribution" in patterns:
            return ChartRecommendation(
                chart_type=ChartType.HISTOGRAM,
                confidence_score=0.8,
                reason="Single numeric column across many rows - histogram shows the value distribution",
                alternative_charts=[ChartType.TABLE],
                data_transformation_needed=False
            )

        # Pie chart for percentages/proportions
        if "percentage" in patterns and characteristics["row_count"] <= 10:
            return ChartRecommendation(
                chart_type=ChartType.PIE,
                confidence_score=0.88,
                reason="Proportion/percentage data - pie chart shows parts of whole",
                alternative_charts=[ChartType.COLUMN, ChartType.BAR],
                data_transformation_needed=False
            )
        
        # Funnel chart
        if "funnel" in patterns:
            return ChartRecommendation(
                chart_type=ChartType.FUNNEL,
                confidence_score=0.85,
                reason="Sequential decreasing values detected - funnel chart visualizes the drop-off",
                alternative_charts=[ChartType.BAR, ChartType.COLUMN],
                data_transformation_needed=False
            )
        
        # Scatter plot for correlation
        if "correlation" in patterns and characteristics["row_count"] >= 10:
            return ChartRecommendation(
                chart_type=ChartType.SCATTER,
                confidence_score=0.82,
                reason="Multiple numeric dimensions detected - scatter plot shows correlation",
                alternative_charts=[ChartType.HEATMAP, ChartType.TABLE],
                data_transformation_needed=False
            )
        
        # Categories with bar/column
        if "categories" in patterns and characteristics["row_count"] <= 50:
            return ChartRecommendation(
                chart_type=ChartType.COLUMN,
                confidence_score=0.85,
                reason="Categorical data with values - column chart for comparison",
                alternative_charts=[ChartType.BAR, ChartType.TABLE],
                data_transformation_needed=False
            )
        
        # Default to table
        return ChartRecommendation(
            chart_type=ChartType.TABLE,
            confidence_score=0.75,
            reason="Complex or multi-dimensional data - table view for detailed inspection",
            alternative_charts=[ChartType.HEATMAP],
            data_transformation_needed=False
        )

    def build_chart_recommendation_prompt(
        self,
        data: Union[List[Dict], Dict],
        columns: List[str],
        user_question: str,
        generated_sql: str
    ) -> Dict[str, str]:
        """
        Build a prompt for LLM-based chart recommendation.
        
        Args:
            data: The query result data.
            columns: List of column names.
            user_question: The user's original question.
            generated_sql: The SQL that was executed.
        
        Returns:
            Dict[str, str]: Dictionary with 'system' and 'user' keys.
        """
        system_prompt = """You are an expert data visualization specialist.

Given query results, recommend the most appropriate chart type.

## CHART TYPES AVAILABLE:

- "line": Time series trends
- "bar": Horizontal ranking/comparison
- "column": Vertical bar chart for categories
- "pie": Proportions and percentages (max 10 slices)
- "area": Stacked time series with magnitude emphasis
- "scatter": Correlation between two numeric dimensions
- "metric": Single KPI display
- "table": Raw data table
- "gauge": Progress toward a goal (0-100%)
- "heatmap": Two-dimensional matrix visualization
- "funnel": Sequential steps with decreasing values
- "waterfall": Cumulative impact visualization

## RESPONSE FORMAT:

Return ONLY a JSON object with no markdown:
{
    "chart_type": "recommended chart type",
    "confidence_score": 0.0-1.0,
    "reason": "Why this chart is best",
    "alternatives": ["alternative1", "alternative2"],
    "configuration": {
        "x_axis": "column name for x-axis",
        "y_axis": "column name for y-axis",
        "group_by": "column name for grouping (optional)",
        "sort_by": "column name for sorting (optional)"
    }
}"""

        characteristics = self.analyze_data_characteristics(data, columns)
        data_preview = json.dumps(data if isinstance(data, list) else [data], indent=2, default=str)[:500]
        
        user_prompt = f"""User Question: {user_question}

Data Characteristics:
- Rows: {characteristics['row_count']}
- Columns: {characteristics['column_count']}
- Time Series: {characteristics['has_time_column']}
- Numeric Data: {characteristics['has_numeric_column']}
- Categories: {characteristics['has_categorical_column']}
- Percentages: {characteristics['has_percentage']}

Column Names: {', '.join(columns)}

Data Sample:
{data_preview}

Recommend the best chart type for this data."""
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }

    def validate_chart_recommendation(
        self,
        recommendation: ChartRecommendation
    ) -> bool:
        """
        Validate a chart recommendation.
        
        Args:
            recommendation: The recommendation to validate.
        
        Returns:
            bool: True if valid.
            
        Raises:
            ValueError: If recommendation is invalid.
        """
        if not isinstance(recommendation, ChartRecommendation):
            raise ValueError("Recommendation must be ChartRecommendation instance")
        
        if recommendation.confidence_score < 0 or recommendation.confidence_score > 1:
            raise ValueError("Confidence score must be between 0 and 1")
        
        if not isinstance(recommendation.chart_type, ChartType):
            raise ValueError("Chart type must be a ChartType enum")
        
        if not recommendation.reason or len(recommendation.reason) == 0:
            raise ValueError("Recommendation must have a reason")
        
        return True

    def format_recommendation_response(
        self,
        recommendation: ChartRecommendation
    ) -> Dict:
        """
        Format chart recommendation for API response.
        
        Args:
            recommendation: The ChartRecommendation object.
        
        Returns:
            Dict: Formatted response for frontend.
        """
        return {
            "chart_type": recommendation.chart_type.value,
            "confidence_score": recommendation.confidence_score,
            "reason": recommendation.reason,
            "alternatives": [chart.value for chart in recommendation.alternative_charts],
            "configuration": recommendation.configuration or {},
            "data_transformation_needed": recommendation.data_transformation_needed
        }

    def get_chart_specific_configuration(
        self,
        chart_type: ChartType,
        data: Union[List[Dict], Dict],
        columns: List[str]
    ) -> Dict:
        """
        Get chart-specific configuration based on data.
        
        Args:
            chart_type: The selected chart type.
            data: The query result data.
            columns: List of column names.
        
        Returns:
            Dict: Chart-specific configuration.
        """
        config = {
            "chart_type": chart_type.value,
            "responsive": True,
            "animation": True
        }
        
        characteristics = self.analyze_data_characteristics(data, columns)
        
        # Chart-specific configs
        if chart_type == ChartType.LINE:
            config.update({
                "x_axis": characteristics["time_columns"][0] if characteristics["time_columns"] else columns[0],
                "y_axis": characteristics["numeric_columns"][0] if characteristics["numeric_columns"] else columns[-1],
                "show_legend": len(characteristics["numeric_columns"]) > 1
            })
        
        elif chart_type == ChartType.BAR:
            config.update({
                "x_axis": characteristics["numeric_columns"][0] if characteristics["numeric_columns"] else columns[-1],
                "y_axis": characteristics["categorical_columns"][0] if characteristics["categorical_columns"] else columns[0],
                "sort_by": "x",
                "sort_order": "descending"
            })
        
        elif chart_type == ChartType.PIE:
            config.update({
                "label_column": characteristics["categorical_columns"][0] if characteristics["categorical_columns"] else columns[0],
                "value_column": characteristics["numeric_columns"][0] if characteristics["numeric_columns"] else columns[-1],
                "show_legend": True
            })
        
        elif chart_type == ChartType.METRIC:
            config.update({
                "format": "currency" if any("price" in col.lower() or "revenue" in col.lower() for col in columns) else "number",
                "show_trend": False
            })
        
        elif chart_type == ChartType.TABLE:
            config.update({
                "paginate": characteristics["row_count"] > 100,
                "sort_enabled": True,
                "search_enabled": True
            })
        
        return config


# ============ Singleton Instance ============
chart_prompt_manager = ChartPromptManager()


def get_chart_prompt_manager() -> ChartPromptManager:
    """
    Get the global Chart Prompt Manager instance.
    
    Returns:
        ChartPromptManager: The prompt manager instance.
    """
    return chart_prompt_manager