"""
Pipeline Routing Evaluation Runner.

Runs every active question in `benchmark_questions` through the actual
read-only NL pipeline (same code path as `/api/user/ask`) and checks
whether it routes to the *expected* outcome: "success" (answered),
"clarification" (ambiguity correctly detected), or "blocked" (a
write/injection/off-schema attempt correctly refused). Scores the run
with a confusion matrix + precision/recall/F1 (`pipeline_metrics.py`)
and persists both the summary (`pipeline_eval_runs`) and per-question
detail (`pipeline_eval_results`).

This is a routing-classification eval, distinct from `run_benchmark.py`
(which scores SQL *correctness* against a gold answer for
"success"-only questions).

Usage:
    python -m backend.ai.evaluation.run_pipeline_eval [--admin-id UUID] [--limit N]
"""

import argparse
import json
import logging
import time

from backend.ai import initialize_ai_core
from backend.ai.llm.generator import get_sql_generator
from backend.ai.rbac.roles import Role
from backend.ai.rbac.access_control import UserContext
from backend.ai.validators.sql_guard_rbac import get_sql_guard_rbac
from backend.ai.evaluation.pipeline_metrics import compute_classification_metrics
from backend.ai.utils.supabase_client import get_supabase_client, get_app_db_client
from backend.ai.utils.supabase_schema_loader import get_supabase_schema_loader
from backend.ai.utils.supabase_executor import get_supabase_query_executor

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

LABELS = ["success", "clarification", "blocked"]


def _classify_actual_outcome(
    question: str,
    schema_definition: str,
    sql_generator,
    query_executor,
    sql_guard_rbac,
    user_context: UserContext
) -> tuple:
    """
    Run one question through the real read-only pipeline and classify
    the actual outcome the same way `/api/user/ask` would resolve it.

    Returns:
        Tuple[str, str]: (outcome, detail)
    """
    sql_result = sql_generator.generate(question, schema_definition, check_ambiguity=True)

    if sql_result.is_ambiguous:
        return "clarification", f"ambiguity_type={sql_result.ambiguity_type}"

    if not sql_result.is_valid or not sql_result.sql:
        return "blocked", f"generation_rejected: {sql_result.error_message}"

    validation = sql_guard_rbac.validate_with_rbac(sql_result.sql, user_context)
    if not validation["is_valid"]:
        return "blocked", f"guard_rejected: {validation['error']}"

    try:
        data, columns, _ = query_executor.execute(sql_result.sql)
        return "success", f"{len(data)} row(s) returned"
    except Exception as e:
        return "blocked", f"execution_failed: {str(e)}"


def run_pipeline_eval(admin_id: str = None, limit: int = None) -> dict:
    """
    Run the routing-classification eval suite and persist results.

    Args:
        admin_id: User id to attribute this run to (nullable).
        limit: Optional cap on number of questions run.

    Returns:
        dict: Summary of the run (matches `compute_classification_metrics` shape).
    """
    initialize_ai_core()

    business_client = get_supabase_client()
    app_client = get_app_db_client()

    schema_loader = get_supabase_schema_loader(business_client)
    query_executor = get_supabase_query_executor(business_client)
    sql_generator = get_sql_generator()
    sql_guard_rbac = get_sql_guard_rbac()

    schema_definition = schema_loader.get_schema_definition()

    user_context = UserContext(user_id=admin_id or "pipeline-eval", role=Role.USER, session_id="pipeline-eval")

    questions, _, _ = app_client.execute_query(
        "SELECT id, question, expected_outcome FROM benchmark_questions "
        "WHERE is_active = true ORDER BY created_at"
    )

    if limit:
        questions = questions[:limit]

    if not questions:
        print("No active benchmark questions found.")
        return {"total_questions": 0}

    pairs = []
    result_rows = []

    for i, q in enumerate(questions):
        if i > 0:
            time.sleep(2.5)  # stay under Groq free-tier rate limits across a long run

        expected = q.get("expected_outcome") or "success"

        try:
            actual, detail = _classify_actual_outcome(
                q["question"], schema_definition, sql_generator,
                query_executor, sql_guard_rbac, user_context
            )
        except Exception as e:
            actual, detail = "blocked", f"unexpected_error: {str(e)}"

        pairs.append((expected, actual))
        result_rows.append({
            "question_id": q["id"],
            "question": q["question"],
            "expected_outcome": expected,
            "actual_outcome": actual,
            "detail": detail
        })

        match = "OK  " if expected == actual else "MISS"
        print(f"[{match}] expected={expected:14} actual={actual:14} | {q['question']}")

    metrics = compute_classification_metrics(pairs, LABELS)

    run_data, _, _ = app_client.execute_write(
        """
        INSERT INTO pipeline_eval_runs (admin_id, total_questions, accuracy, metrics_json)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (admin_id, metrics["total"], metrics["accuracy"], json.dumps(metrics))
    )
    eval_run_id = run_data[0]["id"]

    for row in result_rows:
        app_client.execute_write(
            """
            INSERT INTO pipeline_eval_results
                (eval_run_id, question_id, question, expected_outcome, actual_outcome, detail)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (eval_run_id, row["question_id"], row["question"], row["expected_outcome"], row["actual_outcome"], row["detail"])
        )

    print("\n" + "=" * 70)
    print(f"Total: {metrics['total']}  Accuracy: {metrics['accuracy']:.2%}")
    print("\nConfusion matrix (rows=expected, cols=actual):")
    header = "expected \\ actual".ljust(18) + "".join(l.ljust(16) for l in LABELS)
    print(header)
    for expected in LABELS:
        row = expected.ljust(18) + "".join(str(metrics["confusion_matrix"][expected][actual]).ljust(16) for actual in LABELS)
        print(row)
    print("\nPer-class precision / recall / F1:")
    for label, c in metrics["per_class"].items():
        print(f"  {label:14} precision={c['precision']:.2%}  recall={c['recall']:.2%}  f1={c['f1']:.2%}  support={c['support']}")
    print(f"\nMacro avg: precision={metrics['macro_avg']['precision']:.2%}  "
          f"recall={metrics['macro_avg']['recall']:.2%}  f1={metrics['macro_avg']['f1']:.2%}")
    print("=" * 70)

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the NL pipeline routing-classification eval suite.")
    parser.add_argument("--admin-id", default=None, help="User id to attribute this run to.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions run.")
    args = parser.parse_args()

    run_pipeline_eval(admin_id=args.admin_id, limit=args.limit)
