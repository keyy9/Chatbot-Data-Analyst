"""
User Interface Routes.

Read-only interface for end users (and coworkers) asking questions about
data. Supports multi-turn conversations: if the previous assistant turn
asked a clarifying question, the current message is treated as the answer
and merged with the original question before SQL generation.
"""

import asyncio
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.ai import get_pipeline_orchestrator
from backend.ai.llm.client import SUPPORTED_LLM_PROVIDERS
from backend.ai.rbac.roles import Role
from backend.ai.rbac.access_control import UserContext, get_access_control
from backend.ai.rbac.user_lookup import verify_role
from backend.ai.validators.sql_guard_rbac import get_sql_guard_rbac
from backend.ai.validators.write_intent import has_write_intent
from backend.ai.utils.supabase_client import get_app_db_client
from backend.ai.utils.supabase_schema_loader import get_supabase_schema_loader
from backend.ai.utils.supabase_executor import get_supabase_query_executor
from backend.ai.utils.system_prompt_store import get_active_system_prompt
from backend.ai.utils.chat_history import (
    get_recent_messages, add_message, resolve_follow_up, build_conversation_context, ensure_session
)
from backend.ai.prompts.clarification_prompt import get_clarification_prompt_manager
from backend.ai.monitoring.logger import get_monitoring_logger, EventType
from backend.ai.monitoring.query_log_repository import log_query, list_for_user as list_query_logs_for_user
from backend.api.services import chat_session_service, notes_service

router = APIRouter(prefix="/api/user", tags=["User Interface"])


class QuestionRequest(BaseModel):
    """User question request."""
    question: str
    user_id: str
    session_id: str
    model_provider: str = "groq"  # "groq" or "gemini" - which LLM answers this question


class QuestionResponse(BaseModel):
    """Question response."""
    status: str
    generated_sql: str = ""
    explanation: str = ""
    suggested_questions: list = []
    chart_recommendation: dict = {}
    plotly_figure: dict = {}
    insights: list = []
    sources: dict = {}
    data: list = []
    columns: list = []
    options: list = []
    metadata: dict = {}
    model_provider: str = "groq"
    model_name: str = ""


def _validate_provider(provider: str) -> None:
    if provider not in SUPPORTED_LLM_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model_provider: {provider!r}. Supported: {SUPPORTED_LLM_PROVIDERS}"
        )


def _make_sql_executor_callback(sql_guard_rbac, query_executor, user_context, user_id, session_id, logger):
    """Shared RBAC-checked SQL executor callback, used by both /ask and /ask/compare."""
    def execute_sql_callback(sql: str):
        validation = sql_guard_rbac.validate_with_rbac(sql, user_context)

        if not validation["is_valid"]:
            logger.log_error(
                user_id=user_id,
                session_id=session_id,
                error_message=validation["error"],
                error_type="SQL_VALIDATION_FAILED",
                component="user_questions"
            )
            raise PermissionError(validation["error"])

        max_rows = validation.get("max_rows")
        clean_sql = sql.strip().rstrip(";")
        if max_rows and "LIMIT" not in clean_sql.upper():
            clean_sql = f"{clean_sql} LIMIT {max_rows}"

        return query_executor.execute(clean_sql)

    return execute_sql_callback


class ProviderCompareResult(BaseModel):
    """One provider's answer within a /ask/compare response."""
    provider: str
    model_name: str = ""
    status: str = "error"
    generated_sql: str = ""
    explanation: str = ""
    chart_recommendation: dict = {}
    data: list = []
    columns: list = []
    options: list = []
    error: str = ""
    latency_ms: float = 0.0
    # Token/cost travel with the answer so a comparison can weigh what each
    # model charged, not only which one looked better.
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0


class CompareResponse(BaseModel):
    """Response for /ask/compare - one result per provider, keyed by provider name."""
    results: dict = {}


def _log_compare_outcome(app_client, request, outcome: "ProviderCompareResult") -> None:
    """
    Record one provider's side of a comparison in `query_logs`.

    Each provider gets its own row, tagged with `model_provider`, so the
    per-provider analytics can average cost and latency over real questions
    rather than only over the benchmark set.

    The question text is prefixed so these rows are recognisable in the log
    view: a comparison asks the same question twice, and without the marker the
    duplicate looks like a bug.
    """
    log_query(
        app_client,
        user_id=request.user_id,
        session_id=request.session_id,
        nl_query=f"[compare] {request.question}",
        sql_generated=outcome.generated_sql or None,
        status="success" if outcome.status == "success" else (
            "clarification_needed" if outcome.status == "clarification_needed" else "error"
        ),
        reject_reason=outcome.error or None,
        model_provider=outcome.provider,
        llm_usage={
            "model_name": outcome.model_name,
            "input_tokens": outcome.input_tokens,
            "output_tokens": outcome.output_tokens,
            "estimated_cost": outcome.estimated_cost,
            "llm_latency_ms": outcome.latency_ms,
        },
    )


