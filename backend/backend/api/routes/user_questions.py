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
from backend.ai.utils.supabase_client import get_supabase_client, get_app_db_client
from backend.ai.utils.supabase_schema_loader import get_supabase_schema_loader
from backend.ai.utils.supabase_executor import get_supabase_query_executor
from backend.ai.utils.system_prompt_store import get_active_system_prompt
from backend.ai.utils.chat_history import (
    get_recent_messages, add_message, resolve_follow_up, build_conversation_context, ensure_session
)
from backend.ai.prompts.clarification_prompt import get_clarification_prompt_manager
from backend.ai.monitoring.logger import get_monitoring_logger, EventType
from backend.ai.monitoring.query_log_repository import log_query

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
        if max_rows and "LIMIT" not in sql.upper():
            sql = f"{sql} LIMIT {max_rows}"

        return query_executor.execute(sql)

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


class CompareResponse(BaseModel):
    """Response for /ask/compare - one result per provider, keyed by provider name."""
    results: dict = {}


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
                latency_ms=latency_ms
            )
        if status == "clarification_needed":
            return ProviderCompareResult(
                provider=provider,
                model_name=model_name,
                status=status,
                explanation=result.get("question", ""),
                options=result.get("options") or [],
                latency_ms=latency_ms
            )
        return ProviderCompareResult(
            provider=provider,
            model_name=model_name,
            status="error",
            error=result.get("error", "Failed to answer question"),
            latency_ms=latency_ms
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

    business_client = get_supabase_client()  # the data being asked about
    app_client = get_app_db_client()  # this app's own control-plane DB

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
    recent_messages = get_recent_messages(app_client, request.session_id)
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
        exec_time_ms=(result.get("metadata") or {}).get("query_execution_time_ms")
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
            needs_clarification=True
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
        raise HTTPException(status_code=422, detail=result.get("error", "Failed to answer question"))

    return {**result, "model_provider": request.model_provider, "model_name": model_name}


@router.post("/ask/compare", response_model=CompareResponse)
async def ask_question_compare(request: QuestionRequest):
    """
    Ask a natural language question and get answers from BOTH LLM
    providers side by side (USER: read-only), for per-query model
    comparison. Runs concurrently. Not persisted to chat_history/query_logs
    - this is a side, on-demand comparison, not part of the primary
    conversation thread (the regular /ask call already persisted that turn).
    """
    business_client = get_supabase_client()
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

    rows, _, _ = app_client.execute_read(
        """
        SELECT id, nl_query, sql_generated, status, reject_reason, exec_time_ms, created_at
        FROM query_logs
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (user_id, limit)
    )

    return {
        "logs": [
            {
                "id": str(row["id"]),
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
    app_client = get_app_db_client()
    try:
        rows, _, _ = app_client.execute_read(
            "SELECT id, title, content, session_id as \"sessionId\", last_modified as \"lastModified\" "
            "FROM user_notes WHERE user_id = %s ORDER BY last_modified DESC",
            (user_id,)
        )
        return {"notes": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/notes")
async def save_user_note(request: NoteRequest):
    """Upsert (Insert or Update) a user note/observation."""
    app_client = get_app_db_client()
    try:
        # Check if user exists
        user_check, _, _ = app_client.execute_read(
            "SELECT id FROM users WHERE id = %s AND deleted_at IS NULL",
            (request.user_id,)
        )
        if not user_check:
            raise HTTPException(status_code=404, detail="User account not found")

        # Perform Upsert using PostgreSQL INSERT ... ON CONFLICT
        app_client.execute_write(
            """
            INSERT INTO user_notes (id, user_id, title, content, session_id, last_modified)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                session_id = EXCLUDED.session_id,
                last_modified = EXCLUDED.last_modified
            RETURNING id
            """,
            (request.id, request.user_id, request.title, request.content, request.session_id, request.last_modified)
        )
        return {"status": "success", "note_id": request.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/notes/{note_id}")
async def delete_user_note(note_id: str, user_id: str):
    """Delete a user note/observation."""
    app_client = get_app_db_client()
    try:
        rows, count, _ = app_client.execute_write(
            "DELETE FROM user_notes WHERE id = %s AND user_id = %s RETURNING id",
            (note_id, user_id)
        )
        if count == 0:
            raise HTTPException(status_code=404, detail="Note not found or does not belong to you")
        return {"status": "success", "message": "Note deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


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
    app_client = get_app_db_client()
    try:
        rows, _, _ = app_client.execute_read(
            "SELECT id, title, created_at as \"createdAt\" "
            "FROM chat_sessions WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,)
        )
        return {"sessions": [{**row, "id": str(row["id"]), "createdAt": int(row["createdAt"].timestamp() * 1000)} for row in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/sessions")
async def create_user_session(request: CreateSessionRequest):
    """Register or save a new chat session in the database."""
    app_client = get_app_db_client()
    try:
        app_client.execute_write(
            "INSERT INTO chat_sessions (id, user_id, title) VALUES (%s, %s, %s) "
            "ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title RETURNING id",
            (request.id, request.user_id, request.title)
        )
        return {"status": "success", "session_id": request.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/sessions/rename")
async def rename_user_session(request: RenameSessionRequest):
    """Rename an existing chat session."""
    app_client = get_app_db_client()
    try:
        rows, count, _ = app_client.execute_write(
            "UPDATE chat_sessions SET title = %s WHERE id = %s AND user_id = %s RETURNING id",
            (request.title, request.id, request.user_id)
        )
        if count == 0:
            raise HTTPException(status_code=404, detail="Session not found or does not belong to you")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_user_session(session_id: str, user_id: str):
    """Delete a chat session and all its messages."""
    app_client = get_app_db_client()
    try:
        # First delete messages
        app_client.execute_write(
            "DELETE FROM chat_messages WHERE session_id = %s",
            (session_id,)
        )
        rows, count, _ = app_client.execute_write(
            "DELETE FROM chat_sessions WHERE id = %s AND user_id = %s RETURNING id",
            (session_id, user_id)
        )
        if count == 0:
            raise HTTPException(status_code=404, detail="Session not found or does not belong to you")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, user_id: str):
    """Retrieve formatted message history for a chat session."""
    import json
    app_client = get_app_db_client()
    
    # Verify session ownership
    sess_check, _, _ = app_client.execute_read(
        "SELECT id FROM chat_sessions WHERE id = %s AND user_id = %s",
        (session_id, user_id)
    )
    if not sess_check:
        raise HTTPException(status_code=404, detail="Session not found or does not belong to you")

    try:
        rows, _, _ = app_client.execute_read(
            "SELECT id, role, content as text, sql_generated as sql, result_json, chart_type, needs_clarification, created_at as timestamp "
            "FROM chat_messages WHERE session_id = %s ORDER BY created_at ASC",
            (session_id,)
        )
        
        formatted = []
        for r in rows:
            res_json = r.get("result_json")
            if isinstance(res_json, str):
                try:
                    res_json = json.loads(res_json)
                except:
                    res_json = None
            
            # Format preview if rows exist
            result_preview = None
            if res_json and isinstance(res_json, list) and len(res_json) > 0:
                cols = list(res_json[0].keys()) if isinstance(res_json[0], dict) else []
                result_preview = {"columns": cols, "rows": res_json}
            
            # Setup chartData if type is specified
            chart_data = None
            if r.get("chart_type") and res_json:
                chart_data = {"type": r["chart_type"], "data": res_json}

            status = "Success"
            if r["role"] == "assistant" and not r["sql"] and not r["needs_clarification"] and "error" in r["text"].lower():
                status = "Failed"

            formatted.append({
                "id": str(r["id"]),
                "sender": "user" if r["role"] == "user" else "ai",
                "text": r["text"],
                "timestamp": int(r["timestamp"].timestamp() * 1000),
                "status": status,
                "sql": r["sql"],
                "isClarification": r["needs_clarification"],
                "clarificationOptions": res_json if r["needs_clarification"] else None,
                "resultPreview": result_preview,
                "chartData": chart_data
            })
            
        return {"messages": formatted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
