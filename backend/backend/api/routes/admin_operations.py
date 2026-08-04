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
import logging
import time
import threading

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, Set

from backend.ai.rbac.access_control import get_access_control
from backend.api.dependencies import require_admin, require_admin_session
from backend.api.services import analytics_service, evaluation_service
from backend.api.services.db_errors import explain_database_error
from backend.ai.validators.sql_guard_rbac import (
    get_sql_guard_rbac,
    get_admin_query_builder,
    get_admin_confirmation_store
)
from backend.ai.validators.admin_write_guard import get_admin_write_guard
from backend.ai.validators.write_intent import has_write_intent
from backend.ai.utils.supabase_client import get_supabase_client, get_app_db_client
from backend.ai.utils.supabase_executor import get_supabase_query_executor
from backend.ai.utils.supabase_schema_loader import get_supabase_schema_loader
from backend.ai.utils.chat_history import (
    get_recent_messages, add_message, resolve_follow_up, build_conversation_context,
    ensure_session, find_last_select
)
from backend.ai.monitoring.logger import get_monitoring_logger, EventType
from backend.ai.monitoring.query_log_repository import log_query
from backend.ai.llm.client import get_llm_client, SUPPORTED_LLM_PROVIDERS
from backend.ai.llm.generator import (
    SQLGenerator,
    get_chart_recommender,
    get_pipeline_orchestrator,
    aggregate_llm_usage
)
from backend.ai.prompts.clarification_prompt import get_clarification_prompt_manager
from backend.ai.prompts.admin_write_prompt import ADMIN_WRITE_SYSTEM_PROMPT


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
    mode: Optional[str] = "all"  # "all" | "sql" | "compare" | "pipeline"


_active_eval_modes: Set[str] = set()
_benchmark_run_error: Optional[str] = None
_benchmark_run_lock = threading.Lock()


def _run_benchmark_in_background(admin_id: str, limit: Optional[int], mode: str = "all") -> None:
    """Run outside the request lifecycle; a suite can take minutes due to LLM rate limits."""
    global _benchmark_run_error
    try:
        from backend.ai.evaluation.run_pipeline_eval import run_pipeline_eval
        from backend.ai.evaluation.run_benchmark import run_benchmark, compare_providers

        if mode == "pipeline":
            run_pipeline_eval(admin_id=admin_id, limit=limit)
        elif mode == "sql":
            run_benchmark(admin_id=admin_id, limit=limit, provider="groq")
        elif mode == "compare":
            compare_providers(admin_id=admin_id, limit=limit)
        else:  # "all"
            try:
                run_pipeline_eval(admin_id=admin_id, limit=limit)
            except Exception:
                import logging
                logging.getLogger(__name__).exception("Background pipeline routing evaluation failed")

            compare_providers(admin_id=admin_id, limit=limit)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("Background benchmark run failed")
        with _benchmark_run_lock:
            _benchmark_run_error = str(exc) or "Benchmark run failed unexpectedly"
    finally:
        with _benchmark_run_lock:
            _active_eval_modes.discard(mode)
            if mode == "all":
                _active_eval_modes.clear()


@router.post("/create")
async def create_record(request: CreateRequest):
    """Propose a new record (ADMIN only) - requires /confirm to actually run."""
    try:
        business_client = get_supabase_client()
        app_client = get_app_db_client()
        admin_context = require_admin_session(request.user_id, request.session_id)

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
        # A refused write (foreign key, not-null, unique, check) is the database
        # protecting existing data, not a server fault - report it as a rejected
        # request with an explanation the admin can act on, rather than a 500
        # carrying raw psycopg2 output.
        explanation = explain_database_error(e)
        if explanation:
            raise HTTPException(status_code=409, detail=explanation)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update")
async def update_record(request: UpdateRequest):
    """Propose a record update (ADMIN only) - requires /confirm to actually run."""
    try:
        business_client = get_supabase_client()
        app_client = get_app_db_client()
        admin_context = require_admin_session(request.user_id, request.session_id)

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
        # A refused write (foreign key, not-null, unique, check) is the database
        # protecting existing data, not a server fault - report it as a rejected
        # request with an explanation the admin can act on, rather than a 500
        # carrying raw psycopg2 output.
        explanation = explain_database_error(e)
        if explanation:
            raise HTTPException(status_code=409, detail=explanation)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete")