def _run_pipeline_for_provider(
    provider: str,
    effective_question: str,
    schema_definition: str,
    system_prompt_override: str,
    execute_sql_callback,
    conversation_context: str = ""
) -> ProviderCompareResult:
    """Run the full pipeline for one provider and capture the outcome (never raises)."""
    start = time.time()
    try:
        orchestrator = get_pipeline_orchestrator(provider)
        model_name = orchestrator.sql_generator.llm_client.config.model

        result = orchestrator.process(
            user_question=effective_question,
            schema_definition=schema_definition,
            query_executor_callback=execute_sql_callback,
            override_system_prompt=system_prompt_override,
            conversation_context=conversation_context
        )
        latency_ms = (time.time() - start) * 1000
        status = result.get("status", "error")
        usage = result.get("metadata") or {}

        if status == "success":
            return ProviderCompareResult(
                provider=provider,
                model_name=model_name,
                status=status,
                generated_sql=result.get("generated_sql", ""),
                explanation=result.get("explanation", ""),
                chart_recommendation=result.get("chart_recommendation") or {},
                data=result.get("data") or [],
                columns=result.get("columns") or [],
                latency_ms=latency_ms,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                estimated_cost=usage.get("estimated_cost", 0.0)
            )
        if status == "clarification_needed":
            return ProviderCompareResult(
                provider=provider,
                model_name=model_name,
                status=status,
                explanation=result.get("question", ""),
                options=result.get("options") or [],
                latency_ms=latency_ms,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                estimated_cost=usage.get("estimated_cost", 0.0)
            )
        return ProviderCompareResult(
            provider=provider,
            model_name=model_name,
            status="error",
            error=result.get("error", "Failed to answer question"),
            latency_ms=latency_ms,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            estimated_cost=usage.get("estimated_cost", 0.0)
        )
    except Exception as e:
        return ProviderCompareResult(
            provider=provider,
            status="error",
            error=str(e),
            latency_ms=(time.time() - start) * 1000
        )


