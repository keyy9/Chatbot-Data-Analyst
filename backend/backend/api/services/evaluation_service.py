"""
Evaluation results service.

Reads what the CLI eval scripts already persisted - `eval_runs` /
`eval_results` for the SQL-correctness benchmark, `pipeline_eval_runs` /
`pipeline_eval_results` for the routing-classification eval - plus the
`benchmark_questions` catalogue those runs are scored against.

Nothing here starts a run: a run makes real, rate-limited LLM calls and takes
minutes, so it stays a deliberate CLI action rather than something a page load
can trigger.
"""

import json
import logging
from typing import Any, Dict, List

from backend.ai.utils.supabase_client import get_app_db_client
from backend.ai.utils.timestamps import to_utc_iso
from backend.api.services.errors import ServiceError

logger = logging.getLogger(__name__)

# The dashboard's accuracy trend expects a latency figure per run, but runs
# don't record one yet - see get_benchmark_history.
PLACEHOLDER_RUN_LATENCY_MS = 1200


def get_latest_benchmark_run() -> Dict[str, Any]:
    """
    Return the most recent SQL-correctness run with its per-question detail.

    Raises:
        ServiceError: 404 when no run has been recorded yet.
    """
    client = get_app_db_client()

    runs, _, _ = client.execute_read(
        "SELECT id, total_questions, correct, partial, wrong, accuracy_score, run_at "
        "FROM eval_runs ORDER BY run_at DESC LIMIT 1"
    )
    if not runs:
        raise ServiceError(
            404,
            "No benchmark evaluation runs found yet. "
            "Run backend.ai.evaluation.run_benchmark first."
        )

    run = runs[0]

    results, _, _ = client.execute_read(
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
        "run_at": to_utc_iso(run["run_at"]),
        "total_questions": run["total_questions"],
        "correct": run["correct"],
        "partial": run["partial"],
        "wrong": run["wrong"],
        "accuracy_score": run["accuracy_score"],
        "results": results,
    }


def get_benchmark_history() -> List[Dict[str, Any]]:
    """
    Return every benchmark run oldest-first, for the accuracy trend chart.

    `avgResponseTimeMs` is a placeholder: `eval_runs` doesn't record a latency
    per run, so this reports a constant rather than a measured figure. Treat it
    as a layout filler, not data.
    """
    client = get_app_db_client()

    runs, _, _ = client.execute_read(
        "SELECT id, total_questions, correct, partial, wrong, accuracy_score, run_at "
        "FROM eval_runs ORDER BY run_at ASC"
    )

    return [
        {
            "runId": f"RUN-{str(run['id'])[:8].upper()}",
            "accuracy": round(run["accuracy_score"] * 100, 1),
            "timestamp": run["run_at"].strftime("%b %d, %Y %H:%M"),
            "avgResponseTimeMs": PLACEHOLDER_RUN_LATENCY_MS,
        }
        for run in runs
    ]


def compare_providers() -> List[Dict[str, Any]]:
    """
    Return the newest benchmark run for each provider, for a side-by-side view.

    Every run scores the same questions against the same gold SQL with the same
    comparator, so the accuracies are directly comparable - only the model that
    wrote the SQL differs.

    Accuracy alone doesn't settle the choice, so cost, tokens and latency come
    with it: a model two points more accurate at four times the cost is a
    different decision. Runs recorded before providers were tracked have a NULL
    provider and are left out rather than attributed to a guess.
    """
    client = get_app_db_client()

    rows, _, _ = client.execute_read(
        """
        SELECT DISTINCT ON (model_provider)
            model_provider, model_name, total_questions, correct, partial, wrong,
            accuracy_score, input_tokens, output_tokens, estimated_cost,
            avg_latency_ms, run_at
        FROM eval_runs
        WHERE model_provider IS NOT NULL
        ORDER BY model_provider, run_at DESC
        """
    )

    return [
        {
            "model_provider": r["model_provider"],
            "model_name": r["model_name"],
            "run_at": to_utc_iso(r["run_at"]),
            "total_questions": r["total_questions"],
            "correct": r["correct"],
            "partial": r["partial"],
            "wrong": r["wrong"],
            "accuracy_score": float(r["accuracy_score"] or 0),
            "input_tokens": int(r["input_tokens"] or 0),
            "output_tokens": int(r["output_tokens"] or 0),
            "total_tokens": int((r["input_tokens"] or 0) + (r["output_tokens"] or 0)),
            "estimated_cost": float(r["estimated_cost"] or 0),
            "avg_latency_ms": int(r["avg_latency_ms"] or 0),
        }
        for r in rows
    ]


def list_benchmark_questions() -> List[Dict[str, Any]]:
    """List the active persisted benchmark cases."""
    client = get_app_db_client()

    rows, _, _ = client.execute_read(
        "SELECT id, question, gold_sql, gold_answer, category, created_at "
        "FROM benchmark_questions WHERE is_active = true ORDER BY created_at DESC"
    )
    return [
        {**row, "id": str(row["id"]), "created_at": to_utc_iso(row["created_at"])}
        for row in rows
    ]


def add_benchmark_question(question: str, gold_sql: str, gold_answer: str,
                           category: str) -> Dict[str, Any]:
    """
    Persist one benchmark case.

    Raises:
        ServiceError: 400 when the question or expected SQL is missing, or the
            expected SQL isn't a read-only SELECT - a gold query that writes
            would mutate the business database every time the benchmark runs.
    """
    question = question.strip()
    gold_sql = gold_sql.strip()

    if not question or not gold_sql:
        raise ServiceError(400, "Question and expected SQL are required")
    if not gold_sql.upper().startswith("SELECT"):
        raise ServiceError(400, "Expected SQL must be a read-only SELECT statement")

    client = get_app_db_client()
    rows, _, _ = client.execute_write(
        """
        INSERT INTO benchmark_questions
          (question, gold_sql, gold_answer, category, expected_outcome, is_active)
        VALUES (%s, %s, %s, %s, 'success', true)
        RETURNING id, question, gold_sql, gold_answer, category, created_at
        """,
        (question, gold_sql, gold_answer.strip(), category.strip() or "custom")
    )
    row = rows[0]

    return {
        "id": str(row["id"]),
        "question": row["question"],
        "gold_sql": row["gold_sql"],
        "gold_answer": row["gold_answer"],
        "category": row["category"],
        "created_at": to_utc_iso(row["created_at"]),
    }


def get_latest_pipeline_run() -> Dict[str, Any]:
    """
    Return the most recent routing-classification run with per-question detail.

    Raises:
        ServiceError: 404 when no run has been recorded yet.
    """
    client = get_app_db_client()

    runs, _, _ = client.execute_read(
        "SELECT id, total_questions, accuracy, metrics_json, run_at "
        "FROM pipeline_eval_runs ORDER BY run_at DESC LIMIT 1"
    )
    if not runs:
        raise ServiceError(
            404,
            "No pipeline evaluation runs found yet. "
            "Run backend.ai.evaluation.run_pipeline_eval first."
        )

    run = runs[0]

    results, _, _ = client.execute_read(
        "SELECT question, expected_outcome, actual_outcome, detail "
        "FROM pipeline_eval_results WHERE eval_run_id = %s ORDER BY created_at",
        (run["id"],)
    )

    return {
        "eval_run_id": str(run["id"]),
        "run_at": to_utc_iso(run["run_at"]),
        "total_questions": run["total_questions"],
        "accuracy": run["accuracy"],
        "metrics": json.loads(run["metrics_json"]),
        "results": results,
    }
