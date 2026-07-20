"""
LLM Generator Module.

Orchestrates LLM-based generation for SQL, explanations, and chart recommendations.
Combines prompts, client, and validators into high-level generation functions.
"""

import logging
from typing import Optional, Dict, Any, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime

from backend.ai.llm.client import (
    LLMClient,
    get_llm_client
)
from backend.ai.prompts.sql_prompt import (
    SQLPromptManager,
    get_sql_prompt_manager
)
from backend.ai.prompts.clarification_prompt import (
    ClarificationPromptManager,
    get_clarification_prompt_manager
)
from backend.ai.prompts.explanation_prompt import (
    ExplanationPromptManager,
    get_explanation_prompt_manager,
    QueryResult
)
from backend.ai.prompts.chart_prompt import (
    ChartPromptManager,
    get_chart_prompt_manager,
    ChartRecommendation
)
from backend.ai.chart.plotly_generator import generate_plotly_figure
from backend.ai.validators.sql_guard import (
    SQLGuardValidator,
    get_sql_guard_validator
)
from backend.ai.explanation.explainer import SourceAttributor, get_source_attributor, InsightExtractor

# ============ Setup Logging ============
logger = logging.getLogger(__name__)


@dataclass
class SQLGenerationResult:
    """
    Result of SQL generation.

    Attributes:
        sql: Generated SQL query (or None if clarification needed)
        is_valid: Whether SQL passed validation
        is_ambiguous: Whether input was ambiguous
        ambiguity_type: Type of ambiguity if detected
        clarification_question: Clarification question if needed
        clarification_options: Options for clarification
        llm_response: Raw LLM response metadata
        generation_time_ms: Time taken to generate SQL
        error_message: Error message if generation failed
    """
    sql: Optional[str] = None
    is_valid: bool = False
    is_ambiguous: bool = False
    ambiguity_type: Optional[str] = None
    clarification_question: Optional[str] = None
    clarification_options: Optional[list] = None
    llm_response: Optional[Dict] = None
    generation_time_ms: float = 0.0
    error_message: Optional[str] = None


@dataclass
class ExplanationResult:
    """
    Result of explanation generation.

    Attributes:
        explanation: Natural language explanation
        explanation_type: Type of explanation (llm_generated or simple)
        llm_response: LLM response metadata if LLM-generated
        generation_time_ms: Time taken to generate explanation
        error_message: Error message if generation failed
    """
    explanation: str
    explanation_type: str = "simple"
    llm_response: Optional[Dict] = None
    generation_time_ms: float = 0.0
    error_message: Optional[str] = None


@dataclass
class ChartRecommendationResult:
    """
    Result of chart recommendation.

    Attributes:
        recommendation: ChartRecommendation object
        chart_type: Recommended chart type
        confidence_score: Confidence in recommendation (0-1)
        reason: Explanation for recommendation
        alternatives: Alternative chart types
        configuration: Chart-specific configuration
        generation_time_ms: Time taken to generate recommendation
    """
    recommendation: ChartRecommendation
    chart_type: str
    confidence_score: float
    reason: str
    alternatives: list
    configuration: Dict
    generation_time_ms: float = 0.0