@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a natural language question (USER: read-only).

    Both "user" and "admin" roles may use this read-only endpoint.
    """
    _validate_provider(request.model_provider)

    app_client = get_app_db_client()  # this app's own control-plane DB

    # A refused request is still a question the user asked, so it belongs in
    # the log. Recorded before raising - otherwise the only queries missing
    # from the audit trail would be the ones someone tried to write with.
    if has_write_intent(request.question):
        refusal = (
            "I detected a request to modify database records, but you are currently in "
            "Read-Only Mode. To perform write operations (INSERT, UPDATE, DELETE), "
            "please switch to the Admin Chat page."
        )
        log_query(
            app_client,
            user_id=request.user_id,
            # No session_id: the refusal happens before `ensure_session`, and
            # query_logs.session_id is a FK - naming a row that doesn't exist
            # yet would fail the insert and lose the record entirely.
            session_id=None,
            nl_query=request.question,
            sql_generated=None,
            status="rejected",
            reject_reason="write_intent_in_read_only_mode",
            model_provider=request.model_provider,
        )
        raise HTTPException(status_code=403, detail=refusal)

    # ============ Verify caller (soft: never block a read on a DB hiccup) ============
    verify_role(app_client, request.user_id, allowed_roles=("user", "admin"), hard=False)

    user_context = UserContext(
        user_id=request.user_id,
        role=Role.USER,  # Force USER (read-only) permissions regardless of DB role
        session_id=request.session_id
    )

    logger = get_monitoring_logger()

    orchestrator = get_pipeline_orchestrator(request.model_provider)
    model_name = orchestrator.sql_generator.llm_client.config.model
    schema_loader = get_supabase_schema_loader()
    query_executor = get_supabase_query_executor()
    sql_guard_rbac = get_sql_guard_rbac()
    clarification_manager = get_clarification_prompt_manager()

    schema_definition = schema_loader.get_schema_definition()
    system_prompt_override = get_active_system_prompt(app_client)

    # ============ Ensure the FK target for chat_messages/query_logs exists ============
    ensure_session(app_client, request.session_id, request.user_id)

    # ============ Multi-turn: merge a clarification answer with the original question ============
    # Keep the memory window focused (~10 turns): enough for a flowing
    # conversation, without bloating the prompt with an entire long session.
    recent_messages = get_recent_messages(app_client, request.session_id, limit=20)
    effective_question = resolve_follow_up(
        recent_messages,
        request.question,
        clarification_manager.merge_clarification_with_question
    )
    conversation_context = build_conversation_context(recent_messages, request.question)

    # ============ Define SQL Executor with RBAC ============
    execute_sql_callback = _make_sql_executor_callback(
        sql_guard_rbac, query_executor, user_context, request.user_id, request.session_id, logger
    )

    is_follow_up = False
    if recent_messages:
        last = recent_messages[-1]
        if last.get("role") == "assistant" and last.get("needs_clarification"):
            is_follow_up = True

    try:
        result = orchestrator.process(
            user_question=effective_question,
            schema_definition=schema_definition,
            query_executor_callback=execute_sql_callback,
            override_system_prompt=system_prompt_override,
            conversation_context=conversation_context,
            check_ambiguity=not is_follow_up
        )
    except Exception as e:
        # A crash mid-pipeline is exactly the case worth having in the log, so
        # record it before surfacing the 500 rather than losing the question.
        log_query(
            app_client,
            user_id=request.user_id,
            session_id=request.session_id,
            nl_query=request.question,
            sql_generated=None,
            status="error",
            reject_reason=f"pipeline_error: {str(e)[:400]}",
            model_provider=request.model_provider,
        )
        raise HTTPException(status_code=500, detail=str(e))

    # ============ Persist to query_logs + chat_messages (best-effort) ============
    status = result.get("status", "error")

    log_query(
        app_client,
        user_id=request.user_id,
        session_id=request.session_id,
        nl_query=request.question,
        sql_generated=result.get("generated_sql"),
        status=status,
        reject_reason=result.get("error"),
        exec_time_ms=(result.get("metadata") or {}).get("query_execution_time_ms"),
        model_provider=request.model_provider,
        llm_usage=result.get("metadata") or {}
    )

    add_message(app_client, request.session_id, role="user", content=request.question)

    if status == "success":
        add_message(
            app_client,
            request.session_id,
            role="assistant",
            content=result.get("explanation", ""),
            sql_generated=result.get("generated_sql"),
            result_json=result.get("data"),
            chart_type=(result.get("chart_recommendation") or {}).get("type")
        )
        logger.log_event(
            event_type=EventType.SQL_GENERATION,
            message=f"User question processed: {request.question[:50]}",
            user_id=request.user_id,
            session_id=request.session_id,
            status="success"
        )
    elif status == "clarification_needed":
        add_message(
            app_client,
            request.session_id,
            role="assistant",
            content=result.get("question", ""),
            needs_clarification=True,
            result_json=result.get("options") or []
        )
        return QuestionResponse(
            status=status,
            explanation=result.get("question", ""),
            options=result.get("options") or [],
            model_provider=request.model_provider,
            model_name=model_name
        )
    else:
        add_message(app_client, request.session_id, role="assistant", content=result.get("error", "An error occurred."))
        return {
            "status": "error",
            "explanation": result.get("error", "Failed to answer question."),
            "data": [],
            "columns": [],
            "model_provider": request.model_provider,
            "model_name": model_name
        }

    return {**result, "model_provider": request.model_provider, "model_name": model_name}


@router.post("/ask/compare", response_model=CompareResponse)
async def ask_question_compare(request: QuestionRequest):
    """
    Ask a natural language question and get answers from BOTH LLM
    providers side by side (USER: read-only), for per-query model
    comparison. Runs concurrently.

    Not added to chat_history - this is a side comparison, not a turn in the
    conversation, and the regular /ask call already persisted that turn.

    It IS written to query_logs, one row per provider. Without that every
    comparison vanished when the modal closed, so no amount of real usage could
    ever answer "which model is actually cheaper/faster for our questions?" -
    the per-provider analytics had nothing to aggregate.
    """
    app_client = get_app_db_client()

    verify_role(app_client, request.user_id, allowed_roles=("user", "admin"), hard=False)

    user_context = UserContext(
        user_id=request.user_id,
        role=Role.USER,
        session_id=request.session_id
    )

    logger = get_monitoring_logger()
    schema_loader = get_supabase_schema_loader()
    query_executor = get_supabase_query_executor()
    sql_guard_rbac = get_sql_guard_rbac()
    clarification_manager = get_clarification_prompt_manager()

    schema_definition = schema_loader.get_schema_definition()
    system_prompt_override = get_active_system_prompt(app_client)

    ensure_session(app_client, request.session_id, request.user_id)

    recent_messages = get_recent_messages(app_client, request.session_id)
    effective_question = resolve_follow_up(
        recent_messages,
        request.question,
        clarification_manager.merge_clarification_with_question
    )
    conversation_context = build_conversation_context(recent_messages, request.question)

    execute_sql_callback = _make_sql_executor_callback(
        sql_guard_rbac, query_executor, user_context, request.user_id, request.session_id, logger
    )

    groq_result, gemini_result = await asyncio.gather(
        asyncio.to_thread(
            _run_pipeline_for_provider, "groq", effective_question, schema_definition,
            system_prompt_override, execute_sql_callback, conversation_context
        ),
        asyncio.to_thread(
            _run_pipeline_for_provider, "gemini", effective_question, schema_definition,
            system_prompt_override, execute_sql_callback, conversation_context
        )
    )

    for outcome in (groq_result, gemini_result):
        _log_compare_outcome(app_client, request, outcome)

    return CompareResponse(results={"groq": groq_result, "gemini": gemini_result})


@router.get("/query-logs")
async def get_my_query_logs(user_id: str, limit: int = 100):
    """
    List the caller's own query log history (USER or ADMIN).

    Self-scoped by construction: `user_id` identifies whose history to
    return, not a filter the caller can widen - there is no parameter
    here that could surface another user's rows. Admins needing the
    all-users view use GET /api/admin/query-logs instead.
    """
    app_client = get_app_db_client()

    verify_role(app_client, user_id, allowed_roles=("user", "admin"), hard=False)

    return {"logs": list_query_logs_for_user(app_client, user_id, limit)}


@router.get("/capabilities")
async def get_capabilities(user_id: str):
    """Get user's capabilities."""
    user_context = UserContext(
        user_id=user_id,
        role=Role.USER,
        session_id="unknown"
    )

    access_control = get_access_control()

    return access_control.get_user_capabilities(user_context)


