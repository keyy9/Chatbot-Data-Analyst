"""
Configuration module for AI/LLM Core.

Handles environment variables, API keys, and system settings.
Supports both development and production environments.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Uses pydantic-settings for validation and type safety.
    All fields have sensible defaults for local development.
    """

    # ============ Groq Configuration ============
    groq_api_key: str = Field(
        default="gsk-test-dummy-key-for-development",
        alias="GROQ_API_KEY"
    )
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    groq_temperature: float = Field(default=0.3, alias="GROQ_TEMPERATURE")
    groq_max_tokens: int = Field(default=1024, alias="GROQ_MAX_TOKENS")

    # ============ Gemini Configuration ============
    # Second LLM provider (user-selectable alongside Groq), via Gemini's
    # OpenAI-compatible endpoint.
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-flash-lite-latest", alias="GEMINI_MODEL")
    gemini_temperature: float = Field(default=0.3, alias="GEMINI_TEMPERATURE")
    gemini_max_tokens: int = Field(default=1024, alias="GEMINI_MAX_TOKENS")

    # ============ Database Configuration ============
    # The business/target database - the data users ask questions about
    # (schema introspection + NL-to-SQL query execution).
    database_url: str = Field(
        default="sqlite:///:memory:",  # placeholder for local dev without a real DB
        alias="DATABASE_URL"
    )
    database_schema: str = Field(default="public", alias="DATABASE_SCHEMA")

    # The app's own control-plane database - users, chat history, query
    # logs, system prompts, benchmark/eval tables, admin audit logs. A
    # separate Supabase project from the business database above.
    app_database_url: str = Field(default="", alias="APP_DATABASE_URL")
    
    # ============ Application Configuration ============
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_name: str = Field(default="AI Data Analyst", alias="APP_NAME")
    
    # ============ Logging Configuration ============
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, alias="LOG_FILE")
    
    # ============ SQL Guardrails ============
    enable_sql_validation: bool = Field(default=True, alias="ENABLE_SQL_VALIDATION")
    max_query_timeout: int = Field(default=30, alias="MAX_QUERY_TIMEOUT")  # seconds
    
    # ============ LLM Behavior ============
    enable_clarification: bool = Field(default=True, alias="ENABLE_CLARIFICATION")
    clarification_threshold: float = Field(default=0.6, alias="CLARIFICATION_THRESHOLD")
    
    # ============ Monitoring ============
    enable_monitoring: bool = Field(default=True, alias="ENABLE_MONITORING")
    monitoring_db_url: Optional[str] = Field(default=None, alias="MONITORING_DB_URL")
    
    # ============ Supabase Configuration ============
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_key: str = Field(default="", alias="SUPABASE_KEY")
    supabase_enabled: bool = Field(default=False, alias="SUPABASE_ENABLED")
    
    # ============ Query Execution ============
    max_query_rows: int = Field(default=10000, alias="MAX_QUERY_ROWS")
    query_timeout_seconds: int = Field(default=30, alias="QUERY_TIMEOUT_SECONDS")

    # ============ Email (OTP + password reset) ============
    smtp_host: str = Field(default="smtp.gmail.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# ============ Singleton Instance ============
settings = Settings()


# ============ Validation Functions ============
def validate_config() -> bool:
    """
    Validate critical configuration settings.
    
    Returns:
        bool: True if all critical settings are valid.
        
    Raises:
        ValueError: If critical settings are missing or invalid.
    """
    # Skip API key validation untuk development
    if is_production():
        if not settings.groq_api_key or "dummy" in settings.groq_api_key.lower():
            raise ValueError(
                "GROQ_API_KEY must be set properly in production"
            )

    # Database validation
    if not settings.database_url:
        raise ValueError("DATABASE_URL is not set")

    if settings.groq_temperature < 0 or settings.groq_temperature > 2:
        raise ValueError("GROQ_TEMPERATURE must be between 0 and 2")

    if settings.groq_max_tokens < 100 or settings.groq_max_tokens > 8192:
        raise ValueError("GROQ_MAX_TOKENS must be between 100 and 8192")

    return True


def get_settings() -> Settings:
    """
    Get the global settings instance.
    
    Returns:
        Settings: The validated settings instance.
    """
    return settings


def get_environment() -> str:
    """
    Get the current application environment.
    
    Returns:
        str: Environment name (development, staging, production).
    """
    return settings.app_env.lower()


def is_production() -> bool:
    """
    Check if running in production.
    
    Returns:
        bool: True if environment is production.
    """
    return get_environment() == "production"


def is_development() -> bool:
    """
    Check if running in development.
    
    Returns:
        bool: True if environment is development.
    """
    return get_environment() == "development"


def get_config_status() -> dict:
    """
    Get current configuration status.
    
    Useful untuk debugging config issues.
    
    Returns:
        dict: Config status and loaded values.
    """
    return {
        "environment": get_environment(),
        "app_name": settings.app_name,
        "app_debug": settings.app_debug,
        "database_url": settings.database_url[:30] + "..." if settings.database_url else "Not set",
        "groq_model": settings.groq_model,
        "groq_api_key": "Set (dummy)" if "dummy" in settings.groq_api_key else "Set (actual)",
        "gemini_model": settings.gemini_model,
        "gemini_api_key": "Set" if settings.gemini_api_key else "Not set",
        "supabase_enabled": settings.supabase_enabled,
        "monitoring_enabled": settings.enable_monitoring,
        "sql_validation_enabled": settings.enable_sql_validation
    }