class SQLGenerator:
    """
    High-level SQL generation orchestrator.

    Manages the complete SQL generation pipeline:
    1. Check for ambiguity
    2. Build prompt with schema
    3. Call LLM for SQL generation
    4. Validate generated SQL
    5. Return result or ask clarification
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        sql_prompt_manager: Optional[SQLPromptManager] = None,
        clarification_manager: Optional[ClarificationPromptManager] = None,
        sql_validator: Optional[SQLGuardValidator] = None
    ):
        """
        Initialize SQL Generator.

        Args:
            llm_client: LLM client instance.
            sql_prompt_manager: SQL prompt manager.
            clarification_manager: Clarification prompt manager.
            sql_validator: SQL guard validator.
        """
        self.llm_client = llm_client or get_llm_client()
        self.sql_prompt_manager = sql_prompt_manager or get_sql_prompt_manager()
        self.clarification_manager = clarification_manager or get_clarification_prompt_manager()
        self.sql_validator = sql_validator or get_sql_guard_validator()

        logger.info("SQLGenerator initialized")

    def generate(
        self,
        user_question: str,
        schema_definition: str,
        include_examples: bool = False,
        num_examples: int = 3,
        check_ambiguity: bool = True,
        override_system_prompt: Optional[str] = None,
        conversation_context: str = ""
    ) -> SQLGenerationResult:
        """
        Generate SQL from natural language question.

        Main method for SQL generation.

        Args:
            user_question: The user's natural language question.
            schema_definition: The database schema definition.
            include_examples: Whether to include few-shot examples.
            num_examples: Number of examples to include.
            check_ambiguity: Whether to check for ambiguity first.

        Returns:
            SQLGenerationResult: The generation result.

        Example:
            result = generator.generate(
                user_question="Show top 5 products by revenue",
                schema_definition=schema
            )
            if result.is_valid:
                print(result.sql)
        """
        import time
        start_time = time.time()

        try:
            # ============ Step 1: Check for ambiguity ============
            if check_ambiguity:
                clarification = self.clarification_manager.build_clarification_prompt(user_question)

                if clarification.get("is_ambiguous"):
                    logger.info(f"Ambiguity detected for question: {user_question[:50]}...")

                    return SQLGenerationResult(
                        is_valid=False,
                        is_ambiguous=True,
                        ambiguity_type=clarification.get("ambiguity_type"),
                        clarification_question=clarification.get("question"),
                        clarification_options=clarification.get("options"),
                        generation_time_ms=(time.time() - start_time) * 1000
                    )

            # ============ Step 2: Build prompt with schema ============
            prompt = self.sql_prompt_manager.build_complete_prompt(
                user_question=user_question,
                schema_definition=schema_definition,
                include_examples=include_examples,
                num_examples=num_examples,
                override_system_prompt=override_system_prompt,
                conversation_context=conversation_context
            )

            # ============ Step 3: Call LLM for SQL generation ============
            llm_response = self.llm_client.generate(
                system_prompt=prompt["system"],
                user_prompt=prompt["user"]
            )

            generated_sql = self._clean_sql_output(llm_response.content)

            # ============ Step 4: Validate generated SQL ============
            validation = self.sql_validator.validate(generated_sql)

            if not validation["is_valid"]:
                logger.warning(f"Generated SQL failed validation: {validation['error']}")

                return SQLGenerationResult(
                    sql=generated_sql,
                    is_valid=False,
                    llm_response=llm_response.to_dict(),
                    generation_time_ms=(time.time() - start_time) * 1000,
                    error_message=validation["error"]
                )

            logger.info("SQL generated and validated successfully")

            return SQLGenerationResult(
                sql=generated_sql,
                is_valid=True,
                llm_response=llm_response.to_dict(),
                generation_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            logger.error(f"SQL generation failed: {str(e)}")

            return SQLGenerationResult(
                is_valid=False,
                generation_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )

    def _clean_sql_output(self, raw_output: str) -> str:
        """
        Strip markdown code fences and surrounding whitespace from raw LLM output.

        Args:
            raw_output: The raw LLM response content.

        Returns:
            str: Cleaned SQL string.
        """
        sql = raw_output.strip()

        if "```" in sql:
            parts = sql.split("```")
            # parts look like ['', 'sql\nSELECT ...', ''] or ['', 'SELECT ...', '']
            sql = parts[1] if len(parts) > 1 else sql
            if sql.lower().startswith("sql"):
                sql = sql[3:]

        return sql.strip().rstrip(";").strip()


class ExplanationGenerator:
    """
    High-level explanation generation orchestrator.

    Converts query results into natural language explanations, using a
    fast rule-based explanation by default and optionally an LLM-generated
    one for more nuanced summaries (with automatic fallback on failure).
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        explanation_manager: Optional[ExplanationPromptManager] = None,
        use_llm: bool = True
    ):
        """
        Initialize Explanation Generator.

        Args:
            llm_client: LLM client instance.
            explanation_manager: Explanation prompt manager.
            use_llm: Whether to use LLM-generated explanations by default.
        """
        self.llm_client = llm_client or get_llm_client()
        self.explanation_manager = explanation_manager or get_explanation_prompt_manager()
        self.use_llm = use_llm

        logger.info(f"ExplanationGenerator initialized (use_llm={use_llm})")

    def generate(
        self,
        user_question: str,
        generated_sql: str,
        query_result: QueryResult,
        use_llm: Optional[bool] = None
    ) -> ExplanationResult:
        """
        Generate a natural language explanation for a query result.

        Args:
            user_question: The user's original question.
            generated_sql: The SQL that was executed.
            query_result: The database query result.
            use_llm: Optional override for whether to use the LLM.

        Returns:
            ExplanationResult: The explanation result.
        """
        import time
        start_time = time.time()

        try:
            use_llm_final = use_llm if use_llm is not None else self.use_llm

            # ============ Try simple explanation first ============
            logger.info("Generating simple explanation...")

            simple_explanation = self.explanation_manager.generate_simple_explanation(
                user_question,
                query_result
            )

            # If not using LLM, return simple explanation
            if not use_llm_final:
                logger.info("Using simple explanation (LLM disabled)")

                return ExplanationResult(
                    explanation=simple_explanation,
                    explanation_type="simple",
                    generation_time_ms=(time.time() - start_time) * 1000
                )

            # ============ Use LLM for more sophisticated explanation ============
            logger.info("Calling LLM for detailed explanation...")

            prompt = self.explanation_manager.build_explanation_prompt(
                user_question,
                generated_sql,
                query_result
            )

            llm_response = self.llm_client.generate(
                system_prompt=prompt["system"],
                user_prompt=prompt["user"],
                max_tokens=512  # Explanations are shorter
            )

            # Sanitize explanation
            explanation = self.explanation_manager.sanitize_explanation(llm_response.content)

            logger.info("LLM explanation generated successfully")

            return ExplanationResult(
                explanation=explanation,
                explanation_type="llm_generated",
                llm_response=llm_response.to_dict(),
                generation_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            logger.warning(f"LLM explanation generation failed, falling back to simple: {str(e)}")

            # Fallback to simple explanation
            simple_explanation = self.explanation_manager.generate_simple_explanation(
                user_question,
                query_result
            )

            return ExplanationResult(
                explanation=simple_explanation,
                explanation_type="simple_fallback",
                generation_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )


class ChartRecommender:
    """
    High-level chart recommendation orchestrator.

    Analyzes query results and recommends appropriate visualization types.
    Uses rule-based selection (fast, deterministic, no API cost).
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        chart_manager: Optional[ChartPromptManager] = None,
        use_llm: bool = False
    ):
        """
        Initialize Chart Recommender.

        Args:
            llm_client: LLM client instance.
            chart_manager: Chart prompt manager.
            use_llm: Whether to use LLM for recommendations (vs rule-based).
        """
        self.llm_client = llm_client or get_llm_client()
        self.chart_manager = chart_manager or get_chart_prompt_manager()
        self.use_llm = use_llm

        logger.info(f"ChartRecommender initialized (use_llm={use_llm})")

    def recommend(
        self,
        data: Any,
        columns: list,
        user_question: str,
        generated_sql: str,
        use_llm: Optional[bool] = None
    ) -> ChartRecommendationResult:
        """
        Recommend a chart type for the given data.

        Args:
            data: The query result data.
            columns: List of column names.
            user_question: The user's question.
            generated_sql: The SQL that was executed.
            use_llm: Optional override for LLM usage.

        Returns:
            ChartRecommendationResult: The recommendation result.
        """
        import time
        start_time = time.time()

        use_llm_final = use_llm if use_llm is not None else self.use_llm

        if use_llm_final:
            try:
                prompt = self.chart_manager.build_chart_recommendation_prompt(
                    data, columns, user_question, generated_sql
                )
                llm_response = self.llm_client.generate_json(
                    system_prompt=prompt["system"],
                    user_prompt=prompt["user"],
                    max_tokens=512
                )

                from backend.ai.prompts.chart_prompt import ChartType

                recommendation = ChartRecommendation(
                    chart_type=ChartType(llm_response.get("chart_type", "table")),
                    confidence_score=float(llm_response.get("confidence_score", 0.7)),
                    reason=llm_response.get("reason", "LLM-recommended chart"),
                    alternative_charts=[
                        ChartType(c) for c in llm_response.get("alternatives", [])
                        if c in [ct.value for ct in ChartType]
                    ],
                    configuration=llm_response.get("configuration", {})
                )
            except Exception as e:
                logger.warning(f"LLM chart recommendation failed, falling back to rules: {str(e)}")
                recommendation = self.chart_manager.recommend_chart(data, columns)
        else:
            recommendation = self.chart_manager.recommend_chart(data, columns)

        formatted = self.chart_manager.format_recommendation_response(recommendation)

        return ChartRecommendationResult(
            recommendation=recommendation,
            chart_type=formatted["chart_type"],
            confidence_score=formatted["confidence_score"],
            reason=formatted["reason"],
            alternatives=formatted["alternatives"],
            configuration=formatted["configuration"],
            generation_time_ms=(time.time() - start_time) * 1000
        )


class PipelineOrchestrator:
    """
    Orchestrates the complete NL-to-SQL-to-answer pipeline.

    Steps: generate SQL -> execute (via caller-supplied callback) ->
    explain -> recommend chart -> attribute sources -> format response.
    """

    def __init__(
        self,
        sql_generator: Optional[SQLGenerator] = None,
        explanation_generator: Optional[ExplanationGenerator] = None,
        chart_recommender: Optional[ChartRecommender] = None,
        source_attributor: Optional[SourceAttributor] = None,
        insight_extractor: Optional[InsightExtractor] = None
    ):
        """
        Initialize Pipeline Orchestrator.

        Args:
            sql_generator: SQL generator instance.
            explanation_generator: Explanation generator instance.
            chart_recommender: Chart recommender instance.
            source_attributor: Source attributor instance.
            insight_extractor: Insight extractor instance.
        """
        self.sql_generator = sql_generator or get_sql_generator()
        self.explanation_generator = explanation_generator or get_explanation_generator()
        self.chart_recommender = chart_recommender or get_chart_recommender()
        self.source_attributor = source_attributor or get_source_attributor()
        self.insight_extractor = insight_extractor or InsightExtractor()

        logger.info("PipelineOrchestrator initialized")

    def process(
        self,
        user_question: str,
        schema_definition: str,
        query_executor_callback: Callable[[str], Tuple[list, list, float]],
        override_system_prompt: Optional[str] = None,
        conversation_context: str = "",
        check_ambiguity: bool = True
    ) -> Dict[str, Any]:
        """
        Run the complete pipeline for a user question.

        Args:
            user_question: The user's natural language question.
            schema_definition: The database schema definition.
            query_executor_callback: Callback that executes SQL and returns
                (data, columns, execution_time_ms). Raising inside this
                callback (e.g. for a permission error) aborts the pipeline
                with an error response.
            override_system_prompt: Optional admin-editable system prompt
                (e.g. loaded from the `system_prompts` table) used in place
                of the hardcoded default.
            check_ambiguity: Whether to check for ambiguity.

        Returns:
            Dict: Pipeline response. On success:
                {
                    "status": "success",
                    "user_question", "generated_sql", "explanation",
                    "chart_recommendation", "sources", "data", "columns",
                    "metadata"
                }
                On clarification needed: {"status": "clarification_needed", ...}
                On error: {"status": "error", "error": str}
        """
        logger.info(f"Starting complete pipeline for: {user_question}")

        # ============ Step 1: Generate SQL ============
        sql_result = self.sql_generator.generate(
            user_question,
            schema_definition,
            check_ambiguity=check_ambiguity,
            override_system_prompt=override_system_prompt,
            conversation_context=conversation_context
        )

        if sql_result.is_ambiguous:
            logger.info("Ambiguity detected, asking for clarification")
            return {
                "status": "clarification_needed",
                "ambiguity_type": sql_result.ambiguity_type,
                "question": sql_result.clarification_question,
                "options": sql_result.clarification_options
            }

        if not sql_result.is_valid:
            logger.error(f"SQL generation failed: {sql_result.error_message}")
            return {
                "status": "error",
                "error": sql_result.error_message
            }

        # ============ Step 2: Execute SQL (via caller-supplied callback) ============
        logger.info("Executing SQL...")
        try:
            data, columns, execution_time = query_executor_callback(sql_result.sql)
        except Exception as e:
            logger.error(f"SQL execution failed: {str(e)}")
            return {
                "status": "error",
                "error": f"SQL execution failed: {str(e)}"
            }

        # ============ Step 3: Generate Explanation ============
        query_result = QueryResult(
            data=data,
            row_count=len(data) if isinstance(data, list) else 1,
            columns=columns,
            execution_time=execution_time
        )

        explanation_result = self.explanation_generator.generate(
            user_question,
            sql_result.sql,
            query_result
        )

        # ============ Step 4: Recommend Chart ============
        chart_result = self.chart_recommender.recommend(
            data,
            columns,
            user_question,
            sql_result.sql
        )

        # ============ Step 5: Attribute Sources ============
        sources = self.source_attributor.build_sources(
            sql_result.sql,
            data,
            columns
        )

        # ============ Step 6: Render Plotly Figure ============
        # Renders the chart type already picked above - no new shape
        # detection here, just turning that decision into an actual figure.
        plotly_figure = generate_plotly_figure(chart_result.recommendation, data, columns)

        # ============ Step 7: Extract Insights ============
        # Deterministic max/min/average/trend/ranking extraction, distinct
        # from (and a guaranteed structured complement to) the LLM's own
        # prose explanation above, which only highlights insights at its
        # own discretion.
        insights = self.insight_extractor.extract_insights(data, columns)

        # ============ Step 8: Format Final Response ============
        logger.info("Pipeline completed successfully")

        return {
            "status": "success",
            "user_question": user_question,
            "generated_sql": sql_result.sql,
            "explanation": explanation_result.explanation,
            "chart_recommendation": {
                "type": chart_result.chart_type,
                "confidence": chart_result.confidence_score,
                "reason": chart_result.reason,
                "alternatives": chart_result.alternatives,
                "configuration": chart_result.configuration
            },
            "plotly_figure": plotly_figure,
            "insights": [
                {
                    "type": i.insight_type,
                    "title": i.title,
                    "description": i.description,
                    "value": i.value,
                    "confidence": i.confidence
                }
                for i in insights
            ],
            "sources": sources,
            "data": data,
            "columns": columns,
            "metadata": {
                "sql_generation_time_ms": sql_result.generation_time_ms,
                "query_execution_time_ms": execution_time,
                "explanation_generation_time_ms": explanation_result.generation_time_ms,
                "chart_recommendation_time_ms": chart_result.generation_time_ms,
                "timestamp": datetime.utcnow().isoformat()
            }
        }


# ============ Singleton Instances (one per LLM provider) ============
_sql_generators: Dict[str, SQLGenerator] = {}
_explanation_generators: Dict[str, ExplanationGenerator] = {}
_chart_recommenders: Dict[str, ChartRecommender] = {}
_pipeline_orchestrators: Dict[str, PipelineOrchestrator] = {}


def get_sql_generator(provider: str = "groq") -> SQLGenerator:
    """Get or create the SQL generator for the given LLM provider."""
    if provider not in _sql_generators:
        _sql_generators[provider] = SQLGenerator(llm_client=get_llm_client(provider))
    return _sql_generators[provider]


def get_explanation_generator(provider: str = "groq") -> ExplanationGenerator:
    """Get or create the explanation generator for the given LLM provider."""
    if provider not in _explanation_generators:
        _explanation_generators[provider] = ExplanationGenerator(llm_client=get_llm_client(provider))
    return _explanation_generators[provider]


def get_chart_recommender(provider: str = "groq") -> ChartRecommender:
    """Get or create the chart recommender for the given LLM provider."""
    if provider not in _chart_recommenders:
        _chart_recommenders[provider] = ChartRecommender(llm_client=get_llm_client(provider))
    return _chart_recommenders[provider]


def get_pipeline_orchestrator(provider: str = "groq") -> PipelineOrchestrator:
    """Get or create the pipeline orchestrator for the given LLM provider."""
    if provider not in _pipeline_orchestrators:
        _pipeline_orchestrators[provider] = PipelineOrchestrator(
            sql_generator=get_sql_generator(provider),
            explanation_generator=get_explanation_generator(provider),
            chart_recommender=get_chart_recommender(provider)
        )
    return _pipeline_orchestrators[provider]