class NoteRequest(BaseModel):
    id: str
    user_id: str
    title: str
    content: str
    session_id: str | None = None
    last_modified: int


@router.get("/notes")
async def get_user_notes(user_id: str):
    """Retrieve all saved observations/notes for a user (Client/Admin)."""
    return {"notes": notes_service.list_for_user(user_id)}


@router.post("/notes")
async def save_user_note(request: NoteRequest):
    """Upsert (Insert or Update) a user note/observation."""
    return notes_service.save(
        request.id, request.user_id, request.title,
        request.content, request.session_id, request.last_modified
    )


@router.delete("/notes/{note_id}")
async def delete_user_note(note_id: str, user_id: str):
    """Delete a user note/observation (idempotent - see delete_user_session)."""
    return notes_service.delete(note_id, user_id)


class CreateSessionRequest(BaseModel):
    id: str
    user_id: str
    title: str


class RenameSessionRequest(BaseModel):
    id: str
    user_id: str
    title: str


@router.get("/sessions")
async def get_user_sessions(user_id: str):
    """Retrieve all chat sessions for a user (Client/Admin)."""
    return {"sessions": chat_session_service.list_for_user(user_id)}


@router.post("/sessions")
async def create_user_session(request: CreateSessionRequest):
    """Register or save a new chat session in the database."""
    return chat_session_service.create(request.id, request.user_id, request.title)


@router.post("/sessions/rename")
async def rename_user_session(request: RenameSessionRequest):
    """Rename an existing chat session."""
    return chat_session_service.rename(request.id, request.user_id, request.title)


@router.delete("/sessions/{session_id}")
async def delete_user_session(session_id: str, user_id: str):
    """
    Delete a chat session and all its messages (idempotent).

    Deleting is idempotent: whether or not a matching DB row exists, the
    caller's intent (this session should be gone) is satisfied on return.
    A local-only session that was never persisted - including one with a
    legacy non-UUID id - therefore deletes cleanly from the UI instead of
    reporting a spurious failure.
    """
    return chat_session_service.delete(session_id, user_id)


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, user_id: str):
    """Retrieve formatted message history for a chat session."""
    return {"messages": chat_session_service.get_messages(session_id, user_id)}


@router.get("/tables/{table_name}/rows")
async def get_table_rows(table_name: str, user_id: str, limit: int = 100, offset: int = 0):
    """
    Browse raw rows from any table in the business database (read-only).

    The client supplies only a table name (validated against the live
    DATABASE_URL schema, never raw SQL), so this can never be used to run
    arbitrary queries. Every table physically present in DATABASE_URL is
    browsable here - unlike the chatbot, which only ever sees business
    tables (app-internal tables are hidden from its schema context).
    """
    app_client = get_app_db_client()
    try:
        verify_role(app_client, user_id, allowed_roles=("user", "admin"), hard=True)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be non-negative")

    schema_loader = get_supabase_schema_loader()
    available_tables = schema_loader.get_available_tables()
    if table_name not in available_tables:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    try:
        query_executor = get_supabase_query_executor()
        sql = f"SELECT * FROM {table_name} LIMIT {limit} OFFSET {offset}"
        rows, columns, exec_time = query_executor.execute(sql)

        log_query(
            app_client,
            user_id=user_id,
            session_id=None,
            nl_query=f"[raw table view] {table_name}",
            sql_generated=sql,
            status="success",
            exec_time_ms=exec_time
        )

        return {"status": "success", "data": rows, "columns": columns, "table": table_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
