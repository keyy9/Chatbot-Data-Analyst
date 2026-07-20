"""
Evaluation Results Routes.

Read-only endpoints that surface the results of eval runs already
persisted by the CLI scripts (`run_benchmark.py`, `run_pipeline_eval.py`).
These endpoints never trigger a run themselves - a run makes real LLM
calls against a rate-limited API and can take several minutes, so it
stays a deliberate CLI action, not something a page load can kick off.
"""

import json

from fastapi import APIRouter, HTTPException

from backend.ai.rbac.roles import Role
from backend.ai.rbac.access_control import UserContext
from backend.ai.rbac.user_lookup import verify_role
from backend.ai.utils.supabase_client import get_app_db_client

router = APIRouter(prefix="/api/admin/pipeline-eval", tags=["Evaluation"])


def _require_admin(app_client, user_id: str) -> UserContext:
    verify_role(app_client, user_id, allowed_roles=("admin",), hard=True)
    return UserContext(user_id=user_id, role=Role.ADMIN, session_id="pipeline-eval-view")


@router.get("/latest")
async def get_latest_pipeline_eval(user_id: str):
    """Get the most recent pipeline routing-classification eval run, with per-question detail."""
    app_client = get_app_db_client()

    try:
        _require_admin(app_client, user_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    runs, _, _ = app_client.execute_read(
        "SELECT id, total_questions, accuracy, metrics_json, run_at "
        "FROM pipeline_eval_runs ORDER BY run_at DESC LIMIT 1"
    )

    if not runs:
        raise HTTPException(status_code=404, detail="No pipeline evaluation runs found yet. Run backend.ai.evaluation.run_pipeline_eval first.")

    run = runs[0]

    results, _, _ = app_client.execute_read(
        "SELECT question, expected_outcome, actual_outcome, detail "
        "FROM pipeline_eval_results WHERE eval_run_id = %s ORDER BY created_at",
        (run["id"],)
    )

    return {
        "eval_run_id": str(run["id"]),
        "run_at": run["run_at"].isoformat(),
        "total_questions": run["total_questions"],
        "accuracy": run["accuracy"],
        "metrics": json.loads(run["metrics_json"]),
        "results": results
    }
