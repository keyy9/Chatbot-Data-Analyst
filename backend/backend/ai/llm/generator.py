"""
LLM Generator Module.

Orchestrates LLM-based generation for SQL, explanations, and chart recommendations.
Combines prompts, client, and validators into high-level generation functions.
"""

import logging
import re
from typing import Optional, Dict, Any, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime

from backend.ai.llm.client import (
    LLMClient,
    get_llm_client,
    parse_json_response
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


def ensure_deterministic_order(sql: str) -> str:
    """
    Give a grouped query a stable row order when the model left it out.

    A `GROUP BY` without `ORDER BY` returns rows in whatever order Postgres
    finds convenient, so the same question can answer differently between runs.
    The prompt asks for an explicit ORDER BY, but a small model forgets, so this
    guarantees it instead of hoping.

    `ORDER BY 1` sorts by the first selected column - the grouping label - which
    is what a plain breakdown ("how many customers in each tier") wants. It only
    reorders rows; the set of rows is unchanged, so no answer can become wrong.

    Left alone when the query already has ORDER BY, has no GROUP BY, or carries a
    LIMIT (a LIMIT without ORDER BY is a ranking the model built deliberately -
    reordering there could change which rows come back).

    Pure function: no I/O, so the rule can be tested directly.
    """
    if not sql:
        return sql

    stripped = sql.strip().rstrip(";").strip()
    upper = stripped.upper()

    if "GROUP BY" not in upper:
        return sql
    if re.search(r"\bORDER\s+BY\b", upper):
        return sql
    if re.search(r"\bLIMIT\b", upper):
        return sql

    logger.info("Added ORDER BY 1 to a grouped query that had no explicit ordering")
    return f"{stripped} ORDER BY 1"


def aggregate_llm_usage(*llm_responses: Optional[Dict]) -> Dict[str, Any]:
    """
    Sum token/cost/latency across the LLM calls made for one user question.

    Answering one question takes several LLM calls (SQL, explanation, chart),
    so the per-question figures worth recording are the totals. Calls that
    didn't happen - a step that failed or fell back to a rules-based path -
    come through as None and are skipped, so `llm_calls` says how many of the
    totals are actually backed by a real call.

    Pure function: no I/O, no LLM access.
    """
    total_input = 0
    total_output = 0
    total_cost = 0.0
    total_latency = 0.0
    calls = 0
    model_name: Optional[str] = None

    for response in llm_responses:
        if not response:
            continue
        calls += 1
        total_input += response.get("input_tokens") or 0
        total_output += response.get("output_tokens") or 0
        total_cost += response.get("estimated_cost") or 0.0
        total_latency += response.get("latency_ms") or 0.0
        if model_name is None:
            model_name = response.get("model")

    return {
        "llm_calls": calls,
        "model_name": model_name,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "estimated_cost": round(total_cost, 8),
        "llm_latency_ms": round(total_latency, 2),
    }


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
        llm_response: LLM response metadata, or None when the rules-based
            fallback produced the recommendation without calling the LLM
    """
    recommendation: ChartRecommendation
    chart_type: str
    confidence_score: float
    reason: str
    alternatives: list
    configuration: Dict
    generation_time_ms: float = 0.0
    llm_response: Optional[Dict] = None


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
        conversation_context: str = "",
        error_feedback: Optional[str] = None,
        allow_writes: bool = False
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
            allow_writes: True on the admin path, so the prompt asks for an
                INSERT/UPDATE/DELETE when the request is a modification.
                Leaving this False on a write request yields a SELECT and the
                change silently never happens.

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
                conversation_context=conversation_context,
                allow_writes=allow_writes
            )

            # On a repair attempt, tell the model exactly what went wrong with
            # its previous SQL so it can correct the specific column/table/value
            # instead of blindly regenerating the same broken query.
            user_prompt = prompt["user"]
            if error_feedback:
                user_prompt = (
                    f"{user_prompt}\n\n## PREVIOUS ATTEMPT FAILED\n{error_feedback}\n"
                    "Return a corrected PostgreSQL SELECT query that fixes this error. "
                    "Use only real tables/columns from the schema above."
                )

            # ============ Step 3: Call LLM for SQL generation ============
            llm_response = self.llm_client.generate(
                system_prompt=prompt["system"],
                user_prompt=user_prompt
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

        return ensure_deterministic_order(sql.strip().rstrip(";").strip())


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
        use_llm: Optional[bool] = None,
        conversation_context: str = ""
    ) -> ExplanationResult:
        """
        Generate a natural language explanation for a query result.

        Args:
            user_question: The user's original question.
            generated_sql: The SQL that was executed.
            query_result: The database query result.
            use_llm: Optional override for whether to use the LLM.
            conversation_context: Recent conversation history so the
                explanation can reference prior turns and flow naturally.

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
                query_result,
                conversation_context=conversation_context
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
        llm_usage: Optional[Dict] = None

        if use_llm_final:
            try:
                prompt = self.chart_manager.build_chart_recommendation_prompt(
                    data, columns, user_question, generated_sql
                )
                # generate() + parse_json_response() rather than generate_json():
                # the latter throws the LLMResponse away, and with it the token
                # and cost figures this call contributes to the per-question total.
                response = self.llm_client.generate(
                    system_prompt=prompt["system"],
                    user_prompt=prompt["user"],
                    max_tokens=512
                )
                # Record usage before parsing: those tokens were spent even if
                # the model returned malformed JSON and we fall back below.
                llm_usage = response.to_dict()
                parsed = parse_json_response(response)

                from backend.ai.prompts.chart_prompt import ChartType

                recommendation = ChartRecommendation(
                    chart_type=ChartType(parsed.get("chart_type", "table")),
                    confidence_score=float(parsed.get("confidence_score", 0.7)),
                    reason=parsed.get("reason", "LLM-recommended chart"),
                    alternative_charts=[
                        ChartType(c) for c in parsed.get("alternatives", [])
                        if c in [ct.value for ct in ChartType]
                    ],
                    configuration=parsed.get("configuration", {})
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
            generation_time_ms=(time.time() - start_time) * 1000,
            llm_response=llm_usage
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
            logger.warning(f"SQL execution failed, attempting one self-repair: {str(e)}")

            # One repair attempt: feed the failed SQL and the exact DB error
            # back to the model so it can fix a wrong column/table/literal
            # rather than returning a confusing hard error to the user.
            repair_result = self.sql_generator.generate(
                user_question,
                schema_definition,
                check_ambiguity=False,
                override_system_prompt=override_system_prompt,
                conversation_context=conversation_context,
                error_feedback=f"Failed SQL:\n{sql_result.sql}\n\nDatabase error:\n{str(e)}"
            )

            if not (repair_result.is_valid and repair_result.sql):
                logger.error(f"SQL self-repair could not produce a valid query: {str(e)}")
                return {"status": "error", "error": f"SQL execution failed: {str(e)}"}

            try:
                data, columns, execution_time = query_executor_callback(repair_result.sql)
                sql_result = repair_result  # use the repaired query downstream
                logger.info("SQL self-repair succeeded on retry")
            except Exception as e2:
                logger.error(f"SQL execution failed after self-repair: {str(e2)}")
                return {"status": "error", "error": f"SQL execution failed: {str(e2)}"}

        # ============ Steps 3-8: Turn the rows into an answer ============
        return self.build_answer(
            user_question=user_question,
            sql=sql_result.sql,
            data=data,
            columns=columns,
            execution_time=execution_time,
            conversation_context=conversation_context,
            sql_llm_response=sql_result.llm_response,
            sql_generation_time_ms=sql_result.generation_time_ms
        )

    def build_answer(
        self,
        user_question: str,
        sql: str,
        data: list,
        columns: list,
        execution_time: float,
        conversation_context: str = "",
        sql_llm_response: Optional[Dict] = None,
        sql_generation_time_ms: float = 0.0
    ) -> Dict[str, Any]:
        """
        Explain, chart, attribute and format an already-executed query.

        Split out of `process()` so callers that have to generate and execute
        the SQL themselves still produce the same answer through the same
        code. The admin route is the reason: it authorizes each statement and
        branches on read vs write *before* anything runs, so it cannot hand
        control to `process()` - but it should not own a second copy of the
        explain/chart/format logic either.

        Args:
            user_question: The question being answered.
            sql: The SQL that produced `data`.
            data: Result rows.
            columns: Result column names.
            execution_time: How long the query took, in ms.
            conversation_context: Prior turns, for a context-aware explanation.
            sql_llm_response: LLM metadata from generating `sql`, so its tokens
                count toward the per-question total.
            sql_generation_time_ms: How long generating `sql` took, in ms.

        Returns:
            Dict: the same success payload shape `process()` returns.
        """
        # ============ Step 3: Generate Explanation ============
        query_result = QueryResult(
            data=data,
            row_count=len(data) if isinstance(data, list) else 1,
            columns=columns,
            execution_time=execution_time
        )

        explanation_result = self.explanation_generator.generate(
            user_question,
            sql,
            query_result,
            conversation_context=conversation_context
        )

        # ============ Step 4: Recommend Chart ============
        chart_result = self.chart_recommender.recommend(
            data,
            columns,
            user_question,
            sql
        )

        # ============ Step 5: Attribute Sources ============
        sources = self.source_attributor.build_sources(
            sql,
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
        suggested_questions = self.explanation_generator.explanation_manager.generate_suggested_questions(
            user_question, sql, columns, data
        )

        # ============ Step 8: Format Final Response ============
        logger.info("Pipeline completed successfully")

        return {
            "status": "success",
            "user_question": user_question,
            "generated_sql": sql,
            "explanation": explanation_result.explanation,
            "suggested_questions": suggested_questions,
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
                "sql_generation_time_ms": sql_generation_time_ms,
                "query_execution_time_ms": execution_time,
                "explanation_generation_time_ms": explanation_result.generation_time_ms,
                "chart_recommendation_time_ms": chart_result.generation_time_ms,
                "timestamp": datetime.utcnow().isoformat(),
                # Token/cost/latency totals across every LLM call this question
                # needed, so usage can be persisted and reported per query.
                **aggregate_llm_usage(
                    sql_llm_response,
                    explanation_result.llm_response,
                    chart_result.llm_response
                )
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
