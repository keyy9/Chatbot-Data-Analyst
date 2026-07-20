"""
Schema/Meta Routes.

Read-only schema introspection endpoints, useful for a frontend's
"show me the schema" / "what tables can I ask about" panel. The actual
ask-a-question endpoint lives in `user_questions.py` - this router does
not duplicate it.
"""

from fastapi import APIRouter, HTTPException

from backend.ai.config import get_settings
from backend.ai.utils.supabase_schema_loader import get_supabase_schema_loader

router = APIRouter(prefix="/api", tags=["Schema"])


@router.get("/schema")
async def get_schema():
    """Get the full database schema definition (as injected into prompts)."""
    settings = get_settings()
    if not settings.supabase_enabled:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    schema_loader = get_supabase_schema_loader()

    return {
        "schema": schema_loader.get_schema_definition(),
        "tables": schema_loader.get_available_tables()
    }


@router.get("/tables")
async def get_tables():
    """Get available tables and their columns."""
    settings = get_settings()
    if not settings.supabase_enabled:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    schema_loader = get_supabase_schema_loader()

    return {"tables": schema_loader.get_all_columns_by_table()}
