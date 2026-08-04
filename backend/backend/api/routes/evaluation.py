"""
Evaluation Results Routes.

Read-only endpoints that surface the results of eval runs already
persisted by the CLI scripts (`run_benchmark.py`, `run_pipeline_eval.py`).
These endpoints never trigger a run themselves - a run makes real LLM
calls against a rate-limited API and can take several minutes, so it
stays a deliberate CLI action, not something a page load can kick off.
"""

from fastapi import APIRouter

from backend.api.dependencies import require_admin
from backend.api.services import evaluation_service

router = APIRouter(prefix="/api/admin/pipeline-eval", tags=["Evaluation"])


@router.get("/latest")
async def get_latest_pipeline_eval(user_id: str):
    """Get the most recent pipeline routing-classification eval run, with per-question detail."""
    require_admin(user_id)
    return evaluation_service.get_latest_pipeline_run()
