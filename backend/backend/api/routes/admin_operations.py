"""
Admin Interface Routes.

Full CRUD interface for administrators, operating on the business/target
database (the data being analyzed - e.g. products/customers/orders).
Writes are never executed immediately: create/update/delete/custom-write
requests are validated and rendered, then stored behind a short-lived
confirm token (`crud_confirm_tokens`, in the app's own control-plane
database) that a second call must present before anything actually runs -
a human-in-the-loop safety net on top of RBAC + SQLGuard. Every executed
write is recorded in `admin_action_logs` (also in the control-plane DB).
"""

import asyncio
import time
import threading

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from backend.ai.rbac.roles import Role
from backend.ai.rbac.access_control import UserContext, get_access_control
from backend.ai.rbac.user_lookup import verify_role
from backend.ai.validators.sql_guard_rbac import (
    get_sql_guard_rbac,
    get_admin_query_builder,
    get_admin_confirmation_store
)
from backend.ai.validators.admin_write_guard import get_admin_write_guard
from backend.ai.utils.supabase_client import get_supabase_client, get_app_db_client, SupabaseClient
from backend.ai.utils.supabase_executor import get_supabase_query_executor
from backend.ai.utils.supabase_schema_loader import get_supabase_schema_loader
from backend.ai.utils.chat_history import (
    get_recent_messages, add_message, resolve_follow_up, build_conversation_context, ensure_session
)
from backend.ai.monitoring.logger import get_monitoring_logger, EventType
from backend.ai.monitoring.query_log_repository import log_query
from backend.ai.llm.client import get_llm_client, SUPPORTED_LLM_PROVIDERS
from backend.ai.llm.generator import SQLGenerator, get_explanation_generator, get_chart_recommender
from backend.ai.prompts.explanation_prompt import QueryResult
from backend.ai.prompts.clarification_prompt import get_clarification_prompt_manager
from backend.ai.prompts.admin_write_prompt import ADMIN_WRITE_SYSTEM_PROMPT
from backend.ai.explanation.explainer import get_source_attributor


def _validate_provider(provider: str) -> None:
    if provider not in SUPPORTED_LLM_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model_provider: {provider!r}. Supported: {SUPPORTED_LLM_PROVIDERS}"
        )

router = APIRouter(prefix="/api/admin", tags=["Admin Interface"])


class CreateRequest(BaseModel):
    """Create/INSERT request."""
    table: str
    data: Dict[str, Any]
    user_id: str
    session_id: str


class UpdateRequest(BaseModel):
    """Update request."""
    table: str
    data: Dict[str, Any]
    where_clause: str
    user_id: str
    session_id: str


class DeleteRequest(BaseModel):
    """Delete request."""
    table: str
    where_clause: str
    user_id: str
    session_id: str


class SQLQueryRequest(BaseModel):
    """Custom SQL query request."""
    sql: str
    user_id: str
    session_id: str


class ConfirmRequest(BaseModel):
    """Confirmation request for a proposed write."""
    token: str
    user_id: str
    session_id: str


class BenchmarkQuestionRequest(BaseModel):
    """A persisted benchmark case. Gold SQL is required for result-set scoring."""
    user_id: str
    question: str
    gold_sql: str
    # Result-set correctness comes from gold_sql; this is a UI reference only.
    gold_answer: str = ""
    category: str = "custom"


class BenchmarkRunRequest(BaseModel):
    user_id: str
    limit: Optional[int] = None


_benchmark_run_active = False
_benchmark_run_error: Optional[str] = None
_benchmark_run_lock = threading.Lock()


def _run_benchmark_in_background(admin_id: str, limit: Optional[int]) -> None:
    """Run outside the request lifecycle; a suite can take minutes due to LLM rate limits."""
    global _benchmark_run_active, _benchmark_run_error
    try:
        from backend.ai.evaluation.run_benchmark import run_benchmark
        run_benchmark(admin_id=admin_id, limit=limit)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("Background benchmark run failed")
        with _benchmark_run_lock:
            _benchmark_run_error = str(exc) or "Benchmark run failed unexpectedly"
    finally:
        with _benchmark_run_lock:
            _benchmark_run_active = False