async def delete_record(request: DeleteRequest):
    """Propose a record delete (ADMIN only) - requires /confirm to actually run."""
    try:
        business_client = get_supabase_client()
        app_client = get_app_db_client()
        admin_context = require_admin_session(request.user_id, request.session_id)

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
        # A refused write (foreign key, not-null, unique, check) is the database
        # protecting existing data, not a server fault - report it as a rejected
        # request with an explanation the admin can act on, rather than a 500
        # carrying raw psycopg2 output.
        explanation = explain_database_error(e)
        if explanation:
            raise HTTPException(status_code=409, detail=explanation)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confirm")
async def confirm_action(request: ConfirmRequest):
    """Confirm and execute a previously proposed write (ADMIN only)."""
    try:
        business_client = get_supabase_client()
        app_client = get_app_db_client()
        require_admin_session(request.user_id, request.session_id)

        confirmation_store = get_admin_confirmation_store(business_client, app_client)
        logger = get_monitoring_logger()

        executed_sql, rows, affected_count = confirmation_store.confirm(request.token)

        # Re-run the read the admin was last looking at, or query the full table directly.
        refreshed_data = None
        try:
            previous = find_last_select(app_client, request.session_id)
            if previous:
                refreshed_rows, refreshed_cols, _ = get_supabase_query_executor().execute(
                    previous["sql"]
                )
                chart_res = get_chart_recommender().recommend(
                    refreshed_rows, refreshed_cols, previous["question"], previous["sql"]
                )
                refreshed_data = {
                    "question": f"Show all records for: {previous['question']}",
                    "sql": previous["sql"],
                    "data": refreshed_rows,
                    "columns": refreshed_cols,
                    "chart_type": chart_res.chart_type
                }
        except Exception:
            pass

        if not refreshed_data:
            try:
                match = re.search(r'(?:FROM|INTO|UPDATE)\s+["`]?([a-zA-Z0-9_]+)["`]?', executed_sql, re.IGNORECASE)
                if match:
                    target_table = match.group(1)
                    refreshed_rows, refreshed_cols, _ = get_supabase_query_executor().execute(
                        f"SELECT * FROM {target_table}"
                    )
                    refreshed_data = {
                        "question": f"Show all {target_table}",
                        "sql": f"SELECT * FROM {target_table}",
                        "data": refreshed_rows,
                        "columns": refreshed_cols,
                        "chart_type": "table"
                    }
            except Exception as e:
                logger.log_event(
                    event_type=EventType.SQL_EXECUTION,
                    message=f"Failed to auto-refresh database state proof: {str(e)}",
                    user_id=request.user_id,
                    session_id=request.session_id,
                    status="warning"
                )

        analytics_service.log_admin_write(request.user_id, executed_sql, affected_count)

        log_query(
            app_client,
            user_id=request.user_id,
            session_id=request.session_id,
            nl_query=f"EXECUTE WRITE: {executed_sql}",
            sql_generated=executed_sql,
            status="success",
            exec_time_ms=exec_time,
            model_provider="groq"
        )

        # The write may have introduced a value the schema context doesn't
        # mention yet (a new product category, a new city). Drop the cached
        # schema so the next question is grounded in what the database now
        # holds, rather than waiting out the TTL. Best-effort: the write has
        # already succeeded, so a failure here must not fail the response.
        try:
            get_supabase_schema_loader().invalidate()
        except Exception as e:
            logger.log_event(
                event_type=EventType.SQL_EXECUTION,
                message=f"Could not invalidate schema cache after write: {str(e)}",
                user_id=request.user_id,
                session_id=request.session_id,
                status="warning"
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
        # A refused write (foreign key, not-null, unique, check) is the database
        # protecting existing data, not a server fault - report it as a rejected
        # request with an explanation the admin can act on, rather than a 500
        # carrying raw psycopg2 output.
        explanation = explain_database_error(e)
        if explanation:
            raise HTTPException(status_code=409, detail=explanation)
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
        admin_context = require_admin_session(request.user_id, request.session_id)

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
            log_query(
                app_client,
                user_id=request.user_id,
                session_id=request.session_id,
                nl_query=request.sql,
                sql_generated=request.sql,
                status="success",
                exec_time_ms=exec_time
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
        log_query(
            app_client,
            user_id=request.user_id,
            session_id=request.session_id,
            nl_query=f"[proposed, awaiting confirmation] {request.sql}",
            sql_generated=request.sql,
            status="success"
        )

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
    admin_context = require_admin_session(request.user_id, request.session_id)

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

    is_write_req = has_write_intent(effective_question) or any(
        kw in effective_question.lower() for kw in ["delete", "insert", "update", "hapus", "tambah", "ubah", "drop", "alter"]
    )

    sql_result = sql_generator.generate(
        effective_question,
        schema_definition,
        check_ambiguity=not is_follow_up and not is_write_req,
        override_system_prompt=ADMIN_WRITE_SYSTEM_PROMPT,
        conversation_context=conversation_context,
        allow_writes=True
    )

    add_message(app_client, request.session_id, role="user", content=request.question)

    if sql_result.is_ambiguous and not is_write_req:
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
        return {
            "status": "error",
            "explanation": sql_result.error_message or "Failed to generate SQL.",
            "model_provider": request.model_provider,
            "model_name": model_name
        }

    sql = sql_result.sql.strip().rstrip(";")
    sql_upper = sql.upper()

    try:
        auth = access_control.authorize_sql(admin_context, sql)
        if not auth["authorized"]:
            raise PermissionError(auth["reason"])

        if auth["operation"] == "read":
            max_rows = auth.get("max_rows")
            exec_sql = f"{sql} LIMIT {max_rows}" if max_rows and "LIMIT" not in sql_upper else sql

            data, columns, exec_time = query_executor.execute(exec_sql)

            # Same explain/chart/attribute/format code the user pipeline runs -
            # admin only had to generate and authorize the SQL itself, not own
            # a second copy of everything that happens after it.
            answer = get_pipeline_orchestrator(request.model_provider).build_answer(
                user_question=request.question,
                sql=sql,
                data=data,
                columns=columns,
                execution_time=exec_time,
                conversation_context=conversation_context,
                sql_llm_response=sql_result.llm_response,
                sql_generation_time_ms=sql_result.generation_time_ms
            )

            log_query(
                app_client, user_id=request.user_id, session_id=request.session_id,
                nl_query=request.question, sql_generated=sql, status="success", exec_time_ms=exec_time,
                model_provider=request.model_provider,
                llm_usage=answer["metadata"]
            )
            add_message(
                app_client, request.session_id, role="assistant",
                content=answer["explanation"], sql_generated=sql,
                result_json=data, chart_type=answer["chart_recommendation"]["type"]
            )
            logger.log_event(
                event_type=EventType.SQL_EXECUTION,
                message=f"Admin NL read executed: {request.question[:50]}",
                user_id=request.user_id, session_id=request.session_id, status="success"
            )

            return {
                **answer,
                "operation": "read",
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
            "sql_preview": sql,
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
            conversation_context=conversation_context, allow_writes=True
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

        answer = get_pipeline_orchestrator(provider).build_answer(
            user_question=effective_question,
            sql=sql,
            data=data,
            columns=columns,
            execution_time=exec_time,
            sql_llm_response=sql_result.llm_response,
            sql_generation_time_ms=sql_result.generation_time_ms
        )

        return AdminProviderCompareResult(
            provider=provider, model_name=model_name, status="success", operation="read",
            generated_sql=sql, explanation=answer["explanation"],
            chart_recommendation=answer["chart_recommendation"],
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
    admin_context = require_admin_session(request.user_id, request.session_id)

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
    require_admin(user_id)
    return {"logs": analytics_service.list_all_query_logs(limit)}


@router.get("/analytics/summary")
async def get_analytics_summary(user_id: str):
    """
    Real usage analytics (ADMIN only), aggregated directly from the
    persistent `query_logs` table - query success rate, execution
    metrics, error rate, plus per-provider token/cost/latency totals.
    """
    require_admin(user_id)
    return analytics_service.get_summary()


@router.get("/analytics/query-volume")
async def get_query_volume(user_id: str, days: int = 14):
    """
    Real daily query volume (ADMIN only) for the dashboard trend chart,
    aggregated from `query_logs` over the last `days` days.
    """
    require_admin(user_id)
    return {"trend": analytics_service.get_query_volume(days)}


@router.get("/query-logs/{log_id}/result")
async def get_query_log_result(log_id: str, user_id: str):
    """
    Re-run a logged SELECT query (ADMIN only) so its live output can be
    inspected. `query_logs` stores the SQL but not the result rows, so the
    output is re-fetched on demand against the business DB in a read-only
    session. Only SELECTs are ever re-executed - a logged write statement is
    never re-run - and the caller is told when output isn't available.
    """
    require_admin(user_id)
    return analytics_service.rerun_logged_query(log_id)


@router.get("/benchmark-eval/latest")
async def get_latest_benchmark_eval(user_id: str):
    """
    Get the most recent SQL-correctness benchmark run (ADMIN only) -
    results already persisted by `backend.ai.evaluation.run_benchmark`.
    Never triggers a run itself, same reasoning as /pipeline-eval/latest:
    a run makes real, rate-limited LLM calls and takes minutes.
    """
    require_admin(user_id)
    return evaluation_service.get_latest_benchmark_run()


@router.get("/benchmark-eval/history")
async def get_benchmark_evaluation_history(user_id: str):
    """Get history of all benchmark evaluation runs (ADMIN only)."""
    require_admin(user_id)
    return {"history": evaluation_service.get_benchmark_history()}


@router.get("/benchmark-eval/compare")
async def compare_benchmark_providers(user_id: str):
    """
    Latest benchmark run per LLM provider, side by side (ADMIN only).

    Same questions, same gold SQL, same comparator - only the model differs,
    so accuracy, tokens, cost and latency can be read against each other.
    """
    require_admin(user_id)
    return {"providers": evaluation_service.compare_providers()}


@router.get("/benchmark-questions")
async def list_benchmark_questions(user_id: str):
    """List active persisted cases; never returns a browser-only fixture."""
    require_admin(user_id)
    return {"questions": evaluation_service.list_benchmark_questions()}


@router.post("/benchmark-questions")
async def add_benchmark_question(request: BenchmarkQuestionRequest):
    """Persist a benchmark case in the control-plane database."""
    require_admin(request.user_id)
    return evaluation_service.add_benchmark_question(
        request.question, request.gold_sql, request.gold_answer, request.category
    )


@router.post("/benchmark-eval/run", status_code=202)
async def run_benchmark_evaluation(request: BenchmarkRunRequest, background_tasks: BackgroundTasks):
    """Start a real persisted evaluation run without blocking the HTTP request."""
    global _benchmark_run_error
    require_admin(request.user_id)
    mode = request.mode or "all"

    with _benchmark_run_lock:
        if mode == "all" and len(_active_eval_modes) > 0:
            raise HTTPException(status_code=409, detail="An evaluation run is already in progress")
        if mode in _active_eval_modes or "all" in _active_eval_modes:
            raise HTTPException(status_code=409, detail=f"Evaluation mode '{mode}' is already running")

        _active_eval_modes.add(mode)
        _benchmark_run_error = None

    if request.limit is not None and request.limit < 1:
        with _benchmark_run_lock:
            _active_eval_modes.discard(mode)
        raise HTTPException(status_code=400, detail="limit must be at least 1")

    background_tasks.add_task(_run_benchmark_in_background, request.user_id, request.limit, mode)
    return {"status": "started", "message": f"Benchmark evaluation ({mode}) started. Refresh results after it completes."}


@router.get("/benchmark-eval/status")
async def get_benchmark_evaluation_status(user_id: str):
    require_admin(user_id)
    with _benchmark_run_lock:
        return {
            "is_running": len(_active_eval_modes) > 0,
            "running_modes": list(_active_eval_modes),
            "error": _benchmark_run_error
        }


@router.post("/schema/refresh")
async def refresh_schema_context(user_id: str):
    """
    Re-read the database schema the chatbot is grounded in (ADMIN only).

    The schema context is cached, so a table, column or categorical value
    added outside this app - a migration, or an edit in Supabase Studio - is
    invisible to the chatbot until the cache expires. This forces it now.
    """
    require_admin(user_id)

    loader = get_supabase_schema_loader()
    loader.refresh_schema()

    return {
        "status": "success",
        "tables": len(loader.get_available_tables()),
        "message": "Schema context reloaded from the database.",
    }


@router.get("/capabilities")
async def get_admin_capabilities(user_id: str):
    """Get admin's capabilities. Was the one admin route that never checked
    the caller's role - it built an ADMIN context out of thin air."""
    admin_context = require_admin(user_id)

    access_control = get_access_control()

    return access_control.get_user_capabilities(admin_context)