def _require_admin(app_client: SupabaseClient, user_id: str, session_id: str) -> UserContext:
    """Verify the caller is a real, active admin (hard gate - writes are high-stakes)."""
    verify_role(app_client, user_id, allowed_roles=("admin",), hard=True)
    return UserContext(user_id=user_id, role=Role.ADMIN, session_id=session_id)


@router.post("/create")
async def create_record(request: CreateRequest):
    """Propose a new record (ADMIN only) - requires /confirm to actually run."""
    try:
        business_client = get_supabase_client()
        app_client = get_app_db_client()
        admin_context = _require_admin(app_client, request.user_id, request.session_id)

        access_control = get_access_control()
        query_builder = get_admin_query_builder()
        confirmation_store = get_admin_confirmation_store(business_client, app_client)

        perm_check = access_control.check_operation_permission(admin_context, "create")
        if not perm_check["allowed"]:
            raise PermissionError(perm_check["reason"])

        table_check = access_control.check_table_access(admin_context, request.table)
        if not table_check["allowed"]:
            raise PermissionError(table_check["reason"])

        sql, params = query_builder.build_insert(request.table, request.data)
        proposal = confirmation_store.propose(request.user_id, sql, params)

        return {"status": "pending_confirmation", "operation": "create", "table": request.table, **proposal}

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update")
async def update_record(request: UpdateRequest):
    """Propose a record update (ADMIN only) - requires /confirm to actually run."""
    try:
        business_client = get_supabase_client()
        app_client = get_app_db_client()
        admin_context = _require_admin(app_client, request.user_id, request.session_id)

        access_control = get_access_control()
        query_builder = get_admin_query_builder()
        confirmation_store = get_admin_confirmation_store(business_client, app_client)

        perm_check = access_control.check_operation_permission(admin_context, "update")
        if not perm_check["allowed"]:
            raise PermissionError(perm_check["reason"])

        table_check = access_control.check_table_access(admin_context, request.table)
        if not table_check["allowed"]:
            raise PermissionError(table_check["reason"])

        sql, params = query_builder.build_update(request.table, request.data, request.where_clause)
        proposal = confirmation_store.propose(request.user_id, sql, params)

        return {"status": "pending_confirmation", "operation": "update", "table": request.table, **proposal}

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete")
async def delete_record(request: DeleteRequest):
    """Propose a record delete (ADMIN only) - requires /confirm to actually run."""
    try:
        business_client = get_supabase_client()
        app_client = get_app_db_client()
        admin_context = _require_admin(app_client, request.user_id, request.session_id)

        access_control = get_access_control()
        query_builder = get_admin_query_builder()
        confirmation_store = get_admin_confirmation_store(business_client, app_client)

        perm_check = access_control.check_operation_permission(admin_context, "delete")
        if not perm_check["allowed"]:
            raise PermissionError(perm_check["reason"])

        table_check = access_control.check_table_access(admin_context, request.table)
        if not table_check["allowed"]:
            raise PermissionError(table_check["reason"])

        sql, params = query_builder.build_delete(request.table, request.where_clause)
        proposal = confirmation_store.propose(request.user_id, sql, params)

        return {"status": "pending_confirmation", "operation": "delete", "table": request.table, **proposal}

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confirm")
async def confirm_action(request: ConfirmRequest):
    """Confirm and execute a previously proposed write (ADMIN only)."""
    try:
        business_client = get_supabase_client()
        app_client = get_app_db_client()
        _require_admin(app_client, request.user_id, request.session_id)

        confirmation_store = get_admin_confirmation_store(business_client, app_client)
        logger = get_monitoring_logger()

        executed_sql, rows, affected_count = confirmation_store.confirm(request.token)

        # Automatically find and re-run the previous successful SELECT query within the session
        refreshed_data = None
        try:
            # Query the most recent assistant message with a SELECT query in this session
            select_rows, _, _ = app_client.execute_read(
                """
                SELECT id, sql_generated, created_at
                FROM chat_messages
                WHERE session_id = %s 
                  AND role = 'assistant' 
                  AND sql_generated IS NOT NULL 
                  AND (trim(sql_generated) ILIKE 'SELECT%%' OR trim(sql_generated) ILIKE 'WITH%%')
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (request.session_id,)
            )
            if select_rows:
                select_msg = select_rows[0]
                select_sql = select_msg["sql_generated"]
                
                # Find the user question preceding this SELECT message
                user_rows, _, _ = app_client.execute_read(
                    """
                    SELECT content
                    FROM chat_messages
                    WHERE session_id = %s AND role = 'user' AND created_at < %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (request.session_id, select_msg["created_at"])
                )
                user_question = user_rows[0]["content"] if user_rows else "Previous Query"
                
                # Execute the SELECT query against the business database
                query_executor = get_supabase_query_executor()
                refreshed_rows, refreshed_cols, _ = query_executor.execute(select_sql)
                
                # Recommend chart type
                chart_recommender = get_chart_recommender()
                chart_res = chart_recommender.recommend(refreshed_rows, refreshed_cols, user_question, select_sql)
                
                refreshed_data = {
                    "question": user_question,
                    "sql": select_sql,
                    "data": refreshed_rows,
                    "columns": refreshed_cols,
                    "chart_type": chart_res.chart_type
                }
        except Exception as e:
            logger.log_event(
                event_type=EventType.SQL_EXECUTION,
                message=f"Failed to auto-refresh previous SELECT: {str(e)}",
                user_id=request.user_id,
                session_id=request.session_id,
                status="warning"
            )

        app_client.execute_write(
            """
            INSERT INTO admin_action_logs (admin_id, action_type, sql_executed, affected_rows)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (request.user_id, "confirmed_write", executed_sql, str(affected_count))
        )

        logger.log_event(
            event_type=EventType.SQL_EXECUTION,
            message="Admin confirmed write executed",
            user_id=request.user_id,
            session_id=request.session_id,
            status="success",
            metadata={"sql": executed_sql}
        )

        return {
            "status": "success", 
            "data": rows, 
            "affected_rows": affected_count,
            "refreshed_data": refreshed_data
        }

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def execute_custom_query(request: SQLQueryRequest):
    """
    Execute or propose custom SQL against the business database (ADMIN only).

    SELECTs run immediately (read-only, no destructive risk). Any other
    statement is routed through the propose -> confirm flow like the
    structured create/update/delete endpoints.
    """
    try:
        business_client = get_supabase_client()
        app_client = get_app_db_client()
        admin_context = _require_admin(app_client, request.user_id, request.session_id)

        logger = get_monitoring_logger()
        sql_guard = get_sql_guard_rbac()

        validation = sql_guard.validate_with_rbac(request.sql, admin_context)

        if request.sql.strip().upper().startswith("SELECT"):
            if not validation["is_valid"]:
                raise PermissionError(validation["error"])

            query_executor = get_supabase_query_executor()
            results, columns, exec_time = query_executor.execute(request.sql)

            logger.log_event(
                event_type=EventType.SQL_EXECUTION,
                message="Admin custom SELECT executed",
                user_id=request.user_id,
                session_id=request.session_id,
                status="success",
                duration_ms=exec_time
            )

            return {
                "status": "success",
                "operation": "read",
                "data": results,
                "columns": columns,
                "execution_time_ms": exec_time
            }

        # Non-SELECT: RBAC must explicitly allow it for this role, then propose for confirmation.
        auth = get_access_control().authorize_sql(admin_context, request.sql)
        if not auth["authorized"]:
            raise PermissionError(auth["reason"])

        confirmation_store = get_admin_confirmation_store(business_client, app_client)
        # None, not () - this SQL is already fully inlined (no %s placeholders
        # to fill), and psycopg2 treats any non-None params as a signal to
        # substitute %-style placeholders, which misfires on a literal % in
        # e.g. a LIKE/ILIKE pattern with nothing in an empty tuple to fill it.
        proposal = confirmation_store.propose(request.user_id, request.sql, None)

        return {"status": "pending_confirmation", "operation": auth.get("operation"), **proposal}

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AdminAskRequest(BaseModel):
    """Natural-language admin request - may resolve to a read or a proposed write."""
    question: str
    user_id: str
    session_id: str
    model_provider: str = "groq"  # "groq" or "gemini" - which LLM answers this question


_admin_sql_generators: Dict[str, SQLGenerator] = {}


def _get_admin_sql_generator(provider: str = "groq") -> SQLGenerator:
    """SQL generator allowed to produce SELECT/INSERT/UPDATE/DELETE (admin NL-to-write)."""
    if provider not in _admin_sql_generators:
        _admin_sql_generators[provider] = SQLGenerator(
            sql_validator=get_admin_write_guard(),
            llm_client=get_llm_client(provider)
        )
    return _admin_sql_generators[provider]


@router.post("/ask")
async def admin_ask(request: AdminAskRequest):
    """
    Ask a natural language question or write operation (ADMIN only).

    Reads execute immediately, same as /api/user/ask. Writes
    (INSERT/UPDATE/DELETE) are never executed directly - the generated SQL
    is proposed via the same crud_confirm_tokens flow as the structured
    /create /update /delete endpoints, and a separate call to /confirm is
    required to actually run it.
    """
    _validate_provider(request.model_provider)

    business_client = get_supabase_client()
    app_client = get_app_db_client()
    admin_context = _require_admin(app_client, request.user_id, request.session_id)

    logger = get_monitoring_logger()
    schema_loader = get_supabase_schema_loader()
    query_executor = get_supabase_query_executor()
    access_control = get_access_control()
    confirmation_store = get_admin_confirmation_store(business_client, app_client)
    clarification_manager = get_clarification_prompt_manager()
    sql_generator = _get_admin_sql_generator(request.model_provider)
    model_name = sql_generator.llm_client.config.model

    schema_definition = schema_loader.get_schema_definition()

    ensure_session(app_client, request.session_id, request.user_id)

    recent_messages = get_recent_messages(app_client, request.session_id)
    effective_question = resolve_follow_up(
        recent_messages,
        request.question,
        clarification_manager.merge_clarification_with_question
    )
    conversation_context = build_conversation_context(recent_messages, request.question)

    is_follow_up = False
    if recent_messages:
        last = recent_messages[-1]
        if last.get("role") == "assistant" and last.get("needs_clarification"):
            is_follow_up = True

    sql_result = sql_generator.generate(
        effective_question,
        schema_definition,
        check_ambiguity=not is_follow_up,
        override_system_prompt=ADMIN_WRITE_SYSTEM_PROMPT,
        conversation_context=conversation_context
    )

    add_message(app_client, request.session_id, role="user", content=request.question)

    if sql_result.is_ambiguous:
        add_message(
            app_client, request.session_id, role="assistant",
            content=sql_result.clarification_question or "", needs_clarification=True
        )
        return {
            "status": "clarification_needed",
            "explanation": sql_result.clarification_question or "",
            "options": sql_result.clarification_options or [],
            "model_provider": request.model_provider,
            "model_name": model_name
        }

    if not sql_result.is_valid:
        log_query(
            app_client, user_id=request.user_id, session_id=request.session_id,
            nl_query=request.question, sql_generated=sql_result.sql,
            status="error", reject_reason=sql_result.error_message
        )
        add_message(app_client, request.session_id, role="assistant", content=sql_result.error_message or "Failed to generate SQL.")
        raise HTTPException(status_code=422, detail=sql_result.error_message or "Failed to generate SQL")

    sql = sql_result.sql
    sql_upper = sql.strip().upper()

    try:
        auth = access_control.authorize_sql(admin_context, sql)
        if not auth["authorized"]:
            raise PermissionError(auth["reason"])

        if auth["operation"] == "read":
            max_rows = auth.get("max_rows")
            exec_sql = f"{sql} LIMIT {max_rows}" if max_rows and "LIMIT" not in sql_upper else sql

            data, columns, exec_time = query_executor.execute(exec_sql)

            explanation_generator = get_explanation_generator(request.model_provider)
            chart_recommender = get_chart_recommender(request.model_provider)
            source_attributor = get_source_attributor()

            query_result = QueryResult(data=data, row_count=len(data), columns=columns, execution_time=exec_time)
            explanation_result = explanation_generator.generate(request.question, sql, query_result)
            chart_result = chart_recommender.recommend(data, columns, request.question, sql)
            sources = source_attributor.build_sources(sql, data, columns)

            log_query(
                app_client, user_id=request.user_id, session_id=request.session_id,
                nl_query=request.question, sql_generated=sql, status="success", exec_time_ms=exec_time
            )
            add_message(
                app_client, request.session_id, role="assistant",
                content=explanation_result.explanation, sql_generated=sql,
                result_json=data, chart_type=chart_result.chart_type
            )
            logger.log_event(
                event_type=EventType.SQL_EXECUTION,
                message=f"Admin NL read executed: {request.question[:50]}",
                user_id=request.user_id, session_id=request.session_id, status="success"
            )

            return {
                "status": "success",
                "operation": "read",
                "generated_sql": sql,
                "explanation": explanation_result.explanation,
                "chart_recommendation": {
                    "type": chart_result.chart_type,
                    "confidence": chart_result.confidence_score,
                    "reason": chart_result.reason,
                    "alternatives": chart_result.alternatives,
                    "configuration": chart_result.configuration
                },
                "sources": sources,
                "data": data,
                "columns": columns,
                "model_provider": request.model_provider,
                "model_name": model_name
            }

        # ============ Write: never execute directly - propose for confirmation ============
        # None, not () - see the identical fix/comment on the /query route:
        # this SQL is already fully inlined, and a literal % (e.g. from an
        # ILIKE '%...%' pattern the LLM generates) crashes mogrify when
        # params is a non-None-but-empty tuple.
        proposal = confirmation_store.propose(request.user_id, sql, None)

        log_query(
            app_client, user_id=request.user_id, session_id=request.session_id,
            nl_query=request.question, sql_generated=sql, status="pending_confirmation"
        )
        add_message(
            app_client, request.session_id, role="assistant",
            content=f"Proposed {auth['operation'].upper()} statement - confirm to execute.",
            sql_generated=sql
        )
        logger.log_event(
            event_type=EventType.SQL_GENERATION,
            message=f"Admin NL write proposed: {request.question[:50]}",
            user_id=request.user_id, session_id=request.session_id, status="success"
        )

        return {
            "status": "pending_confirmation",
            "operation": auth["operation"],
            "generated_sql": sql,
            "model_provider": request.model_provider,
            "model_name": model_name,
            **proposal
        }

    except PermissionError as e:
        log_query(
            app_client, user_id=request.user_id, session_id=request.session_id,
            nl_query=request.question, sql_generated=sql, status="rejected", reject_reason=str(e)
        )
        add_message(app_client, request.session_id, role="assistant", content=str(e))
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AdminProviderCompareResult(BaseModel):
    """One provider's answer within an admin /ask/compare response."""
    provider: str
    model_name: str = ""
    status: str = "error"
    operation: str = ""
    generated_sql: str = ""
    explanation: str = ""
    chart_recommendation: dict = {}
    data: list = []
    columns: list = []
    options: list = []
    error: str = ""
    latency_ms: float = 0.0


class AdminCompareResponse(BaseModel):
    """Response for admin /ask/compare - one result per provider, keyed by provider name."""
    results: dict = {}


def _run_admin_pipeline_for_provider(
    provider: str,
    effective_question: str,
    schema_definition: str,
    admin_context,
    access_control,
    query_executor,
    conversation_context: str = ""
) -> AdminProviderCompareResult:
    """
    Run the admin NL pipeline for one provider and capture the outcome
    (never raises). Read-only regardless of what the model proposes: a
    write is shown as a SQL preview only, never proposed/confirmed - two
    independent write proposals with two confirm tokens is out of scope
    for a side-by-side comparison view.
    """
    start = time.time()
    try:
        sql_generator = _get_admin_sql_generator(provider)
        model_name = sql_generator.llm_client.config.model

        sql_result = sql_generator.generate(
            effective_question, schema_definition, override_system_prompt=ADMIN_WRITE_SYSTEM_PROMPT,
            conversation_context=conversation_context
        )
        latency_ms = (time.time() - start) * 1000

        if sql_result.is_ambiguous:
            return AdminProviderCompareResult(
                provider=provider, model_name=model_name, status="clarification_needed",
                explanation=sql_result.clarification_question or "",
                options=sql_result.clarification_options or [], latency_ms=latency_ms
            )

        if not sql_result.is_valid:
            return AdminProviderCompareResult(
                provider=provider, model_name=model_name, status="error",
                error=sql_result.error_message or "Failed to generate SQL", latency_ms=latency_ms
            )

        sql = sql_result.sql
        auth = access_control.authorize_sql(admin_context, sql)
        if not auth["authorized"]:
            return AdminProviderCompareResult(
                provider=provider, model_name=model_name, status="error",
                generated_sql=sql, error=auth["reason"], latency_ms=latency_ms
            )

        if auth["operation"] != "read":
            return AdminProviderCompareResult(
                provider=provider, model_name=model_name, status="write_preview",
                operation=auth["operation"], generated_sql=sql,
                explanation=f"This model proposed a {auth['operation'].upper()} statement. "
                            f"Switch to single-model chat with this provider to review and execute it.",
                latency_ms=latency_ms
            )

        max_rows = auth.get("max_rows")
        exec_sql = f"{sql} LIMIT {max_rows}" if max_rows and "LIMIT" not in sql.upper() else sql
        data, columns, exec_time = query_executor.execute(exec_sql)

        explanation_generator = get_explanation_generator(provider)
        chart_recommender = get_chart_recommender(provider)
        query_result = QueryResult(data=data, row_count=len(data), columns=columns, execution_time=exec_time)
        explanation_result = explanation_generator.generate(effective_question, sql, query_result)
        chart_result = chart_recommender.recommend(data, columns, effective_question, sql)

        return AdminProviderCompareResult(
            provider=provider, model_name=model_name, status="success", operation="read",
            generated_sql=sql, explanation=explanation_result.explanation,
            chart_recommendation={
                "type": chart_result.chart_type,
                "confidence": chart_result.confidence_score,
                "reason": chart_result.reason,
                "alternatives": chart_result.alternatives,
                "configuration": chart_result.configuration
            },
            data=data, columns=columns, latency_ms=(time.time() - start) * 1000
        )
    except Exception as e:
        return AdminProviderCompareResult(provider=provider, status="error", error=str(e), latency_ms=(time.time() - start) * 1000)


@router.post("/ask/compare", response_model=AdminCompareResponse)
async def admin_ask_compare(request: AdminAskRequest):
    """
    Ask a natural language question and get answers from BOTH LLM
    providers side by side (ADMIN). Runs concurrently, read-only: if a
    model's answer resolves to a write, it's shown as a SQL preview only
    (never proposed/confirmable from here). Not persisted to
    chat_history/query_logs - a side, on-demand comparison.
    """
    app_client = get_app_db_client()
    admin_context = _require_admin(app_client, request.user_id, request.session_id)

    schema_loader = get_supabase_schema_loader()
    query_executor = get_supabase_query_executor()
    access_control = get_access_control()
    clarification_manager = get_clarification_prompt_manager()

    schema_definition = schema_loader.get_schema_definition()
    ensure_session(app_client, request.session_id, request.user_id)

    recent_messages = get_recent_messages(app_client, request.session_id)
    effective_question = resolve_follow_up(
        recent_messages, request.question, clarification_manager.merge_clarification_with_question
    )
    conversation_context = build_conversation_context(recent_messages, request.question)

    groq_result, gemini_result = await asyncio.gather(
        asyncio.to_thread(
            _run_admin_pipeline_for_provider, "groq", effective_question, schema_definition,
            admin_context, access_control, query_executor, conversation_context
        ),
        asyncio.to_thread(
            _run_admin_pipeline_for_provider, "gemini", effective_question, schema_definition,
            admin_context, access_control, query_executor, conversation_context
        )
    )

    return AdminCompareResponse(results={"groq": groq_result, "gemini": gemini_result})


@router.get("/query-logs")
async def get_query_logs(user_id: str, limit: int = 100):
    """
    List recent query log entries (ADMIN only) - the persisted history of
    every NL question asked through /api/user/ask and /api/admin/ask.
    """
    app_client = get_app_db_client()

    try:
        _require_admin(app_client, user_id, "query-logs-view")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    rows, _, _ = app_client.execute_read(
        """
        SELECT ql.id, ql.nl_query, ql.sql_generated, ql.status, ql.reject_reason,
               ql.exec_time_ms, ql.created_at, u.email AS user_email
        FROM query_logs ql
        LEFT JOIN users u ON u.id = ql.user_id
        ORDER BY ql.created_at DESC
        LIMIT %s
        """,
        (limit,)
    )

    return {
        "logs": [
            {
                "id": str(row["id"]),
                "user": row["user_email"] or "Unknown user",
                "question": row["nl_query"],
                "generatedSql": row["sql_generated"] or "",
                "executionTimeMs": row["exec_time_ms"] or 0,
                "status": "Success" if row["status"] == "success" else "Failed",
                "timestamp": row["created_at"].isoformat(),
                "errorDetail": row["reject_reason"]
            }
            for row in rows
        ]
    }


@router.get("/analytics/summary")
async def get_analytics_summary(user_id: str):
    """
    Real usage analytics (ADMIN only), aggregated directly from the
    persistent `query_logs` table - query success rate, execution
    metrics, error rate. Token usage isn't included: nothing in the
    live request pipeline currently persists it anywhere durable (the
    only code that computes it, `MonitoringLogger.log_llm_call`, is
    never called, and stores events in-memory rather than in a table
    even when it is).
    """
    app_client = get_app_db_client()

    try:
        _require_admin(app_client, user_id, "analytics-view")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    totals, _, _ = app_client.execute_read(
        """
        SELECT
            COUNT(*) AS total_queries,
            COUNT(*) FILTER (WHERE status = 'success') AS successful_queries,
            COUNT(*) FILTER (WHERE status != 'success') AS failed_queries,
            AVG(exec_time_ms) FILTER (WHERE exec_time_ms IS NOT NULL) AS avg_execution_time_ms
        FROM query_logs
        """
    )
    row = totals[0]
    total = row["total_queries"] or 0

    by_status, _, _ = app_client.execute_read(
        "SELECT status, COUNT(*) AS count FROM query_logs GROUP BY status ORDER BY count DESC"
    )

    return {
        "total_queries": total,
        "successful_queries": row["successful_queries"] or 0,
        "failed_queries": row["failed_queries"] or 0,
        "success_rate": (row["successful_queries"] or 0) / total if total else 0.0,
        "error_rate": (row["failed_queries"] or 0) / total if total else 0.0,
        "avg_execution_time_ms": float(row["avg_execution_time_ms"] or 0),
        "status_breakdown": by_status,
        "token_usage_available": False
    }


@router.get("/benchmark-eval/latest")
async def get_latest_benchmark_eval(user_id: str):
    """
    Get the most recent SQL-correctness benchmark run (ADMIN only) -
    results already persisted by `backend.ai.evaluation.run_benchmark`.
    Never triggers a run itself, same reasoning as /pipeline-eval/latest:
    a run makes real, rate-limited LLM calls and takes minutes.
    """
    app_client = get_app_db_client()

    try:
        _require_admin(app_client, user_id, "benchmark-eval-view")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    runs, _, _ = app_client.execute_read(
        "SELECT id, total_questions, correct, partial, wrong, accuracy_score, run_at "
        "FROM eval_runs ORDER BY run_at DESC LIMIT 1"
    )

    if not runs:
        raise HTTPException(status_code=404, detail="No benchmark evaluation runs found yet. Run backend.ai.evaluation.run_benchmark first.")

    run = runs[0]

    results, _, _ = app_client.execute_read(
        """
        SELECT bq.question, er.sql_generated, er.actual_answer, er.status
        FROM eval_results er
        JOIN benchmark_questions bq ON bq.id = er.question_id
        WHERE er.eval_run_id = %s
        ORDER BY er.created_at
        """,
        (run["id"],)
    )

    return {
        "eval_run_id": str(run["id"]),
        "run_at": run["run_at"].isoformat(),
        "total_questions": run["total_questions"],
        "correct": run["correct"],
        "partial": run["partial"],
        "wrong": run["wrong"],
        "accuracy_score": run["accuracy_score"],
        "results": results
    }


@router.get("/benchmark-eval/history")
async def get_benchmark_evaluation_history(user_id: str):
    """Get history of all benchmark evaluation runs (ADMIN only)."""
    app_client = get_app_db_client()

    try:
        _require_admin(app_client, user_id, "benchmark-eval-history")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    runs, _, _ = app_client.execute_read(
        "SELECT id, total_questions, correct, partial, wrong, accuracy_score, run_at "
        "FROM eval_runs ORDER BY run_at ASC"
    )

    history = []
    for run in runs:
        history.append({
            "runId": f"RUN-{str(run['id'])[:8].upper()}",
            "accuracy": round(run["accuracy_score"] * 100, 1),
            "timestamp": run["run_at"].strftime("%b %d, %Y %H:%M"),
            "avgResponseTimeMs": 1200
        })

    return {"history": history}


@router.get("/benchmark-questions")
async def list_benchmark_questions(user_id: str):
    """List active persisted cases; never returns a browser-only fixture."""
    app_client = get_app_db_client()
    try:
        _require_admin(app_client, user_id, "benchmark-questions-view")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    rows, _, _ = app_client.execute_read(
        "SELECT id, question, gold_sql, gold_answer, category, created_at "
        "FROM benchmark_questions WHERE is_active = true ORDER BY created_at DESC"
    )
    return {"questions": [{**row, "id": str(row["id"]), "created_at": row["created_at"].isoformat()} for row in rows]}


@router.post("/benchmark-questions")
async def add_benchmark_question(request: BenchmarkQuestionRequest):
    """Persist a benchmark case in the control-plane database."""
    app_client = get_app_db_client()
    try:
        _require_admin(app_client, request.user_id, "benchmark-question-create")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    question = request.question.strip()
    gold_sql = request.gold_sql.strip()
    if not question or not gold_sql:
        raise HTTPException(status_code=400, detail="Question and expected SQL are required")
    if not gold_sql.upper().startswith("SELECT"):
        raise HTTPException(status_code=400, detail="Expected SQL must be a read-only SELECT statement")

    rows, _, _ = app_client.execute_write(
        """
        INSERT INTO benchmark_questions
          (question, gold_sql, gold_answer, category, expected_outcome, is_active)
        VALUES (%s, %s, %s, %s, 'success', true)
        RETURNING id, question, gold_sql, gold_answer, category, created_at
        """,
        (question, gold_sql, request.gold_answer.strip(), request.category.strip() or "custom")
    )
    row = rows[0]
    return {"id": str(row["id"]), "question": row["question"], "gold_sql": row["gold_sql"], "gold_answer": row["gold_answer"], "category": row["category"], "created_at": row["created_at"].isoformat()}


@router.post("/benchmark-eval/run", status_code=202)
async def run_benchmark_evaluation(request: BenchmarkRunRequest, background_tasks: BackgroundTasks):
    """Start a real persisted evaluation run without blocking the HTTP request."""
    global _benchmark_run_active, _benchmark_run_error
    app_client = get_app_db_client()
    try:
        _require_admin(app_client, request.user_id, "benchmark-eval-run")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    with _benchmark_run_lock:
        if _benchmark_run_active:
            raise HTTPException(status_code=409, detail="A benchmark evaluation is already running")
        _benchmark_run_active = True
        _benchmark_run_error = None
    if request.limit is not None and request.limit < 1:
        with _benchmark_run_lock:
            _benchmark_run_active = False
        raise HTTPException(status_code=400, detail="limit must be at least 1")

    background_tasks.add_task(_run_benchmark_in_background, request.user_id, request.limit)
    return {"status": "started", "message": "Benchmark evaluation started. Refresh results after it completes."}


@router.get("/benchmark-eval/status")
async def get_benchmark_evaluation_status(user_id: str):
    app_client = get_app_db_client()
    try:
        _require_admin(app_client, user_id, "benchmark-eval-status")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    with _benchmark_run_lock:
        return {"is_running": _benchmark_run_active, "error": _benchmark_run_error}


@router.get("/capabilities")
async def get_admin_capabilities(user_id: str):
    """Get admin's capabilities."""
    admin_context = UserContext(
        user_id=user_id,
        role=Role.ADMIN,
        session_id="unknown"
    )

    access_control = get_access_control()

    return access_control.get_user_capabilities(admin_context)
